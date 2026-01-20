import subprocess
import re
import pandas as pd
import os
import time
from scene_converter import prepare_scenes_for_all_engines, DEFAULT_ENGINE_OPTIONS

# ================= 配置区域 =================

CONFIG = {
    "global_steps": 1000,
    "ctrlnoise": 0.0,
    "timeout_per_scene": 0,  # 每个场景限时（秒），设为 0 则不限时
    # "source_scene_dir": "cuda_mujoco/paper_experiments/model/g1_dense_flat",
    "source_scene_dir": "cuda_mujoco/paper_experiments/model/g1_terrian",
    "temp_dir": "temp",
    "output_file": "benchmark_results.xlsx",
    
    "engines": {
        "mujoco": {
            "enabled": True,
            "cmd_template": "mujoco/build/bin/testspeed {full_path} {steps} 1 {ctrlnoise}",
            "shell": False
        },
        "cuda_mujoco": {
            "enabled": True,
            "cmd_template": "cuda_mujoco/build/bin/01A_testspeed_single {full_path} {steps} 1 {ctrlnoise}",
            "shell": False
        },
        "mujoco_warp": {
            "enabled": True,
            "cmd_template": "source env/bin/activate && mjwarp-testspeed {full_path} --event_trace=True --nworld=1 --nstep={steps}",
            "cwd": "mujoco_warp",
            "shell": True 
        },
        "mjx": {
            "enabled": True,
            "cmd_template": "mjx-testspeed --mjcf {full_path} --base_path . --batch_size 1 --nstep {steps}",
            "shell": False
        },

    }
}

# ================= 辅助逻辑 =================

def truncate_overflow_logs(text):
    """
    针对 mujoco warp 的日志清洗：保留前5句和后5句 overflow 消息。
    """
    if not text: return ""
    lines = text.splitlines()
    pattern = re.compile(r"broadphase overflow - please increase nconmax to \d+ or naconmax to \d+")
    
    overflow_indices = [i for i, line in enumerate(lines) if pattern.search(line)]
    
    if len(overflow_indices) > 10:
        keep_start = set(overflow_indices[:5])
        keep_end = set(overflow_indices[-5:])
        
        new_lines = []
        has_inserted_ellipsis = False
        
        for i, line in enumerate(lines):
            if i in overflow_indices:
                if i in keep_start or i in keep_end:
                    new_lines.append(line)
                elif not has_inserted_ellipsis:
                    new_lines.append("... [此处省略若干条 broadphase overflow 消息] ...")
                    has_inserted_ellipsis = True
            else:
                new_lines.append(line)
        return "\n".join(new_lines)
    return text

def parse_output(engine_name, stdout_text):
    data = {"Simulation Time (s)": None, "SPS": None, "RTF": None, "Time per Step (µs)": None}
    if not stdout_text: return data
    
    patterns = {
        "mujoco": {
            "Simulation Time (s)": r"Simulation time\s+:\s+([\d\.]+)\s+s",
            "SPS": r"Steps per second\s+:\s+([\d\.]+)",
            "RTF": r"Realtime factor\s+:\s+([\d\.]+)\s+x",
            "Time per Step (µs)": r"Time per step\s+:\s+([\d\.]+)\s+µs"
        },
        "mjx": {
            "Simulation Time (s)": r"Total simulation time:\s+([\d\.]+)\s+s",
            "SPS": r"Total steps per second:\s+([\d\.]+)",
            "RTF": r"Total realtime factor:\s+([\d\.]+)\s+x",
            "Time per Step (µs)": r"Total time per step:\s+([\d\.]+)\s+µs"
        },
        "mujoco_warp": {
            "Simulation Time (s)": r"Total simulation time:\s+([\d\.]+)\s+s",
            "SPS": r"Total steps per second:\s+([\d\.]+)",
            "RTF": r"Total realtime factor:\s+([\d\.]+)\s+x",
            "Time per Step (ns)": r"Total time per step:\s+([\d\.]+)\s+ns" 
        },
        "cuda_mujoco": {
            "Simulation Time (s)": r"Total wall time\s+:\s+([\d\.]+)\s+s",
            "SPS": r"Steps per second\s+:\s+([\d\.]+)",
            "RTF": r"Realtime factor\s+:\s+([\d\.]+)\s+x",
            "Time per Step (µs)": r"Time per step\s+:\s+([\d\.]+)\s+µs"
        }
    }

    if engine_name in patterns:
        for key, pattern in patterns[engine_name].items():
            match = re.search(pattern, stdout_text)
            if match:
                val = float(match.group(1))
                if key == "Time per Step (ns)":
                    data["Time per Step (µs)"] = val / 1000.0
                else:
                    data[key] = val
    return data

def save_to_excel(summary, logs, filename):
    """测一个写一个，支持实时查看结果。"""
    if not summary: return
    df_summary = pd.DataFrame(summary)
    df_logs = pd.DataFrame(logs)
    cols = ["Scene", "Engine", "Steps", "Simulation Time (s)", "SPS", "RTF", "Time per Step (µs)", "Status"]
    existing_cols = [c for c in cols if c in df_summary.columns]
    remaining_cols = [c for c in df_summary.columns if c not in cols]
    df_summary = df_summary[existing_cols + remaining_cols]

    with pd.ExcelWriter(filename, engine='openpyxl') as writer:
        df_summary.to_excel(writer, sheet_name='Summary', index=False)
        df_logs.to_excel(writer, sheet_name='Detailed_Logs', index=False)

# ================= 主执行逻辑 =================

def run_benchmarks():
    summary_results = []
    detailed_logs = []
    
    enabled_engines = [name for name, cfg in CONFIG['engines'].items() if cfg.get("enabled", True)]
    engine_scene_dirs = prepare_scenes_for_all_engines(
        source_dir=CONFIG['source_scene_dir'],
        temp_dir=CONFIG['temp_dir'],
        enabled_engines=enabled_engines
    )
    
    timeout_val = CONFIG.get("timeout_per_scene", 0)
    if timeout_val <= 0: timeout_val = None

    for engine_name, engine_cfg in CONFIG['engines'].items():
        if not engine_cfg.get("enabled", True): continue
        
        print(f"\n[Engine] {engine_name}")
        base_cwd = engine_cfg.get("cwd", ".") 
        temp_scene_dir = engine_scene_dirs.get(engine_name)
        if not temp_scene_dir: continue
        
        scene_prefix = os.path.relpath(temp_scene_dir, base_cwd) if base_cwd != "." else temp_scene_dir
        
        def get_sort_key(filename):
            match = re.search(r'\d+', filename)
            return (int(match.group()), filename) if match else (-1, filename)

        files = sorted([f for f in os.listdir(temp_scene_dir) if f.endswith('.xml')], key=get_sort_key)

        for filename in files:
            scene_name_no_ext = os.path.splitext(filename)[0]
            print(f"    -> Testing Scene: {scene_name_no_ext}", end="", flush=True)
            
            full_path_for_cmd = os.path.join(scene_prefix, filename)
            cwd = engine_cfg.get("cwd", os.getcwd())
            use_shell = engine_cfg.get("shell", False)
            
            cmd_str = engine_cfg["cmd_template"].format(
                full_path=full_path_for_cmd, steps=CONFIG["global_steps"], ctrlnoise=CONFIG.get("ctrlnoise", 0.0)
            )
            
            # --- 修复核心：非 shell 模式必须使用列表 ---
            run_cmd = cmd_str if use_shell else cmd_str.split()
            
            output = ""
            status = "Success"
            try:
                process = subprocess.run(
                    run_cmd, 
                    shell=use_shell, 
                    executable='/bin/bash' if use_shell else None,
                    cwd=cwd, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.STDOUT, 
                    text=True, 
                    timeout=timeout_val
                )
                output = process.stdout
            except subprocess.TimeoutExpired as e:
                # 捕获已有的输出并标记超时
                output = e.stdout.decode() if isinstance(e.stdout, bytes) else (e.stdout or "")
                output += "\n--- TIMEOUT EXPIRED ---"
                status = "Timeout"
                print(" | ⏱️ TIMEOUT", end="")
            except Exception as e:
                output = str(e)
                status = "Error"
                print(f" | ❌ ERROR: {e}", end="")

            if engine_name == "mujoco_warp":
                output = truncate_overflow_logs(output)

            metrics = parse_output(engine_name, output)
            result_row = {
                "Scene": scene_name_no_ext, "Engine": engine_name, "Steps": CONFIG["global_steps"],
                **metrics, "Status": status
            }
            summary_results.append(result_row)
            detailed_logs.append({"Scene": scene_name_no_ext, "Engine": engine_name, "Raw Output": output})
            
            # 实时保存到文件
            save_to_excel(summary_results, detailed_logs, CONFIG["output_file"])
            print(f" | SPS: {metrics.get('SPS', 'N/A')}")

    print(f"\n✅ 测试全流程结束。结果已保存至 {CONFIG['output_file']}")

if __name__ == "__main__":
    run_benchmarks()