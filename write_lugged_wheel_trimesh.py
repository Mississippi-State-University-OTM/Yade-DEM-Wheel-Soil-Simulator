import trimesh
import numpy as np

import json
with open('dims_lugged_wheel_Kyoto.json', 'r') as f:
    wheel_dims = json.load(f)

wheel_radius    = wheel_dims['radius']
wheel_width     = wheel_dims['width']
wheel_nSections = wheel_dims['num_sections']
lugs_width      = wheel_dims['lugs']['width']
lugs_height     = wheel_dims['lugs']['height']
lugs_number     = wheel_dims['lugs']['number']
print(f"Wheel dimensions: radius {wheel_radius} width {wheel_width} m ")
print(f" {lugs_width=}")
print(f" {lugs_height=}")
print(f" {lugs_number=}")

# Create the main wheel (cylinder)
wheel = trimesh.creation.cylinder(radius=wheel_radius, height=wheel_width,
                                  sections=wheel_nSections)

# Create a single lug (small box)
lug = trimesh.creation.box(extents=[lugs_height, lugs_width, wheel_width])
lug.apply_translation([wheel_radius, 0, 0])  # Place on the circumfernce

# Create multiple lugs by rotating the first one
lugged_wheel = wheel
for angle in np.linspace(0, 2 * np.pi, lugs_number, endpoint=False):
    matrix = trimesh.transformations.rotation_matrix(angle, [0, 0, 1])
    lugged_wheel = trimesh.util.concatenate([lugged_wheel, lug.copy().apply_transform(matrix)])

# Process the mesh (merge vertices)
lugged_wheel.merge_vertices()

# Apply rotation
rot_y = trimesh.transformations.rotation_matrix(np.radians(90), [0, 1, 0])
lugged_wheel.apply_transform(rot_y)
rot_x = trimesh.transformations.rotation_matrix(np.radians(90), [1, 0, 0])
lugged_wheel.apply_transform(rot_x)

# Show the result
lugged_wheel.show()

bname = "lugged_wheel_trimesh"

ofile = bname + "_ascii.stl"
lugged_wheel.export(ofile, file_type ='stl_ascii')
print(f"trimesh successfully wrote the mesh to \"{ofile}\".")

ofile = bname + "_binary.stl"
lugged_wheel.export(ofile, file_type ='stl')
print(f"trimesh successfully wrote the mesh to \"{ofile}\".")
