import os
import shutil
import re
from typing import Dict, Optional, List, Any

# 各引擎的配置：分为 option (标签属性) 和 custom (子标签)
DEFAULT_ENGINE_OPTIONS = {
    "mujoco": {
        "option": {
            # "timestep": "0.005",
            "integrator": "implicitfast",
            "jacobian": None,
        }
    },
    "cuda_mujoco": {
        "option": {
            # "timestep": "0.005",
            "integrator": "implicitfast",
            "jacobian": None,
        }
    },
    "mjx": {
        "option": {
            # "timestep": "0.005",
            "integrator": "implicitfast",
            "jacobian": None,
        }
    },
    "mujoco_warp": {
        "option": {
            # "timestep": "0.005",
            "integrator": "implicitfast",
            "jacobian": None,
        },
        "custom": {
            "ls_parallel": "1" 
        }
    }
}

def modify_option_tag(xml_content: str, option_configs: Dict[str, Optional[str]]) -> str:
    """修改 <option> 标签属性。如果不存在则自动创建。"""
    if not option_configs:
        return xml_content
        
    # 1. 如果完全没有 <option> 标签，则自动插入一个
    if '<option' not in xml_content:
        # 构建属性字符串，过滤掉 None
        attr_str = " ".join([f'{k}="{v}"' for k, v in option_configs.items() if v is not None])
        if not attr_str:
            return xml_content
        
        new_tag = f'  <option {attr_str}/>'
        # 在 <mujoco> 根标签后插入
        if '<mujoco' in xml_content:
            xml_content = re.sub(r'(<mujoco[^>]*>)', r'\1\n' + new_tag, xml_content, count=1)
        else:
            xml_content = new_tag + "\n" + xml_content
        return xml_content

    # 2. 如果已存在标签，执行原有的正则替换逻辑
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
                # 如果标签内没有该属性，则添加进去
                option_tag = option_tag.replace('<option ', f'<option {attr_name}="{attr_value}" ', 1)
        return option_tag + '/>'
    
    return re.sub(option_pattern, replace_option, xml_content)

def modify_custom_section(xml_content: str, custom_configs: Dict[str, str]) -> str:
    """修改或添加 <custom> 块中的 <numeric> 标签。"""
    if not custom_configs:
        return xml_content

    if '<custom>' not in xml_content:
        if '</mujoco>' in xml_content:
            xml_content = xml_content.replace('</mujoco>', '  <custom>\n  </custom>\n</mujoco>')
        else:
            xml_content += '\n<custom>\n</custom>'

    for name, value in custom_configs.items():
        numeric_pattern = rf'<numeric\s+name="{name}"\s+data="[^"]*"\s*/>'
        new_numeric_tag = f'<numeric name="{name}" data="{value}"/>'
        
        if re.search(numeric_pattern, xml_content):
            xml_content = re.sub(numeric_pattern, new_numeric_tag, xml_content)
        else:
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
                    
                    if "option" in config:
                        content = modify_option_tag(content, config["option"])
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
    # SOURCE_DIR = "cuda_mujoco/paper_experiments/model/g1_dense_flat" 
    # SOURCE_DIR = "cuda_mujoco/paper_experiments/model/g1_terrian" 
    TEMP_DIR = "temp"               
    ENGINES_TO_GENERATE = ["mujoco", "mujoco_warp", "mjx", "cuda_mujoco"] 
    # --------------------

    print(f"🚀 开始单独生成场景文件进行测试...")
    
    result_dirs = prepare_scenes_for_all_engines(
        source_dir=SOURCE_DIR,
        temp_dir=TEMP_DIR,
        enabled_engines=ENGINES_TO_GENERATE,
        engine_options=DEFAULT_ENGINE_OPTIONS
    )
    
    print("✅ 生成完成！")
    for engine, path in result_dirs.items():
        print(f"   - {engine}: {os.path.abspath(path)}")