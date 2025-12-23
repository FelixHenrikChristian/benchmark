import subprocess
import re
import pandas as pd
import os
import time

# ================= 配置区域 (请根据实际情况修改) =================

CONFIG = {
    "global_steps": 1000,  # 全局测试步数
    
    # 测试场景列表 (文件名)
    "scenes": [
        "humanoid.xml",
        "8_humanoids.xml",
        "22_humanoids.xml", 
        "50_humanoids.xml", 
        "100_humanoids.xml", 
        "200_humanoids.xml",
        "300_humanoids.xml",
        "400_humanoids.xml",
        "500_humanoids.xml",
        # "8_humanoids.xml", # 在这里添加更多场景
    ],

    # 引擎配置
    # {scene} 会被替换为场景文件名
    # {steps} 会被替换为全局步数
    "engines": {
        "mujoco": {
            "enabled": True,
            # base_dir: 场景文件相对于执行目录的前缀路径
            "scene_prefix": "humanoid/sparse/", 
            # 执行命令模板
            "cmd_template": "mujoco/build/bin/testspeed {full_path} {steps}",
            # 是否需要特定的 shell 环境 (通常 False, 除非需要 source)
            "shell": False
        },
        "mjx": {
            "enabled": True,
            "scene_prefix": "mujoco_warp/benchmark/humanoid/",
            "cmd_template": "mjx-testspeed --mjcf {full_path} --base_path . --batch_size 1 --nstep {steps}",
            "shell": False
        },
        "mujoco_warp": {
            "enabled": True,
            "scene_prefix": "benchmark/humanoid/",
            # 注意: 如果需要 source activate，建议使用 shell=True 并用 && 连接，或者直接指定 venv 中的 python 路径
            "cmd_template": "source env/bin/activate && mjwarp-testspeed {full_path} --event_trace=True --nworld=1",
            "cwd": "mujoco_warp", # 切换工作目录
            "shell": True # 需要 shell 来处理 source
        },
        "cuda_mujoco": {
            "enabled": True,
            "scene_prefix": "humanoid/",
            "cmd_template": "cuda_mujoco/build/bin/testspeed_cuda {full_path} {steps}",
            "shell": False
        }
    }
}

# ================= 解析逻辑 =================

def parse_output(engine_name, stdout_text):
    """
    根据不同引擎的输出格式解析关键数据。
    返回字典: {Total Time (s), SPS, RTF, Time per Step (µs)}
    """
    data = {
        "Simulation Time (s)": None,
        "SPS": None,
        "RTF": None,
        "Time per Step (µs)": None
    }
    
    # 正则表达式模式
    patterns = {}
    
    if engine_name == "mujoco":
        patterns = {
            "Simulation Time (s)": r"Simulation time\s+:\s+([\d\.]+)\s+s",
            "SPS": r"Steps per second\s+:\s+([\d\.]+)",
            "RTF": r"Realtime factor\s+:\s+([\d\.]+)\s+x",
            "Time per Step (µs)": r"Time per step\s+:\s+([\d\.]+)\s+µs"
        }
    elif engine_name == "mjx":
        patterns = {
            "Simulation Time (s)": r"Total simulation time:\s+([\d\.]+)\s+s",
            "SPS": r"Total steps per second:\s+([\d\.]+)",
            "RTF": r"Total realtime factor:\s+([\d\.]+)\s+x",
            "Time per Step (µs)": r"Total time per step:\s+([\d\.]+)\s+µs"
        }
    elif engine_name == "mujoco_warp":
        patterns = {
            "Simulation Time (s)": r"Total simulation time:\s+([\d\.]+)\s+s",
            "SPS": r"Total steps per second:\s+([\d\.]+)",
            "RTF": r"Total realtime factor:\s+([\d\.]+)\s+x",
            # Warp 使用 ns (纳秒)
            "Time per Step (ns)": r"Total time per step:\s+([\d\.]+)\s+ns" 
        }
    elif engine_name == "cuda_mujoco":
        patterns = {
            "Simulation Time (s)": r"Total wall time\s+:\s+([\d\.]+)\s+s",
            "SPS": r"Steps per second\s+:\s+([\d\.]+)",
            "RTF": r"Realtime factor\s+:\s+([\d\.]+)\s+x",
            "Time per Step (µs)": r"Time per step\s+:\s+([\d\.]+)\s+µs"
        }

    # 执行正则匹配
    for key, pattern in patterns.items():
        match = re.search(pattern, stdout_text)
        if match:
            val = float(match.group(1))
            
            # 特殊处理 Warp 的单位转换 ns -> µs
            if key == "Time per Step (ns)":
                data["Time per Step (µs)"] = val / 1000.0
            else:
                data[key] = val

    return data

# ================= 主执行逻辑 =================

def run_benchmarks():
    summary_results = []
    detailed_logs = []
    
    print(f"🚀 开始执行测试，共 {len(CONFIG['scenes'])} 个场景...")
    
    for scene in CONFIG['scenes']:
        print(f"\n[Scenario] {scene}")
        
        for engine_name, engine_cfg in CONFIG['engines'].items():
            if not engine_cfg.get("enabled", True):
                continue
            
            # 构建路径
            prefix = engine_cfg.get("scene_prefix", "")
            full_path = os.path.join(prefix, scene)
            
            # 构建命令
            cmd = engine_cfg["cmd_template"].format(
                full_path=full_path, 
                steps=CONFIG["global_steps"],
                xml_path=full_path # 兼容不同命名习惯
            )
            
            cwd = engine_cfg.get("cwd", os.getcwd())
            use_shell = engine_cfg.get("shell", False)
            
            print(f"  -> Running {engine_name}...")
            # print(f"     CMD: {cmd}") # 调试用
            
            try:
                # 执行命令
                # 注意：shell=True 允许执行 source 等 shell 命令，但存在安全风险（此处忽略，因为是内网测试）
                if use_shell:
                    # 对于 mujoco_warp 这种需要 source 的情况，推荐用 bash -c
                    process = subprocess.run(
                        cmd, 
                        shell=True, 
                        executable='/bin/bash',
                        cwd=cwd,
                        stdout=subprocess.PIPE, 
                        stderr=subprocess.STDOUT, 
                        text=True
                    )
                else:
                    cmd_parts = cmd.split()
                    process = subprocess.run(
                        cmd_parts, 
                        cwd=cwd,
                        stdout=subprocess.PIPE, 
                        stderr=subprocess.STDOUT, 
                        text=True
                    )
                
                output = process.stdout
                
                # 解析数据
                metrics = parse_output(engine_name, output)
                
                # 汇总结果
                result_row = {
                    "Scene": scene,
                    "Engine": engine_name,
                    "Steps": CONFIG["global_steps"],
                    **metrics
                }
                summary_results.append(result_row)
                
                # 保存详细日志 (为了在 Excel 的第二个 Sheet 中查看详细 Profiling)
                detailed_logs.append({
                    "Scene": scene,
                    "Engine": engine_name,
                    "Raw Output": output
                })
                
                print(f"     Done. SPS: {metrics.get('SPS', 'N/A')}")

            except Exception as e:
                print(f"     ERROR: {e}")
                summary_results.append({
                    "Scene": scene,
                    "Engine": engine_name,
                    "Error": str(e)
                })

    return summary_results, detailed_logs

def save_to_excel(summary, logs, filename="benchmark_results.xlsx"):
    df_summary = pd.DataFrame(summary)
    df_logs = pd.DataFrame(logs)
    
    # 调整列顺序
    cols = ["Scene", "Engine", "Steps", "Simulation Time (s)", "SPS", "RTF", "Time per Step (µs)"]
    # 确保列存在
    existing_cols = [c for c in cols if c in df_summary.columns]
    df_summary = df_summary[existing_cols]

    with pd.ExcelWriter(filename, engine='openpyxl') as writer:
        df_summary.to_excel(writer, sheet_name='Summary', index=False)
        df_logs.to_excel(writer, sheet_name='Detailed_Logs', index=False)
    
    print(f"\n✅ 测试完成！结果已保存至: {filename}")

if __name__ == "__main__":
    summary_data, log_data = run_benchmarks()
    if summary_data:
        save_to_excel(summary_data, log_data)
    else:
        print("没有生成数据。")