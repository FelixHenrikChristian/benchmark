# UR5E Multi-Robot Scenes

This directory contains multi-UR5E robot arm scenes for MuJoCo benchmarking.

## Directory Structure

```
robot_ur5e/
├── universal_robots_ur5e/   # Base model files (copied from mujoco_menagerie)
│   ├── ur5e.xml            # UR5E model definition
│   ├── scene.xml           # Original single-robot scene
│   └── assets/             # Mesh files (.obj)
└── square/                  # Multi-robot scenes in square grid layout
    ├── ur5e.xml            # Base model for attach mechanism
    ├── gen_ur5e_square.py   # Scene generator script
    └── *_ur5e_square.xml    # Generated multi-robot scenes
```

## Available Scenes

| File | Robot Count | Grid |
|------|-------------|------|
| `4_ur5e_square.xml` | 4 | 2×2 |
| `9_ur5e_square.xml` | 9 | 3×3 |
| `16_ur5e_square.xml` | 16 | 4×4 |
| `25_ur5e_square.xml` | 25 | 5×5 |
| `36_ur5e_square.xml` | 36 | 6×6 |
| `49_ur5e_square.xml` | 49 | 7×7 |
| `64_ur5e_square.xml` | 64 | 8×8 |
| `100_ur5e_square.xml` | 100 | 10×10 |

## Generating Custom Scenes

```bash
cd square
python gen_ur5e_square.py <count> [--spacing <meters>]
```

Example:
```bash
python gen_ur5e_square.py 144 --spacing 1.5  # 12×12 grid with 1.5m spacing
```
