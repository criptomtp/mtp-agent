import logging

from fastapi import APIRouter

from backend.services.database import get_supabase
from backend.services.email_service import send_email

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/outreach", tags=["outreach"])


@router.get("/preview/{lead_id}")
def preview_email(lead_id: str):
    """Get email preview for a lead."""
    db = get_supabase()
    lead = db.table("leads").select(
        "id,name,email,email_text,outreach_status,proposal_url"
    ).eq("id", lead_id).single().execute()

    if not lead.data:
        return {"ok": False, "error": "Lead not found"}

    return {"ok": True, "lead": lead.data}


@router.post("/send/{lead_id}")
def send_lead_email(lead_id: str, body: dict = {}):
    """Send email to a single lead."""
    db = get_supabase()
    lead = db.table("leads").select("*").eq("id", lead_id).single().execute()

    if not lead.data:
        return {"ok": False, "error": "Lead not found"}

    data = lead.data
    to_email = data.get("email", "").strip()
    if not to_email:
        return {"ok": False, "error": "Lead has no email"}

    # Get email text — from body override or from lead record
    email_text = body.get("text") or data.get("email_text") or ""
    proposal_url = data.get("proposal_url", "")

    # Append proposal link if available
    if proposal_url and proposal_url not in email_text:
        email_text += f"\n\n📎 Комерційна пропозиція: {proposal_url}"

    subject = body.get("subject") or f"Пропозиція щодо фулфілменту для {data.get('name', '')}"

    result = send_email(
        to=to_email,
        subject=subject,
        text=email_text,
    )

    if result["ok"]:
        db.table("leads").update({
            "outreach_status": f"sent:{to_email}",
        }).eq("id", lead_id).execute()
        logger.info(f"[Outreach] Email sent to lead {lead_id} ({to_email})")
    else:
        db.table("leads").update({
            "outreach_status": f"error:{result.get('error', 'unknown')[:50]}",
        }).eq("id", lead_id).execute()

    return result


@router.post("/send-bulk")
def send_bulk_emails(body: dict):
    """Send emails to multiple leads."""
    lead_ids = body.get("lead_ids", [])
    results = []

    for lead_id in lead_ids:
        result = send_lead_email(lead_id)
        results.append({"lead_id": lead_id, **result})

    sent = sum(1 for r in results if r.get("ok"))
    return {"ok": True, "sent": sent, "total": len(lead_ids), "results": results}
