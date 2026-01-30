import trimesh
import numpy as np

wheel_radius = 1.0
wheel_width = 0.3
num_sections = 32
lug_width = 0.05
lug_height = 0.5
num_lugs = 8

# 1. Create the main wheel (cylinder)
wheel = trimesh.creation.cylinder(radius=wheel_radius, height=wheel_width,
                                  sections=num_sections)

# 2. Create a single lug (small box)
lug = trimesh.creation.box(extents=[lug_height, lug_width, wheel_width])
lug.apply_translation([wheel_radius, 0, 0])  # Place on the circumfernce

# 3. Create multiple lugs by rotating the first one
lugged_wheel = wheel
for angle in np.linspace(0, 2 * np.pi, num_lugs, endpoint=False):
    matrix = trimesh.transformations.rotation_matrix(angle, [0, 0, 1])
    lugged_wheel = trimesh.util.concatenate([lugged_wheel, lug.copy().apply_transform(matrix)])

# 4. Process the mesh (merge vertices)
lugged_wheel.merge_vertices()

# 5. Extract facets (faces with similar normals)
# This identifies flat areas, useful for identifying lugs
#facets = lugged_wheel.facets
#print(f"Number of facets found: {len(facets)}")

# Optionally color the facets to visualize them
#for facet in facets:
#    lugged_wheel.visual.face_colors[facet] = trimesh.visual.random_color()

# 6. Show the result
lugged_wheel.show()

bname = "lugged_wheel_trimesh"

ofile = bname + "_ascii.stl"
lugged_wheel.export(ofile, file_type ='stl_ascii')
print(f"trimesh successfully wrote the mesh to \"{ofile}\".")

ofile = bname + "_binary.stl"
lugged_wheel.export(ofile, file_type ='stl')
print(f"trimesh successfully wrote the mesh to \"{ofile}\".")
