# MTP Fulfillment — Lead Generation Agent

## Компанія
MTP Fulfillment — 3PL/фулфілмент провайдер, м. Бориспіль, Київська обл., Україна.
Спеціалізація: зберігання, комплектація та доставка для e-commerce (косметика, здоров'я, краса).

## URLs
- **Frontend (prod):** https://mtp-lead-agent.vercel.app
- **Backend (prod):** https://mtp-agent-production.up.railway.app
- **GitHub:** https://github.com/criptomtp/mtp-agent
- **Supabase:** https://poybvsigfcxivoiygysk.supabase.co
- **Frontend (dev):** http://localhost:5173
- **Backend (dev):** http://localhost:8000

## Стек технологій
| Шар | Технологія |
|-----|-----------|
| Backend | Python 3.11, FastAPI, uvicorn |
| Frontend | React 19, TypeScript, Vite, Tailwind CSS, react-router-dom v7 |
| БД / Storage | Supabase (PostgreSQL + Storage) |
| AI | Google Gemini 1.5 Flash (primary), Anthropic Claude Sonnet (fallback) |
| PDF | ReportLab (DejaVuSans для кирилиці) |
| Парсинг | BeautifulSoup4 + lxml |
| Deploy | Railway (backend Docker), Vercel (frontend) |
| Шифрування | cryptography.fernet (API ключі в БД) |

## Архітектура: 5-агентна система

Pipeline: **Research → Analysis → Content → Outreach**, координується **Orchestrator**.

### 1. ResearchAgent (`agents/research_agent.py`)
- Пошук лідів з Prom.ua (7 цільових запитів: "косметика виробник", "натуральна косметика магазин" тощо)
- Google Maps Places API (якщо ключ є)
- Fallback: 10 захардкоджених українських косметичних компаній
- `_enrich_lead_from_prom()` — заходить на сторінку компанії для отримання phone/email/city/products_count
- Дедуплікація за нормалізованим іменем
- Dataclass `Lead`: name, website, email, phone, city, description, products_count, source

### 2. AnalysisAgent (`agents/analysis_agent.py`)
- Приймає `api_keys` dict (з Supabase через pipeline), fallback на env vars
- `_scrape_website(url)` — забирає title, meta description, текст (2000 chars) з сайту клієнта
- Промпт просить JSON з полями: company_analysis, mtp_value_proposition, pain_points[], potential (low/medium/high), pricing_estimate, personalization
- Ланцюжок: Gemini → Claude → fallback (математичний розрахунок)
- Тарифи для промпту: з БД (mtp_tariffs) або hardcoded

### 3. ContentAgent (`agents/content_agent.py`)
- Генерує PDF КП (A4, корпоративні кольори: синій #1B3A6B, оранжевий #E8730A)
- Секції PDF: шапка MTP, привітання, про MTP, аналіз клієнта, value proposition, болі (з analysis.pain_points), таблиця тарифів (динамічна з БД), кошторис, CTA, контакти
- Генерує email.txt з персоналізованим текстом
- `generate(lead, analysis, dir, tariffs=None)` — tariffs будує таблицю динамічно

### 4. OutreachAgent (`agents/outreach_agent.py`)
- `_find_email_on_website()` — regex пошук email на сайті
- `_send_gmail()` — заглушка (потребує OAuth), повертає False
- `_save_contact_card()` — зберігає contact_card.txt
- Статуси: `email_sent:{email}`, `ready:{email}`, `manual_required`

### 5. Orchestrator (`agents/orchestrator.py`)
- `__init__(send_email, api_keys=None, tariffs=None)` — передає api_keys до AnalysisAgent, tariffs до analyze()/generate()
- `run(count)` — повний pipeline з CSV summary
- Результати: `results/run_YYYYMMDD_HHMM/` → папка на ліда (proposal.pdf, email.txt, contact_card.txt)

## Backend API

| Метод | Endpoint | Опис |
|-------|----------|------|
| GET | `/api/dashboard/stats` | total_runs, total_leads, active_runs |
| POST | `/api/dashboard/run` | Запуск pipeline (niche, count) |
| GET | `/api/leads/` | Список лідів (?status, ?run_id, ?limit, ?offset) |
| GET | `/api/leads/{id}` | Лід + files |
| GET | `/api/leads/{id}/files` | Файли ліда (file_url, content_text) |
| GET | `/api/runs/` | Список ранів |
| GET | `/api/runs/{id}` | Ран з лідами |
| GET/POST | `/api/settings/api-keys` | CRUD API ключів |
| POST | `/api/settings/api-keys/test` | Тест ключа |
| WS | `/ws/logs` | Live логи pipeline |
| GET | `/health`, `/` | Healthcheck |

## Backend Services
- **`backend/services/database.py`** — `get_supabase()`, `get_tariffs()`, `upload_to_storage(bucket, path, bytes)`
- **`backend/services/pipeline.py`** — `run_pipeline(niche, count)`: завантажує API ключі з БД, тарифи з БД, створює Orchestrator, після генерації завантажує PDF в Supabase Storage "proposals", зберігає file_url/content_text/outreach_status
- **`backend/services/api_keys.py`** — Fernet encrypt/decrypt, `get_decrypted_key(service_name)`, `test_api_key()`

## Frontend (React SPA)
- **Pages:** Dashboard, Leads, Runs, Settings
- **Components:** Layout, StatCard, LeadTable, RunLog, ApiKeyInput
- **Leads.tsx** — таблиця лідів + модальне вікно з:
  - Contact card (name, website, email, phone, city — clickable links)
  - View PDF / Download PDF кнопки (якщо file_url є)
  - Copy Email Text кнопка з feedback
  - Preview email тексту
  - Analysis JSON

## Структура БД (Supabase PostgreSQL)

### `api_keys`
| Колонка | Тип | Опис |
|---------|-----|------|
| id | uuid PK | |
| service_name | text UNIQUE | gemini, anthropic, google_maps |
| encrypted_key | text | Fernet-encrypted |
| is_active | boolean | default true |
| created_at | timestamptz | |

### `runs`
| Колонка | Тип | Опис |
|---------|-----|------|
| id | uuid PK | |
| niche | text | default 'cosmetics' |
| leads_count | integer | |
| status | text | pending / running / completed / failed |
| started_at | timestamptz | |
| finished_at | timestamptz | |

### `leads`
| Колонка | Тип | Опис |
|---------|-----|------|
| id | uuid PK | |
| run_id | uuid FK→runs | cascade delete |
| name | text | |
| website, email, phone, city, source | text | |
| status | text | new / contacted / converted / rejected |
| outreach_status | text | email_sent:x / ready:x / manual_required |
| analysis_json | jsonb | повний результат аналізу |
| created_at | timestamptz | |

### `generated_files`
| Колонка | Тип | Опис |
|---------|-----|------|
| id | uuid PK | |
| lead_id | uuid FK→leads | cascade delete |
| file_type | text | pdf / email |
| file_path | text | локальний шлях |
| file_url | text | Supabase Storage public URL |
| content_text | text | текст email (для відображення в UI) |
| created_at | timestamptz | |

### `mtp_tariffs`
| Колонка | Тип | Опис |
|---------|-----|------|
| id | uuid PK | |
| service_name | text | назва послуги |
| unit | text | одиниця / місяць / замовлення |
| price | numeric | ціна (0 якщо "за тарифом НП") |
| currency | text | default 'UAH' |
| note | text | додаткова інформація |
| sort_order | int | порядок відображення |
| is_active | boolean | |
| updated_at | timestamptz | |

### Supabase Storage
- Bucket: `proposals` (public) — PDF файли: `{run_id}/{lead_id}/proposal.pdf`

## Запуск (dev)
```bash
# Backend
cd /Users/nikolaj/projects/mtp-agent
pip install -r requirements.txt
uvicorn backend.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev

# CLI (без backend)
python main.py           # 5 лідів
python main.py 10        # 10 лідів
python main.py 5 --send  # + автовідправка
```

## Env змінні (.env в корені)
```
SUPABASE_URL=
SUPABASE_KEY=          # anon key для backend
ENCRYPTION_KEY=        # Fernet, 32 bytes base64
GEMINI_API_KEY=        # Google AI Studio
ANTHROPIC_API_KEY=     # Anthropic (fallback)
GOOGLE_MAPS_API_KEY=   # Places API (опціонально)
GMAIL_CLIENT_ID=       # OAuth (не реалізовано)
GMAIL_CLIENT_SECRET=
SENDER_EMAIL=
```

## Структура проекту
```
mtp-agent/
├── agents/
│   ├── research_agent.py    # Lead dataclass + ResearchAgent
│   ├── analysis_agent.py    # AnalysisAgent (Gemini/Claude + scraping)
│   ├── content_agent.py     # ContentAgent (PDF + email)
│   ├── outreach_agent.py    # OutreachAgent (email / contact card)
│   └── orchestrator.py      # Orchestrator (координація)
├── backend/
│   ├── main.py              # FastAPI app + CORS + routers
│   ├── config.py            # Settings (env vars, CORS origins)
│   ├── services/
│   │   ├── database.py      # Supabase client + get_tariffs + upload_to_storage
│   │   ├── pipeline.py      # run_pipeline() — async orchestration
│   │   └── api_keys.py      # Fernet encrypt/decrypt + key CRUD
│   ├── routers/
│   │   ├── dashboard.py     # Stats + run trigger
│   │   ├── leads.py         # Lead CRUD + files endpoint
│   │   ├── runs.py          # Runs list + CSV export
│   │   └── settings.py      # API key management
│   └── ws/
│       └── logs.py          # WebSocket log streaming
├── frontend/src/
│   ├── lib/api.ts           # Fetch-based API client
│   ├── lib/supabase.ts      # Supabase JS client
│   ├── pages/               # Dashboard, Leads, Runs, Settings
│   └── components/          # Layout, StatCard, LeadTable, RunLog, ApiKeyInput
├── supabase/
│   └── migration.sql        # Повна схема БД + seed тарифів
├── results/                 # Генеровані результати (git-ignored)
├── main.py                  # CLI entry point
├── requirements.txt         # Python deps
├── Dockerfile               # Railway deploy
└── railway.json             # Railway config
```

## Відомі проблеми та TODO
1. **Gmail OAuth не реалізовано** — OutreachAgent завжди повертає `manual_required` або `ready`, ніколи не відправляє
2. **Prom.ua парсинг нестабільний** — селектори можуть зламатись при зміні верстки, часто падає на fallback
3. **Migration SQL потребує ручного запуску** — нові таблиці (mtp_tariffs) та ALTER треба виконати в Supabase SQL Editor
4. **Storage upload може fail** — якщо bucket "proposals" не створено або RLS блокує, PDF не завантажиться (file_url буде None)
5. **SUPABASE_KEY** — backend використовує `SUPABASE_KEY` (в config.py), але .env має `SUPABASE_ANON_KEY` — потрібно перевірити що вони збігаються або використовувати service key для storage upload
6. **Немає пагінації на фронтенді** — leads/runs завантажуються з limit=50
7. **Немає автентифікації** — dashboard публічно доступний
8. **CSV export** — є в runs router, але не підключений до UI
9. **WebSocket логи** — працюють тільки поки вкладка відкрита, немає persistent log storage
10. **DejaVuSans шрифт** — може бути відсутній на Railway (Docker), PDF буде з Helvetica без кирилиці
