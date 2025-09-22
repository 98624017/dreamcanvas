"""即梦 API 客户端占位实现。"""

from typing import Any


class JimengService:
    """封装即梦任务提交、轮询与异常处理。"""

    async def submit_task(self, payload: dict[str, Any]) -> dict[str, Any]:
        # TODO: 实现调用 core/token_manager
        return {"status": "queued", "payload": payload}
