"""系统诊断与备份相关 API。"""

from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request

from ..config.settings import get_settings
from ..services.jimeng import JimengService
from ..services.projects import ProjectStorage

router = APIRouter()


async def _get_storage(request: Request) -> ProjectStorage:
    storage: ProjectStorage | None = getattr(request.app.state, "project_storage", None)
    if storage is None:
        raise RuntimeError("ProjectStorage 尚未初始化")
    return storage


async def _get_jimeng(request: Request) -> JimengService:
    service: JimengService | None = getattr(request.app.state, "jimeng_service", None)
    if service is None:
        raise RuntimeError("JimengService 尚未初始化")
    return service


@router.get("/diagnostics")
async def diagnostics(
    storage: ProjectStorage = Depends(_get_storage),
    jimeng: JimengService = Depends(_get_jimeng),
) -> dict[str, object]:
    settings = get_settings()
    tasks = await jimeng.list_tasks()
    return {
        "version": settings.version,
        "phase": settings.phase,
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "logDir": str(settings.log_dir),
        "projects": storage.diagnostics(),
        "tasks": {
            "total": len(tasks),
            "active": sum(1 for task in tasks if task.status in {"queued", "running"}),
        },
    }


@router.post("/backup")
async def trigger_backup(storage: ProjectStorage = Depends(_get_storage)) -> dict[str, str]:
    settings = get_settings()
    backup_root = settings.backups_dir
    backup_root.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    base_name = backup_root / f"{timestamp}-projects"

    try:
        archive_path = Path(shutil.make_archive(str(base_name), "zip", root_dir=storage.root))
    except (FileNotFoundError, OSError) as exc:
        raise HTTPException(status_code=500, detail=f"创建备份失败：{exc}") from exc

    return {
        "status": "succeeded",
        "path": str(archive_path),
    }
