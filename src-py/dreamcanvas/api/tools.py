from fastapi import APIRouter

router = APIRouter()


@router.post("/segment_image")
async def segment_image() -> dict[str, str]:
    # TODO: 集成 rembg 抠图能力
    return {"status": "not_implemented"}


@router.post("/llm_text")
async def llm_text() -> dict[str, str]:
    # TODO: 调用 LLM 代理
    return {"status": "not_implemented"}
