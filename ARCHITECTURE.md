# Architecture

## System overview

LegacyPartBench has five major subsystems:

```text
Dataset generation
      ↓
Prompt/model runner
      ↓
CAD execution sandbox
      ↓
Evaluation/scoring
      ↓
Dashboard/reporting
```

## Pipeline

```text
1. Generate ground-truth CAD
2. Export target STEP/STL
3. Generate drawing image
4. Render prompt
5. Call model
6. Parse response into code
7. Execute generated code
8. Export generated STEP/STL
9. Evaluate generated CAD against target
10. Store scorecard
11. Display results
```

## Data flow

```text
metadata.json
target.step
target.stl
drawing.png
      ↓
prompt renderer
      ↓
OpenRouter model call
      ↓
raw_response.txt
extracted_code.py
      ↓
Docker sandbox
      ↓
generated.step
generated.stl
execution_log.json
      ↓
evaluators
      ↓
scorecard.json
summary.csv
      ↓
Streamlit dashboard
```

## Key modules

### `legacy_part_bench.dataset`

Owns schemas and JSON IO.

### `legacy_part_bench.generators`

Owns target CAD and drawing generation.

Initial family:

```text
mounting_plate
```

Future families:

```text
stepped_block
l_bracket
sheet_metal_bracket
```

### `legacy_part_bench.models`

Owns prompts, OpenRouter calls, response parsing, and caching.

### `legacy_part_bench.sandbox`

Owns execution of generated CadQuery code.

Generated code is untrusted and should be run in Docker once sandboxing is implemented.

### `legacy_part_bench.evaluators`

Owns scoring metrics.

Initial metrics:

```text
execution
valid export
bounding box
volume
feature correctness
```

### `legacy_part_bench.results`

Owns run storage, summary files, and optional SQLite indexing.

### `legacy_part_bench.dashboard`

Owns Streamlit UI.

## Coordinate convention

```text
Origin: lower-left-bottom corner
X: length
Y: width
Z: thickness/height
Units: millimeters
```

This must be consistent across:

```text
part generation
metadata
drawings
prompts
generated-code expectations
evaluators
```

## Failure handling

A failed model run should still create a result folder.

Minimum artifacts after a failed run:

```text
run_config.json
raw_response.txt if available
extracted_code.py if available
execution_log.json
scorecard.json
```

The batch benchmark should continue after individual failures.

## Caching

Model calls should be cached by a hash of:

```text
model
part_id
prompt_mode
prompt_version
image_hash
temperature
max_tokens
```

Caching prevents accidental duplicate API spend.

## Security

Generated CAD code is untrusted code.

The Docker sandbox should:

```text
disable network
use timeout
limit filesystem access
write only to mounted output directory
prefer CPU/memory limits
```

See `SECURITY.md`.
