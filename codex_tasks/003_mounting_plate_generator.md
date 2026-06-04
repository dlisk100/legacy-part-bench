# Codex Task 003 — Mounting Plate Generator

Implement a CadQuery mounting plate generator.

## Requirements

- Rectangular solid plate
- Through holes along Z
- Coordinate convention:
  - lower-left-bottom corner at `(0, 0, 0)`
  - length along +X
  - width along +Y
  - thickness along +Z
- Export `target.step`
- Export `target.stl`
- Write `metadata.json`

## Acceptance criteria

A call to generate one plate creates:

```text
metadata.json
target.step
target.stl
```

Tests should verify generated files and metadata.
