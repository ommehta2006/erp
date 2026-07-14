-- FactoryPulse Finance Payroll Payment Batches
-- Run in Supabase SQL Editor before using /finance/payments if payment_batches is missing.

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

create index if not exists idx_payment_batches_payroll_run
  on public.payment_batches(payroll_run);

create index if not exists idx_payment_batches_status_updated
  on public.payment_batches(payment_status, status, updated_at desc);

create index if not exists idx_payment_batches_payment_date
  on public.payment_batches(payment_date);

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
