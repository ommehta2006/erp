-- FactoryPulse Location Fraud and Device Integrity Risk Controls
-- Run in Supabase SQL Editor before reviewing high-risk attendance/device events.

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create table if not exists public.device_integrity_events (
  id uuid primary key default gen_random_uuid(),
  event_id text unique,
  employee_code text not null,
  device_id text,
  signal_type text,
  risk_score text not null default '0',
  risk_flags text,
  observed_at text,
  status text not null default 'Passed',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.attendance_location_events (
  id uuid primary key default gen_random_uuid(),
  event_id text unique,
  attendance_record_id text,
  employee_code text not null,
  event_type text,
  latitude text,
  longitude text,
  accuracy text,
  altitude text,
  speed text,
  provider text,
  captured_at text,
  received_at text,
  device_time text,
  server_time text,
  geofence_id text,
  geofence_version text,
  distance_meters text,
  inside_fence text,
  tolerance_applied text,
  mock_location_indicator text,
  risk_score text,
  validation_result text,
  failure_reason text,
  device_id text,
  ip_address text,
  app_version text,
  status text not null default 'Open',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_device_integrity_employee_risk
  on public.device_integrity_events(employee_code, status, updated_at desc);

create index if not exists idx_device_integrity_device
  on public.device_integrity_events(device_id, risk_score);

create index if not exists idx_location_events_employee_risk
  on public.attendance_location_events(employee_code, risk_score, updated_at desc);

create index if not exists idx_location_events_device
  on public.attendance_location_events(device_id, event_type, updated_at desc);

alter table public.device_integrity_events enable row level security;
alter table public.attendance_location_events enable row level security;

do $$
declare
  table_name text;
begin
  foreach table_name in array array['device_integrity_events', 'attendance_location_events']
  loop
    if not exists (
      select 1
      from pg_policies
      where schemaname = 'public'
        and tablename = table_name
        and policyname = 'service role erp access'
    ) then
      execute format(
        'create policy "service role erp access" on public.%I for all to service_role using (true) with check (true)',
        table_name
      );
    end if;
  end loop;
end $$;

drop trigger if exists set_device_integrity_events_updated_at on public.device_integrity_events;
create trigger set_device_integrity_events_updated_at
  before update on public.device_integrity_events
  for each row execute function public.set_updated_at();

drop trigger if exists set_attendance_location_events_updated_at on public.attendance_location_events;
create trigger set_attendance_location_events_updated_at
  before update on public.attendance_location_events
  for each row execute function public.set_updated_at();
