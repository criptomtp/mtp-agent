import logging

from fastapi import APIRouter

from backend.services.database import get_supabase
from backend.services.email_service import send_email

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/outreach", tags=["outreach"])


def _extract_subject(email_text: str) -> tuple[str, str]:
    """Extract subject line from email body if present. Returns (subject, body)."""
    lines = email_text.strip().split("\n")
    if lines and lines[0].startswith("Тема:"):
        subject = lines[0].replace("Тема:", "").strip()
        body = "\n".join(lines[1:]).strip()
        return subject, body
    return "", email_text


def _build_email_html(lead_name: str, email_text: str, proposal_url: str) -> str:
    """Build beautiful HTML email."""
    body_html = email_text.replace("\n\n", "</p><p>").replace("\n", "<br>")

    proposal_btn = ""
    if proposal_url:
        proposal_btn = f"""
        <div style="text-align:center;margin:30px 0;">
            <a href="{proposal_url}"
               style="background:#E53E3E;color:#fff;padding:14px 32px;border-radius:8px;
                      text-decoration:none;font-weight:bold;font-size:16px;display:inline-block;">
                Переглянути комерційну пропозицію
            </a>
        </div>"""

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background:#f5f5f5;font-family:Arial,sans-serif;">
  <div style="max-width:600px;margin:0 auto;background:#fff;border-radius:8px;overflow:hidden;margin-top:20px;">
    <div style="background:#1A365D;padding:24px 32px;">
      <h1 style="color:#fff;margin:0;font-size:22px;">MTP Fulfillment</h1>
      <p style="color:#90CDF4;margin:4px 0 0;font-size:13px;">fulfillmentmtp.com.ua</p>
    </div>
    <div style="padding:32px;font-size:14px;line-height:1.6;color:#333;">
      <p>{body_html}</p>
      {proposal_btn}
    </div>
    <div style="background:#f8f8f8;padding:24px 32px;border-top:2px solid #E53E3E;">
      <p style="margin:0 0 4px;font-weight:bold;color:#1A365D;font-size:14px;">Микола | MTP Fulfillment</p>
      <table style="border-collapse:collapse;">
        <tr><td style="padding:2px 8px 2px 0;color:#666;font-size:12px;">📞</td>
            <td><a href="tel:+380501444645" style="color:#1A365D;font-size:12px;text-decoration:none;">+38 (050) 144-46-45</a></td></tr>
        <tr><td style="padding:2px 8px 2px 0;color:#666;font-size:12px;">✈️</td>
            <td><a href="https://t.me/nikolay_mtp" style="color:#1A365D;font-size:12px;text-decoration:none;">@nikolay_mtp</a></td></tr>
        <tr><td style="padding:2px 8px 2px 0;color:#666;font-size:12px;">🌐</td>
            <td><a href="https://fulfillmentmtp.com.ua" style="color:#1A365D;font-size:12px;text-decoration:none;">fulfillmentmtp.com.ua</a></td></tr>
        <tr><td style="padding:2px 8px 2px 0;color:#666;font-size:12px;">✉️</td>
            <td><a href="mailto:info@fulfillmentmtp.com.ua" style="color:#1A365D;font-size:12px;text-decoration:none;">info@fulfillmentmtp.com.ua</a></td></tr>
      </table>
    </div>
  </div>
</body>
</html>"""


def _get_email_text(data: dict) -> str:
    """Get email text from lead data or generated_files."""
    email_text = data.get("email_text") or ""
    if not email_text:
        # Fallback: try generated_files table
        try:
            db = get_supabase()
            gf = db.table("generated_files").select("content_text").eq(
                "lead_id", data["id"]).eq("file_type", "email").execute()
            if gf.data:
                email_text = gf.data[0].get("content_text", "")
        except Exception as e:
            logger.warning(f"[Outreach] Failed to fetch email from generated_files: {e}")
    return email_text


@router.post("/test-send")
def test_send_email():
    """Test email sending to verified address."""
    result = send_email(
        to="criptomtp@gmail.com",
        subject="Тест MTP Fulfillment Email System",
        html=_build_email_html(
            "Test Company",
            "Привіт!\n\nЦе тестовий лист від MTP Lead Agent.\n\nСистема розсилки працює коректно.\n\nMTP Fulfillment",
            "",
        ),
        from_name="MTP Fulfillment",
        from_email="info@fulfillmentmtp.com.ua",
    )
    return result


@router.post("/test-send/{lead_id}")
def test_send_on_own_email(lead_id: str):
    """Send email preview to criptomtp@gmail.com for testing."""
    db = get_supabase()
    lead = db.table("leads").select("*").eq("id", lead_id).single().execute()
    if not lead.data:
        return {"ok": False, "error": "Lead not found"}

    data = lead.data
    email_text = _get_email_text(data)
    if not email_text:
        email_text = (
            f"Привіт!\n\nМи — MTP Fulfillment, надаємо послуги фулфілменту "
            f"для інтернет-магазинів в Україні.\n\nПідготували для {data.get('name', '')} "
            f"персональну комерційну пропозицію.\n\nЗ повагою,\nМикола\nMTP Fulfillment"
        )

    extracted_subject, email_text = _extract_subject(email_text)
    proposal_url = data.get("proposal_url", "")
    subject = f"[ТЕСТ] {extracted_subject}" if extracted_subject else f"[ТЕСТ] Пропозиція для {data.get('name', '')}"

    html_content = _build_email_html(data.get("name", ""), email_text, proposal_url)

    return send_email(
        to="criptomtp@gmail.com",
        subject=subject,
        html=html_content,
        from_name="MTP Fulfillment",
        from_email="info@fulfillmentmtp.com.ua",
    )


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

    email_text = body.get("text") or _get_email_text(data)
    proposal_url = data.get("proposal_url", "")

    if not email_text:
        email_text = (
            f"Привіт!\n\nМи — MTP Fulfillment, надаємо послуги фулфілменту "
            f"для інтернет-магазинів.\n\nПідготували для {data.get('name', '')} "
            f"персональну комерційну пропозицію.\n\nЗ повагою,\nМикола\nMTP Fulfillment"
        )

    extracted_subject, email_text = _extract_subject(email_text)
    subject = body.get("subject") or extracted_subject or f"Пропозиція щодо фулфілменту для {data.get('name', '')}"

    html_content = _build_email_html(data.get("name", ""), email_text, proposal_url)
    result = send_email(
        to=to_email,
        subject=subject,
        html=html_content,
        from_name="MTP Fulfillment",
        from_email="info@fulfillmentmtp.com.ua",
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
