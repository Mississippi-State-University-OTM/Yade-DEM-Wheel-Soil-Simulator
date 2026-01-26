timestart = time.time()

# Wheel properties and initial coordinates
acc_g        = 9.81                # acceleration of gravity
wheelMass    = 500.0               # Rigid-body mass
wheelInertia = (1,1,1)             # Inertia tensor
initX        =  0.0                # Initial x-coordinate
initY        = -1.5                # Initial y-coordinate
initZ        =  1.8                # Wheel waiting-for-soil-to-settle height
initVelY     =  1.0                # set initial value of wheel Vy
fixVelY      = False               # True: fix the initial Vy over time
initWelX     = -17.0               # set initial value of wheel Wx
fixWelX      = True                # True: fix the initial Wy over time
settleTime   = 0.5                 # Time to settle particles
endTime      = 5.0                 # Total simulated time

# Wheel read from STL/OBJ file
stlFile = "lugged_wheel.stl"
stlFile = "cylinder.stl"
if stlFile == "lugged_wheel.stl":
    stlScale = 0.01
    stlShift = Vector3(-50*stlScale/2 + initX, initY, initZ)
elif stlFile == "cylinder.stl":
    stlScale = 1.0
    stlShift = Vector3(initX, initY, initZ)

# Particle parameters
rMean    = 0.05
rRelFuzz = 0.3
rndSeed  = 123

# Box interior region (open top)
hboxX     = 0.5   # half width
hboxY     = 2.0   # half lenght
boxHeight = 1.5   # height of box

# Materials
matWheel = FrictMat(young=1e7, poisson=0.3, frictionAngle=0.5)
matSphere = FrictMat(young=1e7, poisson=0.3, frictionAngle=0.6)
idWheelMat = O.materials.append(matWheel)
idSphereMat = O.materials.append(matSphere)

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

# move wheel to the surface of soil
def heightAdjuster():
    smax = 0      # stores highest particle surface
    idx = None
    for i in range(wheelBodyId + 1, wheelBodyId + partnum): ## + 1):
        z = O.bodies[i].state.pos[2]
        r = O.bodies[i].shape.radius
        top = z ## + r
        if top > smax:
            smax = top
            idx = i
    print(f"Wheel repositioned to reach the highest particle surface of {smax:.3f} m.")
    r = O.bodies[idx].shape.radius
    new_wheel_center_z = smax  + r + wheelRad + .0001
    O.bodies[wheelBodyId].state.pos = Vector3(initX, initY, new_wheel_center_z)
    if fixVelY and fixWelX: # z free
        wheelBody.state.vel = Vector3(0,initVelY,0)
        wheelBody.state.angVel = Vector3(initWelX,0,0)
        O.bodies[wheelBodyId].state.blockedDOFs = 'xyXYZ'
    elif fixWelX: # z and y free
        O.bodies[wheelBodyId].state.blockedDOFs = 'xXYZ'
        wheelBody.state.angVel = Vector3(initWelX,0,0)
    elif fixVelY: # z and wx free
        wheelBody.state.vel = Vector3(0,initVelY,0)
        O.bodies[wheelBodyId].state.blockedDOFs = 'xyYZ'
    else:
        import sys
        print(f"Error: For now, only fixVelY and/or fixWelX can be fixed.\n",
              file = sys.stderr)
        sys.exit(1)

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
    plot.addData(t = O.time,
                 y = posy, z = posz,
                 i=O.time,
                 Vy = vely, Vz = velz,
                 j=O.time,
                 Wx = welx,
                 Fy = fy,
                 k=O.time,
                 Fz = fz,
                 mg = wheelMass*acc_g,
                 GrossTr = -tx/wheelRad)


# Main program
#
# Create rectangular open-top box
O.bodies.append(geom.facetBox((0, 0, boxHeight/2),
                              (hboxX, hboxY, boxHeight/2),
                              wallMask=31))
nb = len(O.bodies)
nf_box = nb # ! no extra body for complete box
print(f"Created open-top box, {nf_box} facets.")
print(f"Number of bodies (box): {nb}")

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
print("... facet normals validated / corrected.")

# Assign mass before clumping
# (required, not used - body properties defined next are used)
for f in facets:
    f.state.mass    = 1.0
    f.state.inertia = (1,1,1)
    f.shape.wire = False

# TODO: find wheelRad from facets
wheelRad = 0.5

# Create body as a rigid clump, define properties
wheelBodyId, wheelBodyPartsIds = O.bodies.appendClumped(facets)
wheelBody = O.bodies[wheelBodyId]
wheelBody.state.mass    = wheelMass
wheelBody.state.inertia = wheelInertia
wheelBody.state.blockedDOFs = 'xyzXYZ'
wheelBody.state.vel = Vector3(0,0,0)
wheelBody.state.angVel = Vector3(0,0,0)

nb = len(O.bodies);
print(f"Number of bodies (box + wheel, no paricles): {nb}")

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

nb=len(O.bodies);
print(f"Number of bodies (box, wheel, particles) {nb}")

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

# Fix vels if prescribed
O.dt = 0.5 * utils.PWaveTimeStep()
settleIt = round(settleTime / O.dt)
endIt    = round(endTime    / O.dt)

# Adjust wheel height to the top of soil
O.engines += [PyRunner(command = 'heightAdjuster()', firstIterRun = settleIt)]

# Record and plot data
from yade import plot
O.engines += [PyRunner(command = rFTrecorderString, iterPeriod = 5,
                   firstIterRun = 0)]
O.engines += [PyRunner(command = 'plot.saveDataTxt("plot.txt")',
                   firstIterRun = endIt-1)]
O.engines += [PyRunner(command = 'plot.plot(noShow=True).savefig("plot.pdf")',
                       firstIterRun = endIt-1)]
plot.plots={
    't':('z'), 't ':('Vy' ,'Vz'), 't  ':('Fz', 'mg'), 't   ':('Fy')
}
# show the plot on the screen, and update while the simulation runs
plot.plot(subPlots=True)

# Timing info
O.engines += [PyRunner(command='timeend = time.time()',
                       firstIterRun = endIt-1)]
O.engines += [PyRunner(command='timeCalculator()',
                       firstIterRun = endIt-1)]

def timeCalculator():
    time0stofinish = timeend - timestart
    print('Total execution time {0} s'.format(time0stofinish))
    f = open('exec_time.txt','w')
    f.write('0s to finish: {0} s\n'.format(time0stofinish))
    f.close()

O.stopAtIter = endIt

GUImode = False
if GUImode:
    # save simulation to memory
    O.saveTmp()
else:
    O.run(wait=True)
