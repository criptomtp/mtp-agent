import logging
import os
import re
import sys
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from backend.services.api_keys import get_api_keys, get_decrypted_key, save_api_key, test_api_key
from backend.services.database import get_supabase
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


# --- Business types & niches ---


@router.get("/business-types")
def get_business_types():
    db = get_supabase()
    result = db.table("business_types").select("*").order("name").execute()
    return result.data


@router.get("/niches/{business_type_slug}")
def get_niches(business_type_slug: str):
    db = get_supabase()
    bt = db.table("business_types").select("id").eq("slug", business_type_slug).single().execute()
    if not bt.data:
        return []
    niches = (
        db.table("niches")
        .select("*")
        .eq("business_type_id", bt.data["id"])
        .eq("is_active", True)
        .order("sort_order")
        .execute()
    )
    return niches.data


@router.get("/user")
def get_user_settings():
    db = get_supabase()
    result = db.table("user_settings").select("*").limit(1).execute()
    if result.data:
        return result.data[0]
    return {
        "business_type_id": None,
        "selected_niches": [],
        "ai_model": "gemini-2.0-flash",
        "email_tone": "friendly",
        "language": "uk",
    }


@router.post("/user")
def save_user_settings(settings_data: dict):
    db = get_supabase()
    # Remove read-only fields
    for key in ["id", "created_at", "updated_at"]:
        settings_data.pop(key, None)
    existing = db.table("user_settings").select("id").limit(1).execute()
    if existing.data:
        db.table("user_settings").update(settings_data).eq("id", existing.data[0]["id"]).execute()
    else:
        db.table("user_settings").insert(settings_data).execute()
    return {"ok": True}


# --- AI niche suggestions ---


@router.post("/suggest-niches")
def suggest_niches(body: dict):
    business = body.get("business", "").strip()
    if not business:
        return {"keywords": []}

    import json

    # Same key loading as pipeline.py line 74-76
    api_key = get_decrypted_key("gemini") or os.getenv("GEMINI_API_KEY")
    logger.info(f"[suggest-niches] key from DB: {bool(get_decrypted_key('gemini'))}, from env: {bool(os.getenv('GEMINI_API_KEY'))}")
    if not api_key:
        logger.error("[suggest-niches] No Gemini API key found in DB or env")
        return {"keywords": [], "error": "no api key"}

    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
    except Exception as e:
        logger.error(f"[suggest-niches] Failed to import/configure genai: {e}")
        return {"keywords": [], "error": str(e)}

    prompt = f"""Ти — B2B маркетолог в Україні.

Мій бізнес: {business}

Твоя задача: визначити ХТО є потенційними B2B клієнтами цього бізнесу, і дати 12 пошукових запитів для Google щоб знайти цих клієнтів в Україні.

Приклади логіки:
- Фулфілмент → клієнти: інтернет-магазини, e-commerce бренди, продавці Rozetka/Prom.ua → запити: "інтернет-магазин косметика", "продавець одягу онлайн", "e-commerce brand Ukraine"
- Юрист → клієнти: стартапи, IT компанії, ФОП → запити: "IT стартап Україна", "відкрити ФОП", "tech company Ukraine"
- Підбір персоналу → клієнти: склади, супермаркети, виробництва → запити: "склад логістика вакансії", "виробниче підприємство Україна"

Відповідай ТІЛЬКИ JSON масивом пошукових запитів. Без пояснень, без markdown.
Запити мають бути для пошуку КЛІЄНТІВ, а не для опису мого бізнесу.
["запит 1", "запит 2", ...]"""

    for model_name in ["gemini-1.5-flash", "gemini-2.0-flash", "gemini-2.5-flash"]:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            text = response.text.strip()
            match = re.search(r'\[.*?\]', text, re.DOTALL)
            if match:
                keywords = json.loads(match.group(0))
                logger.info(f"[suggest-niches] success with {model_name}, got {len(keywords)} keywords")
                return {"keywords": [k for k in keywords if isinstance(k, str)][:12]}
        except Exception as e:
            logger.warning(f"[suggest-niches] {model_name} failed: {str(e)[:100]}")
            continue

    return {"keywords": [], "error": "all models failed"}


# --- Migration helpers ---


@router.get("/migration-sql")
def get_migration_sql():
    """Returns SQL to run in Supabase Dashboard."""
    import os as _os
    sql_path = _os.path.join(_os.path.dirname(__file__), "..", "migrations", "001_business_types.sql")
    with open(sql_path, "r", encoding="utf-8") as f:
        sql = f.read()
    return {"sql": sql}


@router.post("/run-migration")
def run_migration():
    """Seed business_types and niches after tables are created via SQL Editor."""
    db = get_supabase()

    # Check if already seeded
    try:
        existing = db.table("business_types").select("id").limit(1).execute()
        if existing.data:
            return {"status": "already_exists", "message": "Tables already seeded"}
    except Exception:
        return {"status": "error", "message": "Tables not created yet. Run migration SQL in Supabase Dashboard first."}

    try:
        # Seed business types
        db.table("business_types").upsert([
            {"name": "Фулфілмент", "slug": "fulfillment", "icon": "📦"},
            {"name": "Юридичні послуги", "slug": "legal", "icon": "⚖️"},
            {"name": "Медична клініка", "slug": "medical", "icon": "🏥"},
            {"name": "IT компанія", "slug": "it", "icon": "💻"},
            {"name": "Маркетингове агентство", "slug": "marketing", "icon": "📣"},
        ], on_conflict="slug").execute()

        # Get fulfillment id
        bt = db.table("business_types").select("id").eq("slug", "fulfillment").single().execute()
        bt_id = bt.data["id"]

        # Seed niches
        niches = [
            {"business_type_id": bt_id, "name": "Косметика та краса", "slug": "cosmetics", "icon": "💄", "search_queries": ["косметика інтернет-магазин", "beauty shop Ukraine"], "sort_order": 1},
            {"business_type_id": bt_id, "name": "Дитячі іграшки", "slug": "toys", "icon": "🧸", "search_queries": ["іграшки дитячі", "toys shop Ukraine"], "sort_order": 2},
            {"business_type_id": bt_id, "name": "Одяг та взуття", "slug": "fashion", "icon": "👗", "search_queries": ["одяг інтернет-магазин", "fashion Ukraine"], "sort_order": 3},
            {"business_type_id": bt_id, "name": "Електроніка", "slug": "electronics", "icon": "📱", "search_queries": ["електроніка інтернет-магазин", "electronics Ukraine"], "sort_order": 4},
            {"business_type_id": bt_id, "name": "Меблі та декор", "slug": "furniture", "icon": "🛋️", "search_queries": ["меблі онлайн", "furniture Ukraine"], "sort_order": 5},
            {"business_type_id": bt_id, "name": "Спорт та туризм", "slug": "sports", "icon": "⚽", "search_queries": ["спортивні товари", "sports Ukraine"], "sort_order": 6},
            {"business_type_id": bt_id, "name": "Зоотовари", "slug": "pets", "icon": "🐾", "search_queries": ["зоотовари", "pet shop Ukraine"], "sort_order": 7},
            {"business_type_id": bt_id, "name": "Їжа та напої", "slug": "food", "icon": "🍕", "search_queries": ["їжа доставка", "food Ukraine"], "sort_order": 8},
            {"business_type_id": bt_id, "name": "Ювелірні прикраси", "slug": "jewelry", "icon": "💍", "search_queries": ["ювелірні прикраси", "jewelry Ukraine"], "sort_order": 9},
            {"business_type_id": bt_id, "name": "Товари для дому", "slug": "home", "icon": "🏠", "search_queries": ["товари для дому", "home goods Ukraine"], "sort_order": 10},
        ]
        for niche in niches:
            try:
                db.table("niches").insert(niche).execute()
            except Exception:
                pass  # skip duplicates

        return {"status": "ok", "message": f"Seeded {len(niches)} niches for fulfillment"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
