-- FactoryPulse Finance Payroll Policy Settings
-- Run in Supabase SQL Editor before using /finance/settings if payroll_policies is missing.

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create table if not exists public.payroll_policies (
  id uuid primary key default gen_random_uuid(),
  policy_id text unique,
  policy_name text not null,
  proration_method text not null default 'Calendar Day',
  fixed_divisor text,
  rounding_rule text,
  max_adjustment_amount text not null default '50000',
  role_adjustment_limits text,
  retroactive_months_allowed text not null default '2',
  approval_required text not null default 'true',
  lock_after_approval text not null default 'true',
  allow_reversal_after_lock text not null default 'true',
  adjustment_categories text,
  statutory_notes text,
  effective_start_date text,
  effective_end_date text,
  created_by text,
  updated_by text,
  approval_status text not null default 'Approved',
  status text not null default 'Active',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint payroll_policies_proration_check
    check (proration_method in ('Calendar Day', 'Working Day', 'Fixed Divisor', 'Organization Specific Formula')),
  constraint payroll_policies_approval_check
    check (approval_status in ('Draft', 'Pending Approval', 'Approved', 'Rejected'))
);

create index if not exists idx_payroll_policies_status_updated
  on public.payroll_policies(status, approval_status, updated_at desc);

create index if not exists idx_payroll_policies_effective_dates
  on public.payroll_policies(effective_start_date, effective_end_date);

alter table public.payroll_policies enable row level security;

do $$
begin
  if not exists (
    select 1
    from pg_policies
    where schemaname = 'public'
      and tablename = 'payroll_policies'
      and policyname = 'service role erp access'
  ) then
    create policy "service role erp access"
      on public.payroll_policies
      for all
      to service_role
      using (true)
      with check (true);
  end if;
end $$;

drop trigger if exists set_payroll_policies_updated_at on public.payroll_policies;
create trigger set_payroll_policies_updated_at
  before update on public.payroll_policies
  for each row execute function public.set_updated_at();
