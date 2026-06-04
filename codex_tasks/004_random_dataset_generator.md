# Codex Task 004 — Deterministic Random Dataset Generator

Implement seeded random generation for mounting plates.

## Ranges

```text
length: 60–140 mm
width: 40–100 mm
thickness: 4–12 mm
hole_count: 2, 4, or 6
hole_diameter: 4–10 mm
edge_clearance: at least 2 × hole_diameter
minimum hole-to-hole center distance: 2.5 × hole_diameter
```

## CLI

```bash
python scripts/generate_dataset.py --family mounting_plate --count 10 --seed 42 --output-dir data/benchmark
```

## Acceptance criteria

- deterministic by seed
- holes inside bounds
- holes do not overlap
- one folder per generated part
