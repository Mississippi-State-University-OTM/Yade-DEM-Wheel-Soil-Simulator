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

timestart = time.time()

import argparse

parser = argparse.ArgumentParser(description="Wheel-Soil-Box Simulator.")
parser.add_argument("param_file", nargs='?', help="Parameter file", default = "params.json")
parser.add_argument("--params", nargs='+', help="Pairs of param:value (e.g., sim.GUImode:false, sim.timeStep:0.00001)", default=[])

args = parser.parse_args()

# Parse command line parameter values, returns parameter map
# Example cmdline par_list:  ['sim.timeStep:0.0', 'sim.GUImode:true']
def parse_cmdln_params(par_list):
    par_map = {}
    if not par_list:
        return par_map
    for item in par_list:
            par_name, val = item.split(':')
            if val == "true":
                par_map[par_name] = True
            elif val == "false":
                par_map[par_name] = False
            else:
                try:
                    ival = int(val)
                    par_map[par_name] = ival
                except ValueError:
                    try:
                        fval = float(val)
                        par_map[par_name] = fval
                    except ValueError: # not T/F, not int, not float => string
                        par_map[par_name] = val
    return par_map

print("arg params:", args.params)
params_map = parse_cmdln_params(args.params)

param_file = args.param_file
print(f'Parameter file:\n "{param_file}"')

import json
with open(param_file, 'r') as f:
    data = json.load(f)

# Example use: set_nested(data, "sim.GUImode", True)
#              set_nested(data, "sim.timeStep", 0.00001)
def set_nested(data, path, value):
    keys = path.split(".")
    d = data
    for key in keys[:-1]:
        if key not in d or not isinstance(d[key], dict):
            d[key] = {}
        d = d[key]
    d[keys[-1]] = value

# Overwrite parameters from param file by values from command line
for key, value in params_map.items():
    print(f"Cmdln param: {key} = {value}")
    set_nested(data, key, value)

# Wheel properties and initial coordinates from JSON
valLinVel    = data['wheel']['initVals']['vx']   # set initial value of wheel Vx
fixLinVel    = data['wheel']['constrains']['vx'] # True: fix the initial Vx over time
valAngVel    = data['wheel']['initVals']['wy']   # set initial value of wheel Wx
fixAngVel    = data['wheel']['constrains']['wy'] # True: fix the initial Wy over time
wheelRadEff  = data['wheel']['radEff']           # for Gross Traction, Slip, & height above settled soil
acc_g        = 9.81                              # acceleration of gravity
wheelMass    = data['wheel']['mass']             # Rigid-body mass
wheelInertia = (1, data['wheel']['Iyy'], 1)      # Inertia tensor
initX        = data['wheel']['initVals']['x']    # Initial x-coordinate
initY        = data['wheel']['initVals']['y']    # Initial y-coordinate
initZ        = data['wheel']['initVals']['z']    # Wheel waiting-for-soil-to-settle height
settleTime   = data['sim']['settleTime']         # Time to settle particles
endTime      = data['sim']['endTime']            # Total simulated time
progRepInt   = data['sim']['progRepInterval']    # Print simulated time and % done each this simulated interval
dataSaveInt  = data['sim']['dataSaveInterval']   # Sim. time interval to save data
exactARot = True
if 'exactAsphericalRot' in data['sim']:
    exactARot =  data['sim']['exactAsphericalRot']
print(f"Exact Aspherical Rotation: {exactARot}")

if 'vis' in data['sim']:
    # Sim. time interval to save visualization snapshots, 0 = don't save
    visSaveInt = data['sim']['vis']['saveInt']
    # True: save spheres in LAMMPS dump format, more spheres = more disk space
    visSaveSph = data['sim']['vis']['spheres']['on']
    visSaveSphSingleFile = data['sim']['vis']['spheres']['singleFile']
    visSaveSphBname = data['sim']['vis']['spheres']['basename']
    visSaveSphDetailed = data['sim']['vis']['spheres']['detailed']
else:
    visSaveInt = 0.0
GUImode      = data['sim']['GUImode']            # True: run with GUI

stlData      = data['wheel']['stl']
stlFile      = stlData['filename']  # Wheel STL/OBJ file

stlScale = 1.0
key = 'unitsScale'
if key in stlData:
    stlScale = stlData[key]    # Ratio to multiply the coordinates from STL file by

coX = 0; coY = 0; coZ = 0;                       # STL wheel center offset
key = 'centerOffset'
if key in stlData:
    coX, coY, coZ = stlData[key]['x'], stlData[key]['y'], stlData[key]['z']

fixNormals = True
key = 'fixNormals'
if key in stlData:
    fixNormals = stlData[key]

# Which way the wheel moves forward, which way is up: x,-x,-y,z,-z
# (to reorient the wheel for driving - default is x-forward and z-up)
key = 'orientDriving'
if key in stlData:
    x_new = stlData[key]['forward']
    z_new = stlData[key]['up']
else:
    x_new = 'x'
    z_new = 'z'

# Particle parameters
# initial placement of particles up to 0.8 (= 80%) of box' height
pck      = data['particles']['pck']
rndSeed  = data['particles']['rndSeed']
part_gen = data['particles']['generation']
pscale   = data['particles']['scale']
print(f"Particles:")
print(f" Packing level up to z = {pck} m")
print(f" Generation method: {part_gen}, random seed: {rndSeed=}")
print(f" Scale-up particle sizes: {pscale} X original size (to speed up the simulation).")
if part_gen == "meanFuzz":
    rMean    = data['particles']['rMean']
    rRelFuzz = data['particles']['rRelFuzz']
    rndSeed  = data['particles']['rndSeed']
    print(f" MeanFuzz generation method: mean radius: {rMean} m, radius relative fuzz: {rRelFuzz=}")
elif part_gen == "clumpCloud":
    rmin     = data['particles']['rmin']
    rmed     = data['particles']['rmed']
    rmax     = data['particles']['rmax']
    partnum  = data['particles']['num' ]
    print(f" ClumpCloud generation method: Radii: {rmin}, {rmed}, {rmax}, requsted # of particles: {partnum}")

# Box interior region (open top)
hboxY     = data['box']['width']  / 2  # half width
hboxX     = data['box']['length'] / 2  # half lenght
boxHeight = data['box']['height']      # height of box
hboxZ     = boxHeight / 2              # half of height
boxCenterX = data['box']['center']['x'] # x,y,z coordinates of the box center
boxCenterY = data['box']['center']['y']
boxCenterZ = data['box']['center']['z']
print(f"Box dimensions: {hboxX*2} x {hboxY*2} x {boxHeight} m (lenght x width x height)")
print(f"Box center: {boxCenterX} {boxCenterY} {boxCenterZ}")

# Material parameters obtained using material names argument
matWheelParams  = data['materials'][data['wheel']    ['material']]
matSphereParams = data['materials'][data['particles']['material']]
matBoxParams    = data['materials'][data['box'      ]['material']]
# helper function that creates material by calling Yade function FrictMat()
def createFrictMaterial(params, labelarg):
    return FrictMat(density       = params['density'],
                    young         = params['young'],
                    poisson       = params['poisson'],
                    frictionAngle = params['frictionAngle'],
                    label = labelarg)
# create materials, mark them with labels
matWheel  = createFrictMaterial(matWheelParams, "wheelmat")
matSphere = createFrictMaterial(matSphereParams, "mat1")
# set sphere friction to zero for settling only, restore when the wheel is set in motion
sphereFrictionAngle = matSphere.frictionAngle  # store the value before setting to zero
matSphere.frictionAngle = 0.0
matBox = createFrictMaterial(matBoxParams, "wallmat")
idWheelMat  = O.materials.append(matWheel)
idBoxMat = O.materials.append(matBox)
idSphereMat = O.materials.append(matSphere) # last

# Particle-particld pair interaction parameters
intPPparams     = data['matPairs']['pp']
pp_en           = intPPparams['en']
pp_krot         = intPPparams['krot']

# Reposition the wheel to the top surface of soil and set it in motion
def setInMotion():
    matSphere.frictionAngle = sphereFrictionAngle
    smax = boxCenterZ - hboxZ      # stores highest particle surface
    idx = None
    for i in range(wheelBodyId + 1, wheelBodyId + partnum + 1):
        x = O.bodies[i].state.pos[0]
        if abs(x - initX) < 0.5*wheelRadEff: # ~0.5 arbitrary
            z = O.bodies[i].state.pos[2]
            r = O.bodies[i].shape.radius
            top = z + r
            if top > smax:
                smax = top
                idx = i
    print(f"Wheel lowered to highest particle surface (x-coord. within +/-0.5*Reff from wheel center) of {smax:.3f} m.")
    new_wheel_center_z = smax + wheelRadEff + .0001
    wheelBody.state.pos = Vector3(initX, initY, new_wheel_center_z)
    if fixLinVel and fixAngVel: # z free
        wheelBody.state.vel = Vector3(valLinVel,0,0)
        wheelBody.state.angVel = Vector3(0,valAngVel,0)
        wheelBody.state.blockedDOFs = 'xyXYZ'
    elif fixAngVel: # z and x free
        wheelBody.state.blockedDOFs = 'yXYZ'
        wheelBody.state.angVel = Vector3(0,valAngVel,0)
    elif fixLinVel: # z and wy free
        wheelBody.state.vel = Vector3(valLinVel,0,0)
        wheelBody.state.blockedDOFs = 'xyXZ'
    else:
        wheelBody.state.blockedDOFs = 'xYZ' # free x, z, and wy

from datetime import timedelta
firstPrint = True
prevTime = timestart
prev = 0
def printVirtTime():
    curr = O.iter * O.dt
    end = O.stopAtIter * O.dt
    simperc = f"Simulated time: {curr:.3f}s / {end:.3f}s = {curr/end*100:.2f}%"
    d_bottom = ( wheelBody.state.pos[2] - wheelRadEff
                 - (boxCenterZ - boxHeight/2) ) # wheel distance from box bottom
    x = wheelBody.state.pos[0]

    global firstPrint, prevTime, prev
    if firstPrint:
        print(f"{simperc}                            DB: {d_bottom:.3f}m",
              file = sys.stderr)
        firstPrint = False
    else:
        currTime = time.time()
        from_last_time = currTime - prevTime
        from_last_sim = curr - prev
        rem = end - curr
        est = from_last_time/from_last_sim * rem
        delta = timedelta(seconds=round(est))
        if not fixLinVel and fixAngVel:
            print(f"{simperc}    Est. remaining: {delta} DB: {d_bottom:.3f}m ",
                  f"x: {x:.3f}", file = sys.stderr) # print also wheel x-coord.
        else:
            print(f"{simperc}    Est. remaining: {delta} DB: {d_bottom:.3f}m",
                  file = sys.stderr)

    prev = curr
    prevTime = time.time()

# Calculate execution time
def timeCalculator():
    calc_time_total = timeend - timestart
    delta = timedelta(seconds=round(calc_time_total))
    report = (f"Execution time {delta} for {O.time:.2f} s simulation"
              f" using {O.numThreads} threads.")
    print(report, file = sys.stderr)
    with open('exec_time.txt','w') as f:
        f.write(report + "\n")

import numpy as np
from yade import Vector3

def calcRotMatrix(x_new_label, z_new_label):
    """
    Calculate rotation matrix to reorient the wheel from STL for driving
    """
    mapping = {
        "x": (0, 1), "-x": (0, -1),
        "y": (1, 1), "-y": (1, -1),
        "z": (2, 1), "-z": (2, -1)
    }

    # 1. Input Validation
    if x_new_label not in mapping or z_new_label not in mapping:
        raise ValueError(f"Invalid labels. Use {list(mapping.keys())}")

    idx_x, sign_x = mapping[x_new_label]
    idx_z, sign_z = mapping[z_new_label]

    if idx_x == idx_z:
        raise ValueError(f"X_new ({x_new_label}) and Z_new ({z_new_label}) are collinear!")

    # 2. Build Rotation Matrix (R)
    i_new = np.zeros(3); i_new[idx_x] = sign_x
    k_new = np.zeros(3); k_new[idx_z] = sign_z
    j_new = np.cross(k_new, i_new) # Right-hand rule
    R = np.array([i_new, j_new, k_new])

    return R

def reorientShift(shiftXYZ, R):

    # Apply Transformation
    old_shift = np.array([shiftXYZ[0], shiftXYZ[1], shiftXYZ[2]])
    new_shift = R.T @ old_shift
    shiftXYZ = Vector3(new_shift[0], new_shift[1], new_shift[2])
    return shiftXYZ

def reorientWheelFacets(facet_list, R):

    # Apply Transformation
    for b in facet_list:
        # Transform Global Centroid
        old_pos = np.array([b.state.pos[0], b.state.pos[1], b.state.pos[2]])
        new_pos = R @ old_pos
        b.state.pos = Vector3(new_pos[0], new_pos[1], new_pos[2])

        # Transform Local Vertices
        new_verts = []
        for v in b.shape.vertices:
            v_np = np.array([v[0], v[1], v[2]])
            v_rot = R @ v_np
            new_verts.append(Vector3(v_rot[0], v_rot[1], v_rot[2]))

        b.shape.vertices = new_verts

    return facet_list

# Check and fix inverted normals for facets
def fix_normals(facetList):
    """
    Ensure all facets point outward by flipping those whose
    normals point inward based on object centroid.
    """
    # Compute centroids of all vertices
    allVerts = []
    for f in facetList:
        for v in f.shape.vertices:
            allVerts.append(v+f.state.pos)
    if not allVerts:
        return facetList
    centroid = sum(allVerts, Vector3.Zero) / len(allVerts)

    def facet_normal(f):
        v = f.shape.vertices
        p0, p1, p2 = v[0], v[1], v[2]
        return (p1 - p0).cross(p2 - p0)

    count_flipped = 0
    for f in facetList:
        v = f.shape.vertices
        fCenter = f.state.pos
        outward = (fCenter - centroid)
        n = facet_normal(f)

        # If dot < 0 -> normal points toward centroid -> needs flipping
        if n.dot(outward) < 0:
            f.shape.vertices = [v[0], v[2], v[1]]   # swap to flip orientation
            count_flipped = count_flipped + 1
    if count_flipped:
        print(f" Flipped {count_flipped} facets.")

    return facetList

# Record wheel coords, force, torque
def rFTrecorder(bodyID):
    bstate= O.bodies[bodyID].state
    posx = bstate.pos[0]
    posz = bstate.pos[2]
    velx = bstate.vel[0]
    velz = bstate.vel[2]
    wely = bstate.angVel[1]
    fx=O.forces.f(bodyID)[0]
    fz=O.forces.f(bodyID)[2]
    ty=O.forces.t(bodyID)[1]
    gTr = -ty / wheelRadEff
    vrot = wely*wheelRadEff
    try: slip = (vrot - velx)/(vrot)
    except: slip = 0
    if slip < -10: slip = -10
    if slip >  10: slip =  10
    plot.addData(t = O.time,
                 At = O.time,
                 x = posx, z = posz,
                 Vx = velx, Vz = velz, Wy = wely, WxR = wely*wheelRadEff,
                 Fx = fx, Fz = fz, Ty = ty, # store actual Ty and Wy
                 mg = wheelMass * acc_g,
                 GrTr = gTr,
                 RollRes = gTr - fx, # general orient.: compare RollRess and WxR
                 Slip = slip
)

# Write wheel coords, force, torque
def liveDataOut(bodyID):

    bstate= O.bodies[bodyID].state
    x ,  y,  z = bstate.pos
    vx, vy, vz = bstate.vel
    wx, wy, wz = bstate.angVel
    fx, fy, fz = O.forces.f(bodyID)
    tx, ty, tz = O.forces.t(bodyID)
    vrot = wy*wheelRadEff
    slip = 0.0
    if vrot != 0.0:
        slip = (vrot - vx)/(vrot)
    if slip < -10: slip = -10
    if slip >  10: slip =  10

    global firstWrite
    if firstWrite:
        f = open("Data_Output.csv", "w")
        f.write("Time,x,y,z,Fx,Fy,Fz,Tx,Ty,Tz,Vx,Vy,Vz,Wx,Wy,Wz,slip\n")
        firstWrite = False
    else:
        f = open("Data_Output.csv", "a")

    f.write(f"{O.time:.4f},{x:.3g},{y:.3g},{z:.3g},{fx:.6g},{fy:.6g},{fz:.6g},"
            f"{tx:.6g},{ty:.6g},{tz:.6g},{vx:.6g},{vy:.6g},{vz:.6g},"
            f"{wx:.6g},{wy:.6g},{wz:.6g},{slip:.6g}\n")

    f.close()

firstWrite = True

def saveOvitoAndVTK():
    vtk_export.exportFacets(ids = wheelBodyPartsIds)
    if visSaveSph:
        if visSaveSphSingleFile:
            myappend = False if ostep == 0 else True
            exportOVITO(f"{visSaveSphBname}.dump", append=myappend)
        else:
            myappend = False
            exportOVITO(f"{visSaveSphBname}{ostep:08d}.dump", append=myappend)

def exportOVITO(filename, append=False):
    """
    Export YADE spheres to OVITO-compatible LAMMPS dump format.
    Can be called repeatedly to produce a trajectory.
    """

    global ostep
    mode = 'a' if append else 'w'
    f = open(filename, mode)

    # collect only real particles (skip walls, facets, clumps container bodies)
    spheres = [b for b in O.bodies if isinstance(b.shape, Sphere)]

    # --- Header (LAMMPS dump style) ---
    f.write("ITEM: TIMESTEP\n")
    f.write(f"{ostep}\n")
    ostep = ostep + 1

    f.write("ITEM: NUMBER OF ATOMS\n")
    f.write(f"{len(spheres)}\n")

    # simulation box
    minX,minY,minZ = O.cell.refSize if O.periodic else (
        boxCenterX-hboxX, boxCenterY-hboxY, boxCenterZ-boxHeight/2)
    maxX,maxY,maxZ = (10,10,10) if O.periodic else (
        boxCenterX+hboxX, boxCenterY+hboxY, boxCenterZ+boxHeight/2)

    f.write("ITEM: BOX BOUNDS pp pp pp\n")
    f.write(f"{minX} {maxX}\n")
    f.write(f"{minY} {maxY}\n")
    f.write(f"{minZ} {maxZ}\n")

    # columns OVITO will read
    if visSaveSphDetailed:
        f.write("ITEM: ATOMS id type x y z vx vy vz radius fx fy fz wx wy wz\n")
    else:
        f.write("ITEM: ATOMS id x y z radius\n")

    # --- Particle data ---
    for b in spheres:
        state = b.state

        x,y,z = state.pos
        r = b.shape.radius

        if visSaveSphDetailed:
            vx,vy,vz = state.vel
            wx,wy,wz = state.angVel
            fx,fy,fz = O.forces.f(b.id)
            typ = b.material.id
            f.write(
                f"{b.id} {typ} "
                f"{x:.3g} {y:.3g} {z:.3g} "
                f"{vx:.6g} {vy:.6g} {vz:.6g} "
                f"{r:.3g} "
                f"{fx:.6g} {fy:.6g} {fz:.6g} "
                f"{wx:.6g} {wy:.6g} {wz:.6g}\n"
            )
        else:
            f.write(f"{b.id} {x:.3g} {y:.3g} {z:.3g} {r:.3g}\n")
    f.close()

ostep = 0

from yade import plot
plot.plots={
    't':('z', None, 'x'), 't ':('Vz' ,'WxR', 'Vx'),
    't  ':('Fz', 'mg'), 't   ':('GrTr', 'Fx', 'RollRes') #, None, 'Slip')
}
# show the plot on the screen, and update while the simulation runs
plot.plot(subPlots=True)

if visSaveInt != 0:
    from pathlib import Path
    vis_dir = Path('vis/')
    vis_dir.mkdir(parents=True, exist_ok=True)
    print(f"Visualization directory '{vis_dir}' ensured to exist.")

    from yade import export
    vtk_export = export.VTKExporter('vis/export')

# Create rectangular open-top box
O.bodies.append(geom.facetBox((boxCenterX, boxCenterY, boxCenterZ),
                              (hboxX, hboxY, boxHeight/2),
                              wallMask=31, material=idBoxMat),)
nf_box = len(O.bodies) # ! no extra body for complete box
print(f"Created open-top box, {nf_box} facets.")

# Inverse shift to get correct initial wheel position after reorienting wheel coordinate system
shiftXYZ = Vector3(initX, initY, initZ)
if x_new != 'x' or z_new != 'z':
    R = calcRotMatrix(x_new, z_new)
    shiftXYZ = reorientShift(shiftXYZ, R)

# Import wheel from STL (or OBJ) file
from yade import ymport
from yade import config
yade_ver = config.revision
print(yade_ver)

if yade_ver == "2020.01a":
    facets = ymport.stl(
        stlFile,
        material = idWheelMat,
        dynamic = None,
        fixed = False,
        noBound = False
    )
else:
    stlShift = stlScale*Vector3(-coX, -coY, -coZ) + shiftXYZ
    facets = ymport.stl(
        stlFile,
        scale = stlScale,
        shift = stlShift,
        material = idWheelMat,
        dynamic = None,
        fixed = False,
        noBound = False
    )
print(f"Imported {len(facets)} facets from \"{stlFile}\" file.")

# swap coordinats if needed, x_new is forward, z_new is up
if x_new != 'x' or z_new != 'z':

    print(f"Reorienting the wheel for driving: forward: {x_new}, up: {z_new}")
    facets = reorientWheelFacets(facets, R)

if fixNormals:
    print("Checking facet normals...")
    facets = fix_normals(facets)

# Assign mass before clumping
# (required, not used - body properties defined next are used)
for f in facets:
    f.state.mass    = 1.0
    f.state.inertia = (1,1,1)
    f.shape.wire = False

# Create body as a rigid clump, define properties
wheelBodyId, wheelBodyPartsIds = O.bodies.appendClumped(facets)
wheelBody = O.bodies[wheelBodyId]
wheelBody.state.mass    = wheelMass
wheelBody.state.inertia = wheelInertia
wheelBody.state.blockedDOFs = 'xyzXYZ'
wheelBody.state.vel = Vector3(0,0,0)
wheelBody.state.angVel = Vector3(0,0,0)

if yade_ver == "2020.01a":
    # Both YADE and python
    utils.random.seed(rndSeed)
    random.seed(rndSeed)
    wheelBody.state.pos = Vector3(initX, initY, initZ)

nf = len(O.bodies);
print(f"Number of facets (box and wheel): {nf-1}") # there is one extra body for wheel

sp = pack.SpherePack()
if part_gen == "meanFuzz":
    # Add particles inside the box (not on top)
    sp.makeCloud(
        # bottom left corner
        (boxCenterX - hboxX, boxCenterY - hboxY, boxCenterZ - hboxZ),
        # top right corner
        (boxCenterX + hboxX, boxCenterY + hboxY, boxCenterZ - hboxZ + boxHeight*pck),
        rMean=rMean,
        rRelFuzz=rRelFuzz,
        seed=rndSeed
    )
    sp.toSimulation(material=idSphereMat)
    partnum = len(sp)
elif part_gen == "clumpCloud":
    # generate randomly spheres with uniform radius distribution
    S1r = pack.SpherePack([((0,0,0),pscale*rmin)])
    S1  = pack.SpherePack([((0,0,0),pscale*rmed)])
    S1R = pack.SpherePack([((0,0,0),pscale*rmax)])
    if yade_ver == "2020.01a":
        sp.seed = rndSeed
        sp.makeClumpCloud(
            # bottom left corner
            (boxCenterX - hboxX, boxCenterY - hboxY, boxCenterZ - hboxZ),
            # top right corner
            (boxCenterX + hboxX, boxCenterY + hboxY, boxCenterZ - hboxZ + boxHeight*pck),
            [S1, S1r, S1R],
            num = round(80000/pscale**3))
    else:
        sp.makeClumpCloud(
            # bottom left corner
            (boxCenterX - hboxX, boxCenterY - hboxY, boxCenterZ - hboxZ),
            # top right corner
            (boxCenterX + hboxX, boxCenterY + hboxY, boxCenterZ - hboxZ + boxHeight*pck),
            [S1, S1r, S1R],
            num = round(80000/pscale**3), seed = rndSeed)
    sp.toSimulation(color=(.6,.57,.53))
    partnum = len(sp)

print(f"Number of particles generated: {partnum}")

# Time step & number of iterations to settle particles and to end simulation
recDt = 0.5 * utils.PWaveTimeStep()
print(f"Recommened half PWave time step: {recDt:.3g}")
if 'timeStep' in data['sim']:
    paramFileDt = data['sim']['timeStep']
    if paramFileDt == 0.0:
        O.dt = recDt
    else:
        O.dt = paramFileDt
else:
    O.dt = recDt
print(f"Actual time step: {O.dt}")

settleIt = round(settleTime / O.dt)
endIt    = round(endTime    / O.dt)

# Engines, start with necessary
rFTrecorderString='rFTrecorder(' + str(wheelBodyId) + ')'
liveDataOutString='liveDataOut(' + str(wheelBodyId) + ')'
phys = "Frictional"
phys = "Mindlin"
if phys == "Mindlin":
    O.engines = [
        ForceResetter(),
        InsertionSortCollider([Bo1_Sphere_Aabb(), Bo1_Facet_Aabb(), Bo1_Box_Aabb()]),
        InteractionLoop(
            [Ig2_Sphere_Sphere_ScGeom(), Ig2_Facet_Sphere_ScGeom()],
            [Ip2_FrictMat_FrictMat_MindlinPhys(en=pp_en, krot = pp_krot,
                                               label='ContactModel')],
            [Law2_ScGeom_MindlinPhys_Mindlin(label='Mindlin',includeMoment=True)]
        )
    ]
else:
    O.engines = [
        ForceResetter(),
        InsertionSortCollider([Bo1_Sphere_Aabb(), Bo1_Facet_Aabb()]),
        InteractionLoop(
            [Ig2_Sphere_Sphere_ScGeom(), Ig2_Facet_Sphere_ScGeom()],
            [Ip2_FrictMat_FrictMat_FrictPhys()],
            [Law2_ScGeom_FrictPhys_CundallStrack()]
        )
    ]

# Integrator, necessary
O.engines += [NewtonIntegrator(gravity = (0,0,-acc_g), damping = 0.0,
                               exactAsphericalRot=exactARot)]

# Adjust wheel height to the top of soil
O.engines += [PyRunner(command = 'setInMotion()', firstIterRun = settleIt)]

# Record and plot data
dataSaveIter = round(dataSaveInt/O.dt)
O.engines += [PyRunner(command = rFTrecorderString, iterPeriod = dataSaveIter,
                       firstIterRun = 0)]
O.engines += [PyRunner(command = liveDataOutString, iterPeriod = dataSaveIter,
                       firstIterRun = 0)]
O.engines += [PyRunner(command = 'plot.saveDataTxt("plot.txt")',
                   firstIterRun = endIt-1)]
O.engines += [PyRunner(command = 'plot.plot(noShow=True).savefig("plot.pdf")',
                       firstIterRun = endIt-1)]

# Timing info
progReportIter = round(progRepInt/O.dt)
O.engines += [PyRunner(command='printVirtTime()', iterPeriod = progReportIter)]
O.engines += [PyRunner(command='timeend = time.time()', firstIterRun = endIt-1)]
O.engines += [PyRunner(command='timeCalculator()', firstIterRun = endIt-1)]
if visSaveInt != 0:
    visSaveIter = round(visSaveInt/O.dt)
    O.engines += [PyRunner(command = 'saveOvitoAndVTK()',
                           iterPeriod = visSaveIter)]


O.stopAtIter = endIt
#O.stopAtIter = 4 ###

if GUImode:
    O.saveTmp()               # save simulation to memory
    from yade import qt       # set view direction
    v = qt.View()
    v.lookAt = (0, 100, 0)
    v.upVector  = (0, 0, 1)
    v.center()
else:
    O.run(wait=True)
