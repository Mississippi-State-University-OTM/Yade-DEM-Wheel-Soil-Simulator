# DEM Wheel-Soil-Box Simulator

This document describes a Yade DEM based Wheel-Soil-Box Simulator,
`simWheelSoilBox.py`, developed at the [Center for Advanced Vehicular
Systems](https://cavs.msstate.edu/), [Mississippi State
University](https://www.msstate.edu/) to aid in the [Wheel and Track
Design Competition](https://doi.org/10.1016/j.jterra.2025.101117) of
the [International Society of Terrain-Vehicle
Systems](https://www.istvs.org/). It simulates planar motion of a
rigid wheel in a box with granular soil under prescribed forward
and/or angular velocity conditions using open-source [Yade
framework](https://yade-dem.org/doc/), main features of which are
summarized by [Angelidakis et
al. (2024)](https://doi.org/10.1016/j.cpc.2024.109293).

The simulator follows the model and source code published by
[Nakanishi (2020)](https://doi.org/10.1016/j.jterra.2020.10.001)
developed at Kyoto University.

## Installation of Yade DEM Simulation Environment

The Yade DEM simulation environment can be installed according to the
instructions at the [Yade DEM website](https://yade-dem.org/doc/),
which provides an introduction to Linux, Python, and detailed
documentation. The simulator was tested to work under Ubuntu 24.04 and
Ubuntu 22.04 application installed under Windows 11 OS and in Docker
containers.

## Requirements

The `simWheelSoilBox.py` simulator

- requires up-to-date version of [Yade DEM](https://yade-dem.org/doc/)
  environment: Yade 2020.01a or later
  version (Ubuntu 20.04, Debian Bullseye or later). Scaling the wheel
  size currently works only with Yade 2021.01a or later (Ubuntu 24.04,
  Debian Bullseye or later).
  Yade daily build, `yadedaily`, which is automatically generated from a
  recent Yade development source code, should work as well.

The `fixWinding.py` and `writeLuggedWheel.py` scripts

- require [NumPy](https://numpy.org/) Python package, and
  [trimesh](https://trimesh.org/install.html) which requires
  additional packages ("pyglet<2", scipy, numpy-stl, and shapely)
  which can be installed into a Python virtual environment.

A computer with at least 8 GB of memory is recommended.

## Running Simulator with GUI

Start the simulator using Yade from the command line. Use `yade` for
stable releases or `yadedaily` if your Linux distribution provides a
daily build of Yade. Check your installed version with `yade
--version` or `yadedaily --version`.

**Starting simulator using stable release of Yade:**

```bash
yade simWheelSoilBox.py
```

**Starting simulator with daily build of Yade:**

```bash
yadedaily simWheelSoilBox.py
```

Each command will open a GUI control panel window, a plotting window,
and a 3D display window. Press the "Play" button in the controller
window to start the simulation. Closing the 3D display window will
speed up the simulation noticeably. The 3D display window can be
re-opened by clicking the `Show 3D` button in the YADE control panel.

By default, the simulator reads the parameter file `params.json` from
the working directory. This file contains the wheel and soil
parameters used in [Nakanishi
(2020)](https://doi.org/10.1016/j.jterra.2020.10.001) and particles
size scaled up 10X to speed up the simulation. To get the particles
sizes matching the publication, change the `particles` `scale`
parameter in the `params.json` file from 10.0 to 1.0.

To run the simulator with a specific input parameter file, provide the
filename or path as the first command-line argument. If desired,
``yade`` can be replaced by ``yadedaily`` in any of the examples.

The following example opens the GUI, read input parameter file
`params.json` from the current directory, and awaits you to press
`Play` to start the simulation:

```bash
yade simWheelSoilBox.py params.json
```

Paths are resolved relative to the current working directory where you
run `yade`. To execute a simulation with a parameter file
`examples/Kyoto/tow0p30mps_2p0kg/params.json` using, for example,
eight threads, add `-j8` command line parameter:

```bash
yade -j8 simWheelSoilBox.py examples/Kyoto/tow0p30mps_2p0kg/params.json
```

Multi-thread simulations run faster than single-thread. Only the
single-thread (`-j1`) simulations are perfectly reproducible.

## Running Simulator without GUI

First, set the `GUImode` to `false` in the input JSON file to false
(snippet below)

```json
{
   "sim": {
      "GUImode": false
   }
}
```

and then execute with `-n` (no GUI) and `-x` (exit upon completion)
flags as below

```bash
yade -n -x simWheelSoilBox.py
```

Instead of modifying the parameter file, the GUI mode can be
set/overwritten from the command line

```bash
yade -n -x simWheelSoilBox.py --params sim.GUImode:false
```

Note that any simulation parameter, including those in the input
parameter file, can be overwritten/set using the command line option
`--params`, upon spelling out its full path:

```bash
yade -n -x -j8 simWheelSoilBox.py params.json --params sim.GUImode:false \
sim.vis.saveInt:0.01 wheel.initVals.vx:0.6
```

To store screen printouts, for example, standard output in ``log.txt``
file and standard error (including progress messages) in `log2.txt`
file, use:

```bash
yade -n -x -j8 simWheelSoilBox.py params.json 2> log2.txt > log.txt
```

Then you can monitor the progress using

```bash
tail -f log2.txt
```

## Reading Wheel Geometry from STL File

The simulator reads a rigid wheel geometry from a plain text or binary
STL file. The simulator uses `x`-forward, `z`-up coordinate system,
meaning the wheel moves forward in the `+x` direction and the gravity
points in the `-z` direction. The STL file needs to have a wheel in
the `xz` plane, with the wheel rotational axis in the `y` direction,
or it will need to be transformed to comply,
which is done specifying `forward` and `up` directions in the
`wheel.stl.orientDriving` component of the parameter file, as shown in
the snippet below. Acceptable values for `forward` and `up`
directions are `x`, `y`, `z`, `-x`, `-y`, and `-z`.
If the wheel center is
not in the origin of the coordinate system, the wheel center offset
needs to be specified in the input JSON parameter file to position the
wheel to proper initial location in the soil bin. The Yade STL
importer in the simulator returns triangular facets from which the
outer boundary of the rigid wheel body is constructed. Yade STL
importer currently can't rotate the coordinate system of the wheel -
that is why the rotational axis of the wheel in the STL file needs to
point in the `y` direction. Note that the rotation is not difficult to
implement following the facet-checking function in the source
code. The simulator currently supports scaling the wheel size (by
applying multiplicative units ratio factor) and translation (Yade
needs to know wheel center offset). Expected distance units in the STL
file are `meters`. Following is an example snippet from the JSON
parameter file:

```json
{
    "wheel": {
        "stl": {
            "filename": "myTire.stl",
            "unitsScale" : 0.0090909091,
            "centerOffset": {
                "x": 12.1,
                "y": 3.3,
                "z": 12.1
            },
            "orientDriving": {
                "forward": "-x",
                "up": "z"
            }
        },
        "radEff": 0.11,
        "mass": 2.0,
        "Iyy": 0.0025,
        "initVals" : {
            "x": -0.35,
            "y": 0.0,
            "z": 0.6,
            "vx": 0.3,
            "wy": 2.0
        },
        "constrains": {
            "vx": true,
            "wy": false
        },
        "material" : "matWheel"
    }
}
```

Effective radius `radEff` is used to compute the wheel slip. The
constraint `vx=True` means `x`-component of the velocity is fixed at
the specified value `vx` (towed condition). The constraint `wy=True`
means the angular velocity of the wheel is forced to have the
specified value `wy` (self-propelled condition). If not fixed by a
constraint, the initial value of the velocity is set to zero. For a
prescribed slip condition, both `vx` and `wy` to be constrained and
set to a desired value. The wheel is allowed to move freely in the
z-direction.

## YADE 3D Display Keyboard Shortcuts

- `z`: set z-axis up
- `x`: set x-axis up
- `c`: center view
- `o`: zoom in
- `p`: zoom out

To see all available shortcuts, set focus on the 3D display window and
press `h`. Double-click the 3D display window to align the view with
nearest axes.

## Post-processing

`simWheelSoilBox.py` can store soil particles (spheres) in a LAMMPS
dump format, and the wheel geometry in VTK format. A convenient GUI
tool for visualizing these is [OVITO](https://www.ovito.org). OVITO
open-source version is called `OVITO Basic`. OVITO Basic versions
lower than 3.8.0 can visualize particles along with the wheel. Options
for saving the dump files are in the JSON parameter file shown in the
snippet below.

```json
{
    "sim": {
        "Di's": {
            "saveInt": 0.02,
            "spheres": {
                "on": true,
                "singleFile": false,
                "basename" : "vis/ovito-",
                "detailed" : false
            }
        }
    }
}
```

## AI Use

ChatGPT helped to write command line argument parsing, set_nested, and
Ovito exporter routines. Google Gemini helped ChatGPT, Google Gemini
and MS Copilot helped to understand Yade usage and parameter setup.
`plot.py` was created using Google Gemini.

## Acknowledgment

This work was funded by the [Center for Advanced Vehicular
Systems](https://cavs.msstate.edu/), [Mississippi State
University](https://www.msstate.edu/).

## Copyright Statement

```text
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
```

For more information, contact Mississippi State University's Office of
Technology Management at otm@msstate.edu
