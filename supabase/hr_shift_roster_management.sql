-- FactoryPulse HR Shift and Roster Management
-- Run in Supabase SQL Editor before using advanced HR shift settings if columns are missing.

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create table if not exists public.shifts (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  shift_type text not null default 'Fixed',
  start_time text not null,
  end_time text not null,
  cross_midnight text not null default 'No',
  day_in_open_time text,
  day_in_close_time text,
  day_out_open_time text,
  day_out_close_time text,
  grace_minutes text,
  minimum_full_day_minutes text,
  minimum_half_day_minutes text,
  break_minutes text,
  auto_break_deduction text,
  overtime_eligible text,
  overtime_approval_required text,
  early_exit_grace_minutes text,
  late_mark_after_minutes text,
  maximum_late_marks text,
  weekly_working_days text,
  weekly_offs text,
  applicable_locations text,
  applicable_departments text,
  applicable_employees text,
  effective_start_date text,
  effective_end_date text,
  department text,
  supervisor text,
  status text not null default 'Active',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint shifts_type_check check (shift_type in ('Fixed', 'Rotational', 'Night', 'Flexible', 'Split', 'Temporary'))
);

alter table public.shifts
  add column if not exists shift_type text default 'Fixed',
  add column if not exists cross_midnight text default 'No',
  add column if not exists day_in_open_time text,
  add column if not exists day_in_close_time text,
  add column if not exists day_out_open_time text,
  add column if not exists day_out_close_time text,
  add column if not exists grace_minutes text,
  add column if not exists minimum_full_day_minutes text,
  add column if not exists minimum_half_day_minutes text,
  add column if not exists break_minutes text,
  add column if not exists auto_break_deduction text,
  add column if not exists overtime_eligible text,
  add column if not exists overtime_approval_required text,
  add column if not exists early_exit_grace_minutes text,
  add column if not exists late_mark_after_minutes text,
  add column if not exists maximum_late_marks text,
  add column if not exists weekly_working_days text,
  add column if not exists weekly_offs text,
  add column if not exists applicable_locations text,
  add column if not exists applicable_departments text,
  add column if not exists applicable_employees text,
  add column if not exists effective_start_date text,
  add column if not exists effective_end_date text;

create table if not exists public.employee_shift_assignments (
  id uuid primary key default gen_random_uuid(),
  assignment_id text unique,
  employee_code text not null,
  shift text not null,
  shift_type text,
  effective_start_date text,
  effective_end_date text,
  assignment_reason text,
  approved_by text,
  approval_status text not null default 'Approved',
  status text not null default 'Active',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.employee_shift_assignments
  add column if not exists shift_type text,
  add column if not exists assignment_reason text,
  add column if not exists approved_by text;

create table if not exists public.shift_rosters (
  id uuid primary key default gen_random_uuid(),
  roster_id text unique,
  employee_code text not null,
  shift text not null,
  roster_date text not null,
  location_id text,
  planned_start_time text,
  planned_end_time text,
  roster_type text,
  published_status text not null default 'Published',
  approval_status text not null default 'Approved',
  status text not null default 'Active',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.shift_rosters
  add column if not exists planned_start_time text,
  add column if not exists planned_end_time text,
  add column if not exists roster_type text,
  add column if not exists published_status text,
  add column if not exists approval_status text;

create index if not exists idx_shifts_status_type
  on public.shifts(status, shift_type, updated_at desc);

create index if not exists idx_employee_shift_assignments_employee_dates
  on public.employee_shift_assignments(employee_code, effective_start_date, effective_end_date, status);

create unique index if not exists uq_shift_rosters_employee_date_active
  on public.shift_rosters(employee_code, roster_date)
  where status = 'Active';

create index if not exists idx_shift_rosters_date_shift
  on public.shift_rosters(roster_date, shift, published_status);

alter table public.shifts enable row level security;
alter table public.employee_shift_assignments enable row level security;
alter table public.shift_rosters enable row level security;

do $$
begin
  if not exists (select 1 from pg_policies where schemaname = 'public' and tablename = 'shifts' and policyname = 'service role erp access') then
    create policy "service role erp access" on public.shifts for all to service_role using (true) with check (true);
  end if;
  if not exists (select 1 from pg_policies where schemaname = 'public' and tablename = 'employee_shift_assignments' and policyname = 'service role erp access') then
    create policy "service role erp access" on public.employee_shift_assignments for all to service_role using (true) with check (true);
  end if;
  if not exists (select 1 from pg_policies where schemaname = 'public' and tablename = 'shift_rosters' and policyname = 'service role erp access') then
    create policy "service role erp access" on public.shift_rosters for all to service_role using (true) with check (true);
  end if;
end $$;

drop trigger if exists set_shifts_updated_at on public.shifts;
create trigger set_shifts_updated_at before update on public.shifts for each row execute function public.set_updated_at();

drop trigger if exists set_employee_shift_assignments_updated_at on public.employee_shift_assignments;
create trigger set_employee_shift_assignments_updated_at before update on public.employee_shift_assignments for each row execute function public.set_updated_at();

drop trigger if exists set_shift_rosters_updated_at on public.shift_rosters;
create trigger set_shift_rosters_updated_at before update on public.shift_rosters for each row execute function public.set_updated_at();
