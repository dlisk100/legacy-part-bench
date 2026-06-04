import cadquery as cq

length = 111.154
width = 41.501
thickness = 6.2
hole_diameter = 4.837
hole_centers = [
    (13.759, 26.082),
    (97.395, 26.082),
]

result = cq.Workplane("XY").box(length, width, thickness, centered=(False, False, False))

for x, y in hole_centers:
    cutter = (
        cq.Workplane("XY")
        .center(x, y)
        .circle(hole_diameter / 2.0)
        .extrude(thickness + 2.0)
        .translate((0.0, 0.0, -1.0))
    )
    result = result.cut(cutter)
