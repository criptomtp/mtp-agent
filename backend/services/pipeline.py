import asyncio
import json
import logging
import os
import re
import sys
from datetime import datetime, timezone

from backend.services.database import get_supabase, get_tariffs, upload_to_storage
from backend.services.api_keys import get_decrypted_key
from backend.ws.logs import log_manager

logger = logging.getLogger(__name__)

# Add project root to path so we can import agents
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


async def _log(run_id: str, message: str):
    logger.info(f"[run:{run_id}] {message}")
    line = json.dumps({"run_id": run_id, "ts": datetime.now(timezone.utc).isoformat(), "msg": message})
    await log_manager.broadcast(line)


async def _agent_progress(run_id: str, agent: int, name: str, status: str, detail: str = ""):
    """Broadcast structured agent progress event."""
    event = json.dumps({
        "run_id": run_id,
        "type": "agent_progress",
        "agent": agent,
        "name": name,
        "status": status,
        "detail": detail,
    })
    await log_manager.broadcast(event)


async def run_pipeline(niche: str, count: int) -> dict:
    db = get_supabase()

    run = (
        db.table("runs")
        .insert(
            {
                "niche": niche,
                "leads_count": count,
                "status": "running",
                "started_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        .execute()
    )
    run_id = run.data[0]["id"]

    try:
        await _log(run_id, f"Starting pipeline: {count} leads for '{niche}'")

        # Load API keys from DB (fall back to env vars in agents)
        api_keys = {}
        for key_name in ["GEMINI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_MAPS_API_KEY", "GOOGLE_CUSTOM_SEARCH_API_KEY", "SERPER_API_KEY"]:
            service = key_name.replace("_API_KEY", "").lower()
            val = get_decrypted_key(service)
            if not val:
                val = os.getenv(key_name)
            if val:
                api_keys[key_name] = val
                await _log(run_id, f"Loaded {key_name}")

        # Load tariffs from DB
        tariffs = get_tariffs()
        if tariffs:
            await _log(run_id, f"Loaded {len(tariffs)} tariffs from DB")
        else:
            await _log(run_id, "Using hardcoded tariffs (none in DB)")

        from agents.orchestrator import Orchestrator

        orchestrator = Orchestrator(send_email=False, api_keys=api_keys, tariffs=tariffs)

        # 1. Research
        await _agent_progress(run_id, 1, "Research", "running", "Пошук лідів...")
        await _log(run_id, "🔍 Researching leads...")
        leads = orchestrator.research.search(count, niche=niche)
        await _agent_progress(run_id, 1, "Research", "done", f"Знайдено {len(leads)} лідів")
        await _log(run_id, f"Found {len(leads)} leads")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        results_dir = os.path.join(
            os.path.dirname(__file__), "..", "..", "results", f"run_{timestamp}"
        )
        os.makedirs(results_dir, exist_ok=True)

        from agents.style_agent import StyleAgent
        style_agent = StyleAgent()

        for i, lead in enumerate(leads):
            lead_name = lead.name
            progress = f"[{i+1}/{len(leads)}]"

            # 1.5. Style extraction (tries Google if no website)
            brand_style = {}
            try:
                await _log(run_id, f"{progress} 🎨 Extracting brand style: {lead.website or lead_name}")
                brand_style = style_agent.extract(lead.website, lead_name=lead_name)
                primary = brand_style.get("primary_color", "")
                await _log(run_id, f"{progress} StyleAgent: website={lead.website}, primary={primary}, font={brand_style.get('font_family', '')}")
                if primary == "#1A365D":
                    await _log(run_id, f"{progress} ⚠️ WARNING: using default colors for {lead_name}, no website found")
            except Exception as e:
                logger.warning(f"StyleAgent failed for {lead_name}: {e}")

            # 2. Analysis
            await _agent_progress(run_id, 2, "Analysis", "running", f"{progress} Аналіз: {lead_name}")
            await _log(run_id, f"{progress} 🧠 Analyzing: {lead_name}")
            analysis = orchestrator.analysis.analyze(lead, tariffs=tariffs, niche=niche)
            score = analysis.get("score", 0) if isinstance(analysis, dict) else 0
            grade = analysis.get("grade", "?") if isinstance(analysis, dict) else "?"
            await _agent_progress(run_id, 2, "Analysis", "done", f"{progress} {lead_name}: {grade} ({score}/10)")
            await _log(run_id, f"{progress} Analysis done: {lead_name} — {grade} ({score}/10)")

            # 3. Content
            await _agent_progress(run_id, 3, "Content", "running", f"{progress} Генерація КП: {lead_name}")
            await _log(run_id, f"{progress} ✍️ Generating content: {lead_name}")
            safe_name = re.sub(r"[^\w\s-]", "", lead_name).strip().replace(" ", "_")[:50]
            lead_dir = os.path.join(results_dir, f"{i+1:02d}_{safe_name}")
            os.makedirs(lead_dir, exist_ok=True)

            files = orchestrator.content.generate(lead, analysis, lead_dir, tariffs=tariffs, brand_style=brand_style, niche=niche)
            html_path = files.get("html", "")
            email_path = files.get("email", "")
            pptx_path = files.get("pptx", "")
            web_url_detail = f" + web" if files.get("web_url") else ""
            await _agent_progress(run_id, 3, "Content", "done", f"{progress} {lead_name}: HTML + PPTX + email{web_url_detail}")

            # 4. Outreach
            await _agent_progress(run_id, 4, "Outreach", "running", f"{progress} Підготовка розсилки: {lead_name}")
            await _log(run_id, f"{progress} 📧 Processing outreach: {lead_name}")
            outreach_status = orchestrator.outreach.process(lead, lead_dir, False)
            await _agent_progress(run_id, 4, "Outreach", "done", f"{progress} {lead_name}: {outreach_status}")

            # Save lead to DB
            web_url = files.get("web_url", "")
            lead_data = {
                "run_id": run_id,
                "name": lead.name,
                "website": lead.website or "",
                "email": lead.email or "",
                "phone": lead.phone or "",
                "city": lead.city or "",
                "source": lead.source or "",
                "niche": niche,
                "status": "new",
                "analysis_json": analysis if isinstance(analysis, dict) else {},
                "outreach_status": outreach_status,
                "score": analysis.get("score", 0) if isinstance(analysis, dict) else 0,
                "score_grade": analysis.get("grade", "D") if isinstance(analysis, dict) else "D",
                "proposal_url": web_url,
                "extra_phones": getattr(lead, "extra_phones", "") or "",
                "extra_emails": getattr(lead, "extra_emails", "") or "",
                "social_media": getattr(lead, "social_media", "") or "{}",
            }
            try:
                lead_record = db.table("leads").insert(lead_data).execute()
            except Exception:
                # Columns may not exist yet — retry without optional ones
                for col in ["niche", "extra_phones", "extra_emails", "social_media"]:
                    lead_data.pop(col, None)
                lead_record = db.table("leads").insert(lead_data).execute()
            lead_id = lead_record.data[0]["id"]

            # Save file records — upload HTML to Supabase Storage, fall back to local URL
            project_root = os.path.realpath(os.path.join(os.path.dirname(__file__), "..", ".."))
            for file_type, file_path in [("html", html_path), ("email", email_path), ("pptx", pptx_path)]:
                if not file_path or not os.path.exists(file_path):
                    continue

                file_url = None
                content_text = None

                if file_type == "html":
                    # Upload HTML presentation to Supabase Storage
                    storage_path = f"{run_id}/{lead_id}/proposal.html"
                    with open(file_path, "rb") as f:
                        file_bytes = f.read()
                    await _log(run_id, f"[{i+1}/{len(leads)}] Uploading HTML ({len(file_bytes)} bytes)...")
                    storage_url = upload_to_storage("proposals", storage_path, file_bytes, content_type="text/html; charset=utf-8")
                    if storage_url:
                        file_url = storage_url
                        await _log(run_id, f"[{i+1}/{len(leads)}] HTML uploaded to storage")
                    else:
                        rel_path = os.path.relpath(os.path.realpath(file_path), project_root)
                        file_url = f"/api/runs/files/{rel_path}"
                        await _log(run_id, f"[{i+1}/{len(leads)}] HTML saved locally: {file_url}")

                elif file_type == "pptx":
                    storage_path = f"{run_id}/{lead_id}/proposal.pptx"
                    with open(file_path, "rb") as f:
                        file_bytes = f.read()
                    await _log(run_id, f"[{i+1}/{len(leads)}] Uploading PPTX ({len(file_bytes)} bytes)...")
                    storage_url = upload_to_storage("proposals", storage_path, file_bytes,
                                                    content_type="application/vnd.openxmlformats-officedocument.presentationml.presentation")
                    if storage_url:
                        file_url = storage_url
                        await _log(run_id, f"[{i+1}/{len(leads)}] PPTX uploaded to storage")
                    else:
                        rel_path = os.path.relpath(os.path.realpath(file_path), project_root)
                        file_url = f"/api/runs/files/{rel_path}"
                        await _log(run_id, f"[{i+1}/{len(leads)}] PPTX saved locally: {file_url}")

                elif file_type == "email":
                    with open(file_path, "r", encoding="utf-8") as f:
                        content_text = f.read()

                db.table("generated_files").insert(
                    {
                        "lead_id": lead_id,
                        "file_type": file_type,
                        "file_path": file_path,
                        "file_url": file_url,
                        "content_text": content_text,
                    }
                ).execute()

            await _log(run_id, f"[{i+1}/{len(leads)}] Done: {lead_name} ({outreach_status})")

        await _log(run_id, "Pipeline completed!")

        db.table("runs").update(
            {
                "status": "completed",
                "finished_at": datetime.now(timezone.utc).isoformat(),
            }
        ).eq("id", run_id).execute()

        return {"run_id": run_id, "status": "completed", "leads_found": len(leads)}

    except Exception as e:
        logger.exception(f"Pipeline failed for run {run_id}")
        await _log(run_id, f"❌ Error: {str(e)}")
        # Mark all agents as error
        for ag, name in [(1, "Research"), (2, "Analysis"), (3, "Content"), (4, "Outreach")]:
            await _agent_progress(run_id, ag, name, "error", str(e)[:100])
        db.table("runs").update(
            {
                "status": "failed",
                "finished_at": datetime.now(timezone.utc).isoformat(),
            }
        ).eq("id", run_id).execute()
        return {"run_id": run_id, "status": "failed", "error": str(e)}
