-- MTP Fulfillment Dashboard Schema

create table if not exists api_keys (
  id uuid primary key default gen_random_uuid(),
  service_name text unique not null,
  encrypted_key text not null,
  is_active boolean default true,
  created_at timestamptz default now()
);

create table if not exists runs (
  id uuid primary key default gen_random_uuid(),
  niche text not null default 'cosmetics',
  leads_count integer not null default 0,
  status text not null default 'pending',
  started_at timestamptz default now(),
  finished_at timestamptz
);

create table if not exists leads (
  id uuid primary key default gen_random_uuid(),
  run_id uuid references runs(id) on delete cascade,
  name text not null,
  website text default '',
  email text default '',
  phone text default '',
  city text default '',
  source text default '',
  status text default 'new',
  analysis_json jsonb default '{}',
  created_at timestamptz default now()
);

create table if not exists generated_files (
  id uuid primary key default gen_random_uuid(),
  lead_id uuid references leads(id) on delete cascade,
  file_type text not null,
  file_path text not null,
  created_at timestamptz default now()
);

-- Indexes
create index if not exists idx_leads_run_id on leads(run_id);
create index if not exists idx_leads_status on leads(status);
create index if not exists idx_runs_status on runs(status);
create index if not exists idx_generated_files_lead_id on generated_files(lead_id);

-- ============================================================
-- P5: Tariffs table
-- ============================================================

create table if not exists mtp_tariffs (
  id uuid primary key default gen_random_uuid(),
  service_name text not null,
  unit text not null,
  price numeric not null,
  currency text not null default 'UAH',
  note text default '',
  sort_order int default 0,
  is_active boolean default true,
  updated_at timestamptz default now()
);

INSERT INTO mtp_tariffs (service_name, unit, price, currency, note, sort_order) VALUES
  ('Розвантаження коробки', 'коробка', 20, 'UAH', '', 1),
  ('Розвантаження палети', 'палета', 80, 'UAH', '', 2),
  ('Приймання та розміщення', 'одиниця', 3, 'UAH', 'до 2 кг', 3),
  ('Доплата за вагу (приймання)', 'кг', 0.5, 'UAH', 'понад 2 кг', 4),
  ('Зберігання', 'м³/місяць', 650, 'UAH', 'євро-палета ≈ 1.73 м³', 5),
  ('Відвантаження B2C', 'замовлення', 22, 'UAH', 'від 18 до 26 грн залежно від обсягу', 6),
  ('Доукомплектація', 'одиниця', 2.5, 'UAH', '', 7),
  ('Доплата за вагу (відвантаження)', 'кг', 0.5, 'UAH', 'понад 2 кг', 8),
  ('Мінімальний платіж', 'місяць', 5000, 'UAH', '', 9),
  ('Фінансова комісія НП', '%', 10, 'UAH', 'від суми накладеного платежу', 10)
ON CONFLICT DO NOTHING;

-- P5/P3: Extend generated_files for cloud storage
alter table generated_files add column if not exists file_url text;
alter table generated_files add column if not exists content_text text;

-- P5/P3: Outreach status on leads
alter table leads add column if not exists outreach_status text;

-- P3: Storage bucket for proposals
insert into storage.buckets (id, name, public)
values ('proposals', 'proposals', true)
on conflict (id) do nothing;

-- Scoring columns on leads
ALTER TABLE leads ADD COLUMN IF NOT EXISTS score integer DEFAULT 0;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS score_grade text DEFAULT 'D';
