import logging

from fastapi import FastAPI

from .api.routes import register_routes
from .config.settings import get_settings
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

    secret_manager = SecretManager(path=settings.secrets_path)
    if settings.secrets_passphrase:
        try:
            secret_manager.load(passphrase=settings.secrets_passphrase, refresh=True)
        except SecretStoreError as exc:
            logger.warning("预加载加密凭据失败：%s", exc)
    app.state.secret_manager = secret_manager

    register_routes(app)

    @app.get("/healthz", tags=["system"])
    async def health_check() -> dict[str, str]:
        return {"status": "ok", "phase": settings.phase}

    return app


app = create_app()
