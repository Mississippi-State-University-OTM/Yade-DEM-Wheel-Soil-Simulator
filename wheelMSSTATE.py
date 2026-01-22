
from yade import *
import math

############################################################
# USER OPTIONS
############################################################

# --- Cylinder source ---
useOBJ = False                     # Set False → use procedural cylinder
objFile = "cylinder.obj"           # Your triangulated OBJ mesh
objScale = 1.0                     # Scale OBJ on import
objShift = Vector3(0,0,0)          # Shift OBJ after import

# --- Rigid body properties ---
cylMass = 100.0                    # Rigid-body mass
cylInertia = (1,1,1)               # Override inertia tensor
startHeight = 3.0                  # Drop height

# --- Procedural-cylinder fallback parameters ---
radius   = 0.5
height   = 2.0
segments = 40                      # Cylinder resolution

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
    """Create triangulated circular cap."""
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
# IMPORT CYLINDER FROM OBJ OR BUILD PROCEDURALLY
###############################################
facets = []


############################################################
# CHECK AND FIX INVERTED NORMALS FOR OBJ-IMPORTED FACETS
############################################################
def fix_normals(facetList):
    """
    Ensure all facets point outward by flipping those whose
    normals point inward based on object centroid.
    """
    # Compute centroid of all vertices
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

    for f in facetList:
        v = f.shape.vertices
        fCenter = (v[0] + v[1] + v[2]) / 3.0
        outward = (fCenter - centroid)
        n = facet_normal(f)

        # If dot < 0 → normal points toward centroid → needs flipping
        if n.dot(outward) < 0:
            f.shape.vertices = [v[0], v[2], v[1]]   # swap to flip orientation

    return facetList

if useOBJ:
    #
    # YADE imports triangulated OBJ/STL-like meshes using ymport.stl
    # as shown in mesh‑import examples. 
    #
    from yade import ymport
    facets = ymport.stl(
        objFile,
        scale=objScale,
        shift=objShift,
        material=idCylMat,
        dynamic=None,
        fixed=False,
        noBound=False
    )

    print("Checking OBJ facet normals...")
    facets = fix_normals(facets)
    print("OBJ facet normals validated / corrected.")

    print("Imported", len(facets), "facets from OBJ.")
else:
    # --- Procedural closed cylinder ---
    dth = 2*math.pi/segments

# ---- Side facets ----
    for i in range(segments):
        a1 = i*dth
        a2 = (i+1)*dth
        b1 = ringPoint(a1, radius, 0)
        b2 = ringPoint(a2, radius, 0)
        t1 = ringPoint(a1, radius, height)
        t2 = ringPoint(a2, radius, height)

        facets.append(facet([b1, b2, t1], material=idCylMat))
        facets.append(facet([b2, t2, t1], material=idCylMat))

    # Bottom + top caps
    facets += triangulate_cap(0, segments, radius, idCylMat, upward=False)
    facets += triangulate_cap(height, segments, radius, idCylMat, upward=True)

    print("Procedural cylinder:", len(facets), "facets.")

###############################################
# ASSIGN MASS BEFORE CLUMPING (required!)
###############################################
# YADE 2022.01 requires non‑zero mass for clumped facets. [1](https://answers.launchpad.net/yade/+question/696056)

for f in facets:
    # not used, using body mass and inertia instead
    f.state.mass    = 1.0
    f.state.inertia = (1,1,1)
    f.shape.wire = False

###############################################
# CREATE RIGID CLUMP
###############################################
ret = O.bodies.appendClumped(facets)
clumpId = ret[0]
clump = O.bodies[clumpId]

# Override rigid-body properties
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

# ---- Bottom (two triangles) ----
O.bodies.append(facet([(-boxX,-boxY,0),( boxX,-boxY,0),(-boxX, boxY,0)], material=idCylMat))
O.bodies.append(facet([( boxX,-boxY,0),( boxX, boxY,0),(-boxX, boxY,0)], material=idCylMat))

# ---- Four walls ----
# Left wall
O.bodies.append(facet([(-boxX,-boxY,0),(-boxX, boxY,0),(-boxX,-boxY,boxZ)], material=idCylMat))
O.bodies.append(facet([(-boxX, boxY,0),(-boxX, boxY,boxZ),(-boxX,-boxY,boxZ)], material=idCylMat))

# Right wall
O.bodies.append(facet([( boxX,-boxY,0),( boxX,-boxY,boxZ),( boxX, boxY,0)], material=idCylMat))
O.bodies.append(facet([( boxX, boxY,0),( boxX,-boxY,boxZ),( boxX, boxY,boxZ)], material=idCylMat))

# Front wall
O.bodies.append(facet([(-boxX,-boxY,0),(-boxX,-boxY,boxZ),( boxX,-boxY,0)], material=idCylMat))
O.bodies.append(facet([( boxX,-boxY,0),(-boxX,-boxY,boxZ),( boxX,-boxY,boxZ)], material=idCylMat))

# Back wall
O.bodies.append(facet([(-boxX, boxY,0),( boxX, boxY,0),(-boxX, boxY,boxZ)], material=idCylMat))
O.bodies.append(facet([( boxX, boxY,0),( boxX, boxY,boxZ),(-boxX, boxY,boxZ)], material=idCylMat))

###############################################
# ADD PARTICLES INSIDE THE BOX (NOT ON TOP)
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

