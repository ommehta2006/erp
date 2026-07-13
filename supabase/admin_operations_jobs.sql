-- FactoryPulse Admin Operations Jobs support
-- Run in Supabase SQL Editor if automation_jobs table/indexes/policies are missing.

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create table if not exists public.automation_jobs (
  id uuid primary key default gen_random_uuid(),
  job_no text,
  system text,
  job_type text,
  schedule text,
  last_run text,
  owner text,
  status text not null default 'Open',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_automation_jobs_type_status
  on public.automation_jobs(job_type, status, updated_at desc);

create index if not exists idx_automation_jobs_owner_updated
  on public.automation_jobs(owner, updated_at desc);

create index if not exists idx_automation_jobs_schedule_updated
  on public.automation_jobs(schedule, updated_at desc);

alter table public.automation_jobs enable row level security;

do $$
begin
  if not exists (
    select 1
    from pg_policies
    where schemaname = 'public'
      and tablename = 'automation_jobs'
      and policyname = 'service role erp access'
  ) then
    create policy "service role erp access"
      on public.automation_jobs
      for all
      to service_role
      using (true)
      with check (true);
  end if;
end $$;

drop trigger if exists set_automation_jobs_updated_at on public.automation_jobs;
create trigger set_automation_jobs_updated_at
  before update on public.automation_jobs
  for each row execute function public.set_updated_at();
