from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any, Dict

import pytest
from httpx import AsyncClient

from dreamcanvas.app import create_app
from dreamcanvas.config.settings import get_settings
from dreamcanvas.models.tasks import TaskStatus
from dreamcanvas.services.jimeng import JimengService
from dreamcanvas.services.jimeng_client import JimengSubmissionResult
from dreamcanvas.services.projects import ProjectStorage


class MockJimengClient:
    """用于单元测试的即梦客户端，模拟最常见的状态流转。"""

    def __init__(self) -> None:
        self.account_label = "mock"
        self._states: Dict[str, Dict[str, Any]] = {}

    async def submit_generation(
        self,
        *,
        prompt: str,
        model: str | None,
        size: str | None,
        batch: int,
    ) -> JimengSubmissionResult:
        history_id = uuid.uuid4().hex
        scenario = "quota" if "#quota" in (prompt or "").lower() else "success"
        if "准备取消" in (prompt or ""):
            scenario = "slow"
        self._states[history_id] = {"scenario": scenario, "count": 0, "prompt": prompt}
        queue_message = "任务已排队，预计等待数秒" if scenario == "quota" else None
        status = TaskStatus.QUEUED if scenario == "quota" else TaskStatus.RUNNING
        return JimengSubmissionResult(
            history_id=history_id,
            status=status,
            result_urls=[],
            queue_message=queue_message,
            queue_info=None,
        )

    async def fetch_history(self, history_id: str) -> JimengSubmissionResult:
        state = self._states.get(history_id)
        if state is None:
            return JimengSubmissionResult(
                history_id=history_id,
                status=TaskStatus.FAILED,
                result_urls=[],
                error_code="unknown",
                error_message="任务不存在",
            )
        state["count"] += 1
        scenario = state["scenario"]
        if scenario == "quota":
            if state["count"] >= 2:
                return JimengSubmissionResult(
                    history_id=history_id,
                    status=TaskStatus.FAILED,
                    result_urls=[],
                    error_code="1015",
                    error_message="账号请求过于频繁",
                )
            return JimengSubmissionResult(
                history_id=history_id,
                status=TaskStatus.RUNNING,
                result_urls=[],
                queue_message="排队中，请等待",
            )
        if scenario == "slow":
            return JimengSubmissionResult(
                history_id=history_id,
                status=TaskStatus.RUNNING,
                result_urls=[],
            )
        # success 场景
        if state["count"] >= 2:
            return JimengSubmissionResult(
                history_id=history_id,
                status=TaskStatus.SUCCEEDED,
                result_urls=[f"https://mock/{history_id}.png"],
            )
        return JimengSubmissionResult(
            history_id=history_id,
            status=TaskStatus.RUNNING,
            result_urls=[],
        )

    async def fetch_resource(self, url: str) -> bytes:
        return b"mock-binary"

    async def aclose(self) -> None:
        return None


@pytest.fixture(name="api_client")
async def api_client_fixture(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncIterator[AsyncClient]:
    base = tmp_path / "dc"
    base.mkdir(parents=True, exist_ok=True)

    monkeypatch.setenv("DC_LOG_DIR", str(base / "logs"))
    monkeypatch.setenv("DC_PROJECTS_DIR", str(base / "projects"))
    monkeypatch.setenv("DC_BACKUPS_DIR", str(base / "backups"))
    get_settings.cache_clear()

    app = create_app()
    app.state.project_storage = ProjectStorage(base / "projects")
    app.state.jimeng_service = JimengService(
        config={"sessionid": "mock-session", "account_name": "mock"},
        client=MockJimengClient(),
        proxy_config=None,
        poll_interval=0.05,
        poll_timeout=2.0,
        project_storage=app.state.project_storage,
    )

    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

    get_settings.cache_clear()
