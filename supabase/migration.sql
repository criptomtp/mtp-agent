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
