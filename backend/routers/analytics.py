from datetime import datetime, timezone, timedelta

from fastapi import APIRouter

from backend.services.database import get_supabase, get_supabase_admin

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("")
def get_analytics():
    db = get_supabase()

    # ── Leads ──────────────────────────────────────────────────────────────
    try:
        leads_res = db.table("leads").select(
            "id, score, score_grade, niche, outreach_status, created_at, proposal_url, email"
        ).execute()
        leads_data = leads_res.data or []
    except Exception:
        leads_data = []

    total_leads = len(leads_data)
    emails_sent = sum(
        1 for l in leads_data if (l.get("outreach_status") or "").startswith("email_sent")
    )
    ready_count = sum(
        1 for l in leads_data if (l.get("outreach_status") or "").startswith("ready:")
    )

    # ── Proposals ──────────────────────────────────────────────────────────
    try:
        db_admin = get_supabase_admin()
        props_res = db_admin.table("proposals").select(
            "id, views_count, client_name, last_viewed_at"
        ).execute()
        proposals_data = props_res.data or []
    except Exception:
        proposals_data = []

    proposals_viewed = sum(1 for p in proposals_data if (p.get("views_count") or 0) > 0)
    total_views = sum(p.get("views_count") or 0 for p in proposals_data)

    # ── Proposal events ─────────────────────────────────────────────────────
    try:
        events_res = db_admin.table("proposal_events").select(
            "event, ts, proposal_id"
        ).order("ts", desc=True).limit(200).execute()
        events_data = events_res.data or []
    except Exception:
        events_data = []

    calendly_clicks = sum(1 for e in events_data if e.get("event") == "calendly_click")
    zoom_booked = sum(1 for e in events_data if e.get("event") == "zoom_booked")
    engaged_30s = sum(1 for e in events_data if e.get("event") == "engaged_30s")
    scrolled_to_end = sum(1 for e in events_data if e.get("event") == "scrolled_to_end")

    # ── Rates ──────────────────────────────────────────────────────────────
    email_open_rate = round(proposals_viewed / emails_sent * 100, 1) if emails_sent > 0 else 0
    proposal_to_calendly = (
        round(calendly_clicks / proposals_viewed * 100, 1) if proposals_viewed > 0 else 0
    )
    scores = [l.get("score") or 0 for l in leads_data if l.get("score")]
    avg_score = round(sum(scores) / len(scores), 1) if scores else 0

    # ── Score distribution ─────────────────────────────────────────────────
    score_dist = {"A": 0, "B": 0, "C": 0, "D": 0}
    for l in leads_data:
        grade = (l.get("score_grade") or "D").upper()
        if grade in score_dist:
            score_dist[grade] += 1

    # ── Top niches ─────────────────────────────────────────────────────────
    niche_count: dict[str, int] = {}
    for l in leads_data:
        n = (l.get("niche") or "інше").lower().strip()
        niche_count[n] = niche_count.get(n, 0) + 1
    top_niches = sorted(niche_count.items(), key=lambda x: x[1], reverse=True)[:8]

    # ── Leads by day (last 30 days) ────────────────────────────────────────
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    day_count: dict[str, int] = {}
    for l in leads_data:
        ts = l.get("created_at", "")
        if not ts:
            continue
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            if dt >= cutoff:
                day = dt.strftime("%m-%d")
                day_count[day] = day_count.get(day, 0) + 1
        except Exception:
            pass

    leads_by_day = []
    for i in range(29, -1, -1):
        dt = datetime.now(timezone.utc) - timedelta(days=i)
        day = dt.strftime("%m-%d")
        leads_by_day.append({"date": day, "count": day_count.get(day, 0)})

    # ── Recent events (last 15) ────────────────────────────────────────────
    prop_map = {p["id"]: p.get("client_name", "?") for p in proposals_data}
    recent_events = []
    for e in events_data[:15]:
        recent_events.append({
            "client_name": prop_map.get(e.get("proposal_id"), "?"),
            "event": e.get("event"),
            "ts": e.get("ts"),
        })

    return {
        "kpis": {
            "total_leads": total_leads,
            "emails_sent": emails_sent,
            "proposals_viewed": proposals_viewed,
            "calendly_clicks": calendly_clicks,
        },
        "rates": {
            "email_open_rate": email_open_rate,
            "proposal_to_calendly": proposal_to_calendly,
            "avg_score": avg_score,
            "zoom_booked": zoom_booked,
            "engaged_30s": engaged_30s,
            "scrolled_to_end": scrolled_to_end,
        },
        "funnel": [
            {"label": "Лідів знайдено", "value": total_leads},
            {"label": "Email надіслано", "value": emails_sent},
            {"label": "КП відкрито", "value": proposals_viewed},
            {"label": "Calendly клік", "value": calendly_clicks},
        ],
        "leads_by_day": leads_by_day,
        "top_niches": [{"niche": n, "count": c} for n, c in top_niches],
        "score_distribution": score_dist,
        "recent_events": recent_events,
    }
