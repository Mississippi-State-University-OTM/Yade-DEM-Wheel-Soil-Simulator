import pyvista as pv
import os
import glob

# Define input and output paths
input_dir = './'
output_dir = './images'
output_filename_base = 'frame_'

# Create output directory if it doesn't exist
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# Find all VTK files in the directory (adjust pattern as needed)
vtk_files = sorted(glob.glob(os.path.join(input_dir, 'export-facets*.vtk')))
sph_files = sorted(glob.glob(os.path.join(input_dir, 'export-spheres*.vtk')))

# Iterate through files and save screenshots
for i, (vtk_file,sph_file) in enumerate(zip(vtk_files,sph_files)):
    print(i, vtk_file, sph_file)

    # Create the base sphere geometry to use as a template
    sphere_template = pv.Sphere(radius=1.0)

    # Read the VTK data
    mesh_whb = pv.read(vtk_file)
    data = pv.read(sph_file)
    mesh_sph = data.glyph(geom=sphere_template, scale="radius", factor=1.0,
                          orient = False) # otherwise warning

    # Create a plotter instance and set it to off-screen rendering
    plotter = pv.Plotter(off_screen=True)

    # Add the mesh to the plotter
    # You can customize plotting parameters here (e.g., scalars='my_field', cmap='jet')
    plotter.add_mesh(mesh_whb, cmap="jet", style="wireframe", color = "black",
                     line_width=4)
    plotter.add_mesh(mesh_sph, color="skyblue")
    
    # plotter.set_background('white') does nothing, remains transparent

    # Optional: adjust camera view vector
    plotter.view_vector((0, -1, 0), viewup=(0, 0, 1))

    # Define the output filename with sequential numbering and PNG extension
    output_filename = f"{output_filename_base}{i:04d}.png" # Padded with zeros for correct sequence sorting
    output_path = os.path.join(output_dir, output_filename)

    # Save the screenshot
    plotter.screenshot(output_path, window_size=[1024, 768], transparent_background=True)

    # Close the plotter to release resources
    plotter.close()

    print(f"Saved {output_path}")

print("Conversion complete.")
