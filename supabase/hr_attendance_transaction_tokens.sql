-- FactoryPulse Attendance Transaction Tokens
-- Run in Supabase SQL Editor before enforcing secure Day In / Day Out transaction tokens.

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create table if not exists public.attendance_transaction_tokens (
  id uuid primary key default gen_random_uuid(),
  token_id text unique,
  transaction_token_hash text not null,
  employee_code text not null,
  event_type text not null,
  location_validation_id text,
  location_event_id text,
  expires_at text not null,
  consumed_at text,
  biometric_event_id text,
  idempotency_key text,
  status text not null default 'Active',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint attendance_transaction_event_check
    check (event_type in ('day-in', 'day-out')),
  constraint attendance_transaction_status_check
    check (status in ('Active', 'Biometric Verified', 'Consumed', 'Expired', 'Cancelled'))
);

create index if not exists idx_attendance_transactions_employee_event
  on public.attendance_transaction_tokens(employee_code, event_type, status, updated_at desc);

create unique index if not exists uq_attendance_transaction_token_hash
  on public.attendance_transaction_tokens(transaction_token_hash);

create index if not exists idx_attendance_transactions_idempotency
  on public.attendance_transaction_tokens(employee_code, event_type, idempotency_key)
  where idempotency_key is not null and idempotency_key <> '';

alter table public.attendance_transaction_tokens enable row level security;

do $$
begin
  if not exists (
    select 1
    from pg_policies
    where schemaname = 'public'
      and tablename = 'attendance_transaction_tokens'
      and policyname = 'service role erp access'
  ) then
    create policy "service role erp access"
      on public.attendance_transaction_tokens
      for all
      to service_role
      using (true)
      with check (true);
  end if;
end $$;

drop trigger if exists set_attendance_transaction_tokens_updated_at on public.attendance_transaction_tokens;
create trigger set_attendance_transaction_tokens_updated_at
  before update on public.attendance_transaction_tokens
  for each row execute function public.set_updated_at();
