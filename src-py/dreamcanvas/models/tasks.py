"""任务调度与即梦流程相关的数据模型。"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class GenerationTaskInfo(BaseModel):
    task_id: str = Field(alias="taskId")
    prompt: str
    status: TaskStatus
    metadata: Dict[str, Any] = Field(default_factory=dict)
    result_uris: List[str] = Field(default_factory=list, alias="resultUris")
    error_code: Optional[str] = Field(default=None, alias="errorCode")
    error_message: Optional[str] = Field(default=None, alias="errorMessage")
    created_at: int = Field(alias="createdAt")
    updated_at: int = Field(alias="updatedAt")

    model_config = {
        "populate_by_name": True,
        "use_enum_values": True,
    }
