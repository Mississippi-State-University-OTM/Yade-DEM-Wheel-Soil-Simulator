# Yade DEM Soil-Wheel Simulators

Two soil-wheel simulators are provided. The first is `simWheelTestRigKyoto.py`, developed at Kyoto University and published by [Nakanishi (2020)](https://doi.org/10.1016/j.jterra.2020.10.001). It sets the tractive load and uses PID controller to keep angular velocity constant. The published code was adapted here to work with Python 3. The second, `simWheelTestRigMSSTATE.py`, was inspired by `simWheelTestRigKyoto` and developed at the Center for Advanced Vehicular Systems, Mississippi State University by [Bohumir Jelinek](https://www.cavs.msstate.edu/directory/information.php?d=69) to assist students in the [Wheel and Track Design Competition](https://doi.org/10.1016/j.jterra.2025.101117) of the [International Society of Terrain-Vehicle Systems](https://www.istvs.org/). It simulates the wheel motion in towed, self-propelled, and prescribed slip conditions.

## Installation of Yade DEM Simulation Environment

Yade DEM simulation environment can be installed according to the instructions at the [Yade DEM website](https://yade-dem.org/doc/), which provides an introduction to Linux, Python, and detailed documentation.

## Requirements

- Yade DEM [website](https://yade-dem.org/doc/):
- MSSTATE simulator (`simWheelTestRigMSSTATE.py`): requires Yade 2021.01a or later versions. It also works with Yade 2020.01a (Ubuntu 22.04) except for scaling the wheel size.
- Kyoto simulator (`simWheelTestRigKyoto.py`): was executed with Yade 2020.01a or later versions.

## Running the Simulators with GUI

Start the simulators using Yade from the command line. Use `yade` for stable releases or `yadedaily` if you have a daily build installed. Check your installed version with `yade --version` or `yadedaily --version`.

**Kyoto simulator:**

```bash
yade simWheelTestRigKyoto.py
```

**MSSTATE simulator with stable release of Yade:**

```bash
yade simWheelTestRigMSSTATE.py
```

**MSSTATE simulator with daily build of Yade:**

```bash
yadedaily simWheelTestRigMSSTATE.py
```

Each command will open a GUI controller window, a plotting window, and a 3D display window. Press the "Play" button in the controller window to start the simulation.

By default, the MSSTATE simulator `simWheelTestRigMSSTATE.py` reads the parameter file `paramsKyoto.json` from the working directory. This file contains the wheel and soil parameters used in [Nakanishi (2020)](https://doi.org/10.1016/j.jterra.2020.10.001). The Kyoto simulator `simWheelTestRigKyoto.py` uses hard-coded parameters and does not read a parameter file.

To run the MSSTATE simulator with a different parameter file, pass the filename or path as the first command-line argument. Examples:

GUI mode (open the GUI and use alternate params):

```bash
yade simWheelTestRigMSSTATE.py paramsCustom.json
```

Headless mode (no GUI):

```bash
yade -n -x simWheelTestRigMSSTATE.py paramsCustom.json
```

Paths are resolved relative to the current working directory where you run `yade`.

## Running Simulators without GUI

For the MSSTATE simulator `simWheelTestRigMSSTATE.py`, set GUI mode to `false` in the parameter JSON and run with Yade's no-GUI flags. Example snippet:

```json
{
   "sim": {
      "GUImode": false
   }
}
```

Run headless:

```bash
yade -n -x simWheelTestRigMSSTATE.py
```

Or explicitly pass a parameter file (example):

```bash
yade -n -x simWheelTestRigMSSTATE.py paramsCustom.json
```

Note: `simWheelTestRigKyoto.py` uses hard-coded parameters and does not read `paramsKyoto.json`. To run the Kyoto script without a GUI, set the `GUImode = False` near the end of `simWheelTestRigKyoto.py` and use Yade's CLI flags:

```bash
yade -n -x simWheelTestRigKyoto.py
```

## Reading STL File with Wheel Geometry (`simWheelTestRigKyoto.py`)

`simWheelTestRigKyoto.py` uses x-forward, z-up coordinate system. That means the wheel moves forward in the +x direction and the gravity points in the -z direction. Please build you STL file with the wheel in the xz plane (wheel rotational axis in the y direction), or find a way to postprocess your whee's STL file to comply. Wheen center does not need to be in the origin but you need to specify center offset in the JSON parameter file (snippet below) to position the wheel to proper initial location in the soil bin. Yade function importing STL returns triangular facets, which are then used by the `simWheelTestRigKyoto.py` to construct the wheel body. Yade STL importer can't rotate the coordinate system of the wheel at the moment (that's why it is better to provide STL file with the wheel in the xz plan), although a rotation should not be hard to implement in `simWheelTestRigMSSTATE.py` upon reading the facets. `simWheelTestRigKyoto.py` currently supports scaling the wheel size (by applying multiplicative units ratio factor) and translation (Yade needs to know wheel center offset). Expected distance units are meters. Following is an example snipped from the JSON parameter file:

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

Effective radius `radEff` is used to calculate slip. The constraint `vx=True` means x-component of the velocity is fixed at the specified value `vx` (towed condition), and `wy=True` means angular velocity of the wheel is forced to have the specified value `wy` (self-propelled condition). If not fixed by a constrain, the initial value is zero. For a prescribed slip condition, constrain both `vx` and `wy` to a desired value. The wheel is allowed to move freely in the z-direction.

### YADE 3D Display Keyboard Shortcuts

- `z`: set z-axis up
- `x`: set x-axis up
- `c`: center view
- `o`: zoom in
- `p`: zoom out

To see all available shortcuts, focus the 3D display window and press `h`.
