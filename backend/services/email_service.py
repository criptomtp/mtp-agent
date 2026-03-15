import os
import logging
import resend
from backend.services.api_keys import get_decrypted_key

logger = logging.getLogger(__name__)


def send_email(
    to: str,
    subject: str,
    text: str = None,
    html: str = None,
    from_name: str = "MTP Fulfillment",
    from_email: str = "info@fulfillmentmtp.com.ua",
) -> dict:
    """Send email via Resend API."""
    db_key = None
    try:
        db_key = get_decrypted_key("resend")
        logger.info(f"[Email] DB key: {'found' if db_key else 'None'}")
    except Exception as e:
        logger.warning(f"[Email] DB key error: {e}")

    env_key = os.getenv("RESEND_API_KEY")
    logger.info(f"[Email] ENV RESEND_API_KEY: {'found len=' + str(len(env_key)) if env_key else 'None'}")

    env_key2 = os.getenv("RESEND_KEY") or os.getenv("RESEND")
    logger.info(f"[Email] ENV alternatives: {'found' if env_key2 else 'None'}")

    api_key = db_key or env_key or env_key2
    if not api_key:
        logger.error("[Email] NO API KEY - checked DB, RESEND_API_KEY, RESEND_KEY, RESEND")
        return {"ok": False, "error": "No Resend API key"}

    resend.api_key = api_key

    try:
        params: resend.Emails.SendParams = {
            "from": f"{from_name} <{from_email}>",
            "to": [to],
            "subject": subject,
        }
        if html:
            params["html"] = html
        elif text:
            html_body = text.replace("\n", "<br>")
            params["html"] = f"<div style='font-family:Arial,sans-serif;font-size:14px;line-height:1.6'>{html_body}</div>"

        result = resend.Emails.send(params)
        logger.info(f"[Email] Sent to {to}, id={result.get('id')}")
        return {"ok": True, "id": result.get("id")}
    except Exception as e:
        logger.error(f"[Email] Failed to {to}: {e}")
        return {"ok": False, "error": str(e)}
