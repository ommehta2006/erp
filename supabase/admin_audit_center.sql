-- FactoryPulse Admin Audit Center support
-- Run in Supabase SQL Editor if audit_logs table/indexes/policies are missing.

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create table if not exists public.audit_logs (
  id uuid primary key default gen_random_uuid(),
  audit_id text,
  actor text,
  action text,
  entity_type text,
  entity_id text,
  previous_values text,
  new_values text,
  reason text,
  ip_address text,
  device_info text,
  approval_reference text,
  status text not null default 'Active',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_audit_logs_actor_updated
  on public.audit_logs(actor, updated_at desc);

create index if not exists idx_audit_logs_action_updated
  on public.audit_logs(action, updated_at desc);

create index if not exists idx_audit_logs_entity_updated
  on public.audit_logs(entity_type, entity_id, updated_at desc);

create index if not exists idx_audit_logs_status_updated
  on public.audit_logs(status, updated_at desc);

alter table public.audit_logs enable row level security;

do $$
begin
  if not exists (
    select 1
    from pg_policies
    where schemaname = 'public'
      and tablename = 'audit_logs'
      and policyname = 'service role erp access'
  ) then
    create policy "service role erp access"
      on public.audit_logs
      for all
      to service_role
      using (true)
      with check (true);
  end if;
end $$;

drop trigger if exists set_audit_logs_updated_at on public.audit_logs;
create trigger set_audit_logs_updated_at
  before update on public.audit_logs
  for each row execute function public.set_updated_at();
