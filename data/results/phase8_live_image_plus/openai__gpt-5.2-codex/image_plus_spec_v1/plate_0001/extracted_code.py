import cadquery as cq

L = 111.154
W = 41.501
T = 6.2

base = cq.Workplane("XY").box(L, W, T, centered=(False, False, False))

hole_points = [
    (34.975, 13.139),
    (55.577, 13.139),
    (76.179, 13.139),
    (34.975, 28.362),
    (55.577, 28.362),
    (76.179, 28.362)
]

result = (
    base.faces(">Z")
    .workplane(centerOption="CenterOfBoundBox")
    .center(-L/2, -W/2)
    .pushPoints(hole_points)
    .hole(4.532)
)

result = (
    result.faces(">Z")
    .workplane(centerOption="CenterOfBoundBox")
    .center(-L/2, -W/2)
    .center(55.577, 20.75)
    .slot2D(32.476, 8.292, angle=0)
    .cutThruAll()
)
