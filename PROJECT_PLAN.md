# LegacyPartBench Project Plan

This plan breaks LegacyPartBench into milestones that are small enough to give to a coding agent one at a time.

## Phase 0 — Project foundation

### Milestone 1: Repo scaffold and dev environment

Create:

```text
pyproject.toml
README.md
AGENTS.md
.env.example
.gitignore
Makefile
legacy_part_bench/
scripts/
tests/
data/
```

Acceptance:

```bash
pip install -e ".[dev]"
pytest
```

passes.

---

### Milestone 2: Dataset schemas

Implement schemas for:

```text
BenchmarkItem
PartMetadata
PartDimensions
HoleFeature
SlotFeature
FileReferences
```

Acceptance:

- metadata can be saved to JSON,
- metadata can be loaded from JSON,
- JSON round trip preserves values.

---

## Phase 1 — Dataset generation

### Milestone 3: Mounting plate CAD generator

Implement CadQuery generation for rectangular plates with through holes.

Acceptance:

```text
metadata.json
target.step
target.stl
```

are created.

---

### Milestone 4: Deterministic random mounting plates

Implement seeded random generation.

Acceptance:

```bash
python scripts/generate_dataset.py --family mounting_plate --count 10 --seed 42
```

creates 10 valid part folders.

---

### Milestone 5: Drawing renderer

Generate readable top-view drawing PNGs.

Acceptance:

```text
drawing.png
```

exists for each part and includes dimensions and hole callouts.

---

### Milestone 6: Dataset generation CLI

One command generates CAD, drawings, and metadata.

Acceptance:

```bash
python scripts/generate_dataset.py \
  --family mounting_plate \
  --count 10 \
  --seed 42 \
  --output-dir data/benchmark
```

works.

---

## Phase 2 — Prompting and response handling

### Milestone 7: Prompt templates

Implement prompt modes:

```text
text_spec_v1
image_plus_spec_v1
image_only_v1
```

Acceptance:

- all prompt modes render,
- prompts require `result`,
- prompts state coordinate convention.

---

### Milestone 8: Response parser

Extract Python code from model responses.

Acceptance:

- raw code works,
- fenced Python blocks work,
- generic fenced blocks work,
- intro text plus code works.

---

## Phase 3 — CAD execution

### Milestone 9: Local CadQuery executor

Execute generated CadQuery code and export generated STEP/STL.

Acceptance:

```text
generated.step
generated.stl
execution_log.json
```

are produced for valid code.

---

### Milestone 10: Docker sandbox

Run generated code in Docker with no network and timeout.

Acceptance:

- valid code succeeds,
- syntax error fails cleanly,
- infinite loop times out,
- logs are always written.

---

## Phase 4 — Scoring

### Milestone 11: Geometry loading

Load STL files and compute:

```text
bounding box
volume
mesh validity
```

---

### Milestone 12: Bounding box evaluator

Score generated dimensions against target dimensions.

---

### Milestone 13: Volume evaluator

Score generated volume against target volume.

---

### Milestone 14: Feature evaluator

Score expected through holes for mounting plates.

Initial heuristic can be imperfect; it must distinguish:

```text
correct holes
missing holes
no holes
```

---

### Milestone 15: Score aggregator

Combine metrics into a 100-point scorecard.

Initial weights:

```text
execution: 20
export: 10
bbox: 20
volume: 15
features: 35
```

---

## Phase 5 — Local end-to-end benchmark

### Milestone 16: Manual one-item benchmark run

Use a local hand-written answer file instead of a model.

Acceptance:

```bash
python scripts/evaluate_local_answer.py \
  --part-dir data/benchmark/plate_0001 \
  --code-file examples/answers/plate_0001_good.py \
  --output-dir data/results/local_test/plate_0001
```

produces a scorecard.

---

## Phase 6 — Model integration

### Milestone 17: OpenRouter one-model runner

Call one OpenRouter model for one benchmark item, cache the raw response, parse
the answer, execute it in the sandbox, and write the scorecard.

Acceptance:

```bash
python scripts/run_one_model.py \
  --part-dir data/benchmark/plate_0001 \
  --model openai/gpt-4o-mini \
  --prompt-mode image_plus_spec_v1 \
  --output-dir data/results/openrouter_test/plate_0001
```

produces:

```text
run_config.json
raw_response.txt if the model call succeeds or is cached
extracted_code.py if response parsing succeeds
execution_log.json
scorecard.json
```

Live tests must not require OpenRouter. Unit tests should mock model calls.

### Milestone 17: OpenRouter client

Implement model calls through OpenRouter.

Acceptance:

- text-only call supported,
- image call supported where model allows it,
- no API key is hardcoded,
- unit tests mock HTTP calls.

---

### Milestone 18: Run storage and caching

Cache raw model outputs and extracted code.

Acceptance:

- same run key uses cache,
- changed model/prompt/image creates new run key,
- `--force` bypasses cache.

---

### Milestone 19: One real model on one drawing

Run one benchmark item through one real model.

Acceptance:

```bash
python scripts/run_one_model.py \
  --part-dir data/benchmark/plate_0001 \
  --model <model-id> \
  --prompt-mode image_plus_spec_v1 \
  --output-dir data/results/runs
```

produces raw response, code, generated CAD, execution log, and scorecard.

---

### Milestone 20: Batch benchmark runner

Run many parts across many models.

Acceptance:

```bash
python scripts/run_benchmark.py \
  --dataset-dir data/benchmark \
  --models <model-a> <model-b> \
  --prompt-mode image_plus_spec_v1 \
  --max-parts 10 \
  --output-dir data/results
```

creates `summary.csv` and `summary.json`.

---

## Phase 7 — Dashboard

### Milestone 21: Minimal Streamlit leaderboard

Show:

```text
average score by model
category scores
failure count
per-part results
```

---

### Milestone 22: Part-detail view

Show:

```text
input drawing
scorecard
raw model response
extracted code
execution logs
artifact paths
```

---

### Milestone 23: Static STL previews

Render target and generated STL previews to PNG and show them side by side.

---

## Phase 8 — Benchmark expansion

Status: implemented for the deterministic local benchmark loop. The Phase 8
scope adds mounting-plate slots, stepped blocks, L-brackets, difficulty tiers,
image-only/text-only benchmark modes, OpenRouter usage/cost tracking, batch
summaries, manifests, and reproducible docs. Advanced mechanical features remain
out of scope unless explicitly requested.

### Milestone 24: Slots in mounting plates

Add horizontal through-slots.

---

### Milestone 25: Stepped block family

Add a second part family with top and side views.

---

### Milestone 26: L-bracket family

Add a third part family with base flange, vertical flange, and holes.

---

### Milestone 27: Difficulty tiers

Add levels 1, 2, and 3.

---

### Milestone 28: Image-only mode

Run without structured metadata in the prompt.

---

### Milestone 29: Text-spec-only baseline

Separate CAD generation ability from visual drawing interpretation.

---

### Milestone 30: Cost tracking

Store token usage and estimated cost per model run.

---

### Milestone 31: Benchmark manifest

Record dataset version, seed, model list, prompt version, timestamp, and git commit.

---

### Milestone 32: README and portfolio writeup

Produce a public-facing explanation and reproducible demo instructions.

## MVP definition

The MVP is complete when milestones 1–23 are done.

The first portfolio-worthy version is complete when milestones 1–29 are done.
