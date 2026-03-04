#!/usr/bin/env python3
'''
    <DEM Wheel-Soil-Box Simulator.>
    Copyright (C) 2026  Mississippi State University

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.

For more information, contact Mississippi State University's Office of Technology Management at otm@msstate.edu
'''

import sys
from pathlib import Path
import trimesh

# Check if the argument is provided
if len(sys.argv) > 1:
    ifile_path = sys.argv[1]
    print(f"Input file: {ifile_path}")
else:
    print("Please provide an input STL file path as the first argument.")
    sys.exit(1)

ofile_no_ext = str(Path(ifile_path).with_suffix(""))

# Load the mesh from STL, save in text format
# If process=False, load will recalculate normals from winding right away and fix nothing else
# so you must set process=True (DEFAULT) for fix_windings() to work (called ebelow)
# process=True will will also make the mesh watertight right away
wheel = trimesh.load_mesh(ifile_path, process=True)

# This output file WILL differ from input STL if normals are inconsistent with winding
#   - EVEN IF load(process=False)
#   - it seems trimesh must output consistent mesh (= normals must be consistent with winding)
wheel.export(ofile_no_ext + '_ascii.stl', file_type ='stl_ascii')

if not wheel.is_watertight:
    print("WARNING: Mesh is not watertight — outward normals may be ambiguous")
else:
    # load() with process=True will will make the mesh watertight right away
    print("Mesh is watertight — outward normals should not be ambiguous")

# Fix winding (returns None, modifies in-place)
# For ascii wheelKyto.stl, winding will be changed to be the same as that of the FIRST FACET
#   - EVEN IF the first facet normal is wrong (wrong = inward)
#   - then winding will be changed so that ALL normals will point INWARD
#   - TRY changing wheelKyoto.stl
#   - note that wheelKyto.stl is proper except for NOT WATERTIGHT (see with process=False) (WHY?)
trimesh.repair.fix_winding(wheel)

wheel.show() # Opens a viewer to inspect the triangular facets

wheel.export(ofile_no_ext + '_fix_binary.stl')
wheel.export(ofile_no_ext + '_fix_ascii.stl', file_type ='stl_ascii')
