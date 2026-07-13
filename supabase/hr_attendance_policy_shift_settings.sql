-- FactoryPulse HR attendance policy and shift settings
-- Run in Supabase SQL Editor if these tables, indexes, or policies are missing.

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create table if not exists public.attendance_policies (
  id uuid primary key default gen_random_uuid(),
  policy_name text,
  late_after_time text,
  grace_minutes text,
  tracking_interval_minutes text,
  background_location_required text,
  status text not null default 'Active',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.shifts (
  id uuid primary key default gen_random_uuid(),
  name text,
  start_time text,
  end_time text,
  department text,
  supervisor text,
  status text not null default 'Active',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.employee_shift_assignments (
  id uuid primary key default gen_random_uuid(),
  assignment_id text,
  employee_code text,
  shift text,
  effective_start_date text,
  effective_end_date text,
  approval_status text,
  status text not null default 'Active',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_attendance_policies_status_updated
  on public.attendance_policies(status, updated_at desc);

create index if not exists idx_shifts_name_status
  on public.shifts(lower(coalesce(name, '')), status);

create index if not exists idx_employee_shift_assignments_employee_status
  on public.employee_shift_assignments(employee_code, status);

alter table public.attendance_policies enable row level security;
alter table public.shifts enable row level security;
alter table public.employee_shift_assignments enable row level security;

do $$
declare
  target_table text;
begin
  foreach target_table in array array[
    'attendance_policies',
    'shifts',
    'employee_shift_assignments'
  ]
  loop
    if not exists (
      select 1
      from pg_policies
      where schemaname = 'public'
        and tablename = target_table
        and policyname = 'service role erp access'
    ) then
      execute format(
        'create policy "service role erp access" on public.%I for all to service_role using (true) with check (true)',
        target_table
      );
    end if;
  end loop;
end $$;

drop trigger if exists set_attendance_policies_updated_at on public.attendance_policies;
create trigger set_attendance_policies_updated_at
  before update on public.attendance_policies
  for each row execute function public.set_updated_at();

drop trigger if exists set_shifts_updated_at on public.shifts;
create trigger set_shifts_updated_at
  before update on public.shifts
  for each row execute function public.set_updated_at();

drop trigger if exists set_employee_shift_assignments_updated_at on public.employee_shift_assignments;
create trigger set_employee_shift_assignments_updated_at
  before update on public.employee_shift_assignments
  for each row execute function public.set_updated_at();
