from __future__ import annotations

from pathlib import Path

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_system_diagnostics(api_client: AsyncClient):
    resp = await api_client.get("/system/diagnostics")
    resp.raise_for_status()
    payload = resp.json()
    assert payload["phase"]
    assert payload["logDir"]
    assert "projects" in payload
    assert payload["projects"]["projectCount"] == len(payload["projects"]["projects"])


@pytest.mark.asyncio
async def test_system_backup(api_client: AsyncClient):
    resp = await api_client.post("/system/backup")
    resp.raise_for_status()
    payload = resp.json()
    archive = Path(payload["path"])
    assert archive.exists()
    assert archive.suffix == ".zip"
