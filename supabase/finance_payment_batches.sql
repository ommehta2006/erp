-- FactoryPulse Finance Payroll Payment Batches
-- Run once in Supabase SQL Editor before using /finance/payments.
-- This file is self-contained: it creates payroll_runs and salary_slips first
-- because payment batches and finance dashboards depend on those relations.

create extension if not exists pgcrypto;

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create table if not exists public.payment_batches (
  id uuid primary key default gen_random_uuid(),
  batch_id text unique,
  payroll_run text not null,
  payment_date text not null,
  payment_method text not null default 'Bank Transfer',
  total_amount text not null default '0',
  bank_file_reference text,
  payment_status text not null default 'Payment Processing',
  status text not null default 'Payment Processing',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint payment_batches_status_check
    check (payment_status in ('Payment Processing', 'Paid', 'Cancelled', 'Reversed'))
);

create table if not exists public.payroll_runs (
  id uuid primary key default gen_random_uuid(),
  run_no text,
  period text,
  department text,
  gross_pay text,
  deductions text,
  net_pay text,
  approval_status text,
  status text not null default 'Open',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.salary_slips (
  id uuid primary key default gen_random_uuid(),
  employee_code text,
  period text,
  gross_pay text,
  deductions text,
  net_pay text,
  payment_date text,
  status text not null default 'Draft',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.salary_slips
  add column if not exists employee_code text,
  add column if not exists period text,
  add column if not exists gross_pay text,
  add column if not exists deductions text,
  add column if not exists net_pay text,
  add column if not exists payment_date text,
  add column if not exists status text not null default 'Draft',
  add column if not exists created_at timestamptz not null default now(),
  add column if not exists updated_at timestamptz not null default now();

create index if not exists idx_payment_batches_payroll_run
  on public.payment_batches(payroll_run);

create index if not exists idx_payment_batches_status_updated
  on public.payment_batches(payment_status, status, updated_at desc);

create index if not exists idx_payment_batches_payment_date
  on public.payment_batches(payment_date);

create index if not exists idx_payroll_runs_period_status
  on public.payroll_runs(period, status, approval_status);

create index if not exists idx_salary_slips_employee_period
  on public.salary_slips(employee_code, period, status);

create index if not exists idx_salary_slips_payment_status
  on public.salary_slips(payment_date, status);

alter table public.payment_batches enable row level security;

do $$
begin
  if not exists (
    select 1
    from pg_policies
    where schemaname = 'public'
      and tablename = 'payment_batches'
      and policyname = 'service role erp access'
  ) then
    create policy "service role erp access"
      on public.payment_batches
      for all
      to service_role
      using (true)
      with check (true);
  end if;
end $$;

drop trigger if exists set_payment_batches_updated_at on public.payment_batches;
create trigger set_payment_batches_updated_at
  before update on public.payment_batches
  for each row execute function public.set_updated_at();

drop trigger if exists set_payroll_runs_updated_at on public.payroll_runs;
create trigger set_payroll_runs_updated_at
  before update on public.payroll_runs
  for each row execute function public.set_updated_at();

drop trigger if exists set_salary_slips_updated_at on public.salary_slips;
create trigger set_salary_slips_updated_at
  before update on public.salary_slips
  for each row execute function public.set_updated_at();

alter table public.salary_slips enable row level security;

do $$
begin
  if not exists (
    select 1
    from pg_policies
    where schemaname = 'public'
      and tablename = 'salary_slips'
      and policyname = 'service role erp access'
  ) then
    create policy "service role erp access"
      on public.salary_slips
      for all
      to service_role
      using (true)
      with check (true);
  end if;
end $$;

alter table public.payroll_runs enable row level security;

do $$
begin
  if not exists (
    select 1
    from pg_policies
    where schemaname = 'public'
      and tablename = 'payroll_runs'
      and policyname = 'service role erp access'
  ) then
    create policy "service role erp access"
      on public.payroll_runs
      for all
      to service_role
      using (true)
      with check (true);
  end if;
end $$;
