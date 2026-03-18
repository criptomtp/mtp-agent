import base64
import logging
import os
import re
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Request, Header
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel
from typing import Optional

from backend.services.database import get_supabase_admin

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/proposals", tags=["proposals"])

MTP_CABINET_API_SECRET = os.getenv("MTP_CABINET_API_SECRET", "dev-secret")
MTP_BACKEND_URL = os.getenv("MTP_BACKEND_URL", "https://mtp-agent-production.up.railway.app")

# 1×1 transparent GIF — for email tracking pixel
TRANSPARENT_GIF = base64.b64decode(
    "R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"
)

# JS snippet injected into every served proposal HTML
# Tracks: 30s engagement, scroll to 85%, Calendly clicks
_TRACKING_JS_TPL = """
<script>
(function(){{
  var slug="{slug}",api="{api}";
  function tr(ev){{fetch(api+"/api/proposals/track",{{method:"POST",headers:{{"Content-Type":"application/json"}},body:JSON.stringify({{slug:slug,event:ev}})}}).catch(function(){{}});}}
  var t30=false;
  setTimeout(function(){{if(!t30){{t30=true;tr("engaged_30s");}}}},30000);
  var tEnd=false;
  window.addEventListener("scroll",function(){{
    var st=window.scrollY||document.documentElement.scrollTop;
    var dh=document.documentElement.scrollHeight-window.innerHeight;
    if(!tEnd&&dh>0&&st/dh>=0.85){{tEnd=true;tr("scrolled_to_end");}}
  }});
  document.addEventListener("click",function(e){{
    var a=e.target.closest("a");
    if(a&&a.href&&a.href.indexOf("calendly.com")>=0){{tr("calendly_click");}}
  }});
}})();
</script>
"""


def _log_open_event(proposal_id: str, ua: str, ref: str):
    """Server-side open tracking — runs in background."""
    try:
        db = get_supabase_admin()
        db.table("proposal_events").insert({
            "proposal_id": proposal_id,
            "event": "open",
            "ts": datetime.now(timezone.utc).isoformat(),
            "ua": ua,
            "ref": ref,
        }).execute()
        db.table("proposals").update({
            "views_count": db.table("proposals").select("views_count").eq("id", proposal_id).execute().data[0].get("views_count", 0) + 1,
            "last_viewed_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", proposal_id).execute()
    except Exception as e:
        logger.warning(f"_log_open_event failed: {e}")


def _inject_tracking(html: str, slug: str) -> str:
    """Inject tracking JS snippet before </body> or </html>."""
    snippet = _TRACKING_JS_TPL.format(slug=slug, api=MTP_BACKEND_URL)
    for tag in ("</body>", "</html>"):
        idx = html.lower().rfind(tag)
        if idx != -1:
            return html[:idx] + snippet + html[idx:]
    return html + snippet


# --- Create proposal ---

class CreateProposalIn(BaseModel):
    client_name: str
    client_data: dict
    pricing_data: dict = {}
    calendly_url: str = "https://calendly.com/mtpgrouppromo/30min"


@router.post("/create")
def create_proposal(body: CreateProposalIn, authorization: Optional[str] = Header(None)):
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


# --- Email tracking pixel ---

@router.get("/pixel/{slug}")
async def pixel_open(slug: str, request: Request, background_tasks: BackgroundTasks):
    """1×1 transparent GIF — logs email_open when email client loads it."""
    ua = request.headers.get("user-agent", "")
    ref = request.headers.get("referer", "")

    def _track():
        try:
            db = get_supabase_admin()
            result = db.table("proposals").select("id").eq("slug", slug).execute()
            if not result.data:
                return
            proposal_id = result.data[0]["id"]
            db.table("proposal_events").insert({
                "proposal_id": proposal_id,
                "event": "email_open",
                "ts": datetime.now(timezone.utc).isoformat(),
                "ua": ua,
                "ref": ref,
            }).execute()
        except Exception as e:
            logger.warning(f"pixel_open tracking failed: {e}")

    background_tasks.add_task(_track)
    return Response(
        content=TRANSPARENT_GIF,
        media_type="image/gif",
        headers={"Cache-Control": "no-cache, no-store, must-revalidate", "Pragma": "no-cache"},
    )


# --- Get proposal by slug ---

@router.get("/{slug}")
def get_proposal(slug: str, request: Request, background_tasks: BackgroundTasks):
    from fastapi.responses import HTMLResponse

    ua = request.headers.get("user-agent", "")
    ref = request.headers.get("referer", "")

    db = get_supabase_admin()
    result = db.table("proposals").select("*").eq("slug", slug).execute()

    if not result.data:
        return JSONResponse({"error": "Not found"}, status_code=404)

    proposal = result.data[0]

    # Server-side open tracking (background — does not slow page load)
    background_tasks.add_task(_log_open_event, proposal["id"], ua, ref)

    html_content = proposal.get("html_content") or ""
    if not html_content:
        cd = proposal.get("client_data")
        if isinstance(cd, dict):
            html_content = cd.get("html_content", "")

    if html_content:
        tracked_html = _inject_tracking(html_content, slug)
        return HTMLResponse(content=tracked_html, status_code=200)

    return proposal


# --- Track proposal events (called by injected JS) ---

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

    return {"ok": True}
