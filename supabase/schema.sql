create table if not exists records (
  id uuid primary key,
  resource text not null,
  data jsonb not null,
  status text not null,
  created_at bigint not null,
  updated_at bigint not null
);
create index if not exists idx_records_resource on records(resource, updated_at desc);
