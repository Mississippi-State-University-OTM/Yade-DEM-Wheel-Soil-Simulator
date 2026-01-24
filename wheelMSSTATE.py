from yade import *
import math

# --- Wheel properties and initial coordinates ---
wheelMass = 500.0                  # Rigid-body mass
wheelInertia = (1,1,1)             # Inertia tensor
startX      =  0.0                 # Starting x-coordinate
startY      = -1.5                 # Starting y-coordinate
startZ      =  1.8                 # Drop height
startVelY   =  0.0
startWelX   =  25.0

# --- Wheel read from OBJ file
fromFile = True                    # False: build cylindrical wheel
objFile = "cylinder.stl"           # Wheel STL file
objScale = 1.0
# Shift wheel after import
if objFile == "lugged_whel.stl":
    objScale = 0.01
    objShift = Vector3(-50*objScale/2, startY, startZ)
else:
    objScale = 0.01
    objShift = Vector3(0, startY, startZ)

# --- Wheel constructed from cylinder facets ---
wheelRadius  = 0.5
wheelWidth   = 0.25
segments = 10                      # Cylinder resolution

# Particle parameters
rMean    = 0.05
rRelFuzz = 0.3
rndSeed  = 123

# Box interior region (open top)
boxX = 0.5   # half width
boxY = 2.0   # half lenght
boxZ = 1.5   # height of box

# Materials
matWheel = FrictMat(young=1e7, poisson=0.3, frictionAngle=0.5)
matSphere = FrictMat(young=1e7, poisson=0.3, frictionAngle=0.6)

idWheelMat = O.materials.append(matWheel)
idSphereMat = O.materials.append(matSphere)

# Geometry helpers
def ringPoint(axis, angle, r, h):
    """
    Universal ring point generator.
    axis: 'x', 'y', or 'z'
    angle: polar angle 0..2pi
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


def triangulate_cap(axis, centerH, segments, r, material, offset, upward):
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

    center = center+offset

    for i in range(segments):
        a1 = i*dth
        a2 = (i+1)*dth

        p1 = ringPoint(axis, a1, r, centerH) + offset
        p2 = ringPoint(axis, a2, r, centerH) + offset

        # outward normals using right-hand rule
        if upward:
            tri = [p1, p2, center]
        else:
            tri = [p2, p1, center]

        facets.append(facet(tri, material=material))

    return facets


def build_cylinder(axis, radius, height, segments, material,
                   offset):
    """
    Returns a list of facet bodies forming a closed cylindrical surface.
    axis ('x', 'y', or 'z') defines which axis the cylinder is aligned with.
    height = total length along axis
    """

    facets = []
    dth = 2*math.pi / segments

    # ---- side facets ----
    for i in range(segments):
        a1 = i*dth
        a2 = (i+1)*dth

        # bottom ring at h=-height/2, top ring at h=height/2
        b1 = ringPoint(axis, a1, radius, -height/2) + offset
        b2 = ringPoint(axis, a2, radius, -height/2) + offset
        t1 = ringPoint(axis, a1, radius,  height/2) + offset
        t2 = ringPoint(axis, a2, radius,  height/2) + offset

        facets.append(facet([b1, b2, t1], material=material))
        facets.append(facet([b2, t2, t1], material=material))

    # ---- caps ----
    # bottom = h=-height/2 : faces -axis
    facets += triangulate_cap(axis, -height/2, segments, radius, material,
                              offset, upward=False)

    # top = h=height/2 : faces +axis
    facets += triangulate_cap(axis,  height/2, segments, radius, material,
                              offset, upward=True)

    return facets

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
# Import wheel from OBJ file or create it
facets = []
if fromFile:
    #
    # YADE imports triangulated OBJ/STL-like meshes using ymport.stl
    # as shown in mesh import examples.
    #
    from yade import ymport
    facets = ymport.stl(
        objFile,
        scale=objScale,
        shift=objShift,
        material=idWheelMat,
        dynamic=None,
        fixed=False,
        noBound=False
    )
    print(f"Imported {len(facets)} facets from \"{objFile}\" file.")

else:
    myaxis = 'x'
    myOffset = Vector3(startX, startY, startZ)
    facets = build_cylinder(
        axis=myaxis,           # 'x', 'y', or 'z'
        radius=wheelRadius,
        height=wheelWidth,
        segments=segments,
        material=idWheelMat,
        offset = myOffset
    )
    print("Construct cylindical wheel aligned with 'x' axis:",
          len(facets), "facets.")

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

# Build open-top facet box
# Bottom (two triangles)
O.bodies.append(facet([(-boxX,-boxY,0),( boxX,-boxY,   0),(-boxX, boxY,   0)],
                      material=idWheelMat))
O.bodies.append(facet([( boxX,-boxY,0),( boxX, boxY,   0),(-boxX, boxY,   0)],
                      material=idWheelMat))
# Left wall
O.bodies.append(facet([(-boxX,-boxY,0),(-boxX, boxY,   0),(-boxX,-boxY,boxZ)],
                      material=idWheelMat))
O.bodies.append(facet([(-boxX, boxY,0),(-boxX, boxY,boxZ),(-boxX,-boxY,boxZ)],
                      material=idWheelMat))
# Right wall
O.bodies.append(facet([( boxX,-boxY,0),( boxX,-boxY,boxZ),( boxX, boxY,   0)],
                      material=idWheelMat))
O.bodies.append(facet([( boxX, boxY,0),( boxX,-boxY,boxZ),( boxX, boxY,boxZ)],
                      material=idWheelMat))
# Front wall
O.bodies.append(facet([(-boxX,-boxY,0),(-boxX,-boxY,boxZ),( boxX,-boxY,   0)],
                      material=idWheelMat))
O.bodies.append(facet([( boxX,-boxY,0),(-boxX,-boxY,boxZ),( boxX,-boxY,boxZ)],
                      material=idWheelMat))
# Back wall
O.bodies.append(facet([(-boxX, boxY,0),( boxX, boxY,   0),(-boxX, boxY,boxZ)],
                      material=idWheelMat))
O.bodies.append(facet([( boxX, boxY,0),( boxX, boxY,boxZ),(-boxX, boxY,boxZ)],
                      material=idWheelMat))

# Add particles inside the box (not on top)
sp = pack.SpherePack()
sp.makeCloud(
    (-boxX*0.9, -boxY*0.9, 0.05),      # slightly inside box
    ( boxX*0.9,  boxY*0.9, boxZ*0.8),  # well below top edge
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
O.stopAtIter=15000
