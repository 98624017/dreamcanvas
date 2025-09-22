from fastapi import APIRouter, HTTPException

router = APIRouter()


@router.post("/tasks")
async def create_task(payload: dict) -> dict[str, str]:
    if "prompt" not in payload:
        raise HTTPException(status_code=400, detail="缺少 prompt 字段")
    # TODO: 调用即梦 API
    return {"status": "queued", "task_id": "demo-task", "prompt": payload["prompt"]}


@router.get("/history")
async def get_history(task_id: str) -> dict[str, str]:
    # TODO: 查询任务状态
    return {"task_id": task_id, "status": "pending"}
