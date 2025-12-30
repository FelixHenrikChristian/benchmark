#!/usr/bin/env python3
"""
Generate multi-UR5E robot scenes in square grid layout.
UR5E robots are placed on a grid with specified spacing.
"""

import argparse
from pathlib import Path

# UR5E reach is approximately 0.85m, so 1.2m spacing prevents collisions
DEFAULT_SPACING = 1.2

XML_HEADER = '''<mujoco model="{n} UR5E Robots Square">
  
  <option timestep="0.005" solver="CG" integrator="implicit"/>

  <asset>
    <texture type="skybox" builtin="gradient" rgb1=".3 .5 .7" rgb2="0 0 0" width="512" height="512"/>
    <texture name="floor" type="2d" builtin="checker" width="512" height="512" rgb1=".1 .2 .3" rgb2=".2 .3 .4"/>
    <material name="floor" texture="floor" texrepeat="1 1" texuniform="true" reflectance=".2"/>
    <model name="ur5e" file="ur5e.xml"/>
  </asset>

  <visual>
    <map force="0.1" zfar="100"/>
    <rgba haze="0.15 0.25 0.35 1"/>
    <quality shadowsize="4096"/>
    <global offwidth="1920" offheight="1080"/>
  </visual>

  <worldbody>
    <geom name="floor" size="{floor_size} {floor_size} .05" type="plane" material="floor" condim="3"/>
    <light directional="true" diffuse=".4 .4 .4" specular="0.1 0.1 0.1" pos="0 0 5" dir="0 0 -1" castshadow="false"/>
    <light name="spotlight" mode="targetbodycom" target="world" diffuse="1 1 1" specular="0.3 0.3 0.3" pos="0 0 10" cutoff="60"/>
'''

XML_FOOTER = '''  </worldbody>
</mujoco>
'''

FRAME_TEMPLATE = '''    <frame pos="{x:.4f} {y:.4f} 0">
      <attach model="ur5e" body="base" prefix="u{idx}_"/>
    </frame>
'''


def generate_square_positions(count: int, spacing: float):
    """Generate positions for a square grid layout."""
    import math
    side = math.ceil(math.sqrt(count))
    positions = []
    
    # Center the grid
    offset = (side - 1) * spacing / 2
    
    for i in range(count):
        row = i // side
        col = i % side
        x = col * spacing - offset
        y = row * spacing - offset
        positions.append((x, y))
    
    return positions, side


def generate_scene(count: int, spacing: float) -> str:
    """Generate a multi-robot scene XML."""
    positions, side = generate_square_positions(count, spacing)
    
    # Floor size should accommodate all robots with margin
    floor_size = side * spacing * 0.75 + 1
    
    xml_parts = [XML_HEADER.format(n=count, floor_size=floor_size)]
    
    for idx, (x, y) in enumerate(positions):
        xml_parts.append(FRAME_TEMPLATE.format(x=x, y=y, idx=idx))
    
    xml_parts.append(XML_FOOTER)
    
    return ''.join(xml_parts)


def main():
    parser = argparse.ArgumentParser(description='Generate multi-UR5E robot scene')
    parser.add_argument('count', type=int, help='Number of robots')
    parser.add_argument('--spacing', type=float, default=DEFAULT_SPACING,
                        help=f'Spacing between robots (default: {DEFAULT_SPACING}m)')
    parser.add_argument('--output', '-o', type=str, default=None,
                        help='Output file path (default: <count>_ur5e_square.xml)')
    
    args = parser.parse_args()
    
    if args.output is None:
        output_path = Path(__file__).parent / f'{args.count}_ur5e_square.xml'
    else:
        output_path = Path(args.output)
    
    xml_content = generate_scene(args.count, args.spacing)
    
    with open(output_path, 'w') as f:
        f.write(xml_content)
    
    print(f'Generated {output_path} with {args.count} UR5E robots')


if __name__ == '__main__':
    main()
