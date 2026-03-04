from fastapi import APIRouter, Query

from backend.services.database import get_supabase

router = APIRouter(prefix="/api/leads", tags=["leads"])


@router.get("/")
def list_leads(
    status: str | None = Query(None),
    run_id: str | None = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
):
    db = get_supabase()
    query = db.table("leads").select("*").order("created_at", desc=True)
    if status:
        query = query.eq("status", status)
    if run_id:
        query = query.eq("run_id", run_id)
    result = query.range(offset, offset + limit - 1).execute()
    return result.data


@router.get("/{lead_id}")
def get_lead(lead_id: str):
    db = get_supabase()
    lead = db.table("leads").select("*").eq("id", lead_id).single().execute()
    files = (
        db.table("generated_files")
        .select("*")
        .eq("lead_id", lead_id)
        .execute()
    )
    return {**lead.data, "files": files.data}


@router.get("/{lead_id}/files")
def get_lead_files(lead_id: str):
    """Return generated files for a lead, including storage URLs and email text."""
    db = get_supabase()
    result = (
        db.table("generated_files")
        .select("*")
        .eq("lead_id", lead_id)
        .order("created_at", desc=True)
        .execute()
    )
    return result.data
