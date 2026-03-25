import asyncio
import gc
import json
import logging
import os
import re
import sys
from datetime import datetime, timezone

from backend.services.database import get_supabase, get_tariffs, upload_to_storage
from backend.services.api_keys import get_decrypted_key
from backend.services.pipeline_settings import load_settings as load_pipeline_settings
from backend.ws.logs import log_manager

logger = logging.getLogger(__name__)

# Add project root to path so we can import agents
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


def _is_neutral_color(hex_color: str) -> bool:
    """Check if color is too neutral/grey to be a brand color."""
    try:
        h = hex_color.lstrip('#')
        if len(h) == 3:
            h = ''.join(c * 2 for c in h)
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        diff = max(r, g, b) - min(r, g, b)
        brightness = (r * 299 + g * 587 + b * 114) / 1000
        return diff < 30 and 80 < brightness < 200
    except Exception:
        return False


async def _log(run_id: str, message: str):
    logger.info(f"[run:{run_id}] {message}")
    line = json.dumps({"run_id": run_id, "ts": datetime.now(timezone.utc).isoformat(), "msg": message})
    await log_manager.broadcast(line)


def _get_excluded_domains() -> set:
    """Load excluded domains from DB."""
    try:
        db = get_supabase()
        r = db.table("excluded_domains").select("domain").execute()
        return {row["domain"] for row in r.data}
    except Exception:
        return set()


def _extract_domain(url: str) -> str:
    """Extract clean domain from URL."""
    domain = re.sub(r'^https?://', '', url or '')
    domain = re.sub(r'^www\.', '', domain)
    return domain.split('/')[0].lower()


def _get_calendly_url() -> str:
    """Load calendly_url from user_settings, fall back to default."""
    try:
        db = get_supabase()
        r = db.table("user_settings").select("calendly_url").limit(1).execute()
        if r.data and r.data[0].get("calendly_url"):
            return r.data[0]["calendly_url"]
    except Exception:
        pass
    return "https://calendly.com/mtpgrouppromo/30min"


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

        # Load pipeline settings (outreach toggle)
        pipeline_cfg = load_pipeline_settings()
        auto_send_email = pipeline_cfg.get("agents", {}).get("outreach", {}).get("enabled", False)
        await _log(run_id, f"Auto email send: {'ON' if auto_send_email else 'OFF'}")

        # Load calendly URL from user settings
        calendly_url = _get_calendly_url()
        await _log(run_id, f"Calendly URL: {calendly_url}")

        from agents.orchestrator import Orchestrator

        orchestrator = Orchestrator(send_email=False, api_keys=api_keys, tariffs=tariffs)

        # 1. Research
        await _agent_progress(run_id, 1, "Research", "running", "Пошук лідів...")
        await _log(run_id, "🔍 Researching leads...")

        excluded = _get_excluded_domains()
        if excluded:
            await _log(run_id, f"Loaded {len(excluded)} excluded domains")

        raw_leads = orchestrator.research.search(count * 2, niche=niche)
        await _log(run_id, f"Found {len(raw_leads)} raw leads")

        # Filter: must have email, not excluded
        leads = []
        skipped_no_email = 0
        skipped_excluded = 0
        seen_domains = set()
        for lead in raw_leads:
            domain = _extract_domain(lead.website)
            if not (lead.email or "").strip():
                skipped_no_email += 1
                continue
            if domain and domain in excluded:
                skipped_excluded += 1
                await _log(run_id, f"⏭️ Skipping excluded: {lead.name} ({domain})")
                continue
            if domain and domain in seen_domains:
                continue
            if domain:
                seen_domains.add(domain)
            leads.append(lead)
            if len(leads) >= count:
                break

        if skipped_no_email:
            await _log(run_id, f"⏭️ Skipped {skipped_no_email} leads without email")
        if skipped_excluded:
            await _log(run_id, f"⏭️ Skipped {skipped_excluded} excluded domains")

        # If not enough leads, try one more search round
        if len(leads) < count:
            extra_needed = count - len(leads)
            await _log(run_id, f"🔄 Need {extra_needed} more leads, searching again...")
            extra_raw = orchestrator.research.search(extra_needed * 3, niche=niche)
            for lead in extra_raw:
                domain = _extract_domain(lead.website)
                if not (lead.email or "").strip():
                    continue
                if domain and (domain in excluded or domain in seen_domains):
                    continue
                if domain:
                    seen_domains.add(domain)
                leads.append(lead)
                if len(leads) >= count:
                    break

        leads = leads[:count]
        # Free research data no longer needed
        del raw_leads, seen_domains, excluded
        gc.collect()

        await _agent_progress(run_id, 1, "Research", "done", f"Знайдено {len(leads)} лідів з email")
        await _log(run_id, f"Final leads with email: {len(leads)}")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        results_dir = os.path.join(
            os.path.dirname(__file__), "..", "..", "results", f"run_{timestamp}"
        )
        os.makedirs(results_dir, exist_ok=True)

        from agents.style_agent import StyleAgent
        style_agent = StyleAgent()
        total = len(leads)
        project_root = os.path.realpath(os.path.join(os.path.dirname(__file__), "..", ".."))

        async def process_lead(i: int, lead):
            """Process a single lead: style → analysis → content → outreach → DB save."""
            loop = asyncio.get_event_loop()
            lead_name = lead.name
            progress = f"[{i+1}/{total}]"

            # 1.5. Style extraction
            brand_style = {}
            try:
                await _log(run_id, f"{progress} 🎨 Extracting brand style: {lead.website or lead_name}")
                brand_style = await loop.run_in_executor(
                    None, lambda _w=lead.website, _n=lead_name: style_agent.extract(_w, lead_name=_n))
                primary = brand_style.get("primary_color", "")
                await _log(run_id, f"{progress} StyleAgent: website={lead.website}, primary={primary}, font={brand_style.get('font_family', '')}")
                if primary == "#1A365D" or _is_neutral_color(primary):
                    brand_style["primary_color"] = "#1A365D"
                    await _log(run_id, f"{progress} ⚠️ Using default colors (site unavailable or neutral color: {primary})")
            except Exception as e:
                logger.warning(f"StyleAgent failed for {lead_name}: {e}")

            # 2. Analysis
            await _agent_progress(run_id, 2, "Analysis", "running", f"{progress} Аналіз: {lead_name}")
            await _log(run_id, f"{progress} 🧠 Analyzing: {lead_name}")
            analysis = await loop.run_in_executor(
                None, lambda _l=lead, _t=tariffs, _n=niche: orchestrator.analysis.analyze(_l, tariffs=_t, niche=_n))
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

            files = await loop.run_in_executor(
                None, lambda _l=lead, _a=analysis, _d=lead_dir, _t=tariffs, _b=brand_style, _n=niche, _c=calendly_url: orchestrator.content.generate(
                    _l, _a, _d, tariffs=_t, brand_style=_b, niche=_n, calendly_url=_c))
            html_path = files.get("html", "")
            email_path = files.get("email", "")
            web_url = files.get("web_url", "")
            web_url_detail = f" + web" if web_url else ""
            await _agent_progress(run_id, 3, "Content", "done", f"{progress} {lead_name}: HTML + email{web_url_detail}")

            # Read email text from file
            email_text = ""
            if email_path and os.path.exists(email_path):
                with open(email_path, "r", encoding="utf-8") as f:
                    email_text = f.read()

            # 4. Outreach
            await _agent_progress(run_id, 4, "Outreach", "running", f"{progress} Підготовка розсилки: {lead_name}")
            await _log(run_id, f"{progress} 📧 Processing outreach: {lead_name}")
            outreach_status = await loop.run_in_executor(
                None, lambda _l=lead, _d=lead_dir: orchestrator.outreach.process(_l, _d, False))

            # Send email via Resend if address found AND auto-send is enabled in Settings
            if auto_send_email and outreach_status.startswith("ready:") and email_text:
                to_email = outreach_status.split(":", 1)[1]
                lines = email_text.split("\n")
                subject = lines[0].replace("Тема: ", "").strip() if lines else f"Пропозиція від MTP Fulfillment для {lead_name}"
                body_text = "\n".join(lines[2:]).strip() if len(lines) > 2 else email_text

                # Build HTML email with tracking pixel + proposal link
                backend_url = os.getenv("MTP_BACKEND_URL", "https://mtp-agent-production.up.railway.app")

                # Extract slug from web_url for pixel tracking
                proposal_slug = web_url.split("/api/proposals/")[-1] if web_url and "/api/proposals/" in web_url else ""
                # Also check frontend URL pattern /proposals/{slug}
                if not proposal_slug and web_url:
                    m = re.search(r"/proposals/([^/?#]+)", web_url)
                    if m:
                        proposal_slug = m.group(1)

                pixel_html = (
                    f'<img src="{backend_url}/api/proposals/pixel/{proposal_slug}" '
                    f'width="1" height="1" style="display:none" alt="">'
                ) if proposal_slug else ""

                proposal_link_html = (
                    f'<p style="margin-top:20px"><a href="{web_url}" '
                    f'style="background:#E8730A;color:#fff;padding:10px 22px;border-radius:6px;'
                    f'text-decoration:none;font-weight:bold">📋 Переглянути пропозицію →</a></p>'
                ) if web_url else ""

                html_body = (
                    f'<div style="font-family:Arial,sans-serif;font-size:14px;line-height:1.7;color:#222;max-width:600px">'
                    f'{body_text.replace(chr(10), "<br>")}'
                    f'{proposal_link_html}'
                    f'</div>'
                    f'{pixel_html}'
                )

                from backend.services.email_service import send_email
                send_result = send_email(to=to_email, subject=subject, html=html_body)
                if send_result.get("ok"):
                    outreach_status = f"email_sent:{to_email}"
                    await _log(run_id, f"{progress} ✉️ Email sent to {to_email}" + (" (with pixel)" if pixel_html else ""))
                else:
                    await _log(run_id, f"{progress} ⚠️ Email failed ({to_email}): {send_result.get('error')}")

            await _agent_progress(run_id, 4, "Outreach", "done", f"{progress} {lead_name}: {outreach_status}")

            # Save lead to DB
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
                "email_text": email_text,
                "extra_phones": getattr(lead, "extra_phones", "") or "",
                "extra_emails": getattr(lead, "extra_emails", "") or "",
                "social_media": getattr(lead, "social_media", "") or "{}",
            }
            try:
                lead_record = db.table("leads").insert(lead_data).execute()
            except Exception:
                for col in ["niche", "extra_phones", "extra_emails", "social_media", "email_text"]:
                    lead_data.pop(col, None)
                lead_record = db.table("leads").insert(lead_data).execute()
            lead_id = lead_record.data[0]["id"]

            # Save file records — upload to Supabase Storage, fall back to local URL
            for file_type, file_path in [("html", html_path), ("email", email_path)]:
                if not file_path or not os.path.exists(file_path):
                    continue

                file_url = None
                content_text = None

                if file_type == "html":
                    storage_path = f"{run_id}/{lead_id}/proposal.html"
                    with open(file_path, "rb") as f:
                        file_bytes = f.read()
                    await _log(run_id, f"{progress} Uploading HTML ({len(file_bytes)} bytes)...")
                    storage_url = upload_to_storage("proposals", storage_path, file_bytes, content_type="text/html; charset=utf-8")
                    del file_bytes  # Free immediately after upload
                    if storage_url:
                        file_url = storage_url
                        await _log(run_id, f"{progress} HTML uploaded to storage")
                    else:
                        rel_path = os.path.relpath(os.path.realpath(file_path), project_root)
                        file_url = f"/api/runs/files/{rel_path}"
                        await _log(run_id, f"{progress} HTML saved locally: {file_url}")

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

            # Free large objects to reduce memory pressure
            del brand_style, analysis, files, email_text, lead_data

            await _log(run_id, f"{progress} Done: {lead_name} ({outreach_status})")

        # Process leads sequentially to limit peak memory usage (Railway ~512MB RAM)
        for i, lead in enumerate(leads):
            await process_lead(i, lead)
            gc.collect()  # Free memory after each lead

        # Final progress events so dashboard shows completed state
        await _agent_progress(run_id, 1, "Research", "done", f"Знайдено {len(leads)} лідів")
        await _agent_progress(run_id, 2, "Analysis", "done", f"Оброблено {len(leads)} лідів")
        await _agent_progress(run_id, 3, "Content", "done", f"Згенеровано {len(leads)} КП")
        await _agent_progress(run_id, 4, "Outreach", "done", f"Готово {len(leads)} лідів")

        # Free orchestrator and agents after pipeline completes
        del orchestrator, style_agent
        gc.collect()

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
