-- FactoryPulse HR Leave Policy Accrual, Carry Forward, Expiry, and Encashment
-- Run in Supabase SQL Editor before using the advanced leave policy controls.

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create table if not exists public.leave_policies (
  id uuid primary key default gen_random_uuid(),
  policy_name text not null,
  leave_type text not null,
  accrual_rule text,
  carry_forward_rule text,
  negative_balance_allowed text not null default 'false',
  approval_levels text,
  payroll_impact text not null default 'Paid',
  status text not null default 'Active',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.leave_allocations (
  id uuid primary key default gen_random_uuid(),
  allocation_id text unique,
  employee_code text not null,
  leave_type text not null,
  period text not null,
  allocated_days text not null default '0',
  used_days text not null default '0',
  available_days text not null default '0',
  expiry_date text,
  status text not null default 'Active',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_leave_policies_type_status
  on public.leave_policies(leave_type, status, updated_at desc);

create index if not exists idx_leave_allocations_employee_period
  on public.leave_allocations(employee_code, leave_type, period, status);

create index if not exists idx_leave_allocations_expiry
  on public.leave_allocations(expiry_date, status);

alter table public.leave_policies enable row level security;
alter table public.leave_allocations enable row level security;
alter table public.payroll_adjustments enable row level security;

do $$
declare
  table_name text;
begin
  foreach table_name in array array['leave_policies', 'leave_allocations', 'payroll_adjustments']
  loop
    if not exists (
      select 1
      from pg_policies
      where schemaname = 'public'
        and tablename = table_name
        and policyname = 'service role erp access'
    ) then
      execute format(
        'create policy "service role erp access" on public.%I for all to service_role using (true) with check (true)',
        table_name
      );
    end if;
  end loop;
end $$;

drop trigger if exists set_leave_policies_updated_at on public.leave_policies;
create trigger set_leave_policies_updated_at
  before update on public.leave_policies
  for each row execute function public.set_updated_at();

drop trigger if exists set_leave_allocations_updated_at on public.leave_allocations;
create trigger set_leave_allocations_updated_at
  before update on public.leave_allocations
  for each row execute function public.set_updated_at();
