from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from services.pipeline import run_pipeline
from utils.result_store import save_result, get_result

router = APIRouter()


class AnalyzeRequest(BaseModel):
    use_mock: bool = True


@router.post("/analyze-store")
async def analyze_store(
    request: AnalyzeRequest,
    background_tasks: BackgroundTasks
):
    try:
        result = run_pipeline(use_mock=request.use_mock)
        save_result(result["id"], result)
        return result

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "message": str(e)
            }
        )


@router.get("/result/{run_id}")
async def get_run_result(run_id: str):
    result = get_result(run_id)

    if not result:
        raise HTTPException(
            status_code=404,
            detail={
                "status": "error",
                "message": f"Result {run_id} not found"
            }
        )

    return result


@router.get("/health")
async def health():
    return {"status": "ok", "pipeline": "ready"}