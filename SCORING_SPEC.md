# Scoring Specification

## Goal

LegacyPartBench scores whether a model-generated CAD reconstruction matches the ground-truth CAD.

The score should be deterministic, JSON-serializable, and explainable.

## Initial 100-point score

| Category | Points |
|---|---:|
| Code executes | 20 |
| Valid CAD export | 10 |
| Bounding box accuracy | 20 |
| Volume similarity | 15 |
| Feature correctness | 35 |
| **Total** | **100** |

## Execution score

```text
20/20 if generated code runs successfully.
0/20 if code fails.
```

The executor must write an `execution_log.json` either way.

## Export score

```text
10/10 if generated STEP/STL artifacts are created and loadable.
0/10 otherwise.
```

## Bounding box score

Compare generated STL bounding box extents against metadata dimensions.

Expected extents for mounting plate:

```text
[length, width, thickness]
```

Scoring:

```text
relative_error = abs(generated - target) / target
dimension_score = max(0, 1 - relative_error / 0.20)
bbox_score = average(dimension_scores) × 20
```

This gives zero credit for a dimension at or above 20% error.

## Volume score

Compare generated STL volume against target STL volume.

Scoring:

```text
relative_error = abs(generated_volume - target_volume) / target_volume
volume_score = max(0, 1 - relative_error / 0.30) × 15
```

This gives zero credit at or above 30% volume error.

## Feature score v0

Initial feature score focuses on through-holes and horizontal through-slots.

Score components can include:

```text
expected hole exists near target center
expected slot exists near target center
hole appears to go through the part
slot appears to go through the part
diameter approximately correct if measurable
no severe extra/missing features if detectable
```

Initial scoring can be heuristic. It must at least distinguish:

```text
correct holes
missing some holes
missing all holes
correct slots
missing slots
```

Current v0 implementation detects an expected through hole by looking for STL
mesh vertices near the expected circular wall radius, with enough angular
coverage and vertices near both the top and bottom of the part. This is an MVP
heuristic for generated mounting plates, not a general feature-recognition
system. Horizontal slots use a similar boundary-vertex heuristic along the slot
wall. Parts with no explicit hole or slot features, such as simple stepped
blocks, receive full feature credit because their geometry is judged by bounding
box and volume in v0.

## Scorecard format

```json
{
  "total_score": 83.4,
  "max_score": 100,
  "categories": {
    "execution": {
      "score": 20,
      "max_score": 20,
      "details": {}
    },
    "export": {
      "score": 10,
      "max_score": 10,
      "details": {}
    },
    "bbox": {
      "score": 18.2,
      "max_score": 20,
      "details": {
        "target_extents": [100.0, 60.0, 8.0],
        "generated_extents": [99.5, 60.2, 8.0],
        "relative_errors": [0.005, 0.0033, 0.0]
      }
    },
    "volume": {
      "score": 13.4,
      "max_score": 15,
      "details": {
        "target_volume": 45120.0,
        "generated_volume": 47000.0,
        "relative_error": 0.0417
      }
    },
    "features": {
      "score": 21.8,
      "max_score": 35,
      "details": {
        "expected_holes": 4,
        "detected_expected_holes": 3,
        "missed_holes": [[80.0, 20.0]]
      }
    }
  },
  "passed": true,
  "notes": []
}
```

## Failure behavior

If execution fails:

```text
execution = 0
export = 0
bbox = 0
volume = 0
features = 0
```

A valid scorecard must still be written.

## Future metrics

Potential v2 metrics:

```text
voxel IoU
multi-view silhouette similarity
Chamfer distance between sampled surfaces
cylindrical face detection
slot/pocket/chamfer detection
feature graph similarity
```
