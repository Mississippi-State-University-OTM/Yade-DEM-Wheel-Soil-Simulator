timestart = time.time()

import json
with open('params_MSSTATE.json', 'r') as f:
    data = json.load(f)

# Wheel properties and initial coordinates from JSON
valLinVel    = data['wheel']['initVals']['vy']   # set initial value of wheel Vy
fixLinVel    = data['wheel']['constrains']['vy'] # True: fix the initial Vy over time
valAngVel    = data['wheel']['initVals']['wx']   # set initial value of wheel Wx
fixAngVel    = data['wheel']['constrains']['wx'] # True: fix the initial Wy over time
wheelRadEff  = data['wheel']['radEff']           # for Gross Traction, Slip, & height above settled soil
acc_g        = 9.81                              # acceleration of gravity
wheelMass    = data['wheel']['mass']             # Rigid-body mass
wheelInertia = (data['wheel']['Ixx'], 1, 1)      # Inertia tensor
initX        = data['wheel']['initVals']['x']    # Initial x-coordinate
initY        = data['wheel']['initVals']['y']    # Initial y-coordinate
initZ        = data['wheel']['initVals']['z']    # Wheel waiting-for-soil-to-settle height
settleTime   = data['sim']['settleTime']         # Time to settle particles
endTime      = data['sim']['endTime']            # Total simulated time

# Wheel read from STL/OBJ file
stlFile = "cylinder.stl"
#stlFile = "lugged_wheel_cadquery_ascii.stl"
#stlFile = "lugged_wheel_trimesh_ascii.stl"
stlScale = 1.0
stlShift = Vector3(initX, initY, initZ)
if stlFile == "lugged_wheel.stl":
    stlShift = Vector3(-0.4 + initX, initY, initZ)

# Particle parameters
rMean    = data['particles']['rMean']
rRelFuzz = data['particles']['rRelFuzz']
rndSeed  = data['particles']['rndSeed']
print(f"Particles: Mean Radius: {rMean} m, {rRelFuzz=}, {rndSeed=}")

# Box interior region (open top)
hboxX     = data['box']['width']  / 2 # half width
hboxY     = data['box']['length'] / 2 # half lenght
boxHeight = data['box']['height']     # height of box
print(f"Box dimensions: {hboxX*2} x {hboxY*2} x {boxHeight} m (width x lenght x height)")

# Materials
matWheelParams  = data['materials'][data['wheel']    ['material']]
matSphereParams = data['materials'][data['particles']['material']]
matBoxParams    = data['materials'][data['box'      ]['material']]
def createFrictMaterial(params):
    return FrictMat(young         = params['young'],
                    poisson       = params['poisson'],
                    frictionAngle = params['frictionAngle'])
matWheel  = createFrictMaterial(matWheelParams)
matSphere = createFrictMaterial(matSphereParams)
matBox = createFrictMaterial(matBoxParams)
idWheelMat  = O.materials.append(matWheel)
idSphereMat = O.materials.append(matSphere)
idBoxMat = O.materials.append(matBox)

# Reposition the wheel to the top surface of soil and set it in motion
def setInMotion():
    smax = 0      # stores highest particle surface
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
        wheelBody.state.vel = Vector3(0,valLinVel,0)
        wheelBody.state.angVel = Vector3(valAngVel,0,0)
        wheelBody.state.blockedDOFs = 'xyXYZ'
    elif fixAngVel: # z and y free
        wheelBody.state.blockedDOFs = 'xXYZ'
        wheelBody.state.angVel = Vector3(valAngVel,0,0)
    elif fixLinVel: # z and wx free
        wheelBody.state.vel = Vector3(0,valLinVel,0)
        wheelBody.state.blockedDOFs = 'xyYZ'
    else:
        wheelBody.state.blockedDOFs = 'yYZ'

# Calculate execution time
def timeCalculator():
    calc_time_total = timeend - timestart
    report = f"Execution time {calc_time_total:.2f} s for {O.time:.2f} s simulation."
    print(report, file = sys.stderr)
    f = open('exec_time.txt','w')
    f.write(report + "\n")
    f.close()

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
        print(" Flipped ", count_flipped, " facets.")

    return facetList

# Record wheel coords, force, torque
def rFTrecorder(bodyID):
    bstate= O.bodies[bodyID].state
    posy = bstate.pos[1]
    posz = bstate.pos[2]
    vely = bstate.vel[1]
    velz = bstate.vel[2]
    welx = bstate.angVel[0]
    fy=O.forces.f(bodyID)[1]
    fz=O.forces.f(bodyID)[2]
    tx=O.forces.t(bodyID)[0]
    gTr = tx / wheelRadEff
    vrot = -welx*wheelRadEff
    try: slip = (vrot - vely)/(vrot)
    except: slip = 0
    if slip < -10: slip = -10
    if slip >  10: slip =  10
    plot.addData(t = O.time,
                 At = O.time,
                 y = posy, z = posz,
                 Vy = vely, Vz = velz, Wx = welx, WxR = -welx*wheelRadEff,
                 Fy = fy, Fz = fz, Tx = tx,
                 mg = wheelMass * acc_g,
                 GrTr = gTr,
                 RollRes = gTr - fy,
                 Slip = slip
)

from yade import plot
plot.plots={
    't':('z', None, 'y'), 't ':('Vz' ,'WxR', 'Vy'),
    't  ':('Fz', 'mg'), 't   ':('GrTr', 'Fy', 'RollRes') #, None, 'Slip')
}
# show the plot on the screen, and update while the simulation runs
plot.plot(subPlots=True)

# Main program
#
# Create rectangular open-top box
O.bodies.append(geom.facetBox((0, 0, boxHeight/2),
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
print(f"Number of facets (box and wheel): {nf}")

# Add particles inside the box (not on top)
sp = pack.SpherePack()
sp.makeCloud(
    (-hboxX, -hboxY, 0.0),            # slightly inside box
    ( hboxX,  hboxY, boxHeight*0.8),  # well below top edge
    rMean=rMean,
    rRelFuzz=rRelFuzz,
    seed=rndSeed
)
sp.toSimulation(material=idSphereMat)
partnum = len(sp)
print(f"Number of generated particles: {partnum}")

# Time step & number of iterations to settle particles and to end simulation
O.dt = 0.5 * utils.PWaveTimeStep()
settleIt = round(settleTime / O.dt)
endIt    = round(endTime    / O.dt)

# Engines, start with necessary
rFTrecorderString='rFTrecorder(' + str(wheelBodyId) + ')'
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
O.engines += [NewtonIntegrator(gravity = (0,0,-acc_g), damping = 0.3)]

# Adjust wheel height to the top of soil
O.engines += [PyRunner(command = 'setInMotion()', firstIterRun = settleIt)]

# Record and plot data
O.engines += [PyRunner(command = rFTrecorderString, iterPeriod = 5,
                   firstIterRun = 0)]
O.engines += [PyRunner(command = 'plot.saveDataTxt("plot.txt")',
                   firstIterRun = endIt-1)]
O.engines += [PyRunner(command = 'plot.plot(noShow=True).savefig("plot.pdf")',
                       firstIterRun = endIt-1)]

# Timing info
O.engines += [PyRunner(command='timeend = time.time()', firstIterRun = endIt-1)]
O.engines += [PyRunner(command='timeCalculator()', firstIterRun = endIt-1)]

O.stopAtIter = endIt

GUImode = True
GUImode = False
if GUImode:
    O.saveTmp()               # save simulation to memory
    from yade import qt       # set view direction
    v = qt.View()
    v.lookAt = (-100, 0, 0)
    v.upVector  = (0, 0, 1)
    v.center()
else:
    O.run(wait=True)
