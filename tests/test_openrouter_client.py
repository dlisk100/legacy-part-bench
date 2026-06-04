from __future__ import annotations

import base64

import pytest

from legacy_part_bench.models.openrouter_client import (
    OpenRouterClient,
    OpenRouterError,
    build_user_content,
    extract_assistant_content,
    image_path_to_data_url,
)


def test_image_path_to_data_url_encodes_local_png(tmp_path):
    image_path = tmp_path / "drawing.png"
    image_bytes = b"\x89PNG\r\n"
    image_path.write_bytes(image_bytes)

    data_url = image_path_to_data_url(image_path)

    assert data_url == f"data:image/png;base64,{base64.b64encode(image_bytes).decode('ascii')}"


def test_build_user_content_uses_string_for_text_only_prompt():
    assert build_user_content("hello") == "hello"


def test_build_user_content_puts_text_before_image(tmp_path):
    image_path = tmp_path / "drawing.png"
    image_path.write_bytes(b"image")

    content = build_user_content("make CAD", image_path=image_path)

    assert isinstance(content, list)
    assert content[0] == {"type": "text", "text": "make CAD"}
    assert content[1]["type"] == "image_url"
    assert content[1]["image_url"]["url"].startswith("data:image/png;base64,")


def test_extract_assistant_content_accepts_string_content():
    raw = {"choices": [{"message": {"content": "result = 1"}}]}

    assert extract_assistant_content(raw) == "result = 1"


def test_extract_assistant_content_accepts_text_parts():
    raw = {"choices": [{"message": {"content": [{"type": "text", "text": "result = 1"}]}}]}

    assert extract_assistant_content(raw) == "result = 1"


def test_from_env_requires_api_key(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    with pytest.raises(OpenRouterError, match="OPENROUTER_API_KEY"):
        OpenRouterClient.from_env()


def test_create_completion_posts_openrouter_payload(monkeypatch):
    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"choices": [{"message": {"content": "result = 1"}}]}

    def fake_post(url, headers, json, timeout):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr("legacy_part_bench.models.openrouter_client.requests.post", fake_post)
    client = OpenRouterClient(api_key="test-key", timeout_seconds=7)

    response = client.create_completion(
        model="test/model",
        prompt_text="make CAD",
        temperature=0.2,
        max_tokens=100,
    )

    assert response.content == "result = 1"
    assert captured["headers"]["Authorization"] == "Bearer test-key"
    assert captured["json"]["model"] == "test/model"
    assert captured["json"]["messages"][0]["content"] == "make CAD"
    assert captured["json"]["temperature"] == 0.2
    assert captured["json"]["max_tokens"] == 100
    assert captured["timeout"] == 7
