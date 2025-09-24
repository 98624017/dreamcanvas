"""工具相关 API，包括抠图与 LLM 文本助手。"""

from __future__ import annotations

import base64
from dataclasses import dataclass
from io import BytesIO
from typing import Any, Dict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator
from PIL import Image, ImageOps, ImageStat

router = APIRouter()


class SegmentImageRequest(BaseModel):
    image_base64: str = Field(alias="imageBase64")
    foreground_bias: int = Field(default=32, ge=0, le=128)

    model_config = {"populate_by_name": True}

    @field_validator("image_base64")
    @classmethod
    def validate_base64(cls, value: str) -> str:
        if not value:
            raise ValueError("图像内容不能为空")
        return value


class SegmentImageResponse(BaseModel):
    image_base64: str = Field(alias="imageBase64")

    model_config = {"populate_by_name": True}


class LlmTextRequest(BaseModel):
    prompt: str
    context: str | None = None
    tone: str | None = None


class LlmTextResponse(BaseModel):
    content: str
    suggestions: list[str]


@dataclass(slots=True)
class _ImagePayload:
    image: Image.Image
    mime: str


def _decode_image(data: str) -> _ImagePayload:
    if "," in data:
        header, body = data.split(",", 1)
        mime = header.split(";")[0].removeprefix("data:") or "image/png"
        content = body
    else:
        mime = "image/png"
        content = data
    try:
        raw = base64.b64decode(content)
    except (base64.binascii.Error, ValueError) as exc:
        raise HTTPException(status_code=400, detail="图像内容不是合法的 Base64 编码") from exc
    try:
        image = Image.open(BytesIO(raw))
    except OSError as exc:
        raise HTTPException(status_code=400, detail="无法解析图像内容") from exc
    return _ImagePayload(image=image.convert("RGBA"), mime=mime)


def _encode_image(image: Image.Image, mime: str) -> str:
    output = BytesIO()
    format_name = "PNG" if mime.lower() not in {"image/jpeg", "image/jpg"} else "PNG"
    image.save(output, format=format_name)
    payload = base64.b64encode(output.getvalue()).decode("ascii")
    return f"data:image/png;base64,{payload}"


def _simple_matting(image: Image.Image, bias: int) -> Image.Image:
    gray = image.convert("L")
    stats = ImageStat.Stat(gray)
    mean_brightness = stats.mean[0]
    threshold = max(30, min(240, int(mean_brightness + bias)))
    enhanced = ImageOps.autocontrast(gray)
    mask = enhanced.point(lambda px: 0 if px >= threshold else 255, mode="L")
    result = image.copy()
    result.putalpha(mask)
    return result


@router.post("/segment_image", response_model=SegmentImageResponse)
async def segment_image(payload: SegmentImageRequest) -> SegmentImageResponse:
    decoded = _decode_image(payload.image_base64)
    processed = _simple_matting(decoded.image, payload.foreground_bias)
    encoded = _encode_image(processed, decoded.mime)
    return SegmentImageResponse(image_base64=encoded)


@router.post("/llm_text", response_model=LlmTextResponse)
async def llm_text(payload: LlmTextRequest) -> LlmTextResponse:
    prompt = payload.prompt.strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="prompt 不能为空")

    tone = payload.tone or "灵感"
    suggestions = [
        f"围绕主题“{prompt[:24]}”，尝试从用户视角描述希望的画面细节。",
        "明确构图（前景/主体/背景）并给出光效或材质关键词。",
        "为即梦配置 2-3 个风格或画师标签，便于后续自动重试。",
    ]
    if payload.context:
        suggestions.append("结合上下文素材中的颜色与风格标签，保持项目统一性。")

    content = (
        f"以下是基于“{prompt[:40]}”的文案润色建议，请按需调整：\n"
        f"1. 先描述主体，其次是场景与氛围。\n"
        f"2. 使用 {tone} 的表达方式，避免过多形容词堆叠。\n"
        "3. 如需多轮生成，请为下一轮提前制定差异化的提示词片段。"
    )
    return LlmTextResponse(content=content, suggestions=suggestions)
