# AGENTS.md

This file gives coding agents the project context, rules, and implementation priorities for **LegacyPartBench**.

## Project summary

LegacyPartBench is a benchmark for evaluating whether multimodal language models can reconstruct editable 3D CAD from 2D mechanical drawings.

The system:

1. Generates original ground-truth mechanical parts.
2. Exports each part as STEP/STL.
3. Generates a clean dimensioned drawing image.
4. Prompts a model to produce executable CadQuery code.
5. Executes the generated code in a sandbox.
6. Exports the generated model as STEP/STL.
7. Scores the generated model against the target using deterministic metrics.
8. Displays results in a dashboard.

The benchmark is not a chatbot. The model must output CAD code that can be executed and scored.

## Build philosophy

Build the project incrementally.

Do not jump ahead to advanced features before the basic benchmark loop works.

The correct order is:

```text
schemas
→ part generator
→ drawing renderer
→ local execution
→ scoring
→ local end-to-end run
→ OpenRouter model call
→ batch runner
→ dashboard
```

Avoid adding dependencies, features, or abstractions that are not needed for the current milestone.

## Coordinate convention

Use this convention everywhere:

```text
Units: millimeters
Origin: lower-left-bottom corner of the part at (0, 0, 0)
Length: +X
Width: +Y
Thickness/height: +Z
```

All generated parts, metadata, prompts, and evaluators should follow this convention.

## CadQuery output contract

Model-generated CadQuery code must satisfy:

```text
- Python code only
- Uses CadQuery
- Creates one final part
- Assigns the final CadQuery object to a variable named `result`
- Uses millimeters
- Follows the project coordinate convention
```

The executor should fail clearly if `result` is missing.

## Initial MVP constraints

Only implement the MVP unless asked otherwise.

MVP part family:

```text
mounting_plate
```

Initial mounting plate features:

```text
length
width
thickness
through holes
```

Do not implement these until explicitly requested:

```text
assemblies
threads
GD&T
tolerances
section views
scanned drawings
sheet-metal bend radii
flat patterns
SolidWorks API
direct STEP generation by the model
cloud deployment
Palantir integration
```

## Files and modules

Preferred package layout:

```text
legacy_part_bench/
  dataset/
    schemas.py
    io.py
  generators/
    mounting_plate.py
    drawing_renderer.py
    generate_dataset.py
  models/
    openrouter_client.py
    response_parser.py
    run_model.py
  sandbox/
    execute_cadquery.py
    sandbox_runner.py
  evaluators/
    bbox_eval.py
    volume_eval.py
    feature_eval.py
    score.py
  results/
    db.py
    run_store.py
  dashboard/
    streamlit_app.py
```

Scripts go in:

```text
scripts/
```

Tests go in:

```text
tests/
```

Generated benchmark data goes in:

```text
data/benchmark/
```

Generated results go in:

```text
data/results/
```

## Testing expectations

Every milestone should add or update tests.

Use `pytest`.

At minimum, keep this passing:

```bash
pytest
```

Do not write tests that require a live OpenRouter API call. Mock external API calls.

Docker/CadQuery integration tests may be marked as integration tests if they are slow or environment-dependent.

## Error handling expectations

Prefer explicit, structured failure outputs over exceptions that kill the full benchmark.

A failed model run should produce:

```text
raw_response.txt if available
extracted_code.py if available
execution_log.json
scorecard.json
```

The batch runner should continue if one part/model fails.

## Data format expectations

Each part folder should contain:

```text
metadata.json
drawing.png
target.step
target.stl
```

Each run folder should contain:

```text
run_config.json
raw_response.txt
extracted_code.py
generated.step if execution succeeds
generated.stl if execution succeeds
execution_log.json
scorecard.json
```

## Scoring v0

Initial score should total 100 points:

```text
Code executes: 20
Valid CAD export: 10
Bounding box: 20
Volume: 15
Features: 35
```

If execution fails, geometry and feature metrics should be skipped or scored zero, but a valid scorecard should still be written.

## Model calls

Use OpenRouter only through a small wrapper module.

Read the API key from:

```text
OPENROUTER_API_KEY
```

Never hardcode API keys.

Cache model responses. Use a run key based on:

```text
model
part_id
prompt_mode
prompt_version
image_hash
temperature
```

Do not pay twice for the same run unless `--force` is provided.

## Security rule

Model-generated CAD code is untrusted code.

Do not execute generated code directly in the main application process once Docker sandboxing exists.

The Docker sandbox should use:

```text
--network none
timeout
limited mounted output directory
memory/CPU limits if practical
```

## Code style

Prefer:

- simple functions,
- typed dataclasses or Pydantic models,
- clear JSON-serializable outputs,
- small modules,
- explicit path handling with `pathlib.Path`,
- deterministic random generation via seeds,
- human-readable logs.

Avoid:

- global mutable state,
- hidden network calls,
- broad exception swallowing without logging,
- over-engineered class hierarchies,
- premature frontend work,
- silent changes to coordinate conventions.

## Documentation expectations

When adding a feature, update docs if the behavior changes.

Relevant docs:

```text
README.md
PROJECT_PLAN.md
ARCHITECTURE.md
DATASET_SPEC.md
SCORING_SPEC.md
PROMPTING.md
SECURITY.md
```

## Definition of done for any milestone

A milestone is done when:

1. The requested functionality exists.
2. Tests pass.
3. CLI command, if applicable, works.
4. Errors are understandable.
5. Outputs are written to the expected folders.
6. Documentation is updated if needed.
