from yade import *
import math

# Wheel properties and initial coordinates
wheelMass = 500.0                  # Rigid-body mass
wheelInertia = (1,1,1)             # Inertia tensor
startX      =  0.0                 # Starting x-coordinate
startY      = -1.5                 # Starting y-coordinate
startZ      =  1.8                 # Drop height
startVelY   =  0.0
startWelX   =  25.0

# Wheel read from STL/OBJ file
stlFile = "cylinder.stl"
if stlFile == "lugged_whel.stl":
    stlScale = 0.01
    stlShift = Vector3(-50*stlScale/2, startY, startZ)
elif stlFile == "cylinder.stl":
    stlScale = 1.0
    stlShift = Vector3(0, startY, startZ)

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

def setConstantVelY(bodyID, value):
    # Set y-component of body linear velocity
    O.bodies[bodyID].state.vel[1] = value

def setConstantWelX(bodyID, value):
    # Set x-component of body angular velocity
    O.bodies[bodyID].state.angVel[0] = value

# Main program
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

# Create body as a rigid clump, define properties
wheelBodyId, wheelBodyPartsIds = O.bodies.appendClumped(facets)
wheelBody = O.bodies[wheelBodyId]
wheelBody.state.mass    = wheelMass
wheelBody.state.inertia = wheelInertia
wheelBody.state.blockedDOFs = 'xYZ'
wheelBody.state.vel = Vector3(0,startVelY,0)
wheelBody.state.angVel = Vector3(startWelX,0,0)

# Create rectangular open-top box
O.bodies.append(geom.facetBox((0, 0, boxHeight/2),
                              (hboxX, hboxY, boxHeight/2),
                              wallMask=31))

# Add particles inside the box (not on top)
sp = pack.SpherePack()
sp.makeCloud(
    (-hboxX*0.9, -hboxY*0.9, 0.05),      # slightly inside box
    ( hboxX*0.9,  hboxY*0.9, boxHeight*0.8),  # well below top edge
    rMean=rMean,
    rRelFuzz=rRelFuzz,
    seed=rndSeed
)
sp.toSimulation(material=idSphereMat)

# Engines
setVelYCall='setConstantVelY(' + str(wheelBodyId) + ',' + str( startVelY) + ')'
setWelXCall='setConstantWelX(' + str(wheelBodyId) + ',' + str(-startWelX) + ')'
O.engines = [
    ForceResetter(),
    InsertionSortCollider([Bo1_Sphere_Aabb(), Bo1_Facet_Aabb()]),
    InteractionLoop(
        [Ig2_Sphere_Sphere_ScGeom(), Ig2_Facet_Sphere_ScGeom()],
        [Ip2_FrictMat_FrictMat_FrictPhys()],
        [Law2_ScGeom_FrictPhys_CundallStrack()]
    ),
    # PyRunner(command=setVelYCall, iterPeriod=1),
    PyRunner(command=setWelXCall, iterPeriod=1),
    NewtonIntegrator(gravity=(0,0,-9.81), damping=0.3)
]


O.dt = 0.5 * utils.PWaveTimeStep()

# save simulation to memory
O.saveTmp()
O.stopAtIter=10000
