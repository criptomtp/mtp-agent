import csv
import io
import os

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse, FileResponse

from backend.services.database import get_supabase

router = APIRouter(prefix="/api/runs", tags=["runs"])


@router.get("/")
def list_runs(limit: int = Query(50, le=200), offset: int = Query(0)):
    db = get_supabase()
    result = (
        db.table("runs")
        .select("*")
        .order("started_at", desc=True)
        .range(offset, offset + limit - 1)
        .execute()
    )
    return result.data


@router.get("/{run_id}")
def get_run(run_id: str):
    db = get_supabase()
    run = db.table("runs").select("*").eq("id", run_id).single().execute()
    leads = (
        db.table("leads")
        .select("*")
        .eq("run_id", run_id)
        .order("created_at")
        .execute()
    )
    return {**run.data, "leads": leads.data}


@router.get("/{run_id}/csv")
def download_csv(run_id: str):
    db = get_supabase()
    leads = db.table("leads").select("*").eq("run_id", run_id).execute()

    output = io.StringIO()
    if leads.data:
        writer = csv.DictWriter(output, fieldnames=leads.data[0].keys())
        writer.writeheader()
        writer.writerows(leads.data)

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=run_{run_id}.csv"},
    )


@router.get("/files/{file_path:path}")
def download_file(file_path: str):
    full_path = os.path.join(os.path.dirname(__file__), "..", "..", file_path)
    full_path = os.path.realpath(full_path)
    # Ensure path is within the project
    project_root = os.path.realpath(os.path.join(os.path.dirname(__file__), "..", ".."))
    if not full_path.startswith(project_root):
        return {"error": "Invalid path"}
    if not os.path.exists(full_path):
        return {"error": "File not found"}
    return FileResponse(full_path)
