"""即梦任务相关 API。"""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from ..models.tasks import GenerationTaskInfo, TaskStatus
from ..services.jimeng import JimengService

router = APIRouter()


class CreateTaskRequest(BaseModel):
    prompt: str
    model: str = Field(default="sdxl")
    size: str = Field(default="1024x1024")
    batch: int = Field(default=1, ge=1, le=4)
    project_id: str | None = Field(default=None, alias="projectId")
    reference_image: str | None = Field(default=None, alias="referenceImage")
    simulate_delay_ms: int | None = Field(default=None, alias="simulateDelayMs")
    simulate_error_code: str | None = Field(default=None, alias="simulateErrorCode")

    def to_payload(self) -> Dict[str, Any]:
        return self.model_dump(by_alias=True, exclude_none=True)


class CreateTaskResponse(BaseModel):
    task: GenerationTaskInfo


class HistoryResponse(BaseModel):
    task: GenerationTaskInfo


class CancelResponse(BaseModel):
    task: GenerationTaskInfo


async def _get_service(request: Request) -> JimengService:
    service: JimengService | None = getattr(request.app.state, "jimeng_service", None)
    if service is None:
        raise RuntimeError("JimengService 尚未初始化")
    return service


@router.post("/tasks", response_model=CreateTaskResponse)
async def create_task(
    payload: CreateTaskRequest,
    service: JimengService = Depends(_get_service),
) -> CreateTaskResponse:
    try:
        task = await service.submit_task(payload.to_payload())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return CreateTaskResponse(task=task)


@router.get("/history", response_model=HistoryResponse)
async def get_history(
    task_id: str = Query(alias="taskId"),
    service: JimengService = Depends(_get_service),
) -> HistoryResponse:
    try:
        task = await service.get_task(task_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="任务不存在") from exc
    return HistoryResponse(task=task)


@router.post("/tasks/{task_id}/cancel", response_model=CancelResponse)
async def cancel_task(
    task_id: str,
    service: JimengService = Depends(_get_service),
) -> CancelResponse:
    try:
        task = await service.cancel_task(task_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="任务不存在") from exc
    if task.status != TaskStatus.CANCELLED:
        raise HTTPException(status_code=409, detail="任务已完成，无法取消")
    return CancelResponse(task=task)
