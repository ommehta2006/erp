-- FactoryPulse employee notifications and self-service salary support
-- Run in Supabase SQL Editor if the notifications table/indexes are missing.

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create table if not exists public.notifications (
  id uuid primary key default gen_random_uuid(),
  notification_id text,
  recipient_employee_code text,
  recipient_email text,
  notification_type text,
  title text,
  message text,
  read_status text,
  delivery_status text,
  status text not null default 'Open',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_notifications_employee_read
  on public.notifications(recipient_employee_code, read_status, updated_at desc);

create index if not exists idx_notifications_email_read
  on public.notifications(lower(coalesce(recipient_email, '')), read_status, updated_at desc);

create index if not exists idx_notifications_type_status
  on public.notifications(notification_type, status);

alter table public.notifications enable row level security;

do $$
begin
  if not exists (
    select 1
    from pg_policies
    where schemaname = 'public'
      and tablename = 'notifications'
      and policyname = 'service role erp access'
  ) then
    create policy "service role erp access"
      on public.notifications
      for all
      to service_role
      using (true)
      with check (true);
  end if;
end $$;

drop trigger if exists set_notifications_updated_at on public.notifications;
create trigger set_notifications_updated_at
  before update on public.notifications
  for each row execute function public.set_updated_at();
