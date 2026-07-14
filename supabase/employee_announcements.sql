-- FactoryPulse employee announcements and circulars
-- Run in Supabase SQL Editor before publishing employee circulars.

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create table if not exists public.announcements (
  id uuid primary key default gen_random_uuid(),
  announcement_id text unique,
  title text not null,
  message text not null,
  audience text not null default 'All Employees',
  department text,
  location_id text,
  employee_code text,
  priority text not null default 'Normal',
  publish_date text,
  expiry_date text,
  published_by text,
  approval_status text not null default 'Approved',
  status text not null default 'Published',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint announcements_priority_check
    check (priority in ('Low', 'Normal', 'High', 'Critical'))
);

create index if not exists idx_announcements_status_dates
  on public.announcements(status, approval_status, publish_date, expiry_date);

create index if not exists idx_announcements_audience_department
  on public.announcements(audience, department, location_id, employee_code);

create index if not exists idx_announcements_priority_updated
  on public.announcements(priority, updated_at desc);

alter table public.announcements enable row level security;

do $$
begin
  if not exists (
    select 1
    from pg_policies
    where schemaname = 'public'
      and tablename = 'announcements'
      and policyname = 'service role erp access'
  ) then
    create policy "service role erp access"
      on public.announcements
      for all
      to service_role
      using (true)
      with check (true);
  end if;
end $$;

drop trigger if exists set_announcements_updated_at on public.announcements;
create trigger set_announcements_updated_at
  before update on public.announcements
  for each row execute function public.set_updated_at();
