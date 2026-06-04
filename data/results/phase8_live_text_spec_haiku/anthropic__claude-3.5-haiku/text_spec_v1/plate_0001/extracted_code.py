import cadquery as cq

result = (
    cq.Workplane("XY")
    .box(111.154, 41.501, 6.2)
    .translate((111.154/2, 41.501/2, 6.2/2))
    .faces(">Z")
    .workplane()
    .pushPoints([
        (34.975, 13.139),
        (55.577, 13.139),
        (76.179, 13.139),
        (34.975, 28.362),
        (55.577, 28.362),
        (76.179, 28.362)
    ])
    .hole(4.532)
    .faces(">Z")
    .workplane()
    .center(55.577, 20.75)
    .slot(32.476, 8.292, 0)
)
