"""Small OpenRouter client for benchmark model calls."""

from __future__ import annotations

import base64
import mimetypes
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests

OPENROUTER_CHAT_COMPLETIONS_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_TIMEOUT_SECONDS = 120.0


class OpenRouterError(RuntimeError):
    """Raised when an OpenRouter request cannot produce usable model text."""


@dataclass(frozen=True)
class OpenRouterResponse:
    """Normalized model response plus the raw provider payload."""

    content: str
    raw_json: dict[str, Any]
    model: str


@dataclass(frozen=True)
class OpenRouterClient:
    """Minimal OpenRouter chat-completions client."""

    api_key: str
    base_url: str = OPENROUTER_CHAT_COMPLETIONS_URL
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
    app_title: str = "LegacyPartBench"
    http_referer: str | None = None

    @classmethod
    def from_env(cls, **kwargs: Any) -> "OpenRouterClient":
        """Create a client using ``OPENROUTER_API_KEY``."""

        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            raise OpenRouterError("OPENROUTER_API_KEY is not set.")
        return cls(api_key=api_key, **kwargs)

    def create_completion(
        self,
        *,
        model: str,
        prompt_text: str,
        image_path: Path | str | None = None,
        temperature: float = 0.0,
        max_tokens: int | None = None,
    ) -> OpenRouterResponse:
        """Call OpenRouter and return assistant message content."""

        payload: dict[str, Any] = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": build_user_content(prompt_text, image_path=image_path),
                }
            ],
            "temperature": temperature,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        try:
            response = requests.post(
                self.base_url,
                headers=self._headers(),
                json=payload,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise OpenRouterError(f"OpenRouter request failed: {exc}") from exc

        try:
            raw_json = response.json()
        except ValueError as exc:
            raise OpenRouterError("OpenRouter response was not valid JSON.") from exc

        content = extract_assistant_content(raw_json)
        return OpenRouterResponse(content=content, raw_json=raw_json, model=model)

    def _headers(self) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-Title": self.app_title,
        }
        if self.http_referer:
            headers["HTTP-Referer"] = self.http_referer
        return headers


def build_user_content(
    prompt_text: str, *, image_path: Path | str | None = None
) -> str | list[dict[str, Any]]:
    """Build OpenRouter message content for text-only or text-plus-image prompts."""

    if image_path is None:
        return prompt_text

    return [
        {"type": "text", "text": prompt_text},
        {
            "type": "image_url",
            "image_url": {
                "url": image_path_to_data_url(image_path),
            },
        },
    ]


def image_path_to_data_url(image_path: Path | str) -> str:
    """Encode a local image as a base64 data URL for multimodal requests."""

    path = Path(image_path)
    if not path.exists():
        raise OpenRouterError(f"Image input does not exist: {path}")
    mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def extract_assistant_content(raw_json: dict[str, Any]) -> str:
    """Extract ``choices[0].message.content`` from an OpenRouter response."""

    try:
        content = raw_json["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise OpenRouterError("OpenRouter response did not include assistant content.") from exc

    if isinstance(content, str) and content.strip():
        return content

    if isinstance(content, list):
        text_parts = [
            part.get("text", "")
            for part in content
            if isinstance(part, dict) and part.get("type") == "text"
        ]
        joined = "\n".join(part for part in text_parts if part).strip()
        if joined:
            return joined

    raise OpenRouterError("OpenRouter assistant content was empty.")
