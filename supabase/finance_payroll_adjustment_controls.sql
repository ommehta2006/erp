-- FactoryPulse Finance Payroll Adjustment Controls
-- Run in Supabase SQL Editor before using /finance/adjustments if these columns/tables are missing.

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create table if not exists public.payroll_adjustments (
  id uuid primary key default gen_random_uuid(),
  adjustment_id text unique,
  employee_code text not null,
  payroll_month text not null,
  adjustment_type text not null,
  addition_or_deduction text not null,
  amount text not null,
  calculation_method text,
  quantity text,
  rate text,
  reason text not null,
  policy_reference text not null,
  supporting_attachment text,
  requested_by text,
  approval_status text not null default 'Pending Approval',
  approved_by text,
  rejected_by text,
  approval_remarks text,
  payroll_inclusion_status text not null default 'Pending Approval',
  limit_check text,
  duplicate_key text,
  reversal_of text,
  status text not null default 'Pending Approval',
  created_time text,
  updated_time text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint payroll_adjustments_direction_check
    check (addition_or_deduction in ('Addition', 'Deduction')),
  constraint payroll_adjustments_approval_check
    check (approval_status in ('Pending Approval', 'Approved', 'Rejected', 'Reversed', 'Cancelled'))
);

alter table public.payroll_adjustments
  add column if not exists supporting_attachment text,
  add column if not exists rejected_by text,
  add column if not exists limit_check text,
  add column if not exists duplicate_key text,
  add column if not exists reversal_of text,
  add column if not exists created_time text,
  add column if not exists updated_time text;

create table if not exists public.payroll_approvals (
  id uuid primary key default gen_random_uuid(),
  approval_id text unique,
  payroll_run text,
  approver text,
  decision text,
  remarks text,
  decided_at text,
  status text not null default 'Open',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_payroll_adjustments_employee_month
  on public.payroll_adjustments(employee_code, payroll_month, updated_at desc);

create index if not exists idx_payroll_adjustments_status_month
  on public.payroll_adjustments(approval_status, payroll_month, updated_at desc);

create index if not exists idx_payroll_adjustments_duplicate_key
  on public.payroll_adjustments(duplicate_key)
  where approval_status not in ('Rejected', 'Reversed', 'Cancelled');

create unique index if not exists uq_payroll_adjustments_active_duplicate_key
  on public.payroll_adjustments(duplicate_key)
  where duplicate_key is not null
    and duplicate_key <> ''
    and approval_status not in ('Rejected', 'Reversed', 'Cancelled');

create index if not exists idx_payroll_approvals_run_decision
  on public.payroll_approvals(payroll_run, decision, updated_at desc);

alter table public.payroll_adjustments enable row level security;
alter table public.payroll_approvals enable row level security;

do $$
begin
  if not exists (
    select 1 from pg_policies
    where schemaname = 'public'
      and tablename = 'payroll_adjustments'
      and policyname = 'service role erp access'
  ) then
    create policy "service role erp access"
      on public.payroll_adjustments
      for all
      to service_role
      using (true)
      with check (true);
  end if;

  if not exists (
    select 1 from pg_policies
    where schemaname = 'public'
      and tablename = 'payroll_approvals'
      and policyname = 'service role erp access'
  ) then
    create policy "service role erp access"
      on public.payroll_approvals
      for all
      to service_role
      using (true)
      with check (true);
  end if;
end $$;

drop trigger if exists set_payroll_adjustments_updated_at on public.payroll_adjustments;
create trigger set_payroll_adjustments_updated_at
  before update on public.payroll_adjustments
  for each row execute function public.set_updated_at();

drop trigger if exists set_payroll_approvals_updated_at on public.payroll_approvals;
create trigger set_payroll_approvals_updated_at
  before update on public.payroll_approvals
  for each row execute function public.set_updated_at();
