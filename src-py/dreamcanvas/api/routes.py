from fastapi import FastAPI

from . import jimeng, system, tools


def register_routes(app: FastAPI) -> None:
    """注册所有路由模块。"""

    app.include_router(system.router, prefix="/system", tags=["system"])
    app.include_router(jimeng.router, prefix="/jimeng", tags=["jimeng"])
    app.include_router(tools.router, prefix="/tools", tags=["tools"])
