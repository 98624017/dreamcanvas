from datetime import datetime

from fastapi import APIRouter

from ..config.settings import get_settings

router = APIRouter()


@router.get("/diagnostics")
async def diagnostics() -> dict[str, str]:
    settings = get_settings()
    return {
        "version": settings.version,
        "phase": settings.phase,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


@router.post("/backup")
async def trigger_backup() -> dict[str, str]:
    # TODO: 集成备份任务调度
    return {"status": "queued", "message": "备份任务已加入队列"}
