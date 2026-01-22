
from yade import *
import math

###############################################
# PARAMETERS
###############################################
radius   = 0.5
height   = 2.0
segments = 40
cylMass  = 1000.0
cylInertia = (1,1,1)          # override later as clump inertia
startHeight = 3.0             # cylinder starting height

# Particle parameters
rMean    = 0.05
rRelFuzz = 0.3

# Box interior region (open top)
boxX = 2.0
boxY = 2.0
boxZ = 1.5   # height of box

###############################################
# MATERIALS
###############################################
matCyl = FrictMat(young=1e7, poisson=0.3, frictionAngle=0.5)
matSphere = FrictMat(young=1e7, poisson=0.3, frictionAngle=0.6)

idCylMat = O.materials.append(matCyl)
idSphereMat = O.materials.append(matSphere)

###############################################
# GEOMETRY HELPERS
###############################################
def ringPoint(angle, r, z):
    return Vector3(r*math.cos(angle), r*math.sin(angle), z)

def triangulate_cap(z, segments, r, material, upward):
    """Create triangulated circular cap with correct normal direction."""
    facets = []
    center = Vector3(0,0,z)
    dth = 2*math.pi/segments
    for i in range(segments):
        a1 = i*dth
        a2 = (i+1)*dth
        p1 = ringPoint(a1, r, z)
        p2 = ringPoint(a2, r, z)
        if upward:
            tri = [p1, p2, center]
        else:
            tri = [p2, p1, center]
        facets.append(facet(tri, material=material))
    return facets

###############################################
# BUILD CLOSED CYLINDER (side + top + bottom)
###############################################
facets = []

# ---- Side facets ----
dth = 2*math.pi/segments
for i in range(segments):
    a1 = i*dth
    a2 = (i+1)*dth
    b1 = ringPoint(a1, radius, 0)
    b2 = ringPoint(a2, radius, 0)
    t1 = ringPoint(a1, radius, height)
    t2 = ringPoint(a2, radius, height)

    facets.append(facet([b1, b2, t1], material=idCylMat))
    facets.append(facet([b2, t2, t1], material=idCylMat))

# ---- Caps ----
facets += triangulate_cap(0, segments, radius, idCylMat, upward=False)  # bottom
facets += triangulate_cap(height, segments, radius, idCylMat, upward=True)  # top

###############################################
# ASSIGN MASS BEFORE CLUMPING (required!)
###############################################
# YADE 2022.01 requires non‑zero mass for clumped facets (developer‑confirmed).
for f in facets:
    f.state.mass    = 100.0
    f.state.inertia = (1,1,1)

###############################################
# CREATE THE RIGID CLUMP
###############################################
ret = O.bodies.appendClumped(facets)
clumpId = ret[0]
clump = O.bodies[clumpId]

# Override global rigid-body properties
clump.state.mass    = cylMass
clump.state.inertia = cylInertia
clump.state.pos     = Vector3(0,0,startHeight)

# No initial angular velocity
clump.state.angVel = Vector3(0,0,0)
clump.state.vel = Vector3(0,0,0)

# Allow *ONLY* translation in Z direction: block X,Y & all rotations including about Z
clump.state.blockedDOFs = 'xyXYZ'

###############################################
# BUILD OPEN-TOP FACET BOX
###############################################
# Bottom
O.bodies.append(facet([
    (-boxX, -boxY, 0),
    ( boxX, -boxY, 0),
    (-boxX,  boxY, 0)
], material=idCylMat))
O.bodies.append(facet([
    ( boxX, -boxY, 0),
    ( boxX,  boxY, 0),
    (-boxX,  boxY, 0)
], material=idCylMat))

# Walls (no top)
# Left
O.bodies.append(facet([
    (-boxX, -boxY, 0),
    (-boxX,  boxY, 0),
    (-boxX, -boxY, boxZ)
], material=idCylMat))
O.bodies.append(facet([
    (-boxX,  boxY, 0),
    (-boxX,  boxY, boxZ),
    (-boxX, -boxY, boxZ)
], material=idCylMat))

# Right
O.bodies.append(facet([
    (boxX, -boxY, 0),
    (boxX, -boxY, boxZ),
    (boxX,  boxY, 0)
], material=idCylMat))
O.bodies.append(facet([
    (boxX,  boxY, 0),
    (boxX, -boxY, boxZ),
    (boxX,  boxY, boxZ)
], material=idCylMat))

# Front
O.bodies.append(facet([
    (-boxX, -boxY, 0),
    (-boxX, -boxY, boxZ),
    ( boxX, -boxY, 0)
], material=idCylMat))
O.bodies.append(facet([
    ( boxX, -boxY, 0),
    (-boxX, -boxY, boxZ),
    ( boxX, -boxY, boxZ)
], material=idCylMat))

# Back
O.bodies.append(facet([
    (-boxX, boxY, 0),
    ( boxX, boxY, 0),
    (-boxX, boxY, boxZ)
], material=idCylMat))
O.bodies.append(facet([
    ( boxX, boxY, 0),
    ( boxX, boxY, boxZ),
    (-boxX, boxY, boxZ)
], material=idCylMat))

###############################################
# PARTICLES INSIDE THE BOX (NOT ON TOP)
###############################################
sp = pack.SpherePack()
sp.makeCloud(
    (-boxX*0.9, -boxY*0.9, 0.05),      # slightly inside box
    ( boxX*0.9,  boxY*0.9, boxZ*0.8),  # well below top edge
    rMean=rMean,
    rRelFuzz=rRelFuzz
)
sp.toSimulation(material=idSphereMat)

###############################################
# ENGINES
###############################################
O.engines = [
    ForceResetter(),
    InsertionSortCollider([Bo1_Sphere_Aabb(), Bo1_Facet_Aabb()]),
    InteractionLoop(
        [Ig2_Sphere_Sphere_ScGeom(), Ig2_Facet_Sphere_ScGeom()],
        [Ip2_FrictMat_FrictMat_FrictPhys()],
        [Law2_ScGeom_FrictPhys_CundallStrack()]
    ),
    NewtonIntegrator(gravity=(0,0,-9.81), damping=0.3),
]

O.dt = 0.5 * utils.PWaveTimeStep()

