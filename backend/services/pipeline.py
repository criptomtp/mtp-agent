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
        for key_name in ["GEMINI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_MAPS_API_KEY", "GOOGLE_CUSTOM_SEARCH_API_KEY"]:
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

        # 1. Research — method is .search(count)
        await _log(run_id, "Researching leads...")
        leads = orchestrator.research.search(count)
        await _log(run_id, f"Found {len(leads)} leads")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        results_dir = os.path.join(
            os.path.dirname(__file__), "..", "..", "results", f"run_{timestamp}"
        )
        os.makedirs(results_dir, exist_ok=True)

        for i, lead in enumerate(leads):
            lead_name = lead.name
            await _log(run_id, f"[{i+1}/{len(leads)}] Analyzing: {lead_name}")

            # 2. Analysis — .analyze(lead, tariffs) returns dict
            analysis = orchestrator.analysis.analyze(lead, tariffs=tariffs)

            await _log(run_id, f"[{i+1}/{len(leads)}] Generating content: {lead_name}")
            safe_name = re.sub(r"[^\w\s-]", "", lead_name).strip().replace(" ", "_")[:50]
            lead_dir = os.path.join(results_dir, f"{i+1:02d}_{safe_name}")
            os.makedirs(lead_dir, exist_ok=True)

            # 3. Content — .generate(lead, analysis, dir, tariffs) returns {'html': path, 'email': path}
            files = orchestrator.content.generate(lead, analysis, lead_dir, tariffs=tariffs)
            html_path = files.get("html", "")
            email_path = files.get("email", "")

            # 4. Outreach — .process(lead, dir, send_email) returns status string
            await _log(run_id, f"[{i+1}/{len(leads)}] Processing outreach: {lead_name}")
            outreach_status = orchestrator.outreach.process(lead, lead_dir, False)

            # Save lead to DB
            lead_record = (
                db.table("leads")
                .insert(
                    {
                        "run_id": run_id,
                        "name": lead.name,
                        "website": lead.website or "",
                        "email": lead.email or "",
                        "phone": lead.phone or "",
                        "city": lead.city or "",
                        "source": lead.source or "",
                        "status": "new",
                        "analysis_json": analysis if isinstance(analysis, dict) else {},
                        "outreach_status": outreach_status,
                        "score": analysis.get("score", 0) if isinstance(analysis, dict) else 0,
                        "score_grade": analysis.get("grade", "D") if isinstance(analysis, dict) else "D",
                    }
                )
                .execute()
            )
            lead_id = lead_record.data[0]["id"]

            # Save file records — upload HTML to Supabase Storage, fall back to local URL
            project_root = os.path.realpath(os.path.join(os.path.dirname(__file__), "..", ".."))
            for file_type, file_path in [("html", html_path), ("email", email_path)]:
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
                    storage_url = upload_to_storage("proposals", storage_path, file_bytes, content_type="text/html")
                    if storage_url:
                        file_url = storage_url
                        await _log(run_id, f"[{i+1}/{len(leads)}] HTML uploaded to storage")
                    else:
                        rel_path = os.path.relpath(os.path.realpath(file_path), project_root)
                        file_url = f"/api/runs/files/{rel_path}"
                        await _log(run_id, f"[{i+1}/{len(leads)}] HTML saved locally: {file_url}")

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
        await _log(run_id, f"Error: {str(e)}")
        db.table("runs").update(
            {
                "status": "failed",
                "finished_at": datetime.now(timezone.utc).isoformat(),
            }
        ).eq("id", run_id).execute()
        return {"run_id": run_id, "status": "failed", "error": str(e)}
