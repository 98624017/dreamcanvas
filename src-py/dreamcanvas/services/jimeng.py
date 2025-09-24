"""即梦任务服务，负责对接真实生产管道并管理本地状态。"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..models.project import AssetPayload, GenerationRecord, ProjectPayload
from ..models.tasks import GenerationTaskInfo, TaskStatus
from .jimeng_client import JimengApiError, JimengClient, JimengSubmissionResult
from .projects import ProjectStorage

logger = logging.getLogger(__name__)

_DEFAULT_POLL_INTERVAL = 3.0
_DEFAULT_POLL_TIMEOUT = 240.0


@dataclass(slots=True)
class TaskContext:
    """跟踪任务轮询所需的上下文信息。"""

    history_id: str
    created_ms: int
    started_monotonic: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class JimengService:
    """封装即梦任务提交、轮询与异常追踪。"""

    def __init__(
        self,
        *,
        config: Dict[str, Any] | None,
        proxy_config: Dict[str, str] | str | None = None,
        client: JimengClient | None = None,
        poll_interval: float = _DEFAULT_POLL_INTERVAL,
        poll_timeout: float = _DEFAULT_POLL_TIMEOUT,
        project_storage: ProjectStorage | None = None,
    ) -> None:
        config = config or {}
        sessionid = (config.get("sessionid") or "").strip()
        if not sessionid:
            raise ValueError("即梦凭据缺少 sessionid，请在 secrets 中填写后重试")
        account_name = (config.get("account_name") or "").strip() or "default"
        self._client = client or JimengClient(sessionid=sessionid, account_name=account_name, proxies=proxy_config)
        self._poll_interval = poll_interval
        self._poll_timeout = poll_timeout
        self._project_storage = project_storage

        self._tasks: Dict[str, GenerationTaskInfo] = {}
        self._contexts: Dict[str, TaskContext] = {}
        self._pollers: Dict[str, asyncio.Task[Any]] = {}
        self._asset_tasks: Dict[str, asyncio.Task[Any]] = {}
        self._traces: Dict[str, List[Dict[str, Any]]] = {}
        self._lock = asyncio.Lock()

    @property
    def account_label(self) -> str:
        return self._client.account_label

    async def submit_task(self, payload: Dict[str, Any]) -> GenerationTaskInfo:
        prompt = (payload.get("prompt") or "").strip()
        if not prompt:
            raise ValueError("prompt 不能为空")

        model = payload.get("model")
        size = payload.get("size")
        batch = int(payload.get("batch") or 1)
        metadata: Dict[str, Any] = {
            "model": model or "3.0",
            "size": size or "1024x1024",
            "batch": batch,
            "account": self.account_label,
        }
        if payload.get("projectId"):
            metadata["projectId"] = payload["projectId"]
        if payload.get("referenceImage"):
            metadata["referenceImage"] = payload["referenceImage"]

        now_ms = int(time.time() * 1000)
        try:
            submission = await self._client.submit_generation(
                prompt=prompt,
                model=model,
                size=size,
                batch=batch,
            )
        except JimengApiError as exc:
            logger.error("即梦任务提交失败：%s", exc)
            task_id = f"failed-{uuid4_hex()}"
            metadata["historyId"] = task_id
            self._record_trace(task_id, "submit_failed", message=str(exc), code=exc.code)
            return await self._store_task(
                task_id=task_id,
                prompt=prompt,
                created_ms=now_ms,
                submission=JimengSubmissionResult(
                    history_id=task_id,
                    status=TaskStatus.FAILED,
                    result_urls=[],
                    error_code=exc.code or "api_error",
                    error_message=str(exc),
                    raw=exc.payload,
                ),
                metadata=metadata,
            )

        task_id = submission.history_id
        metadata["historyId"] = task_id
        if submission.queue_message:
            metadata["queueMessage"] = submission.queue_message

        task = await self._store_task(
            task_id=task_id,
            prompt=prompt,
            created_ms=now_ms,
            submission=submission,
            metadata=metadata,
        )

        if self._status_value(task.status) not in {
            TaskStatus.SUCCEEDED.value,
            TaskStatus.FAILED.value,
            TaskStatus.CANCELLED.value,
        }:
            context = TaskContext(
                history_id=task_id,
                created_ms=now_ms,
                started_monotonic=time.monotonic(),
                metadata=dict(metadata),
            )
            self._contexts[task_id] = context
            poller = asyncio.create_task(self._poll_task(task_id), name=f"jimeng-poller-{task_id}")
            poller.add_done_callback(self._on_poller_done)
            self._pollers[task_id] = poller

        self._record_trace(task_id, "submit", state=self._status_value(task.status), metadata=dict(metadata))
        if self._status_value(task.status) == TaskStatus.SUCCEEDED.value:
            self._record_trace(task_id, "completed")
        elif self._status_value(task.status) == TaskStatus.FAILED.value:
            self._record_trace(task_id, "failed", error=task.error_code)
        return task

    async def get_task(self, task_id: str) -> GenerationTaskInfo:
        async with self._lock:
            if task_id not in self._tasks:
                raise KeyError(f"任务 {task_id} 不存在")
            return self._tasks[task_id]

    async def list_tasks(self) -> List[GenerationTaskInfo]:
        async with self._lock:
            return list(self._tasks.values())

    async def cancel_task(self, task_id: str) -> GenerationTaskInfo:
        async with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                raise KeyError(f"任务 {task_id} 不存在")
            if self._status_value(task.status) in {
                TaskStatus.SUCCEEDED.value,
                TaskStatus.FAILED.value,
                TaskStatus.CANCELLED.value,
            }:
                return task
            now = int(time.time() * 1000)
            metadata = dict(task.metadata)
            metadata["cancelledAt"] = now
            updated = task.model_copy(
                update={
                    "status": TaskStatus.CANCELLED,
                    "updated_at": now,
                    "metadata": metadata,
                }
            )
            self._tasks[task_id] = updated
        self._record_trace(task_id, "cancelled")
        poller = self._pollers.pop(task_id, None)
        if poller:
            poller.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await poller
        self._contexts.pop(task_id, None)
        return updated

    async def aclose(self) -> None:
        for poller in list(self._pollers.values()):
            poller.cancel()
        for poller in list(self._pollers.values()):
            with contextlib.suppress(asyncio.CancelledError):
                await poller
        self._pollers.clear()

        for task in list(self._asset_tasks.values()):
            task.cancel()
        for task in list(self._asset_tasks.values()):
            with contextlib.suppress(asyncio.CancelledError):
                await task
        self._asset_tasks.clear()

        self._contexts.clear()
        await self._client.aclose()

    def get_trace(self, task_id: str) -> List[Dict[str, Any]]:
        return list(self._traces.get(task_id, ()))

    async def _store_task(
        self,
        *,
        task_id: str,
        prompt: str,
        created_ms: int,
        submission: JimengSubmissionResult,
        metadata: Dict[str, Any],
        lock_guarded: bool = True,
    ) -> GenerationTaskInfo:
        async def _store() -> GenerationTaskInfo:
            now = int(time.time() * 1000)
            metadata_copy = dict(metadata)
            if submission.queue_message:
                metadata_copy["queueMessage"] = submission.queue_message
            if submission.queue_info:
                metadata_copy["queueInfo"] = submission.queue_info
            update: Dict[str, Any] = {
                "task_id": task_id,
                "prompt": prompt,
                "status": submission.status,
                "metadata": metadata_copy,
                "result_uris": submission.result_urls,
                "error_code": submission.error_code,
                "error_message": submission.error_message,
                "created_at": created_ms,
                "updated_at": now,
            }
            task = GenerationTaskInfo(**update)
            self._tasks[task_id] = task
            return task

        if lock_guarded:
            async with self._lock:
                task = await _store()
        else:
            task = await _store()
        self._schedule_asset_persist(task)
        return task

    async def _apply_submission(self, task_id: str, submission: JimengSubmissionResult) -> GenerationTaskInfo | None:
        async with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return None
            metadata = dict(task.metadata)
            if submission.queue_message:
                metadata["queueMessage"] = submission.queue_message
            if submission.queue_info:
                metadata["queueInfo"] = submission.queue_info
            update: Dict[str, Any] = {
                "metadata": metadata,
                "status": submission.status,
                "updated_at": int(time.time() * 1000),
                "result_uris": submission.result_urls or task.result_uris,
                "error_code": submission.error_code,
                "error_message": submission.error_message,
            }
            updated = task.model_copy(update=update)
            self._tasks[task_id] = updated
            self._schedule_asset_persist(updated)
            return updated

    async def _poll_task(self, task_id: str) -> None:
        try:
            while True:
                await asyncio.sleep(self._poll_interval)
                context = self._contexts.get(task_id)
                if context is None:
                    return
                elapsed = time.monotonic() - context.started_monotonic
                if elapsed > self._poll_timeout:
                    self._record_trace(task_id, "timeout", elapsed=elapsed)
                    await self._apply_submission(
                        task_id,
                        JimengSubmissionResult(
                            history_id=context.history_id,
                            status=TaskStatus.FAILED,
                            result_urls=[],
                            error_code="timeout",
                            error_message="轮询超时，已终止任务",
                        ),
                    )
                    return
                try:
                    submission = await self._client.fetch_history(context.history_id)
                except JimengApiError as exc:
                    logger.warning("轮询任务 %s 失败：%s", task_id, exc)
                    submission = JimengSubmissionResult(
                        history_id=context.history_id,
                        status=TaskStatus.FAILED,
                        result_urls=[],
                        error_code=exc.code or "poll_error",
                        error_message=str(exc),
                        raw=exc.payload,
                    )
                updated = await self._apply_submission(task_id, submission)
                self._record_trace(task_id, "poll", state=self._status_value(submission.status))
                if submission.status in {TaskStatus.SUCCEEDED, TaskStatus.FAILED}:
                    event = "completed" if submission.status == TaskStatus.SUCCEEDED else "failed"
                    self._record_trace(task_id, event, error=submission.error_code)
                    return
        except asyncio.CancelledError:
            self._record_trace(task_id, "poll_cancelled")
            raise
        finally:
            self._contexts.pop(task_id, None)
            self._pollers.pop(task_id, None)

    def _on_poller_done(self, task: asyncio.Task[Any]) -> None:
        try:
            task.result()
        except asyncio.CancelledError:
            pass
        except Exception as exc:  # pragma: no cover - 仅记录日志
            logger.exception("轮询任务抛出未捕获异常：%s", exc)

    def _schedule_asset_persist(self, task: GenerationTaskInfo) -> None:
        if self._project_storage is None:
            return
        if self._status_value(task.status) != TaskStatus.SUCCEEDED.value:
            return
        project_id = str(task.metadata.get("projectId") or "").strip()
        if not project_id:
            return
        if not task.result_uris:
            return
        if task.task_id in self._asset_tasks:
            return
        asset_task = asyncio.create_task(
            self._download_and_store_assets(task, project_id),
            name=f"jimeng-assets-{task.task_id}",
        )
        self._asset_tasks[task.task_id] = asset_task

        def _cleanup(fut: asyncio.Task[Any], task_id: str = task.task_id) -> None:
            self._asset_tasks.pop(task_id, None)
            with contextlib.suppress(asyncio.CancelledError, Exception):
                fut.result()

        asset_task.add_done_callback(_cleanup)

    async def _download_and_store_assets(self, task: GenerationTaskInfo, project_id: str) -> None:
        storage = self._project_storage
        if storage is None:
            return
        try:
            payload = storage.load_project(project_id)
        except FileNotFoundError:
            logger.warning("项目 %s 不存在，无法保存生成结果", project_id)
            return

        images_dir = storage.root / project_id / "assets" / "images"
        images_dir.mkdir(parents=True, exist_ok=True)

        assets_map: Dict[str, AssetPayload] = {asset.id: asset for asset in payload.assets}
        history_map: Dict[str, GenerationRecord] = {record.id: record for record in payload.history}
        history_result_uris: List[str] = []
        local_uris: List[str] = []
        now_ms = int(time.time() * 1000)

        for index, url in enumerate(task.result_uris):
            asset_id = f"{task.task_id}-{index + 1}"
            file_name = f"{asset_id}.png"
            relative_path = Path("assets") / "images" / file_name
            target_path = images_dir / file_name
            downloaded = False
            relative_uri = url

            if url.startswith("http"):
                try:
                    content = await self._client.fetch_resource(url)
                except JimengApiError as exc:
                    logger.warning("下载任务 %s 结果失败：%s", task.task_id, exc)
                else:
                    target_path.write_bytes(content)
                    relative_uri = str(relative_path)
                    downloaded = True
                    local_uris.append(relative_uri)
            history_result_uris.append(relative_uri)

            metadata = {
                "taskId": task.task_id,
                "index": index,
                "source": "jimeng",
                "sourceUri": url,
                "downloaded": downloaded,
            }

            if asset_id in assets_map:
                existing = assets_map[asset_id]
                asset = existing.model_copy(
                    update={
                        "uri": relative_uri,
                        "metadata": metadata,
                        "updated_at": now_ms,
                    }
                )
            else:
                asset = AssetPayload(
                    id=asset_id,
                    project_id=project_id,
                    kind="image",
                    uri=relative_uri,
                    metadata=metadata,
                    created_at=now_ms,
                    updated_at=now_ms,
                )
            assets_map[asset_id] = asset

        history_record = GenerationRecord(
            id=task.task_id,
            prompt=task.prompt,
            session_id=str(task.metadata.get("account")),
            status=self._status_value(task.status),
            result_uris=history_result_uris,
            error=task.error_code,
            created_at=task.created_at,
            completed_at=task.updated_at,
        )
        history_map[task.task_id] = history_record

        updated_payload = ProjectPayload(
            manifest=payload.manifest,
            canvas=payload.canvas,
            assets=list(assets_map.values()),
            history=list(history_map.values()),
        )
        storage.save_project(updated_payload)

        if local_uris:
            async with self._lock:
                current = self._tasks.get(task.task_id)
                if current is not None:
                    metadata = dict(current.metadata)
                    metadata["localUris"] = local_uris
                    updated_task = current.model_copy(
                        update={
                            "metadata": metadata,
                            "result_uris": history_result_uris,
                            "updated_at": int(time.time() * 1000),
                        }
                    )
                    self._tasks[task.task_id] = updated_task
                    task = updated_task
        self._record_trace(task.task_id, "assets_persisted", local=len(local_uris))

    def _record_trace(self, task_id: str, event: str, **payload: Any) -> None:
        trace = self._traces.setdefault(task_id, [])
        trace.append(
            {
                "event": event,
                "timestamp": int(time.time() * 1000),
                **payload,
            }
        )

    @staticmethod
    def _status_value(status: TaskStatus | str) -> str:
        return status.value if isinstance(status, TaskStatus) else str(status)


def uuid4_hex() -> str:
    return uuid.uuid4().hex
