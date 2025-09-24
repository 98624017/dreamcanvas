import logging

from fastapi import FastAPI

from .api.routes import register_routes
from .config.settings import get_settings
from .services.jimeng import JimengService
from .services.projects import ProjectStorage
from .services.secret_manager import SecretManager, SecretStoreError

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """构建 FastAPI 应用，注册路由与中间件。"""
    settings = get_settings()
    app = FastAPI(
        title="DreamCanvas API",
        description="DreamCanvas 桌面端后端服务",
        version=settings.version,
    )

    secret_manager = SecretManager(
        path=settings.secrets_path,
        plaintext_path=settings.secrets_plaintext_path,
    )
    secrets_payload: dict[str, object] | None
    try:
        secrets_payload = secret_manager.load(passphrase=settings.secrets_passphrase, refresh=True)
    except SecretStoreError as exc:
        secrets_payload = None
        logger.warning("加载凭据时出现问题：%s", exc)
    app.state.secret_manager = secret_manager

    project_storage = ProjectStorage(settings.projects_dir)
    app.state.project_storage = project_storage

    jimeng_config = (secrets_payload or {}).get("jimeng") if isinstance(secrets_payload, dict) else None
    proxy_config = (secrets_payload or {}).get("proxy") if isinstance(secrets_payload, dict) else None
    if not jimeng_config or not (jimeng_config.get("sessionid") or "").strip():
        logger.warning("未检测到有效的即梦凭据，将以离线占位配置启动，仅供调试使用。")
        jimeng_config = {"sessionid": "placeholder", "account_name": "offline"}
    app.state.jimeng_service = JimengService(
        config=jimeng_config,
        proxy_config=proxy_config,
        project_storage=project_storage,
    )

    register_routes(app)

    @app.get("/healthz", tags=["system"])
    async def health_check() -> dict[str, str]:
        return {"status": "ok", "phase": settings.phase}

    @app.on_event("shutdown")
    async def shutdown_services() -> None:
        await app.state.jimeng_service.aclose()

    return app


app = create_app()
