import numpy as np
import trimesh
from shapely.geometry import Polygon

import json
basename = "dims_lugged_wheel_"
mywheel="Kyoto"
ifile = basename + mywheel + ".json"
with open(ifile, 'r') as f:
    wheel_dims = json.load(f)

wheel_radius    = wheel_dims['radius']
wheel_width     = wheel_dims['width']
nseg_bw_lugs    = wheel_dims['num_segments_between_lugs']
lugs_width      = wheel_dims['lugs']['width']
lugs_height     = wheel_dims['lugs']['true_height']
lugs_number     = wheel_dims['lugs']['number']
print(f"Wheel dimensions: radius {wheel_radius} width {wheel_width} m ")
print(f" {lugs_width=}")
print(f" {lugs_height=}")
print(f" {lugs_number=}")

def create_lugged_wheel(radius=wheel_radius, width=wheel_width,
                        num_lugs=lugs_number, lug_height=lugs_height,
                        lug_width=lugs_width, nseg_between_lugs=nseg_bw_lugs):
    """Generates a 3D lugged wheel mesh using triangular facets."""
    # Generate 2D Profile Points
    angles = np.linspace(0, 2 * np.pi, num_lugs, endpoint=False)

    angLugOuter = np.atan( (lug_width/2) / (radius+lug_height) ) * 2
    angLugInner = np.atan( (lug_width/2) / (radius) )            * 2
    angSegments = ( 2*np.pi - num_lugs*angLugInner ) / num_lugs / nseg_between_lugs

    points = []
    for angle in angles:
        # Create teeth by alternating radius
        current_radius = radius
        # inner 1st
        points.append([np.cos(angle-angLugInner/2) * current_radius,
                       np.sin(angle-angLugInner/2) * current_radius])

        current_radius = (radius + lug_height) / np.cos(angLugOuter/2)
        # outer 1st
        points.append([np.cos(angle-angLugOuter/2) * current_radius,
                       np.sin(angle-angLugOuter/2) * current_radius])
        # outer 2nd
        points.append([np.cos(angle+angLugOuter/2) * current_radius,
                       np.sin(angle+angLugOuter/2) * current_radius])

        current_radius = radius
        # inner 2nd
        points.append([np.cos(angle+angLugInner/2) * current_radius,
                       np.sin(angle+angLugInner/2) * current_radius])

        # points between lugs
        for idx in range(1, nseg_between_lugs):
            ang2 = (angle+angLugInner/2) + idx*angSegments
            points.append([np.cos(ang2) * current_radius,
                           np.sin(ang2) * current_radius])

    # Create Polygon and Extrude
    wheel_2d = Polygon(points)
    wheel_3d = trimesh.creation.extrude_polygon(wheel_2d, height=width)
    
    return wheel_3d

# Execute
wheel = create_lugged_wheel()
wheel.merge_vertices()

wheel.apply_translation([0, 0, -(wheel_width/2)])

# Apply rotation
rot_x = trimesh.transformations.rotation_matrix(np.radians(90), [1, 0, 0])
wheel.apply_transform(rot_x)

wheel.show() # Opens a viewer to inspect the triangular facets
wheel.export('wheelKyoto2_binary.stl')
wheel.export('wheelKyoto2.stl', file_type ='stl_ascii')
