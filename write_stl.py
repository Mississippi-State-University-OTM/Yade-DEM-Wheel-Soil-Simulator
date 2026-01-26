import numpy as np
import stl, sys

def create_cylinder(radius, height, nsegments, orient):
    # 1. Generate Vertices (Centered at origin, along Z-axis)
    vertices = []
    # Bottom cap center and top cap center
    bottom_center = [0, 0, -height/2]
    top_center = [0, 0, height/2]
    vertices.append(bottom_center)
    vertices.append(top_center)
    
    # Circumference points
    for i in range(nsegments):
        angle = 2 * np.pi * i / nsegments
        x = radius * np.cos(angle)
        y = radius * np.sin(angle)
        vertices.append([x, y, -height/2]) # Bottom
        vertices.append([x, y, height/2])  # Top
    
    # 2. Generate Faces (Triangles)
    faces = []
    for i in range(nsegments):
        # Bottom cap triangles
        b1 = 2 + (i * 2)
        b2 = 2 + ((i + 1) * 2) % (2 * nsegments)
        faces.append([0, b2, b1])
        
        # Top cap triangles
        t1 = 3 + (i * 2)
        t2 = 3 + ((i + 1) * 2) % (2 * nsegments)
        faces.append([1, t1, t2])
        
        # Side faces (two triangles per segment)
        faces.append([b1, b2, t1])
        faces.append([b2, t2, t1])

    # 3. Convert to np array and return
    vertices = np.array(vertices)
    faces = np.array(faces)
    for i in range(len(vertices)):
        if orient == 'z':
            pass
        elif orient == 'x':
            vertices[i] = np.roll(vertices[i], shift=1)
        elif orient == 'y':
            vertices[i] = np.roll(vertices[i], shift=2)
        else:
            print(f"Error: Wrong orientation: \"{orient}\"", file = sys.stderr)
            sys.exit(1)

    return vertices, faces


def create_cube():
    # Define the 8 vertices of the cube
    vertices = np.array([
        [0, 0, 0], [10, 0, 0], [10, 10, 0], [0, 10, 0],  # Bottom vertices
        [0, 0, 10], [10, 0, 10], [10, 10, 10], [0, 10, 10]   # Top vertices
    ]) * 10 # Scale up for better visualization

    # Define the 12 triangles (faces) that make up the cube's surface
    faces = np.array([
        [0, 3, 1], [1, 3, 2],  # Bottom face (2 triangles)
        [0, 4, 7], [0, 7, 3],  # Front face
        [4, 5, 6], [4, 6, 7],  # Top face
        [5, 1, 2], [5, 2, 6],  # Right face
        [2, 3, 6], [3, 7, 6],  # Back face
        [0, 1, 5], [0, 5, 4]   # Left face
    ])

    return vertices, faces

# Main program
object = "cube"
object = "cylinder"

if object == "cylinder":
    wheelRadius  = 0.5
    wheelWidth   = 0.25
    segments = 16     # Cylinder resolution
    myorient = 'x'
    vertices, faces = create_cylinder(radius=wheelRadius, height=wheelWidth,
                                      nsegments=segments, orient=myorient)
elif object == "cube":
    vertices, faces = create_cube()
else:
    import sys
    print("Error: Unknown object to write: ", object, file = sys.stderr)
    sys.exit(1)

# Initialize the mesh data structure with number of triangles
smesh = stl.mesh.Mesh(np.zeros(faces.shape[0], dtype=stl.mesh.Mesh.dtype))

# Populate the mesh vectors with the vertices from our faces list
for i, f in enumerate(faces):
    for j in range(3):
        smesh.vectors[i][j] = vertices[f[j], :]

# Write the mesh to an STL file
ofile = object + '.stl'
smesh.save(ofile, mode=stl.Mode.ASCII)
print(f"numpy-stl successfully wrote the mesh to \"{ofile}\".")

"""
# Fix normals to be outward
import trimesh
tmesh = trimesh.load(ofile)
out = tmesh.fix_normals()
print("out:", out)
# Check if watertight (required for reliable outward normals)
print(tmesh.is_watertight)
# Save the repaired mesh
ofile = object + "_fix.stl"
tmesh.export(ofile, file_type ='stl_ascii')
print(f"trimesh successfully wrote the mesh to \"{ofile}\".")
"""
