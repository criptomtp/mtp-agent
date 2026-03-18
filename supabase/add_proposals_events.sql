-- Proposals table (for AI-generated web proposals served via /proposals/:slug)
create table if not exists proposals (
  id uuid primary key default gen_random_uuid(),
  slug text unique not null,
  client_name text not null default '',
  client_data jsonb default '{}',
  pricing_data jsonb default '{}',
  calendly_url text default 'https://calendly.com/mtpgrouppromo/30min',
  html_content text default '',
  html_url text default '',
  views_count integer default 0,
  last_viewed_at timestamptz,
  created_at timestamptz default now()
);

create index if not exists idx_proposals_slug on proposals(slug);

-- Proposal events (open, engaged_30s, scrolled_to_end, calendly_click, zoom_booked, pdf_download)
create table if not exists proposal_events (
  id uuid primary key default gen_random_uuid(),
  proposal_id uuid references proposals(id) on delete cascade,
  event text not null,
  ts timestamptz default now(),
  ua text default '',
  ref text default ''
);

create index if not exists idx_proposal_events_proposal_id on proposal_events(proposal_id);
create index if not exists idx_proposal_events_ts on proposal_events(ts desc);

-- Extra columns on leads
alter table leads add column if not exists niche text default '';
alter table leads add column if not exists proposal_url text default '';
alter table leads add column if not exists email_text text default '';
alter table leads add column if not exists extra_emails text default '';
