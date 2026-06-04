import pytest

from legacy_part_bench.models import extract_python_code, parse_model_response


def test_extract_python_code_accepts_raw_code():
    code = "import cadquery as cq\nresult = cq.Workplane('XY').box(1, 2, 3)\n"

    assert extract_python_code(code) == code


def test_parse_model_response_prefers_python_fenced_code():
    response = """
Here is the code:

```python
import cadquery as cq
result = cq.Workplane("XY").box(1, 2, 3)
```
"""

    parsed = parse_model_response(response)

    assert parsed.source == "python_fence"
    assert parsed.fence_language == "python"
    assert parsed.code == 'import cadquery as cq\nresult = cq.Workplane("XY").box(1, 2, 3)\n'


def test_parse_model_response_accepts_python3_fence_with_options():
    response = """
```python3 linenums
result = 1
```
"""

    parsed = parse_model_response(response)

    assert parsed.source == "python_fence"
    assert parsed.fence_language == "python3"
    assert parsed.code == "result = 1\n"


def test_parse_model_response_uses_first_generic_fence_when_no_python_fence():
    response = """
Some prose.

```
result = 1
```

```
result = 2
```
"""

    parsed = parse_model_response(response)

    assert parsed.source == "generic_fence"
    assert parsed.fence_language is None
    assert parsed.code == "result = 1\n"


def test_parse_model_response_prefers_later_python_fence_over_generic_fence():
    response = """
```
not python
```

```py
result = 42
```
"""

    parsed = parse_model_response(response)

    assert parsed.source == "python_fence"
    assert parsed.fence_language == "py"
    assert parsed.code == "result = 42\n"


def test_parse_model_response_extracts_code_after_intro_text():
    response = """
Sure, here is one way to do it.

import cadquery as cq

result = cq.Workplane("XY").box(1, 2, 3)
"""

    parsed = parse_model_response(response)

    assert parsed.source == "raw"
    assert parsed.code.startswith("import cadquery as cq")
    assert "result =" in parsed.code


def test_parse_model_response_rejects_empty_or_unrecognizable_text():
    with pytest.raises(ValueError, match="empty"):
        parse_model_response("")

    with pytest.raises(ValueError, match="No Python code"):
        parse_model_response("This is only an explanation.")
