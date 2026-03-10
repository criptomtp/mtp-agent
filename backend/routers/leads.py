import logging
import re

from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from pydantic import BaseModel

from backend.services.database import get_supabase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/leads", tags=["leads"])


class StatusUpdate(BaseModel):
    outreach_status: str


class LeadCreate(BaseModel):
    name: str
    city: str = ""
    website: str = ""
    email: str = ""
    phone: str = ""
    source: str = ""
    status: str = "new"
    analysis_json: dict = {}
    score: int = 0
    score_grade: str = "D"


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


@router.post("/")
def create_lead(body: LeadCreate):
    db = get_supabase()
    result = db.table("leads").insert(body.model_dump()).execute()
    return result.data[0] if result.data else {"error": "failed to create"}


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


@router.patch("/{lead_id}/status")
def update_lead_status(lead_id: str, body: StatusUpdate):
    db = get_supabase()
    result = (
        db.table("leads")
        .update({"outreach_status": body.outreach_status})
        .eq("id", lead_id)
        .execute()
    )
    return result.data[0] if result.data else {"error": "not found"}


@router.get("/{lead_id}/proposal", response_class=HTMLResponse)
async def get_lead_proposal(lead_id: str):
    try:
        sb = get_supabase()

        lead = sb.table("leads").select("*").eq("id", lead_id).single().execute()
        if not lead.data:
            return HTMLResponse("<h1>Лід не знайдений</h1>", status_code=404)

        lead_data = lead.data

        # Redirect to web proposal if available
        proposal_url = lead_data.get("proposal_url", "")
        if proposal_url:
            return RedirectResponse(url=proposal_url, status_code=302)

        safe_name = re.sub(r"[^\w\s-]", "", lead_data.get("name", "")).strip().replace(" ", "_")[:50]
        run_id = lead_data.get("run_id", "test")

        # Also check generated_files table for the stored file_url
        files = sb.table("generated_files").select("file_url").eq("lead_id", lead_id).in_("file_type", ["html", "pdf"]).execute()
        storage_paths = [f"{run_id}/{lead_id}/proposal.html", f"test/{safe_name}/proposal.html"]

        html_content = None
        for path in storage_paths:
            try:
                response = sb.storage.from_("proposals").download(path)
                if response:
                    html_content = response.decode("utf-8")
                    break
            except Exception:
                continue

        if not html_content:
            return HTMLResponse("<h1>Презентація не знайдена</h1>", status_code=404)

        return HTMLResponse(content=html_content, status_code=200)

    except Exception as e:
        logger.error(f"Proposal fetch error: {e}")
        return HTMLResponse(f"<h1>Помилка: {e}</h1>", status_code=500)


@router.get("/{lead_id}/proposal.pptx")
async def get_lead_pptx(lead_id: str):
    try:
        sb = get_supabase()
        lead = sb.table("leads").select("*").eq("id", lead_id).single().execute()
        if not lead.data:
            return Response("Not found", status_code=404)

        lead_data = lead.data
        safe_name = re.sub(r"[^\w\s-]", "", lead_data.get("name", "")).strip().replace(" ", "_")[:50]
        run_id = lead_data.get("run_id", "test")

        # Check generated_files for a direct storage URL first
        pptx_files = sb.table("generated_files").select("file_url").eq("lead_id", lead_id).eq("file_type", "pptx").execute()
        if pptx_files.data:
            file_url = pptx_files.data[0].get("file_url")
            if file_url:
                return RedirectResponse(url=file_url, status_code=302)

        # Fallback: try to download from storage directly
        for path in [f"{run_id}/{lead_id}/proposal.pptx", f"test/{safe_name}/proposal.pptx"]:
            try:
                response = sb.storage.from_("proposals").download(path)
                if response:
                    return Response(
                        content=response,
                        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                        headers={"Content-Disposition": f'attachment; filename="proposal_{safe_name}.pptx"'},
                    )
            except Exception:
                continue

        return Response("PPTX not found", status_code=404)
    except Exception as e:
        logger.error(f"PPTX fetch error: {e}")
        return Response(f"Error: {e}", status_code=500)


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
