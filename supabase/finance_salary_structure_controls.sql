-- FactoryPulse Finance Salary Structure Controls
-- Run in Supabase SQL Editor before using /finance/salary if salary columns/tables are missing.

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create table if not exists public.salary_structures (
  id uuid primary key default gen_random_uuid(),
  structure_id text unique,
  structure_name text not null,
  currency text not null default 'INR',
  payment_frequency text not null default 'Monthly',
  proration_method text not null default 'Payroll Policy',
  basic_salary text,
  allowances text,
  deductions text,
  employer_contributions text,
  employee_contributions text,
  gross_salary text,
  ctc text,
  net_salary_estimate text,
  approval_status text not null default 'Approved',
  status text not null default 'Active',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.salary_structures
  add column if not exists basic_salary text,
  add column if not exists allowances text,
  add column if not exists deductions text,
  add column if not exists employer_contributions text,
  add column if not exists employee_contributions text,
  add column if not exists gross_salary text,
  add column if not exists ctc text,
  add column if not exists net_salary_estimate text;

create table if not exists public.salary_structure_components (
  id uuid primary key default gen_random_uuid(),
  component_id text unique,
  structure_id text not null,
  component_name text not null,
  component_type text not null default 'Earning',
  calculation_method text not null default 'Fixed',
  amount text,
  percentage_of text,
  taxable text,
  payroll_impact text,
  status text not null default 'Active',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.salary_structure_components
  add column if not exists percentage_of text,
  add column if not exists payroll_impact text;

create table if not exists public.employee_salary_assignments (
  id uuid primary key default gen_random_uuid(),
  assignment_id text unique,
  employee_code text not null,
  structure_id text not null,
  effective_date text not null,
  basic_salary text,
  allowances text,
  deductions text,
  employer_contributions text,
  employee_contributions text,
  gross_salary text,
  ctc text,
  net_salary_estimate text,
  currency text,
  payment_frequency text,
  approval_status text not null default 'Approved',
  status text not null default 'Active',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.employee_salary_assignments
  add column if not exists basic_salary text,
  add column if not exists allowances text,
  add column if not exists deductions text,
  add column if not exists employer_contributions text,
  add column if not exists employee_contributions text,
  add column if not exists net_salary_estimate text,
  add column if not exists currency text,
  add column if not exists payment_frequency text;

create table if not exists public.salary_revision_history (
  id uuid primary key default gen_random_uuid(),
  revision_id text unique,
  employee_code text not null,
  structure_id text not null,
  effective_date text not null,
  basic_salary text,
  allowances text,
  deductions text,
  gross_salary text,
  ctc text,
  net_salary_estimate text,
  revision_type text,
  previous_salary text,
  new_salary text,
  increase_amount text,
  increase_percent text,
  reason text,
  supporting_document text,
  requested_by text,
  approved_by text,
  approval_status text not null default 'Pending Approval',
  created_time text,
  status text not null default 'Pending Approval',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.salary_revision_history
  add column if not exists supporting_document text,
  add column if not exists requested_by text,
  add column if not exists approval_status text,
  add column if not exists created_time text;

create index if not exists idx_salary_structures_status
  on public.salary_structures(status, approval_status, updated_at desc);

create index if not exists idx_salary_components_structure
  on public.salary_structure_components(structure_id, component_type, status);

create index if not exists idx_salary_assignments_employee_effective
  on public.employee_salary_assignments(employee_code, effective_date desc, status);

create index if not exists idx_salary_revisions_employee_status
  on public.salary_revision_history(employee_code, approval_status, effective_date desc);

alter table public.salary_structures enable row level security;
alter table public.salary_structure_components enable row level security;
alter table public.employee_salary_assignments enable row level security;
alter table public.salary_revision_history enable row level security;

do $$
begin
  if not exists (select 1 from pg_policies where schemaname = 'public' and tablename = 'salary_structures' and policyname = 'service role erp access') then
    create policy "service role erp access" on public.salary_structures for all to service_role using (true) with check (true);
  end if;
  if not exists (select 1 from pg_policies where schemaname = 'public' and tablename = 'salary_structure_components' and policyname = 'service role erp access') then
    create policy "service role erp access" on public.salary_structure_components for all to service_role using (true) with check (true);
  end if;
  if not exists (select 1 from pg_policies where schemaname = 'public' and tablename = 'employee_salary_assignments' and policyname = 'service role erp access') then
    create policy "service role erp access" on public.employee_salary_assignments for all to service_role using (true) with check (true);
  end if;
  if not exists (select 1 from pg_policies where schemaname = 'public' and tablename = 'salary_revision_history' and policyname = 'service role erp access') then
    create policy "service role erp access" on public.salary_revision_history for all to service_role using (true) with check (true);
  end if;
end $$;

drop trigger if exists set_salary_structures_updated_at on public.salary_structures;
create trigger set_salary_structures_updated_at before update on public.salary_structures for each row execute function public.set_updated_at();

drop trigger if exists set_salary_structure_components_updated_at on public.salary_structure_components;
create trigger set_salary_structure_components_updated_at before update on public.salary_structure_components for each row execute function public.set_updated_at();

drop trigger if exists set_employee_salary_assignments_updated_at on public.employee_salary_assignments;
create trigger set_employee_salary_assignments_updated_at before update on public.employee_salary_assignments for each row execute function public.set_updated_at();

drop trigger if exists set_salary_revision_history_updated_at on public.salary_revision_history;
create trigger set_salary_revision_history_updated_at before update on public.salary_revision_history for each row execute function public.set_updated_at();
