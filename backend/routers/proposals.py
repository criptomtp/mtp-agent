import logging
import os
import re
import httpx
from datetime import datetime, timezone

from fastapi import APIRouter, Request, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional

from backend.services.database import get_supabase_admin

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/proposals", tags=["proposals"])

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
MTP_CABINET_API_SECRET = os.getenv("MTP_CABINET_API_SECRET", "dev-secret")


# --- Telegram notifications ---

async def notify_telegram(event_type: str, client_name: str, proposal_url: str = ""):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    messages = {
        "open": f"👁 <b>{client_name}</b> відкрив КП\n🕐 {datetime.now().strftime('%H:%M')}\n🔗 {proposal_url}",
        "engaged_30s": f"⏱ <b>{client_name}</b> читає КП вже 30 секунд",
        "scrolled_to_end": f"📜 <b>{client_name}</b> прочитав КП до кінця!",
        "calendly_click": f"📅 <b>{client_name}</b> клікнув на Zoom!",
        "zoom_booked": f"🎉 <b>{client_name}</b> ЗАБРОНЮВАВ ZOOM!\nПеревір Google Calendar 📆",
        "pdf_download": f"📥 <b>{client_name}</b> завантажив PDF",
    }
    text = messages.get(event_type, f"📌 <b>{client_name}</b>: {event_type}")
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                json={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True},
                timeout=10,
            )
    except Exception as e:
        logger.warning(f"Telegram notify failed: {e}")


# --- Create proposal ---

class CreateProposalIn(BaseModel):
    client_name: str
    client_data: dict
    pricing_data: dict = {}
    calendly_url: str = "https://calendly.com/mtpgrouppromo"


@router.post("/create")
def create_proposal(body: CreateProposalIn, authorization: Optional[str] = Header(None)):
    # Auth check
    token = (authorization or "").replace("Bearer ", "")
    if not token or token != MTP_CABINET_API_SECRET:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    slug = (
        re.sub(r"[^\w\s-]", "", body.client_name.lower())
        .strip()
        .replace(" ", "-")[:50]
        + "-"
        + format(int(datetime.now().timestamp() * 1000), "x")
    )

    db = get_supabase_admin()
    result = (
        db.table("proposals")
        .insert({
            "slug": slug,
            "client_name": body.client_name,
            "client_data": body.client_data,
            "pricing_data": body.pricing_data,
            "calendly_url": body.calendly_url,
        })
        .execute()
    )

    if not result.data:
        return JSONResponse({"error": "Failed to create proposal"}, status_code=500)

    row = result.data[0]
    base_url = os.getenv("MTP_FRONTEND_URL", "https://mtp-lead-agent.vercel.app")
    return {
        "slug": row["slug"],
        "url": f"{base_url}/proposals/{row['slug']}",
        "proposal_id": row["id"],
    }


# --- Get proposal by slug ---

@router.get("/{slug}")
def get_proposal(slug: str):
    from fastapi.responses import RedirectResponse

    db = get_supabase_admin()
    result = db.table("proposals").select("*").eq("slug", slug).execute()

    if not result.data:
        return JSONResponse({"error": "Not found"}, status_code=404)

    proposal = result.data[0]

    # If proposal has Gemini-generated HTML in Storage — redirect to it
    html_url = proposal.get("html_url") or ""
    # Also check inside client_data (used when html_url column doesn't exist)
    if not html_url:
        cd = proposal.get("client_data")
        if isinstance(cd, dict):
            html_url = cd.get("html_url", "")
    if html_url:
        return RedirectResponse(html_url, status_code=302)

    # Otherwise return JSON for React-rendered ProposalPage
    return proposal


# --- Track proposal events ---

class TrackEventIn(BaseModel):
    proposal_id: Optional[str] = None
    slug: Optional[str] = None
    event: str
    ts: Optional[str] = None


@router.post("/track")
async def track_event(body: TrackEventIn, request: Request):
    db = get_supabase_admin()
    ua = request.headers.get("user-agent", "")
    ref = request.headers.get("referer", "")

    # Resolve proposal_id from slug if needed
    proposal_id = body.proposal_id
    if not proposal_id and body.slug:
        try:
            result = db.table("proposals").select("id").eq("slug", body.slug).execute()
            if result.data:
                proposal_id = result.data[0]["id"]
        except Exception:
            pass

    if not proposal_id:
        return JSONResponse({"error": "proposal_id or slug required"}, status_code=400)

    db.table("proposal_events").insert({
        "proposal_id": proposal_id,
        "event": body.event,
        "ts": body.ts or datetime.now(timezone.utc).isoformat(),
        "ua": ua,
        "ref": ref,
    }).execute()

    # Update views on 'open' event
    if body.event == "open":
        try:
            result = db.table("proposals").select("views_count, client_name, slug").eq("id", proposal_id).execute()
            proposal = result.data[0] if result.data else None
            if proposal:
                db.table("proposals").update({
                    "views_count": (proposal.get("views_count") or 0) + 1,
                    "last_viewed_at": datetime.now(timezone.utc).isoformat(),
                }).eq("id", proposal_id).execute()

                # Notify on first view
                if (proposal.get("views_count") or 0) == 0 and proposal.get("client_name"):
                    base_url = os.getenv("MTP_FRONTEND_URL", "https://mtp-lead-agent.vercel.app")
                    await notify_telegram(
                        "open",
                        proposal["client_name"],
                        f"{base_url}/proposals/{proposal.get('slug', '')}",
                    )
        except Exception:
            pass

    # Notify on key engagement events
    if body.event in ("scrolled_to_end", "zoom_booked"):
        try:
            result = db.table("proposals").select("client_name").eq("id", proposal_id).execute()
            if result.data and result.data[0].get("client_name"):
                await notify_telegram(body.event, result.data[0]["client_name"])
        except Exception:
            pass

    return {"ok": True}
