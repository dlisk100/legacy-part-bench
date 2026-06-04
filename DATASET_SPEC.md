# Dataset Specification

## Purpose

The dataset contains original generated mechanical parts, their engineering drawings, and ground-truth CAD artifacts.

Each dataset item is a self-contained benchmark task.

## Folder structure

```text
data/benchmark/
  plate_0001/
    metadata.json
    drawing.png
    target.step
    target.stl
  plate_0002/
    metadata.json
    drawing.png
    target.step
    target.stl
```

## Metadata schema

```json
{
  "id": "plate_0001",
  "family": "mounting_plate",
  "units": "mm",
  "difficulty": 1,
  "dimensions": {
    "length": 100.0,
    "width": 60.0,
    "thickness": 8.0
  },
  "features": {
    "holes": [
      {
        "diameter": 6.0,
        "center": [20.0, 20.0],
        "through": true
      }
    ],
    "slots": []
  },
  "files": {
    "drawing_png": "drawing.png",
    "target_step": "target.step",
    "target_stl": "target.stl"
  }
}
```

## Coordinate convention

```text
Lower-left-bottom corner: (0, 0, 0)
Length: +X
Width: +Y
Thickness/height: +Z
Units: millimeters
```

Hole centers are specified as:

```text
[x, y]
```

with the hole axis along Z for mounting plates.

## Initial part family: mounting plate

A mounting plate is a rectangular solid with through-holes.

Required parameters:

```text
length
width
thickness
holes
```

Hole parameters:

```text
diameter
center
through
```

## Random generation rules

Initial ranges:

```text
length: 60–140 mm
width: 40–100 mm
thickness: 4–12 mm
hole_count: 2, 4, or 6
hole_diameter: 4–10 mm
edge_clearance: at least 2 × hole_diameter
minimum hole-to-hole center distance: 2.5 × hole_diameter
```

Random generation must be deterministic by seed.

## Drawing requirements v0

For mounting plates, `drawing.png` should show:

```text
top view
overall length
overall width
thickness note
hole diameter callout
hole center coordinates or dimensions from edges
units: mm
```

The drawing does not need to meet full drafting standards in v0. It must be readable and consistent.

## Dataset versioning

Future benchmark runs should record:

```text
dataset version
seed
generation config
part families
difficulty levels
git commit if available
```
