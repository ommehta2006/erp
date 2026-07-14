-- FactoryPulse HR work locations and geofence controls
-- Run in Supabase SQL Editor if these tables or indexes are missing.

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create table if not exists public.work_locations (
  id uuid primary key default gen_random_uuid(),
  location_id text,
  company text,
  branch text,
  location_name text,
  location_type text,
  full_address text,
  city text,
  state text,
  country text,
  latitude text,
  longitude text,
  geofence_type text,
  geofence_radius_meters text,
  allowed_gps_accuracy_meters text,
  time_zone text,
  approval_status text,
  status text not null default 'Active',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.geofences (
  id uuid primary key default gen_random_uuid(),
  geofence_id text,
  location_id text,
  geofence_type text,
  center_latitude text,
  center_longitude text,
  radius_meters text,
  polygon_coordinates text,
  allowed_accuracy_meters text,
  boundary_version text,
  effective_start_date text,
  effective_end_date text,
  approval_status text,
  status text not null default 'Active',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.geofence_versions (
  id uuid primary key default gen_random_uuid(),
  version_id text,
  geofence_id text,
  boundary_version text,
  change_summary text,
  changed_by text,
  approved_by text,
  effective_date text,
  status text not null default 'Active',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.geofence_polygon_points (
  id uuid primary key default gen_random_uuid(),
  point_id text,
  geofence_id text,
  boundary_version text,
  point_order text,
  latitude text,
  longitude text,
  status text not null default 'Active',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.employee_location_assignments (
  id uuid primary key default gen_random_uuid(),
  assignment_id text,
  employee_code text,
  location_id text,
  shift text,
  effective_start_date text,
  effective_end_date text,
  assignment_type text,
  approval_status text,
  status text not null default 'Active',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.attendance_validation_results (
  id uuid primary key default gen_random_uuid(),
  validation_id text,
  employee_code text,
  event_type text,
  location_id text,
  geofence_id text,
  employee_latitude text,
  employee_longitude text,
  geofence_latitude text,
  geofence_longitude text,
  distance_meters text,
  radius_meters text,
  inside_fence text,
  accuracy_meters text,
  allowed_accuracy_meters text,
  geofence_status text,
  validation_reason text,
  risk_flags text,
  server_validated_at text,
  status text not null default 'Open',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create unique index if not exists idx_work_locations_location_id
  on public.work_locations (lower(coalesce(location_id, '')));

create unique index if not exists idx_geofences_geofence_id
  on public.geofences (lower(coalesce(geofence_id, '')));

create index if not exists idx_geofences_location_status
  on public.geofences (location_id, status);

create index if not exists idx_geofence_polygon_points_boundary
  on public.geofence_polygon_points (geofence_id, boundary_version, point_order);

create index if not exists idx_location_assignments_employee_status
  on public.employee_location_assignments (employee_code, status);

create index if not exists idx_location_assignments_location_status
  on public.employee_location_assignments (location_id, status);

create index if not exists idx_attendance_validation_location_status
  on public.attendance_validation_results (location_id, geofence_status, status);

alter table public.work_locations enable row level security;
alter table public.geofences enable row level security;
alter table public.geofence_versions enable row level security;
alter table public.geofence_polygon_points enable row level security;
alter table public.employee_location_assignments enable row level security;
alter table public.attendance_validation_results enable row level security;

do $$
declare
  target_table text;
begin
  foreach target_table in array array[
    'work_locations',
    'geofences',
    'geofence_versions',
    'geofence_polygon_points',
    'employee_location_assignments',
    'attendance_validation_results'
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

drop trigger if exists set_work_locations_updated_at on public.work_locations;
create trigger set_work_locations_updated_at
  before update on public.work_locations
  for each row execute function public.set_updated_at();

drop trigger if exists set_geofences_updated_at on public.geofences;
create trigger set_geofences_updated_at
  before update on public.geofences
  for each row execute function public.set_updated_at();

drop trigger if exists set_geofence_versions_updated_at on public.geofence_versions;
create trigger set_geofence_versions_updated_at
  before update on public.geofence_versions
  for each row execute function public.set_updated_at();

drop trigger if exists set_geofence_polygon_points_updated_at on public.geofence_polygon_points;
create trigger set_geofence_polygon_points_updated_at
  before update on public.geofence_polygon_points
  for each row execute function public.set_updated_at();

drop trigger if exists set_employee_location_assignments_updated_at on public.employee_location_assignments;
create trigger set_employee_location_assignments_updated_at
  before update on public.employee_location_assignments
  for each row execute function public.set_updated_at();

drop trigger if exists set_attendance_validation_results_updated_at on public.attendance_validation_results;
create trigger set_attendance_validation_results_updated_at
  before update on public.attendance_validation_results
  for each row execute function public.set_updated_at();
