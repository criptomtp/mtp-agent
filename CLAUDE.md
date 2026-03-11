# MTP Agent — Claude Code Instructions

## Project Overview

MTP Agent is an automated lead generation system for MTP Fulfillment, a Ukrainian 3PL company based in Boryspil (Kyiv region). The system discovers potential e-commerce clients, analyzes their business, generates personalized commercial proposals (HTML, PPTX, email text), and prepares outreach materials. The pipeline runs as a web dashboard with real-time WebSocket logs.

## Architecture

| Layer | Technology | Deployment |
|-------|-----------|------------|
| Backend | Python 3.11, FastAPI, uvicorn | Railway (Docker) |
| Frontend | React 19, TypeScript, Vite, Tailwind CSS | Vercel |
| Database | Supabase (PostgreSQL + Storage) | Supabase Cloud |
| AI | Google Gemini 2.5 Flash (primary), Anthropic Claude Sonnet (fallback) | API |
| Presentations | python-pptx (PPTX), Gemini-generated HTML (web proposals) | — |
| Parsing | BeautifulSoup4 + lxml | — |
| Encryption | cryptography.fernet (API keys at rest) | — |

### Agent Pipeline

```
ResearchAgent → AnalysisAgent → ContentAgent → OutreachAgent
     ↑                                              |
     └──────────── Orchestrator coordinates ────────┘
```

- **ResearchAgent** (`agents/research_agent.py`) — finds leads via Serper.dev (Google), Prom.ua, Google Maps, OLX; scrapes contacts from websites
- **AnalysisAgent** (`agents/analysis_agent.py`) — scrapes client website + cooperation pages, generates AI analysis (pain points, scoring, pricing estimate)
- **ContentAgent** (`agents/content_agent.py`) — generates HTML proposal, PPTX presentation, email text, and AI-generated web proposal
- **OutreachAgent** (`agents/outreach_agent.py`) — prepares contact cards, email sending stub
- **Orchestrator** (`agents/orchestrator.py`) — coordinates the pipeline

### Key URLs

- Frontend (prod): https://mtp-lead-agent.vercel.app
- Backend (prod): https://mtp-agent-production.up.railway.app
- Frontend (dev): http://localhost:5173
- Backend (dev): http://localhost:8000

## Known Issues

1. **Gmail OAuth not implemented** — OutreachAgent always returns `manual_required` or `ready`, never actually sends email
2. **Prom.ua parsing unstable** — selectors break when Prom changes their HTML; falls back to other channels
3. **Supabase Storage upload can fail** — if bucket "proposals" is missing or RLS blocks, file_url will be None. Backend has fallback logic but PPTX/HTML may not be downloadable
4. **Cyrillic fonts in Docker** — DejaVuSans may be missing on Railway, PDF output will fall back to Helvetica without Cyrillic support
5. **No authentication** — dashboard is publicly accessible
6. **No frontend pagination** — leads/runs load with limit=50
7. **Ukrposhta API blocked on Vercel IPs** — manual fallback in use
8. **Migration SQL requires manual execution** — new columns/tables must be run in Supabase SQL Editor

## Working Rules

1. **Plan before implementing.** For any non-trivial change, write the plan to `tasks/todo.md` before writing code. Include what files will change and why.
2. **Never mark a task complete without verifying it works.** Run syntax checks (`python3 -c "import ast; ast.parse(...)"` for Python, `npx tsc --noEmit` for TypeScript) at minimum. Run the actual test/server when possible.
3. **After any bug fix or correction, append a lesson to `tasks/lessons.md`.** Include: what broke, why, and how to avoid it next time.
4. **Keep changes minimal and focused.** Don't touch unrelated code. Don't add docstrings, comments, or type annotations to unchanged code. Don't refactor nearby code "while you're in there."
5. **For any non-trivial change, ask: "Is there a more elegant solution?"** Prefer simple, direct solutions over clever abstractions. Three similar lines are better than a premature abstraction.
6. **Fix bugs autonomously.** Don't ask the user for hand-holding. Read the relevant code, understand the problem, fix it, verify it.
7. **Respect the fallback chain.** This codebase has many fallbacks (Gemini → Claude → hardcoded, Storage → local file, Serper → Prom → Gemini → static). When modifying one layer, don't break the fallback chain.
8. **All user-facing text is in Ukrainian.** Code comments and logs can be in English.

## Environment Variables

Required in `.env` at project root (never commit values):

```
SUPABASE_URL=              # Supabase project URL
SUPABASE_KEY=              # Supabase anon key (or SUPABASE_ANON_KEY)
SUPABASE_SERVICE_ROLE_KEY= # Service role key for storage uploads
ENCRYPTION_KEY=            # Fernet key, 32 bytes base64
GEMINI_API_KEY=            # Google AI Studio
ANTHROPIC_API_KEY=         # Anthropic (fallback AI)
SERPER_API_KEY=            # Serper.dev Google search API
GOOGLE_MAPS_API_KEY=       # Places API (optional)
DATABASE_URL=              # Direct PostgreSQL connection (optional)
```

## Key Reminders

- **ENCRYPTION_KEY must be replaced before production launch.** The current key may be a development placeholder. Generate a new one with `python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`.
- **Ukrposhta API is blocked on Vercel IPs** — manual fallback is in use for any postal service integration.
- **Cyrillic font support is required for PDF generation.** ReportLab needs DejaVuSans font files present in the Docker image. The Dockerfile should include `apt-get install -y fonts-dejavu-core` or copy the font files manually.
- **Supabase Storage needs the `proposals` bucket created manually** with public access enabled. RLS policies must allow uploads via service role key.
- **The `leads` table has been extended** with `extra_phones` (text), `social_media` (jsonb), `score` (int), `score_grade` (text), `niche` (text), `proposal_url` (text). Run `supabase/migration.sql` if columns are missing.

## Dev Commands

```bash
# Backend
pip install -r requirements.txt
uvicorn backend.main:app --reload --port 8000

# Frontend
cd frontend && npm install && npm run dev

# CLI (without backend)
python main.py           # 5 leads
python main.py 10        # 10 leads

# Syntax checks
python3 -c "import ast; ast.parse(open('agents/research_agent.py').read())"
cd frontend && npx tsc --noEmit
```
