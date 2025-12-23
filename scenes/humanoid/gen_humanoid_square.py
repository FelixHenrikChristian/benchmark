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
    生成 Humanoid 方阵场景。
    
    参数:
    - use_dense_jacobian: True 则在 option 中添加 jacobian="dense"，False 则去掉。
    """
    
    # --- 1. 环境准备 ---
    if not os.path.exists(base_model):
        print(f"错误：当前目录下找不到 {base_model}，请确保脚本和 xml 在同一位置。")
        return

    # 这里的文件夹名字可以根据配置自动变一下，方便区分？
    # 或者就保持 'square'，由用户自己决定。这里为了简单，依然使用传入的 folder_name。
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)
        print(f"已创建文件夹: {folder_name}")
    
    # 复制 base_model
    dst_model_path = os.path.join(folder_name, base_model)
    shutil.copy(base_model, dst_model_path)
    print(f"已复制 {base_model} 到目标目录")

    # --- 2. 构造 Option 字符串 ---
    # 根据开关决定是否添加 jacobian="dense"
    if use_dense_jacobian:
        option_str = '<option timestep="0.005" solver="CG" integrator="implicit" jacobian="dense"/>'
        mode_desc = "Dense (密集矩阵)"
    else:
        # 去掉 jacobian="dense"，MuJoCo 默认使用 sparse
        option_str = '<option timestep="0.005" solver="CG" integrator="implicit"/>'
        mode_desc = "Sparse (稀疏矩阵 - 默认)"

    print(f"当前生成模式: {mode_desc}")

    # --- 3. 批量生成 ---
    for side_length in grid_sides:
        total_count = side_length * side_length
        
        # 也可以在文件名上加个标记方便区分，比如 9_humanoid_square_sparse.xml
        # 这里为了保持你原有的命名习惯，还是保持原样，或者你可以手动修改下面这行：
        filename = f"{total_count}_humanoid_square.xml"
        
        filepath = os.path.join(folder_name, filename)
        
        floor_half_width = (side_length * spacing) / 2 + 10
        offset = (side_length - 1) * spacing / 2.0

        # XML 内容
        xml_content = f"""<mujoco model="{total_count} Humanoids Square">
  
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
        # 循环生成 frame
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
        
        print(f"  -> 生成完毕: {filename}")

# ==========================================
# 配置参数
# ==========================================

# 1. 方阵边长列表
sides = [3, 5, 8, 10, 15, 18, 20, 24]

# 2. 是否使用 Dense Jacobian
# True  = 添加 jacobian="dense" (更精确但大场景慢)
# False = 不添加 (默认 Sparse，大场景更快)
USE_DENSE = True 

# 3. 输出文件夹名称
OUTPUT_FOLDER = "square" 

# 执行
generate_scenes_custom(
    sides, 
    spacing=1.5, 
    folder_name=OUTPUT_FOLDER, 
    use_dense_jacobian=USE_DENSE
)

print("\n所有操作完成！")