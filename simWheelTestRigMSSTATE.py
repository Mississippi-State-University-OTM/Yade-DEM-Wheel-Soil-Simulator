timestart = time.time()

param_file = sys.argv[1] if len(sys.argv) > 1 else 'paramsKyoto.json'
print(f'Parameter file:\n "{param_file}"')

import json
with open(param_file, 'r') as f:
    data = json.load(f)

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
if 'vis' in data['sim']:
    visSaveInt = data['sim']['vis']['saveInt'] # Sim. time interval to save visualization snapshots, 0 = don't save
    visSaveSph = data['sim']['vis']['spheres'] # True: save spheres into VTK (many spheres = lot of disk space)
else:
    visSaveInt = 0.0
GUImode      = data['sim']['GUImode']            # True: run with GUI
stlFile      = data['wheel']['stlFile']          # Wheel STL/OBJ file

stlScale = 1.0
if 'stlScaleUp' in data['wheel']:
    stlScale = data['wheel']['stlUnitsScale']    # Ratio to multiply the coordinates from STL file by
stlShift = Vector3(initX, initY, initZ)

# Particle parameters
# initial placement of particles up to 0.8 (= 80%) of box' height
pck      = data['particles']['pck']
rndSeed  = data['particles']['rndSeed']
part_gen = data['particles']['generation']
pscale   = data['particles']['scale']
print(f"Particles:")
print(f" Packing level up to z = {pck} m")
print(f" Generation method: {part_gen}, random seed: {rndSeed=}")
print(f" Scale-up particle sizes: {pscale} X original size (to speed up simulation")
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
    smax = boxCenterZ - hboxZ      # stores highest particle surface
    idx = None
    for i in range(wheelBodyId + 1, wheelBodyId + partnum + 1):
        z = O.bodies[i].state.pos[2]
        r = O.bodies[i].shape.radius
        top = z ## + r
        if top > smax:
            smax = top
            idx = i
    print(f"Wheel repositioned to reach the highest particle surface of {smax:.3f} m.")
    r = O.bodies[idx].shape.radius
    new_wheel_center_z = smax  + r + wheelRadEff + .0001
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

    global firstPrint, prevTime, prev
    if firstPrint:
        print(simperc, file = sys.stderr)
        firstPrint = False
    else:
        currTime = time.time()
        from_last_time = currTime - prevTime
        from_last_sim = curr - prev
        rem = end - curr
        est = from_last_time/from_last_sim * rem
        delta = timedelta(seconds=round(est))
        print(f"{simperc}          Est. remaining: {delta}", file = sys.stderr)

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
            allVerts.append(v)
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
        fCenter = (v[0] + v[1] + v[2]) / 3.0
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

def save_vtk_data():
    # 'what' is a dictionary defining what to export
    vtk_export.exportFacets(what = {'color': 'b.shape.color'})
    if visSaveSph:
        vtk_export.exportSpheres()

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

# Main program
#
# Create rectangular open-top box
O.bodies.append(geom.facetBox((boxCenterX, boxCenterY, boxCenterZ),
                              (hboxX, hboxY, boxHeight/2),
                              wallMask=31, material=idBoxMat),)
nf_box = len(O.bodies) # ! no extra body for complete box
print(f"Created open-top box, {nf_box} facets.")

# Import wheel from STL (or OBJ) file
from yade import ymport
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
    O.dt = data['sim']['timeStep']
else:
    O.dt = recDt
print(f"Actual time step: {O.dt}")

settleIt = round(settleTime / O.dt)
endIt    = round(endTime    / O.dt)

# Engines, start with necessary
rFTrecorderString='rFTrecorder(' + str(wheelBodyId) + ')'
phys = "Frictional"
phys = "Mindlin"
if phys == "Mindlin":
    O.engines = [
        ForceResetter(),
        InsertionSortCollider([Bo1_Sphere_Aabb(), Bo1_Facet_Aabb(), Bo1_Box_Aabb()]),
        InteractionLoop(
            [Ig2_Sphere_Sphere_ScGeom(), Ig2_Facet_Sphere_ScGeom(),
             Ig2_Box_Sphere_ScGeom(), Ig2_Box_Sphere_ScGeom6D()],
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
O.engines += [NewtonIntegrator(gravity = (0,0,-acc_g), damping = 0.0)]

# Adjust wheel height to the top of soil
O.engines += [PyRunner(command = 'setInMotion()', firstIterRun = settleIt)]

# Record and plot data
dataSaveIter = round(dataSaveInt/O.dt)
O.engines += [PyRunner(command = rFTrecorderString, iterPeriod = dataSaveIter,
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
    O.engines += [PyRunner(command='save_vtk_data()', iterPeriod = visSaveIter)]


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
