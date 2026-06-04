# LegacyPartBench

**LegacyPartBench** is a benchmark for evaluating whether multimodal language models can reconstruct editable 3D CAD from 2D mechanical drawings.

The core task:

> Given a dimensioned mechanical drawing image, generate executable CadQuery code that recreates the part.

The system then executes the generated CAD code in a sandbox, exports a model, compares it against the ground-truth CAD, and produces a deterministic score.

```text
Ground-truth CAD
      ↓
Generated engineering drawing
      ↓
Model receives drawing/spec
      ↓
Model outputs CadQuery code
      ↓
Sandbox executes code
      ↓
Generated CAD is exported
      ↓
Evaluator compares generated CAD to target
      ↓
Scorecard + dashboard
```

## Why this exists

Many industrial companies have large archives of legacy 2D drawings, PDFs, scans, and old documentation, but modern engineering workflows depend on editable 3D CAD. Current AI demos often show plausible outputs; LegacyPartBench asks whether the output is actually executable, dimensionally correct, feature-complete, and geometrically faithful.

This benchmark tests a practical combination of capabilities:

- visual interpretation of mechanical drawings,
- dimensional reasoning,
- 2D-to-3D reconstruction,
- CAD code generation,
- geometric validation,
- feature-level engineering correctness.

## MVP scope

The first version should stay intentionally narrow:

```text
1 part family: mounting plates
10 generated parts
3 prompt modes:
  - text spec only
  - image + structured spec
  - image only
2–3 models through OpenRouter
CadQuery output
Dockerized execution
basic deterministic scoring
Streamlit dashboard
```

Do not start with assemblies, GD&T, threads, scanned drawings, sheet-metal bend radii, or SolidWorks integration.

## Recommended stack

| Layer | Tool |
|---|---|
| CAD generation | CadQuery |
| Generated CAD artifacts | STEP and STL |
| Drawing generation | Python, matplotlib/SVG |
| Model calls | OpenRouter |
| Execution sandbox | Docker |
| Geometry analysis | trimesh + CadQuery/OpenCascade |
| Results storage | SQLite plus local files |
| Dashboard | Streamlit |
| Tests | pytest |

## Repository layout

```text
legacy-part-bench/
  README.md
  AGENTS.md
  PROJECT_PLAN.md
  ARCHITECTURE.md
  DATASET_SPEC.md
  SCORING_SPEC.md
  PROMPTING.md
  SECURITY.md
  pyproject.toml
  .env.example
  .gitignore
  Makefile

  legacy_part_bench/
    __init__.py
    config.py

    dataset/
      __init__.py
      schemas.py
      io.py

    generators/
      __init__.py
      mounting_plate.py
      drawing_renderer.py
      generate_dataset.py

    models/
      __init__.py
      openrouter_client.py
      response_parser.py
      run_model.py

    sandbox/
      Dockerfile
      execute_cadquery.py
      sandbox_runner.py

    evaluators/
      __init__.py
      bbox_eval.py
      volume_eval.py
      feature_eval.py
      score.py

    results/
      __init__.py
      db.py
      run_store.py

    dashboard/
      streamlit_app.py

  scripts/
    generate_dataset.py
    run_one_model.py
    run_benchmark.py
    evaluate_local_answer.py

  tests/
    test_package_import.py
    test_dataset_io.py
    test_response_parser.py
    test_bbox_eval.py
    test_feature_eval.py

  data/
    benchmark/
    results/
```

## Coordinate convention

Use this convention everywhere:

```text
Lower-left-bottom corner of the part is at (0, 0, 0).
Length runs along +X.
Width runs along +Y.
Thickness/height runs along +Z.
Units are millimeters.
```

The prompt to models should repeat this convention and require the final CadQuery object to be assigned to a variable named `result`.

Phase-2 prompt helpers live in `legacy_part_bench.models`:

```python
from legacy_part_bench.models import extract_python_code, render_prompt

prompt = render_prompt(
    "image_plus_spec_v1",
    metadata=metadata,
    image_path=part_dir / "drawing.png",
)
code = extract_python_code(raw_model_response)
```

Phase-6 model runs call OpenRouter, cache raw responses, execute extracted code,
and score the generated CAD:

```bash
python scripts/run_one_model.py \
  --part-dir data/benchmark/plate_0001 \
  --model openai/gpt-4o-mini \
  --prompt-mode image_plus_spec_v1 \
  --output-dir data/results/openrouter_test/plate_0001
```

Set `OPENROUTER_API_KEY` before live model runs. The cache key uses the model,
part id, prompt mode, prompt version, drawing image hash, and temperature; pass
`--force` to bypass a cached response. Docker is the default executor for
model-generated code; use `--executor local` only for local development.

## Dataset item structure

Each benchmark item should live in its own folder:

```text
data/benchmark/plate_0001/
  metadata.json
  drawing.png
  target.step
  target.stl
```

Example `metadata.json`:

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
      },
      {
        "diameter": 6.0,
        "center": [80.0, 20.0],
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

## Scoring v0

Initial 100-point score:

| Category | Points |
|---|---:|
| Code executes | 20 |
| Valid CAD export | 10 |
| Bounding box accuracy | 20 |
| Volume similarity | 15 |
| Hole/feature correctness | 35 |

The v0 evaluators load STL files with `trimesh`, compare bounding-box extents
against metadata dimensions, compare volume against the target STL, and use a
mounting-plate-specific through-hole heuristic. The feature heuristic looks for
mesh vertices on the expected circular hole wall near both top and bottom faces;
it is intentionally simple, but distinguishes correct, partially missing, and
absent through holes for the MVP.

Example scorecard:

```json
{
  "total_score": 83.4,
  "max_score": 100,
  "categories": {
    "execution": {"score": 20, "max_score": 20},
    "export": {"score": 10, "max_score": 10},
    "bbox": {"score": 18.2, "max_score": 20},
    "volume": {"score": 13.4, "max_score": 15},
    "features": {"score": 21.8, "max_score": 35}
  },
  "passed": true,
  "notes": []
}
```

## Development setup

Create a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Copy environment variables:

```bash
cp .env.example .env
```

Run tests:

```bash
pytest
```

## First working loop

The first end-to-end loop should not call any model. It should use a local, hand-written answer file.

```bash
python scripts/generate_dataset.py \
  --family mounting_plate \
  --count 10 \
  --seed 42 \
  --output-dir data/benchmark

python scripts/evaluate_local_answer.py \
  --part-dir data/benchmark/plate_0001 \
  --code-file examples/answers/plate_0001_good.py \
  --output-dir data/results/local_test/plate_0001
```

The local run folder contains:

```text
run_config.json
extracted_code.py
generated.step
generated.stl
execution_log.json
scorecard.json
```

To score an already executed run folder, omit `--code-file` and pass the same
benchmark item and run directory:

```bash
python scripts/evaluate_local_answer.py \
  --item-dir data/benchmark/plate_0001 \
  --run-dir data/results/local_test/plate_0001
```

Only after local generation, execution, and scoring works should model calls be added.

## CAD execution

Generated CadQuery answers must assign the final part to `result`. Phase 3 provides
a local child-process executor:

```bash
python -m legacy_part_bench.sandbox.execute_cadquery \
  --code-file examples/answers/plate_0001_good.py \
  --output-dir data/results/local_test/plate_0001
```

The executor writes:

```text
generated.step
generated.stl
execution_log.json
```

Valid code exports STEP/STL. Syntax errors, missing `result`, runtime errors, export
errors, and timeouts still produce `execution_log.json`.

For untrusted model output, use the Docker sandbox:

```bash
python -m legacy_part_bench.sandbox.sandbox_runner --build-image \
  --code-file examples/answers/plate_0001_good.py \
  --output-dir data/results/docker_test/plate_0001
```

The Docker runner uses `--network none`, CPU/memory limits, read-only mounting for
the code file, a writable mounted output directory, an outer timeout, and
`--platform linux/amd64` by default for CadQuery wheel compatibility on Apple
Silicon Docker hosts.

## Model benchmark flow

```bash
python scripts/run_one_model.py \
  --part-dir data/benchmark/plate_0001 \
  --model anthropic/claude-sonnet-4.5 \
  --prompt-mode image_plus_spec_v1 \
  --output-dir data/results/runs
```

Then batch:

```bash
python scripts/run_benchmark.py \
  --dataset-dir data/benchmark \
  --models anthropic/claude-sonnet-4.5 openai/gpt-4.1-mini google/gemini-2.5-flash \
  --prompt-mode image_plus_spec_v1 \
  --max-parts 10 \
  --output-dir data/results
```

## Dashboard

```bash
streamlit run legacy_part_bench/dashboard/streamlit_app.py
```

Dashboard should show:

- model leaderboard,
- average score by model,
- score by prompt mode,
- failed execution table,
- per-part result details,
- input drawing,
- generated code,
- execution logs,
- target/generated previews when available.

## Current limitations

The MVP intentionally avoids:

- assemblies,
- threads,
- GD&T,
- tolerances,
- section views,
- scanned drawings,
- sheet-metal flat patterns,
- SolidWorks API,
- direct STEP generation by the model,
- subjective human scoring.

These can be added later after the benchmark loop works.

## Project thesis

Existing CAD-generation benchmarks often focus on text prompts, meshes, renders, or broad CAD program generation. LegacyPartBench focuses on a practical industrial workflow: reconstructing editable 3D CAD from dimensioned 2D mechanical drawings, using generated ground-truth parts and deterministic feature-level scoring.
