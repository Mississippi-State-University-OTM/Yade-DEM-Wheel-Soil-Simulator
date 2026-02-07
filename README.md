# Yade DEM Soil-Wheel Simulators

Two soil-wheel simulators are provided. The first is `simWheelTestRigKyoto.py`, developed at Kyoto University and published by [Nakanishi (2020)](https://doi.org/10.1016/j.jterra.2020.10.001). It sets the tractive load and uses PID controller to keep angular velocity constant. The published code was adapted here to work with Python 3. The second, `simWheelTestRigMSSTATE.py`, was inspired by `simWheelTestRigKyoto` and developed at the Center for Advanced Vehicular Systems, Mississippi State University by [Bohumir Jelinek](https://www.cavs.msstate.edu/directory/information.php?d=69) to assist students in the [Wheel and Track Design Competition](https://doi.org/10.1016/j.jterra.2025.101117) of the [International Society of Terrain-Vehicle Systems](https://www.istvs.org/). It simulates the wheel motion in towed, self-propelled, and prescribed slip conditions.

## Installation of Yade DEM Simulation Environment

Yade DEM simulation environment can be installed according to the instructions at the [Yade DEM website](https://yade-dem.org/doc/), which provides an introduction to Linux, Python, and detailed documentation.

## Requirements

- **Yade (tested versions):**
  - MSSTATE simulator (`simWheelTestRigMSSTATE.py`): Yade 2022.01a, Yade daily build `20260115-8983~7c8d01e~noble1`
  - Kyoto simulator (`simWheelTestRigKyoto.py`): Yade 2022.01a

**Note:** The Kyoto simulator does not work with newer versions of Yade. The MSSTATE simulator is recommended for use with the latest stable release of Yade or recent daily builds.

## Running the Simulators with GUI

Start the simulators using Yade from the command line. Use `yade` for stable releases or `yadedaily` if you have a daily build installed. Check your installed version with `yade --version` or `yadedaily --version`.

**Kyoto simulator:**

```bash
yade simWheelTestRigKyoto.py
```

**MSSTATE simulator with stable release:**

```bash
yade simWheelTestRigMSSTATE.py
```

**MSSTATE simulator with daily build:**

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

### YADE 3D Display Keyboard Shortcuts

- `z`: set z-axis up
- `x`: set x-axis up
- `c`: center view
- `o`: zoom in
- `p`: zoom out

To see all available shortcuts, focus the 3D display window and press `h`.
