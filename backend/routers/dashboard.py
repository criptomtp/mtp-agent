import asyncio

from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel

from backend.services.database import get_supabase
from backend.services.pipeline import run_pipeline

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


class RunAgentsIn(BaseModel):
    niche: str = "cosmetics"
    count: int = 5


@router.get("/stats")
def get_stats():
    db = get_supabase()
    runs = db.table("runs").select("id", count="exact").execute()
    leads = db.table("leads").select("id", count="exact").execute()
    active_runs = (
        db.table("runs")
        .select("id", count="exact")
        .eq("status", "running")
        .execute()
    )
    return {
        "total_runs": runs.count or 0,
        "total_leads": leads.count or 0,
        "active_runs": active_runs.count or 0,
    }


@router.post("/run")
async def start_run(body: RunAgentsIn, background_tasks: BackgroundTasks):
    background_tasks.add_task(asyncio.run, run_pipeline(body.niche, body.count))
    return {"status": "started", "niche": body.niche, "count": body.count}
