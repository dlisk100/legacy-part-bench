"""Extract executable Python code from model responses."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

CodeSource = Literal["python_fence", "generic_fence", "raw"]

_FENCE_RE = re.compile(
    r"```(?P<language>[^\n`]*)\n(?P<code>.*?)(?:\n```|```)",
    flags=re.DOTALL,
)

_PYTHON_LANGUAGE_HINTS = {
    "py",
    "python",
    "python3",
}

_CODE_START_RE = re.compile(
    r"^\s*(import\s+cadquery|import\s+cq|from\s+cadquery|import\s+\w+|from\s+\w+|"
    r"cq\s*=|result\s*=|def\s+\w+\(|class\s+\w+)",
    flags=re.MULTILINE,
)


@dataclass(frozen=True)
class ParsedResponse:
    """Parsed model response and where the code came from."""

    code: str
    source: CodeSource
    fence_language: str | None = None


def extract_python_code(response_text: str) -> str:
    """Extract Python code from a raw model response."""

    return parse_model_response(response_text).code


def parse_model_response(response_text: str) -> ParsedResponse:
    """Parse a model response, preferring fenced Python code when available."""

    if not response_text or not response_text.strip():
        raise ValueError("Model response is empty; no Python code can be extracted.")

    fences = list(_FENCE_RE.finditer(response_text))
    for fence in fences:
        language = _normalize_language(fence.group("language"))
        if language in _PYTHON_LANGUAGE_HINTS:
            return ParsedResponse(
                code=_clean_code(fence.group("code")),
                source="python_fence",
                fence_language=language or None,
            )

    if fences:
        first_fence = fences[0]
        return ParsedResponse(
            code=_clean_code(first_fence.group("code")),
            source="generic_fence",
            fence_language=_normalize_language(first_fence.group("language")) or None,
        )

    return ParsedResponse(code=_extract_raw_code(response_text), source="raw")


def _normalize_language(language: str) -> str:
    cleaned = language.strip().lower().split(maxsplit=1)
    return cleaned[0] if cleaned else ""


def _clean_code(code: str) -> str:
    cleaned = code.strip()
    if not cleaned:
        raise ValueError("Extracted code block is empty.")
    return cleaned + "\n"


def _extract_raw_code(response_text: str) -> str:
    stripped = response_text.strip()
    match = _CODE_START_RE.search(stripped)
    if not match:
        raise ValueError("No Python code block or recognizable Python code was found.")
    return _clean_code(stripped[match.start() :])
