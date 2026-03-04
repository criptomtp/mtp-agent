import asyncio
import json
import os
import sys
from datetime import datetime, timezone

from backend.services.database import get_supabase
from backend.ws.logs import log_manager

# Add project root to path so we can import agents
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


async def _log(run_id: str, message: str):
    line = json.dumps({"run_id": run_id, "ts": datetime.now(timezone.utc).isoformat(), "msg": message})
    await log_manager.broadcast(line)


async def run_pipeline(niche: str, count: int) -> dict:
    db = get_supabase()

    # Create run record
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

        from agents.orchestrator import Orchestrator

        orchestrator = Orchestrator(send_email=False)

        await _log(run_id, "Researching leads...")
        leads = orchestrator.research.search_leads(count)
        await _log(run_id, f"Found {len(leads)} leads")

        results_dir = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "results",
            f"run_{datetime.now().strftime('%Y%m%d_%H%M')}",
        )
        os.makedirs(results_dir, exist_ok=True)

        for i, lead in enumerate(leads):
            lead_name = lead.name
            await _log(run_id, f"[{i+1}/{len(leads)}] Analyzing: {lead_name}")

            analysis = orchestrator.analysis.analyze(lead)

            await _log(run_id, f"[{i+1}/{len(leads)}] Generating content: {lead_name}")
            safe_name = "".join(c if c.isalnum() or c in " -_" else "" for c in lead_name)[:50]
            lead_dir = os.path.join(results_dir, f"{i+1:02d}_{safe_name}")
            os.makedirs(lead_dir, exist_ok=True)

            pdf_path, email_path = orchestrator.content.generate(lead, analysis, lead_dir)

            await _log(run_id, f"[{i+1}/{len(leads)}] Saving: {lead_name}")
            contact_path = orchestrator.outreach.process(lead, email_path, lead_dir)

            # Save lead to DB
            lead_record = (
                db.table("leads")
                .insert(
                    {
                        "run_id": run_id,
                        "name": lead.name,
                        "website": getattr(lead, "website", ""),
                        "email": getattr(lead, "email", ""),
                        "phone": getattr(lead, "phone", ""),
                        "city": getattr(lead, "city", ""),
                        "source": getattr(lead, "source", ""),
                        "status": "new",
                        "analysis_json": analysis if isinstance(analysis, dict) else {},
                    }
                )
                .execute()
            )
            lead_id = lead_record.data[0]["id"]

            # Save generated files
            for file_type, file_path in [("pdf", pdf_path), ("email", email_path), ("contact", contact_path)]:
                if file_path and os.path.exists(file_path):
                    db.table("generated_files").insert(
                        {
                            "lead_id": lead_id,
                            "file_type": file_type,
                            "file_path": file_path,
                        }
                    ).execute()

        await _log(run_id, "Pipeline completed!")

        db.table("runs").update(
            {
                "status": "completed",
                "finished_at": datetime.now(timezone.utc).isoformat(),
            }
        ).eq("id", run_id).execute()

        return {"run_id": run_id, "status": "completed", "leads_found": len(leads)}

    except Exception as e:
        await _log(run_id, f"Error: {str(e)}")
        db.table("runs").update(
            {
                "status": "failed",
                "finished_at": datetime.now(timezone.utc).isoformat(),
            }
        ).eq("id", run_id).execute()
        return {"run_id": run_id, "status": "failed", "error": str(e)}
