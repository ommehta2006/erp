-- FactoryPulse Finance Statutory Payroll Rules
-- Run in Supabase SQL Editor before using /finance/statutory if payroll_statutory_rules is missing.

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create table if not exists public.payroll_statutory_rules (
  id uuid primary key default gen_random_uuid(),
  rule_id text unique,
  rule_name text not null,
  component_name text not null,
  deduction_type text not null default 'Percentage',
  calculation_base text not null default 'Gross Pay',
  rate_percent text,
  fixed_amount text,
  monthly_cap text,
  annual_exemption text,
  employee_min_gross text,
  employee_max_gross text,
  slab_config text,
  jurisdiction text,
  employer_contribution text not null default 'false',
  employee_contribution text not null default 'true',
  effective_start_date text,
  effective_end_date text,
  created_by text,
  approved_by text,
  approval_status text not null default 'Approved',
  status text not null default 'Active',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint payroll_statutory_rules_type_check
    check (deduction_type in ('Fixed', 'Percentage', 'Slab')),
  constraint payroll_statutory_rules_base_check
    check (calculation_base in ('Gross Pay', 'Basic Salary', 'Net Before Statutory')),
  constraint payroll_statutory_rules_approval_check
    check (approval_status in ('Draft', 'Pending Approval', 'Approved', 'Rejected'))
);

create index if not exists idx_payroll_statutory_rules_status
  on public.payroll_statutory_rules(status, approval_status, updated_at desc);

create index if not exists idx_payroll_statutory_rules_effective_dates
  on public.payroll_statutory_rules(effective_start_date, effective_end_date);

create index if not exists idx_payroll_statutory_rules_jurisdiction
  on public.payroll_statutory_rules(jurisdiction, component_name);

alter table public.payroll_statutory_rules enable row level security;

do $$
begin
  if not exists (
    select 1
    from pg_policies
    where schemaname = 'public'
      and tablename = 'payroll_statutory_rules'
      and policyname = 'service role erp access'
  ) then
    create policy "service role erp access"
      on public.payroll_statutory_rules
      for all
      to service_role
      using (true)
      with check (true);
  end if;
end $$;

drop trigger if exists set_payroll_statutory_rules_updated_at on public.payroll_statutory_rules;
create trigger set_payroll_statutory_rules_updated_at
  before update on public.payroll_statutory_rules
  for each row execute function public.set_updated_at();
