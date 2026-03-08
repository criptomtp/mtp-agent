import logging
import os
import re
import sys
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from backend.services.api_keys import get_api_keys, get_decrypted_key, save_api_key, test_api_key
from backend.services.pipeline_settings import load_settings, save_settings, reset_prompts

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/settings", tags=["settings"])

# --- Existing API key endpoints ---


class ApiKeyIn(BaseModel):
    service_name: str
    key_value: str


class TestKeyIn(BaseModel):
    service_name: str
    key_value: str = ""


@router.get("/api-keys")
def list_keys():
    return get_api_keys()


@router.post("/api-keys")
def upsert_key(body: ApiKeyIn):
    return save_api_key(body.service_name, body.key_value)


@router.post("/api-keys/test")
def test_key(body: TestKeyIn):
    key = body.key_value
    if not key:
        logger.info(f"No key in request, reading saved key for {body.service_name}")
        key = get_decrypted_key(body.service_name)
        if not key:
            return {"valid": False, "error": "No saved key found"}
    return test_api_key(body.service_name, key)


# --- Pipeline settings endpoints ---


@router.get("")
def get_settings():
    settings = load_settings()
    # Include default prompts from the analysis agent for the frontend
    from agents.analysis_agent import _build_prompt, Lead
    dummy = Lead(name="{company_name}", city="{city}", website="{website}",
                 description="{description}", products_count=0, source="{source}")
    default_system, default_user = _build_prompt(dummy, "{tariffs}", {})
    settings["default_prompts"] = {
        "analysis_system": default_system,
        "analysis_user_template": default_user,
    }
    return settings


class SettingsUpdate(BaseModel):
    agents: Optional[dict] = None
    prompts: Optional[dict] = None


@router.post("")
def update_settings(body: SettingsUpdate):
    data = {}
    if body.agents is not None:
        data["agents"] = body.agents
    if body.prompts is not None:
        data["prompts"] = body.prompts
    return save_settings(data)


@router.post("/reset-prompts")
def reset_prompts_endpoint():
    return reset_prompts()


# --- Test lead endpoint ---


class TestLeadIn(BaseModel):
    name: str
    city: str = ""
    website: str = ""
    description: str = ""
    products_count: int = 0


@router.post("/test-lead")
def test_lead(body: TestLeadIn):
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

    from agents.research_agent import Lead
    from agents.analysis_agent import AnalysisAgent
    from agents.content_agent import ContentAgent
    from backend.services.database import get_tariffs, upload_to_storage

    # Build API keys
    api_keys = {}
    for key_name in ["GEMINI_API_KEY", "ANTHROPIC_API_KEY"]:
        service = key_name.replace("_API_KEY", "").lower()
        val = get_decrypted_key(service) or os.getenv(key_name)
        if val:
            api_keys[key_name] = val

    lead = Lead(
        name=body.name,
        city=body.city,
        website=body.website,
        description=body.description,
        products_count=body.products_count,
        source="manual_test",
    )

    tariffs = get_tariffs()
    analysis_agent = AnalysisAgent(api_keys=api_keys)
    analysis = analysis_agent.analyze(lead, tariffs=tariffs)

    # Generate content
    import tempfile
    output_dir = tempfile.mkdtemp(prefix="mtp_test_")
    content_agent = ContentAgent(api_keys=api_keys)
    files = content_agent.generate(lead, analysis, output_dir, tariffs=tariffs, niche="e-commerce")

    # Upload HTML presentation if generated
    html_url = None
    html_path = files.get("html", "")
    logger.info(f"[test-lead] HTML path: {html_path}, exists: {os.path.exists(html_path) if html_path else False}")

    if html_path and os.path.exists(html_path):
        safe_name = re.sub(r"[^\w\s-]", "", body.name).strip().replace(" ", "_")[:50]
        storage_path = f"test/{safe_name}/proposal.html"
        with open(html_path, "rb") as f:
            file_bytes = f.read()
        logger.info(f"[test-lead] Uploading HTML ({len(file_bytes)} bytes) to {storage_path}")
        html_url = upload_to_storage("proposals", storage_path, file_bytes, content_type="text/html; charset=utf-8")
        logger.info(f"[test-lead] Upload result: {html_url}")
        if not html_url:
            html_url = None

    # Upload PPTX if generated
    pptx_url = None
    pptx_path = files.get("pptx", "")
    if pptx_path and os.path.exists(pptx_path):
        storage_path = f"test/{safe_name}/proposal.pptx"
        with open(pptx_path, "rb") as f:
            file_bytes = f.read()
        logger.info(f"[test-lead] Uploading PPTX ({len(file_bytes)} bytes) to {storage_path}")
        pptx_url = upload_to_storage("proposals", storage_path, file_bytes,
                                     content_type="application/vnd.openxmlformats-officedocument.presentationml.presentation")

    # Read email text
    email_text = ""
    email_path = files.get("email", "")
    if email_path and os.path.exists(email_path):
        with open(email_path, "r", encoding="utf-8") as f:
            email_text = f.read()

    return {
        "analysis": analysis,
        "email_text": email_text,
        "html_url": html_url,
        "pptx_url": pptx_url,
        "web_url": files.get("web_url"),
        "web_proposal": files.get("web_proposal"),
    }
