# Prompting Specification

## Output contract

All prompts should require:

```text
- Return only executable Python code.
- Use CadQuery.
- Use millimeters.
- Follow the coordinate convention.
- Assign the final CadQuery object to a variable named `result`.
```

## Coordinate convention to include in prompts

```text
Coordinate system:
- Place the lower-left-bottom corner of the part at (0, 0, 0).
- Length runs along +X.
- Width runs along +Y.
- Thickness/height runs along +Z.
- Use millimeters.
```

## Prompt mode: `text_spec_v1`

Use this mode to test CAD generation without visual interpretation.

Template:

```text
You are given a mechanical part specification.

Create executable CadQuery Python code for the part.

Requirements:
- Use CadQuery.
- Use millimeters.
- Place the lower-left-bottom corner of the part at (0, 0, 0).
- Length runs along +X.
- Width runs along +Y.
- Thickness/height runs along +Z.
- Assign the final CadQuery object to a variable named `result`.
- Return only Python code. Do not include Markdown or explanations.

Part specification:
{{ structured_spec }}
```

## Prompt mode: `image_plus_spec_v1`

Use this mode to test CAD generation and basic drawing use while reducing OCR ambiguity.

Template:

```text
You are given a dimensioned mechanical drawing image and a structured summary of the same part.

Create executable CadQuery Python code for the part.

Requirements:
- Use CadQuery.
- Use millimeters.
- Place the lower-left-bottom corner of the part at (0, 0, 0).
- Length runs along +X.
- Width runs along +Y.
- Thickness/height runs along +Z.
- Assign the final CadQuery object to a variable named `result`.
- Return only Python code. Do not include Markdown or explanations.

Structured summary:
{{ structured_spec }}
```

The model call should include `drawing.png` as the image input.

## Prompt mode: `image_only_v1`

Use this mode to test the actual drawing-to-CAD task.

Template:

```text
You are given a dimensioned mechanical drawing image.

Create executable CadQuery Python code for the part.

Requirements:
- Use CadQuery.
- Use millimeters.
- Place the lower-left-bottom corner of the part at (0, 0, 0).
- Length runs along +X.
- Width runs along +Y.
- Thickness/height runs along +Z.
- Assign the final CadQuery object to a variable named `result`.
- Return only Python code. Do not include Markdown or explanations.
```

The model call should include `drawing.png` as the image input.

## Why multiple modes matter

`text_spec_v1` separates CAD code generation from vision.

`image_plus_spec_v1` tests whether the model can use the drawing while still giving it structured dimensions.

`image_only_v1` tests the real target workflow.

A model that succeeds on text-spec mode but fails image-only mode likely has a drawing interpretation problem.

A model that fails all modes likely has a CAD generation or spatial construction problem.

## Response parsing

Models may ignore instructions and return Markdown.

The parser should support:

```text
raw Python code
```python fenced code blocks
``` generic fenced code blocks
intro paragraph + code
```

Prefer the first fenced Python block if present.

The phase-2 API is:

```python
from legacy_part_bench.models import extract_python_code, render_prompt

prompt = render_prompt(
    "image_plus_spec_v1",
    metadata=metadata,
    image_path=part_dir / "drawing.png",
)
code = extract_python_code(raw_model_response)
```

`text_spec_v1` and `image_plus_spec_v1` render a stable structured JSON spec from
metadata by default. `image_only_v1` omits the structured spec but still requires
the drawing image and repeats the CadQuery output contract.

Phase 8 structured specs may include:

```text
family: mounting_plate, stepped_block, or l_bracket
difficulty: 1, 2, or 3
features.holes
features.slots
features.steps
parameters.base_height for stepped blocks
parameters.flange_thickness for L-brackets
```

## OpenRouter runner

The one-model runner sends prompts through `legacy_part_bench.models.OpenRouterClient`.
Text-only prompts are sent as a normal user message. Image prompts send message
content as a list with the text prompt first and `drawing.png` second as a
base64 `image_url` data URL.

```bash
python scripts/run_one_model.py \
  --part-dir data/benchmark/plate_0001 \
  --model openai/gpt-4o-mini \
  --prompt-mode image_plus_spec_v1 \
  --output-dir data/results/openrouter_test/plate_0001
```

The runner reads `OPENROUTER_API_KEY`, caches raw responses by model, part id,
prompt mode, prompt version, image hash, and temperature, then writes the usual
run artifacts before scoring. Pass `--env-file .env` when the API key is stored
locally rather than exported in the shell. Use `--force` to bypass the cache.
When OpenRouter returns usage metadata, the runner writes `usage.json` and stores
token counts and provider cost in `run_config.json`.
