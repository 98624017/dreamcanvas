"""项目数据结构的 Pydantic 定义。"""

from __future__ import annotations

from typing import Any, Dict, List

from pydantic import BaseModel, Field


class CamelModel(BaseModel):
    """统一使用驼峰字段的基础模型。"""

    model_config = {
        "populate_by_name": True,
        "alias_generator": lambda field_name: "".join(
            word.capitalize() if index > 0 else word
            for index, word in enumerate(field_name.split("_"))
        ),
        "ser_json_typed": False,
    }


class ProjectManifest(CamelModel):
    id: str
    name: str
    created_at: int = Field(alias="createdAt")
    updated_at: int = Field(alias="updatedAt")
    version: str = "1.0.0"
    canvas_checksum: str = Field(default="", alias="canvasChecksum")


class AssetPayload(CamelModel):
    id: str
    project_id: str = Field(alias="projectId")
    kind: str
    uri: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: int = Field(alias="createdAt")
    updated_at: int = Field(alias="updatedAt")


class GenerationRecord(CamelModel):
    id: str
    prompt: str
    session_id: str = Field(alias="sessionId")
    status: str
    result_uris: List[str] = Field(default_factory=list, alias="resultUris")
    error: str | None = None
    created_at: int = Field(alias="createdAt")
    completed_at: int | None = Field(default=None, alias="completedAt")


class ProjectPayload(CamelModel):
    manifest: ProjectManifest
    canvas: Dict[str, Any]
    assets: List[AssetPayload] = Field(default_factory=list)
    history: List[GenerationRecord] = Field(default_factory=list)
