from __future__ import annotations

import base64
from io import BytesIO

import pytest
from httpx import AsyncClient
from PIL import Image


def _make_test_image() -> str:
    image = Image.new("RGBA", (4, 4), (255, 255, 255, 255))
    for x in range(1, 3):
        for y in range(1, 3):
            image.putpixel((x, y), (20, 120, 220, 255))
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    payload = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{payload}"


@pytest.mark.asyncio
async def test_segment_image_alpha_channel(api_client: AsyncClient):
    encoded = _make_test_image()
    resp = await api_client.post(
        "/tools/segment_image",
        json={"imageBase64": encoded, "foregroundBias": 40},
    )
    resp.raise_for_status()
    result = resp.json()["imageBase64"]
    _, base64_data = result.split(",", 1)
    decoded = base64.b64decode(base64_data)
    image = Image.open(BytesIO(decoded))
    alpha_values = [image.getpixel((x, y))[3] for x in range(4) for y in range(4)]
    assert min(alpha_values) == 0
    assert max(alpha_values) == 255


@pytest.mark.asyncio
async def test_llm_text_response(api_client: AsyncClient):
    resp = await api_client.post(
        "/tools/llm_text",
        json={"prompt": "设计未来感主视觉", "tone": "鼓舞"},
    )
    resp.raise_for_status()
    payload = resp.json()
    assert "文案润色" in payload["content"]
    assert len(payload["suggestions"]) >= 3
