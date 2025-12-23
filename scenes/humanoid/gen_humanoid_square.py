import os
import shutil

def generate_scenes_custom(
    grid_sides, 
    spacing=1.5, 
    folder_name="square", 
    base_model="humanoid.xml",
    use_dense_jacobian=False
):
    """
    生成 Humanoid 方阵场景的核心函数。
    """
    
    # --- 1. 环境准备 ---
    if not os.path.exists(base_model):
        print(f"错误：当前目录下找不到 {base_model}，请确保脚本和 xml 在同一位置。")
        return

    # 创建文件夹
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)
        print(f"\n>> 创建目录: {folder_name}")
    
    # 复制 base_model
    dst_model_path = os.path.join(folder_name, base_model)
    shutil.copy(base_model, dst_model_path)
    
    # --- 2. 确定配置 ---
    if use_dense_jacobian:
        option_str = '<option timestep="0.005" solver="CG" integrator="implicit" jacobian="dense"/>'
        mode_desc = "Dense (密集矩阵)"
    else:
        option_str = '<option timestep="0.005" solver="CG" integrator="implicit"/>'
        mode_desc = "Sparse (默认稀疏)"

    print(f"   模式: {mode_desc} | 正在生成场景...")

    # --- 3. 批量生成 ---
    for side_length in grid_sides:
        total_count = side_length * side_length
        filename = f"{total_count}_humanoid_square.xml"
        filepath = os.path.join(folder_name, filename)
        
        floor_half_width = (side_length * spacing) / 2 + 10
        offset = (side_length - 1) * spacing / 2.0

        xml_content = f"""<mujoco model="{total_count} Humanoids Square ({'Dense' if use_dense_jacobian else 'Sparse'})">
  
  {option_str}

  <asset>
    <texture type="skybox" builtin="gradient" rgb1=".3 .5 .7" rgb2="0 0 0" width="512" height="512"/>
    <texture name="floor" type="2d" builtin="checker" width="512" height="512" rgb1=".1 .2 .3" rgb2=".2 .3 .4"/>
    <material name="floor" texture="floor" texrepeat="1 1" texuniform="true" reflectance=".2"/>
    <model name="humanoid" file="{base_model}"/>
  </asset>

  <visual>
    <map force="0.1" zfar="100"/>
    <rgba haze="0.15 0.25 0.35 1"/>
    <quality shadowsize="4096"/>
    <global offwidth="1920" offheight="1080"/>
  </visual>

  <worldbody>
    <geom name="floor" size="{floor_half_width} {floor_half_width} .05" type="plane" material="floor" condim="3"/>
    <light directional="true" diffuse=".4 .4 .4" specular="0.1 0.1 0.1" pos="0 0 5" dir="0 0 -1" castshadow="false"/>
    <light name="spotlight" mode="targetbodycom" target="world" diffuse="1 1 1" specular="0.3 0.3 0.3" pos="0 0 10" cutoff="60"/>

"""
        for row in range(side_length):
            for col in range(side_length):
                x = row * spacing - offset
                y = col * spacing - offset
                index = row * side_length + col
                
                block = f"""    <frame pos="{x:.4f} {y:.4f} 0">
      <attach model="humanoid" body="torso" prefix="u{index}_"/>
    </frame>
"""
                xml_content += block

        xml_content += """  </worldbody>
</mujoco>
"""
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(xml_content)
        
    print(f"   -> 完成。所有文件已保存至 {folder_name}/")

# ==========================================
# 主程序：自动生成两套数据
# ==========================================

# 1. 配置基础参数
SIDES = [3, 5, 8, 10, 15, 18, 20, 24] # 对应数量: 9, 25, 64, 100, 225, 324, 400, 576
SPACING = 0.75
BASE_FOLDER_NAME = "square"

print("=== 开始批量生成任务 ===")

# 2. 任务一：生成 Sparse (稀疏) 版本
# 结果文件夹: square_sparse
generate_scenes_custom(
    grid_sides=SIDES, 
    spacing=SPACING, 
    folder_name=f"{BASE_FOLDER_NAME}_sparse", 
    base_model="humanoid.xml",
    use_dense_jacobian=False
)

# 3. 任务二：生成 Dense (密集) 版本
# 结果文件夹: square_dense
generate_scenes_custom(
    grid_sides=SIDES, 
    spacing=SPACING, 
    folder_name=f"{BASE_FOLDER_NAME}_dense", 
    base_model="humanoid.xml",
    use_dense_jacobian=True
)

print("\n=== 全部任务完成 ===")
print(f"1. 稀疏矩阵场景位于: {BASE_FOLDER_NAME}_sparse/")
print(f"2. 密集矩阵场景位于: {BASE_FOLDER_NAME}_dense/")