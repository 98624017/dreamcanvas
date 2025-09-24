from __future__ import annotations

import asyncio
from typing import Any

import pytest
from httpx import AsyncClient


async def _poll_history(client: AsyncClient, task_id: str, timeout: float = 2.0) -> dict[str, Any]:
    deadline = asyncio.get_event_loop().time() + timeout
    last: dict[str, Any] | None = None
    while asyncio.get_event_loop().time() < deadline:
        resp = await client.get("/jimeng/history", params={"taskId": task_id})
        resp.raise_for_status()
        payload = resp.json()
        last = payload
        status = payload["task"]["status"]
        if status in {"succeeded", "failed"}:
            return payload
        await asyncio.sleep(0.05)
    if last is None:
        raise AssertionError("未能获取任务历史记录")
    return last


@pytest.mark.asyncio
async def test_jimeng_task_lifecycle_success(api_client: AsyncClient):
    resp = await api_client.post(
        "/jimeng/tasks",
        json={"prompt": "渲染未来城市", "simulateDelayMs": 50},
    )
    resp.raise_for_status()
    task_id = resp.json()["task"]["taskId"]

    payload = await _poll_history(api_client, task_id)
    assert payload["task"]["status"] == "succeeded"
    assert payload["task"]["resultUris"], "结果应包含资源链接"


@pytest.mark.asyncio
async def test_jimeng_task_failure_code(api_client: AsyncClient):
    resp = await api_client.post(
        "/jimeng/tasks",
        json={"prompt": "触发 #quota 限频", "simulateDelayMs": 10},
    )
    resp.raise_for_status()
    task_id = resp.json()["task"]["taskId"]

    payload = await _poll_history(api_client, task_id)
    assert payload["task"]["status"] == "failed"
    assert payload["task"].get("errorCode") == "1015"


@pytest.mark.asyncio
async def test_jimeng_cancel_task(api_client: AsyncClient):
    resp = await api_client.post(
        "/jimeng/tasks",
        json={"prompt": "准备取消", "simulateDelayMs": 1000},
    )
    resp.raise_for_status()
    task_id = resp.json()["task"]["taskId"]

    cancel_resp = await api_client.post(f"/jimeng/tasks/{task_id}/cancel")
    cancel_resp.raise_for_status()
    payload = cancel_resp.json()
    assert payload["task"]["status"] == "cancelled"
