
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
cylMass = 500.0                    # Rigid-body mass
cylInertia = (10000,10000,10000)   # Override inertia tensor
startHeight =  1.8                 # Drop height
startY      = -1.5                 # Starting y-coordinate

# --- Procedural-cylinder fallback parameters ---
radius   = 0.5
height   = 0.25
segments = 20                      # Cylinder resolution

# Particle parameters
rMean    = 0.05
rRelFuzz = 0.3

# Box interior region (open top)
boxX = 0.5
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

def ringPoint(axis, angle, r, h):
    """
    Universal ring point generator.
    axis: 'x', 'y', or 'z'
    angle: polar angle 0..2π
    r: radius
    h: height position along cylinder axis
    Returns a Vector3 point on a circular ring.
    """

    c = math.cos(angle)
    s = math.sin(angle)

    if axis == 'x':
        # cylinder axis = X
        return Vector3(h, r*c, r*s)

    elif axis == 'y':
        # cylinder axis = Y
        return Vector3(r*c, h, r*s)

    elif axis == 'z':
        # cylinder axis = Z
        return Vector3(r*c, r*s, h)

    else:
        raise ValueError("axis must be 'x','y', or 'z'")


def triangulate_cap(axis, centerH, segments, r, material, upward):
    """
    Create a circular cap on a cylinder aligned with X, Y, or Z axis.
    centerH  = coordinate along cylinder axis for this cap
    upward   = True  -> normal direction is +axis
               False -> normal direction is -axis
    """

    facets = []
    dth = 2*math.pi/segments

    # center of cap
    if axis == 'x':
        center = Vector3(centerH, 0, 0)
        normal_dir = Vector3(1,0,0 if upward else -1)

    elif axis == 'y':
        center = Vector3(0, centerH, 0)

    elif axis == 'z':
        center = Vector3(0,0, centerH)

    for i in range(segments):
        a1 = i*dth
        a2 = (i+1)*dth

        p1 = ringPoint(axis, a1, r, centerH)
        p2 = ringPoint(axis, a2, r, centerH)

        # outward normals using right‑hand rule
        if upward:
            tri = [p1, p2, center]
        else:
            tri = [p2, p1, center]

        facets.append(facet(tri, material=material))

    return facets


def build_cylinder(axis, radius, height, segments, material):
    """
    Returns a list of facet bodies forming a closed cylindrical surface.
    axis ∈ {'x','y','z'} defines which axis the cylinder is aligned with.
    height = total length along axis
    """

    facets = []
    dth = 2*math.pi / segments

    # ---- side facets ----
    for i in range(segments):
        a1 = i*dth
        a2 = (i+1)*dth

        # bottom ring at h=0, top ring at h=height
        b1 = ringPoint(axis, a1, radius, 0.0)
        b2 = ringPoint(axis, a2, radius, 0.0)
        t1 = ringPoint(axis, a1, radius, height)
        t2 = ringPoint(axis, a2, radius, height)

        facets.append(facet([b1, b2, t1], material=material))
        facets.append(facet([b2, t2, t1], material=material))

    # ---- caps ----
    # bottom = h=0 → faces -axis
    facets += triangulate_cap(axis, 0.0, segments, radius, material, upward=False)

    # top = h=height → faces +axis
    facets += triangulate_cap(axis, height, segments, radius, material, upward=True)

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
    myaxis = 'x'
    facets = build_cylinder(
        axis=myaxis,           # 'x', 'y', or 'z'
        radius=radius,
        height=height,
        segments=segments,
        material=idCylMat
    )
    print("Built procedural cylinder aligned with'", myaxis , "'axis:",
          len(facets), "facets.")

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
clump.state.pos     = Vector3(0,startY,startHeight)

# No initial angular velocity
clump.state.angVel = Vector3(-25,0,0)
clump.state.vel = Vector3(0,0,0)

# Allow *ONLY* translation in Z direction: block X,Y & all rotations including about Z
clump.state.blockedDOFs = 'xYZ'

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

# save simulation to memory
O.saveTmp()
O.stopAtIter=30000
