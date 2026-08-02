-- Run this once in the Supabase SQL editor
-- Re-running is safe (uses IF NOT EXISTS / OR REPLACE)

-- ── Watchlist ────────────────────────────────────────────────────────────────
create table if not exists watchlist (
  id         uuid primary key default gen_random_uuid(),
  user_id    uuid references auth.users(id) on delete cascade not null,
  ticker     text not null,
  added_at   timestamptz default now(),
  unique(user_id, ticker)
);

create index if not exists watchlist_user_id_idx on watchlist(user_id);

alter table watchlist enable row level security;

drop policy if exists "Users manage own watchlist" on watchlist;
create policy "Users manage own watchlist"
  on watchlist for all
  using  (auth.uid() = user_id)
  with check (auth.uid() = user_id);

-- ── Subscriptions ────────────────────────────────────────────────────────────
create table if not exists subscriptions (
  id                      uuid primary key default gen_random_uuid(),
  user_id                 uuid references auth.users(id) on delete cascade unique not null,
  stripe_customer_id      text unique,
  stripe_subscription_id  text unique,
  plan                    text not null default 'free',   -- 'free' | 'pro'
  status                  text not null default 'active', -- 'active' | 'canceled' | 'past_due'
  current_period_end      timestamptz,
  created_at              timestamptz default now(),
  updated_at              timestamptz default now()
);

create index if not exists subscriptions_user_id_idx on subscriptions(user_id);
create index if not exists subscriptions_stripe_customer_idx on subscriptions(stripe_customer_id);

alter table subscriptions enable row level security;

drop policy if exists "Users read own subscription" on subscriptions;
create policy "Users read own subscription"
  on subscriptions for select
  using (auth.uid() = user_id);

drop policy if exists "Backend can insert subscriptions" on subscriptions;
create policy "Backend can insert subscriptions"
  on subscriptions for insert
  with check (true);

drop policy if exists "Backend can update subscriptions" on subscriptions;
create policy "Backend can update subscriptions"
  on subscriptions for update
  using (true)
  with check (true);

-- ── AI Insights ──────────────────────────────────────────────────────────────
create table if not exists ai_insights (
  id                        uuid primary key default gen_random_uuid(),
  ticker                    text not null unique,
  business_overview         text not null,
  income_statement_summary  text not null,
  performance_verdict       text not null check (performance_verdict in ('healthy', 'improving', 'declining', 'mixed')),
  performance_drivers       text[] not null default '{}',
  notable_flags             text[] not null default '{}',
  data_basis                text not null check (data_basis in ('single_period', 'multi_period')),
  latest_fiscal_period_end  date not null,
  model                     text not null,
  generated_at              timestamptz not null default now(),
  created_at                timestamptz default now()
);

create index if not exists ai_insights_ticker_idx on ai_insights(ticker);

alter table ai_insights enable row level security;

drop policy if exists "Public can read insights" on ai_insights;
create policy "Public can read insights"
  on ai_insights for select
  using (true);

drop policy if exists "Backend can insert insights" on ai_insights;
create policy "Backend can insert insights"
  on ai_insights for insert
  with check (true);

drop policy if exists "Backend can update insights" on ai_insights;
create policy "Backend can update insights"
  on ai_insights for update
  using (true)
  with check (true);
