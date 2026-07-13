-- FactoryPulse HR employee biometric enrollment metadata
-- Run in Supabase SQL Editor if this table does not already exist.
--
-- Privacy rule: this table must never contain raw fingerprints, face images,
-- biometric templates, or irreversible biometric feature vectors. It stores
-- only trusted-device enrollment metadata and assertion references.

create table if not exists public.employee_biometric_enrollments (
  id uuid primary key default gen_random_uuid(),
  enrollment_id text,
  employee_code text,
  verification_method text,
  trusted_device_id text,
  assertion_reference text,
  enrolled_at text,
  privacy_notice text,
  approval_status text,
  status text not null default 'Open',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create unique index if not exists idx_employee_biometric_enrollments_unique
  on public.employee_biometric_enrollments (
    lower(coalesce(employee_code, '')),
    lower(coalesce(verification_method, '')),
    lower(coalesce(trusted_device_id, ''))
  );

create index if not exists idx_employee_biometric_enrollments_employee_status
  on public.employee_biometric_enrollments(employee_code, status);

alter table public.employee_biometric_enrollments enable row level security;

do $$
begin
  if not exists (
    select 1
    from pg_policies
    where schemaname = 'public'
      and tablename = 'employee_biometric_enrollments'
      and policyname = 'service role biometric enrollment access'
  ) then
    create policy "service role biometric enrollment access"
      on public.employee_biometric_enrollments
      for all
      to service_role
      using (true)
      with check (true);
  end if;
end $$;

drop trigger if exists set_employee_biometric_enrollments_updated_at on public.employee_biometric_enrollments;
create trigger set_employee_biometric_enrollments_updated_at
  before update on public.employee_biometric_enrollments
  for each row
  execute function public.set_updated_at();
