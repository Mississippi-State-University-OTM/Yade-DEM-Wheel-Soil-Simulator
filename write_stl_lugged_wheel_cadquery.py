import cadquery as cq
import math

# --- Parameters ---
R_wheel = 50        # wheel outer radius
W_wheel = 50        # wheel width (Z length)
R_bore  = 10        # hub bore radius (0 = solid)

lug_count   = 12
lug_height  = 6     # radial protrusion beyond the wheel
lug_length  = 4     # tangential length
lug_width   = W_wheel  # axial width = wheel width

# --- Wheel ---
wheel = (
    cq.Workplane("YZ")
    .circle(R_wheel)
    .circle(R_bore) if R_bore > 0 else cq.Workplane("YZ").circle(R_wheel)
).extrude(W_wheel)

# --- One Lug (centered at rim) ---
center_r = R_wheel # + lug_height / 2
lug = (
    cq.Workplane("YZ")
    .center(center_r, 0)
    .box(lug_height, lug_length, lug_width, centered=False)
)

# --- Array of Lugs ---
for i in range(lug_count):
    angle = i * (360 / lug_count)
    wheel = wheel.union(lug.rotate((0, 0, 0), (1, 0, 0), angle))

# --- Export ---
# cq.exporters.export(wheel, "lugged_wheel_bin.stl")
cq.exporters.export(
    wheel,
    "lugged_wheel.stl",
    exportType="STL",
    opt={"ascii": True}
)

print("Wrote lugged_wheel.stl")
