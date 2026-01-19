import os
import shutil
import re
from typing import Dict, Optional, List, Any

# 各引擎的配置：分为 option (标签属性) 和 custom (子标签)
DEFAULT_ENGINE_OPTIONS = {
    "mujoco": {
        "option": {
            "integrator": "implicitfast",
            "jacobian": None,
        }
    },
    "cuda_mujoco": {
        "option": {
            "integrator": "implicitfast",
            "jacobian": None,
        }
    },
    "mjx": {
        "option": {
            "integrator": "implicitfast",
            "jacobian": None,
        }
    },
    "mujoco_warp": {
        "option": {
            "integrator": "implicitfast",
            "jacobian": None,
        },
        "custom": {
            "ls_parallel": "1"  # 新增：针对 mujoco_warp 的并行配置
        }
    }
}

def modify_option_tag(xml_content: str, option_configs: Dict[str, Optional[str]]) -> str:
    """修改 <option> 标签属性"""
    if not option_configs:
        return xml_content
        
    option_pattern = r'(<option\s+[^>]*)/>'
    
    def replace_option(match):
        option_tag = match.group(1)
        for attr_name, attr_value in option_configs.items():
            attr_pattern = rf'{attr_name}="[^"]*"'
            if attr_value is None:
                option_tag = re.sub(rf'\s*{attr_pattern}', '', option_tag)
            elif re.search(attr_pattern, option_tag):
                option_tag = re.sub(attr_pattern, f'{attr_name}="{attr_value}"', option_tag)
            else:
                option_tag = option_tag.replace('<option ', f'<option {attr_name}="{attr_value}" ', 1)
        return option_tag + '/>'
    
    return re.sub(option_pattern, replace_option, xml_content)

def modify_custom_section(xml_content: str, custom_configs: Dict[str, str]) -> str:
    """
    修改或添加 <custom> 块中的 <numeric> 标签。
    格式：<numeric name="ls_parallel" data="1"/>
    """
    if not custom_configs:
        return xml_content

    # 1. 确保存在 <custom> 块
    if '<custom>' not in xml_content:
        # 如果没有 custom 块，就在 </mujoco> 之前插入一个
        if '</mujoco>' in xml_content:
            xml_content = xml_content.replace('</mujoco>', '  <custom>\n  </custom>\n</mujoco>')
        else:
            # 极简 XML 情况
            xml_content += '\n<custom>\n</custom>'

    for name, value in custom_configs.items():
        # 匹配已有的 <numeric name="xxx" ... />
        numeric_pattern = rf'<numeric\s+name="{name}"\s+data="[^"]*"\s*/>'
        new_numeric_tag = f'<numeric name="{name}" data="{value}"/>'
        
        if re.search(numeric_pattern, xml_content):
            # 替换已有项
            xml_content = re.sub(numeric_pattern, new_numeric_tag, xml_content)
        else:
            # 插入新项到 <custom> 块内
            xml_content = xml_content.replace('<custom>', f'<custom>\n    {new_numeric_tag}')

    return xml_content

def prepare_scenes_for_all_engines(
    source_dir: str,
    temp_dir: str,
    enabled_engines: List[str],
    engine_options: Dict[str, Dict] = None
) -> Dict[str, str]:
    """为所有启用的引擎准备场景文件"""
    if engine_options is None:
        engine_options = DEFAULT_ENGINE_OPTIONS
    
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    os.makedirs(temp_dir, exist_ok=True)
    
    print(f"📁 准备场景文件...")
    engine_scene_dirs = {}
    
    for engine_name in enabled_engines:
        if engine_name not in engine_options:
            continue
        
        engine_temp_dir = os.path.join(temp_dir, engine_name)
        shutil.copytree(source_dir, engine_temp_dir)
        
        config = engine_options[engine_name]
        xml_count = 0
        
        for root, _, files in os.walk(engine_temp_dir):
            for filename in files:
                if filename.endswith('.xml'):
                    filepath = os.path.join(root, filename)
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # 1. 修改 option
                    if "option" in config:
                        content = modify_option_tag(content, config["option"])
                    
                    # 2. 修改 custom (新增逻辑)
                    if "custom" in config:
                        content = modify_custom_section(content, config["custom"])
                    
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(content)
                    xml_count += 1
        
        print(f"   ✓ {engine_name}: 已处理 {xml_count} 个 XML 文件")
        engine_scene_dirs[engine_name] = engine_temp_dir
    
    return engine_scene_dirs

if __name__ == "__main__":
    # --- 自定义配置区域 ---
    SOURCE_DIR = "cuda_mujoco/paper_experiments/model/g1_dense_flat"  # 源场景文件路径
    TEMP_DIR = "temp_test_scenes"               # 生成的测试场景存放路径
    ENGINES_TO_GENERATE = ["mujoco", "mujoco_warp", "mjx", "cuda_mujoco"] 
    # --------------------

    print(f"🚀 开始单独生成场景文件进行测试...")
    
    # 调用准备函数
    result_dirs = prepare_scenes_for_all_engines(
        source_dir=SOURCE_DIR,
        temp_dir=TEMP_DIR,
        enabled_engines=ENGINES_TO_GENERATE,
        engine_options=DEFAULT_ENGINE_OPTIONS
    )
    
    print("✅ 生成完成！你可以前往以下目录查看生成的 XML 文件：")
    for engine, path in result_dirs.items():
        print(f"   - {engine}: {os.path.abspath(path)}")
        
    # 验证生成的 mujoco_warp 文件是否包含新的 custom 标签
    warp_xml_path = os.path.join(TEMP_DIR, "mujoco_warp")
    if os.path.exists(warp_xml_path):
        print(f"\n💡 提示：请检查 {warp_xml_path} 下的 XML，")
        print(f"   确认是否已包含 <numeric name=\"ls_parallel\" data=\"1\"/>")