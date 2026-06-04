# Codex Task 002 — Dataset Schemas

Implement dataset schemas for benchmark items.

## Implement

- `BenchmarkItem`
- `PartMetadata`
- `PartDimensions`
- `HoleFeature`
- `SlotFeature`
- `FileReferences`

Use dataclasses or Pydantic models. Prefer JSON-serializable structures.

## Add helpers

- save metadata to JSON
- load metadata from JSON

## Acceptance criteria

- metadata can be saved and loaded
- JSON round trip preserves values
- tests pass
