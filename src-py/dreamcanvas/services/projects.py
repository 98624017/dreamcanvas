"""项目数据的磁盘持久化服务。"""

from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, Dict, Iterable, List

from pydantic import ValidationError

from ..models.project import (
    AssetPayload,
    GenerationRecord,
    ProjectManifest,
    ProjectPayload,
)

_JSON_INDENT = 2


def _atomic_write(path: Path, data: Any) -> None:
    """将 JSON 数据原子写入磁盘。"""

    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(".tmp")
    payload = json.dumps(data, ensure_ascii=False, indent=_JSON_INDENT)
    tmp_path.write_text(payload, encoding="utf-8")
    os.replace(tmp_path, path)


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


@dataclass(slots=True)
class ProjectSummary:
    manifest: ProjectManifest
    assets_count: int
    history_count: int


class ProjectStorage:
    """按要求维护 `%APPDATA%/DreamCanvas/projects` 目录结构。"""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def _project_dir(self, project_id: str) -> Path:
        return self.root / project_id

    def _manifest_path(self, project_id: str) -> Path:
        return self._project_dir(project_id) / "manifest.json"

    def _canvas_path(self, project_id: str) -> Path:
        return self._project_dir(project_id) / "canvas.json"

    def _assets_path(self, project_id: str) -> Path:
        return self._project_dir(project_id) / "assets.json"

    def _history_path(self, project_id: str) -> Path:
        return self._project_dir(project_id) / "history.json"

    def list_projects(self) -> List[ProjectSummary]:
        summaries: List[ProjectSummary] = []
        for entry in sorted(self.root.glob("*/manifest.json")):
            try:
                manifest = ProjectManifest.model_validate_json(entry.read_text(encoding="utf-8"))
            except (ValidationError, json.JSONDecodeError):
                continue
            project_id = manifest.id
            assets = _read_json(self._assets_path(project_id), default=[])
            history = _read_json(self._history_path(project_id), default=[])
            summaries.append(
                ProjectSummary(
                    manifest=manifest,
                    assets_count=len(assets),
                    history_count=len(history),
                )
            )
        return summaries

    def create_project(self, name: str) -> ProjectPayload:
        project_id = uuid.uuid4().hex
        now = int(time.time() * 1000)
        manifest = ProjectManifest(
            id=project_id,
            name=name,
            created_at=now,
            updated_at=now,
            version="1.0.0",
            canvas_checksum="",
        )
        project_dir = self._project_dir(project_id)
        project_dir.mkdir(parents=True, exist_ok=True)
        _atomic_write(self._manifest_path(project_id), manifest.model_dump(by_alias=True))
        _atomic_write(self._canvas_path(project_id), {})
        _atomic_write(self._assets_path(project_id), [])
        _atomic_write(self._history_path(project_id), [])
        return self.load_project(project_id)

    def load_project(self, project_id: str) -> ProjectPayload:
        manifest_json = _read_json(self._manifest_path(project_id), default=None)
        if manifest_json is None:
            raise FileNotFoundError(f"项目 {project_id} 不存在")
        manifest = ProjectManifest.model_validate(manifest_json)
        canvas = _read_json(self._canvas_path(project_id), default={})
        assets_raw = _read_json(self._assets_path(project_id), default=[])
        history_raw = _read_json(self._history_path(project_id), default=[])
        assets = [AssetPayload.model_validate(item) for item in assets_raw]
        history = [GenerationRecord.model_validate(item) for item in history_raw]
        return ProjectPayload(manifest=manifest, canvas=canvas, assets=assets, history=history)

    def save_project(self, payload: ProjectPayload) -> ProjectPayload:
        project_id = payload.manifest.id
        now = int(time.time() * 1000)
        manifest = payload.manifest.model_copy(update={"updated_at": now})
        canvas_checksum = sha256(json.dumps(payload.canvas, sort_keys=True).encode("utf-8")).hexdigest()
        manifest = manifest.model_copy(update={"canvas_checksum": canvas_checksum})

        _atomic_write(self._manifest_path(project_id), manifest.model_dump(by_alias=True))
        _atomic_write(self._canvas_path(project_id), payload.canvas)
        _atomic_write(
            self._assets_path(project_id),
            [asset.model_dump(by_alias=True) for asset in payload.assets],
        )
        _atomic_write(
            self._history_path(project_id),
            [record.model_dump(by_alias=True) for record in payload.history],
        )
        return ProjectPayload(
            manifest=manifest,
            canvas=payload.canvas,
            assets=payload.assets,
            history=payload.history,
        )

    def append_history(self, project_id: str, record: GenerationRecord) -> None:
        history_raw = _read_json(self._history_path(project_id), default=[])
        history_raw.append(record.model_dump(by_alias=True))
        _atomic_write(self._history_path(project_id), history_raw)

    def diagnostics(self) -> Dict[str, Any]:
        summaries = self.list_projects()
        return {
            "projectCount": len(summaries),
            "projects": [
                {
                    "id": item.manifest.id,
                    "name": item.manifest.name,
                    "updatedAt": item.manifest.updated_at,
                    "assets": item.assets_count,
                    "history": item.history_count,
                }
                for item in summaries
            ],
        }
