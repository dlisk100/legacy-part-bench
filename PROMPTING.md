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
