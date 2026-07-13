-- FactoryPulse ERP Supabase schema
-- Run this file in Supabase SQL Editor before connecting Railway.

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

-- Generic compatibility table used by older API builds.
create table if not exists public.records (
  id uuid primary key default gen_random_uuid(),
  resource text not null,
  data jsonb not null default '{}'::jsonb,
  status text not null default 'Open',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists idx_records_resource_updated_at on public.records(resource, updated_at desc);
alter table public.records enable row level security;

-- Platform/catalog tables.
create table if not exists public.erp_departments (
  id text primary key,
  name text not null,
  sort_order integer not null default 0,
  status text not null default 'Active',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create table if not exists public.erp_modules (
  department_id text not null references public.erp_departments(id) on delete cascade,
  resource text not null,
  label text not null,
  fields jsonb not null default '[]'::jsonb,
  sort_order integer not null default 0,
  status text not null default 'Active',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key (department_id, resource)
);
create table if not exists public.app_users (
  id uuid primary key default gen_random_uuid(),
  email text not null unique,
  password_hash text,
  full_name text,
  role text not null default 'FACTORY_USER',
  department_id text references public.erp_departments(id),
  status text not null default 'Active',
  failed_login_count integer not null default 0,
  locked_until bigint,
  last_login_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create table if not exists public.audit_events (
  id uuid primary key default gen_random_uuid(),
  actor_email text,
  action text not null,
  resource text,
  record_id uuid,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create table if not exists public.uploaded_files (
  id uuid primary key default gen_random_uuid(),
  resource text,
  record_id uuid,
  file_name text not null,
  content_type text,
  size_bytes bigint,
  storage_path text not null,
  uploaded_by text,
  status text not null default 'Active',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create table if not exists public.integration_events (
  id uuid primary key default gen_random_uuid(),
  provider text not null,
  event_type text not null,
  payload jsonb not null default '{}'::jsonb,
  status text not null default 'Pending',
  error_message text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists idx_erp_modules_department on public.erp_modules(department_id, sort_order);
create index if not exists idx_app_users_department on public.app_users(department_id);
create index if not exists idx_app_users_email_status on public.app_users(email, status);
create index if not exists idx_audit_events_resource on public.audit_events(resource, created_at desc);
create index if not exists idx_uploaded_files_record on public.uploaded_files(resource, record_id);
create index if not exists idx_integration_events_status on public.integration_events(status, created_at desc);
alter table public.erp_departments enable row level security;
alter table public.erp_modules enable row level security;
alter table public.app_users enable row level security;
alter table public.audit_events enable row level security;
alter table public.uploaded_files enable row level security;
alter table public.integration_events enable row level security;

-- HR & Employee
create table if not exists public.employees (
  id uuid primary key default gen_random_uuid(),
  employee_code text,
  full_name text,
  department text,
  role text,
  phone text,
  email text,
  shift text,
  status text not null default 'Open',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create table if not exists public.attendance (
  id uuid primary key default gen_random_uuid(),
  employee_code text,
  date text,
  shift text,
  check_in text,
  check_out text,
  gps_area text,
  status text not null default 'Open',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create table if not exists public.leave_requests (
  id uuid primary key default gen_random_uuid(),
  employee_code text,
  leave_type text,
  from_date text,
  to_date text,
  reason text,
  status text not null default 'Open',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create table if not exists public.shifts (
  id uuid primary key default gen_random_uuid(),
  name text,
  start_time text,
  end_time text,
  department text,
  supervisor text,
  status text not null default 'Open',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create table if not exists public.departments (
  id uuid primary key default gen_random_uuid(),
  name text,
  head text,
  cost_center text,
  location text,
  status text not null default 'Open',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
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
create table if not exists public.recruitment (
  id uuid primary key default gen_random_uuid(),
  candidate_no text,
  full_name text,
  department text,
  position text,
  stage text,
  owner text,
  status text not null default 'Open',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create table if not exists public.performance_reviews (
  id uuid primary key default gen_random_uuid(),
  review_no text,
  employee_code text,
  period text,
  manager text,
  rating text,
  summary text,
  status text not null default 'Open',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create table if not exists public.training_records (
  id uuid primary key default gen_random_uuid(),
  training_no text,
  employee_code text,
  course text,
  trainer text,
  completion_date text,
  score text,
  status text not null default 'Open',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create table if not exists public.expense_claims (
  id uuid primary key default gen_random_uuid(),
  claim_no text,
  employee_code text,
  department text,
  amount text,
  category text,
  approver text,
  status text not null default 'Open',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create table if not exists public.visitor_passes (
  id uuid primary key default gen_random_uuid(),
  pass_no text,
  visitor_name text,
  company text,
  host_employee text,
  area text,
  check_in text,
  check_out text,
  status text not null default 'Open',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- Finance & Accounts
create table if not exists public.invoices (
  id uuid primary key default gen_random_uuid(),
  invoice_no text,
  party text,
  invoice_type text,
  amount text,
  due_date text,
  payment_status text,
  status text not null default 'Open',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create table if not exists public.purchase_orders (
  id uuid primary key default gen_random_uuid(),
  po_no text,
  supplier text,
  amount text,
  delivery_date text,
  department text,
  status text not null default 'Open',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create table if not exists public.sales_orders (
  id uuid primary key default gen_random_uuid(),
  so_no text,
  customer text,
  product text,
  quantity text,
  amount text,
  dispatch_date text,
  status text not null default 'Open',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create table if not exists public.budgets (
  id uuid primary key default gen_random_uuid(),
  budget_no text,
  department text,
  period text,
  allocated_amount text,
  used_amount text,
  owner text,
  status text not null default 'Open',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create table if not exists public.tax_records (
  id uuid primary key default gen_random_uuid(),
  tax_no text,
  tax_type text,
  period text,
  amount text,
  jurisdiction text,
  filing_status text,
  status text not null default 'Open',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create table if not exists public.farmer_payments (
  id uuid primary key default gen_random_uuid(),
  payment_no text,
  farmer_code text,
  season text,
  tonnage text,
  rate text,
  amount text,
  status text not null default 'Open',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create table if not exists public.approvals (
  id uuid primary key default gen_random_uuid(),
  request_type text,
  request_ref text,
  requested_by text,
  approver text,
  risk text,
  decision text,
  status text not null default 'Open',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- Cane & Farmer
create table if not exists public.farmers (
  id uuid primary key default gen_random_uuid(),
  farmer_code text,
  full_name text,
  village text,
  mobile text,
  bank_status text,
  status text not null default 'Open',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create table if not exists public.cane_registrations (
  id uuid primary key default gen_random_uuid(),
  farmer_code text,
  plot_no text,
  village text,
  area_acres text,
  variety text,
  expected_tonnage text,
  status text not null default 'Open',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create table if not exists public.harvest_plans (
  id uuid primary key default gen_random_uuid(),
  plot_no text,
  planned_date text,
  contractor text,
  vehicle_no text,
  expected_tonnage text,
  status text not null default 'Open',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create table if not exists public.vehicles (
  id uuid primary key default gen_random_uuid(),
  vehicle_no text,
  type text,
  driver text,
  gps_device text,
  capacity_ton text,
  status text not null default 'Open',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create table if not exists public.weighbridge_tickets (
  id uuid primary key default gen_random_uuid(),
  ticket_no text,
  vehicle_no text,
  farmer_code text,
  gross_weight text,
  tare_weight text,
  net_weight text,
  quality_status text,
  status text not null default 'Open',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- Manufacturing
create table if not exists public.production_batches (
  id uuid primary key default gen_random_uuid(),
  batch_no text,
  date text,
  cane_crushed_ton text,
  sugar_bags text,
  recovery_percent text,
  molasses_ton text,
  power_kwh text,
  status text not null default 'Open',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create table if not exists public.boiler_logs (
  id uuid primary key default gen_random_uuid(),
  log_no text,
  shift text,
  steam_pressure text,
  bagasse_feed text,
  water_level text,
  operator text,
  status text not null default 'Open',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create table if not exists public.packaging_runs (
  id uuid primary key default gen_random_uuid(),
  run_no text,
  product text,
  bag_size text,
  bags_packed text,
  line text,
  supervisor text,
  status text not null default 'Open',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create table if not exists public.byproducts (
  id uuid primary key default gen_random_uuid(),
  lot_no text,
  type text,
  quantity text,
  storage_location text,
  quality_grade text,
  disposition text,
  status text not null default 'Open',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create table if not exists public.power_generation (
  id uuid primary key default gen_random_uuid(),
  shift text,
  date text,
  turbine text,
  generation_kwh text,
  export_kwh text,
  steam_pressure text,
  status text not null default 'Open',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create table if not exists public.distillery_batches (
  id uuid primary key default gen_random_uuid(),
  batch_no text,
  feedstock text,
  start_date text,
  wash_volume text,
  alcohol_percent text,
  yield_litre text,
  status text not null default 'Open',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create table if not exists public.ethanol_dispatches (
  id uuid primary key default gen_random_uuid(),
  dispatch_no text,
  buyer text,
  litres text,
  grade text,
  tanker_no text,
  invoice_no text,
  status text not null default 'Open',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create table if not exists public.energy_meters (
  id uuid primary key default gen_random_uuid(),
  meter_no text,
  area text,
  reading_date text,
  kwh text,
  operator text,
  variance text,
  status text not null default 'Open',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- Inventory & Dispatch
create table if not exists public.inventory_items (
  id uuid primary key default gen_random_uuid(),
  item_code text,
  name text,
  category text,
  warehouse text,
  quantity text,
  reorder_level text,
  status text not null default 'Open',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create table if not exists public.warehouses (
  id uuid primary key default gen_random_uuid(),
  warehouse_code text,
  name text,
  type text,
  manager text,
  capacity text,
  utilization_percent text,
  status text not null default 'Open',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create table if not exists public.dispatches (
  id uuid primary key default gen_random_uuid(),
  dispatch_no text,
  customer text,
  product text,
  vehicle_no text,
  quantity text,
  gate_pass text,
  status text not null default 'Open',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create table if not exists public.assets (
  id uuid primary key default gen_random_uuid(),
  asset_code text,
  name text,
  department text,
  criticality text,
  last_service text,
  status text not null default 'Open',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- Quality & Compliance
create table if not exists public.quality_tests (
  id uuid primary key default gen_random_uuid(),
  sample_no text,
  source text,
  brix text,
  pol text,
  purity text,
  tested_by text,
  status text not null default 'Open',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create table if not exists public.lab_instruments (
  id uuid primary key default gen_random_uuid(),
  instrument_code text,
  name text,
  lab_area text,
  calibration_due text,
  owner text,
  condition text,
  status text not null default 'Open',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create table if not exists public.compliance_register (
  id uuid primary key default gen_random_uuid(),
  compliance_no text,
  department text,
  law_or_standard text,
  owner text,
  due_date text,
  risk text,
  status text not null default 'Open',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create table if not exists public.documents (
  id uuid primary key default gen_random_uuid(),
  document_no text,
  title text,
  category text,
  owner text,
  classification text,
  expiry_date text,
  status text not null default 'Open',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create table if not exists public.incidents (
  id uuid primary key default gen_random_uuid(),
  incident_no text,
  area text,
  severity text,
  reported_by text,
  summary text,
  corrective_action text,
  status text not null default 'Open',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- Maintenance, Sales, and Admin
create table if not exists public.maintenance_work_orders (
  id uuid primary key default gen_random_uuid(),
  work_order_no text,
  asset_code text,
  priority text,
  issue text,
  assigned_to text,
  due_date text,
  status text not null default 'Open',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create table if not exists public.tasks (
  id uuid primary key default gen_random_uuid(),
  title text,
  owner text,
  department text,
  due_date text,
  priority text,
  status text not null default 'Open',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create table if not exists public.support_tickets (
  id uuid primary key default gen_random_uuid(),
  ticket_no text,
  requester text,
  category text,
  priority text,
  assigned_to text,
  summary text,
  status text not null default 'Open',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create table if not exists public.customer_portal_requests (
  id uuid primary key default gen_random_uuid(),
  request_no text,
  customer text,
  category text,
  summary text,
  assigned_to text,
  priority text,
  status text not null default 'Open',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

insert into public.erp_departments (id, name, sort_order, status) values
  ('hr', 'HR & Employee', 1, 'Active'),
  ('finance', 'Finance & Accounts', 2, 'Active'),
  ('cane', 'Cane & Farmer', 3, 'Active'),
  ('manufacturing', 'Manufacturing', 4, 'Active'),
  ('inventory', 'Inventory & Dispatch', 5, 'Active'),
  ('quality', 'Quality & Compliance', 6, 'Active'),
  ('maintenance', 'Maintenance & Assets', 7, 'Active'),
  ('sales', 'Sales & Customer', 8, 'Active'),
  ('admin', 'Administration', 9, 'Active')
on conflict (id) do update set
  name = excluded.name,
  sort_order = excluded.sort_order,
  status = excluded.status,
  updated_at = now();

insert into public.erp_modules (resource, department_id, label, fields, sort_order, status) values
  ('employees', 'hr', 'Employees', '["employee_code", "full_name", "department", "role", "phone", "email", "shift", "status"]'::jsonb, 1, 'Active'),
  ('attendance', 'hr', 'Attendance', '["employee_code", "date", "shift", "check_in", "check_out", "gps_area", "status"]'::jsonb, 2, 'Active'),
  ('leave_requests', 'hr', 'Leave Requests', '["employee_code", "leave_type", "from_date", "to_date", "reason", "status"]'::jsonb, 3, 'Active'),
  ('shifts', 'hr', 'Shifts', '["name", "start_time", "end_time", "department", "supervisor", "status"]'::jsonb, 4, 'Active'),
  ('departments', 'hr', 'Departments', '["name", "head", "cost_center", "location", "status"]'::jsonb, 5, 'Active'),
  ('payroll_runs', 'hr', 'Payroll Runs', '["run_no", "period", "department", "gross_pay", "deductions", "net_pay", "approval_status", "status"]'::jsonb, 6, 'Active'),
  ('recruitment', 'hr', 'Recruitment', '["candidate_no", "full_name", "department", "position", "stage", "owner", "status"]'::jsonb, 7, 'Active'),
  ('performance_reviews', 'hr', 'Performance Reviews', '["review_no", "employee_code", "period", "manager", "rating", "summary", "status"]'::jsonb, 8, 'Active'),
  ('training_records', 'hr', 'Training Records', '["training_no", "employee_code", "course", "trainer", "completion_date", "score", "status"]'::jsonb, 9, 'Active'),
  ('expense_claims', 'hr', 'Expense Claims', '["claim_no", "employee_code", "department", "amount", "category", "approver", "status"]'::jsonb, 10, 'Active'),
  ('visitor_passes', 'hr', 'Visitor Passes', '["pass_no", "visitor_name", "company", "host_employee", "area", "check_in", "check_out", "status"]'::jsonb, 11, 'Active'),
  ('invoices', 'finance', 'Invoices', '["invoice_no", "party", "invoice_type", "amount", "due_date", "payment_status", "status"]'::jsonb, 12, 'Active'),
  ('purchase_orders', 'finance', 'Purchase Orders', '["po_no", "supplier", "amount", "delivery_date", "department", "status"]'::jsonb, 13, 'Active'),
  ('sales_orders', 'finance', 'Sales Orders', '["so_no", "customer", "product", "quantity", "amount", "dispatch_date", "status"]'::jsonb, 14, 'Active'),
  ('payroll_runs', 'finance', 'Payroll Runs', '["run_no", "period", "department", "gross_pay", "deductions", "net_pay", "approval_status", "status"]'::jsonb, 15, 'Active'),
  ('budgets', 'finance', 'Budgets', '["budget_no", "department", "period", "allocated_amount", "used_amount", "owner", "status"]'::jsonb, 16, 'Active'),
  ('tax_records', 'finance', 'Tax Records', '["tax_no", "tax_type", "period", "amount", "jurisdiction", "filing_status", "status"]'::jsonb, 17, 'Active'),
  ('farmer_payments', 'finance', 'Farmer Payments', '["payment_no", "farmer_code", "season", "tonnage", "rate", "amount", "status"]'::jsonb, 18, 'Active'),
  ('approvals', 'finance', 'Approvals', '["request_type", "request_ref", "requested_by", "approver", "risk", "decision", "status"]'::jsonb, 19, 'Active'),
  ('farmers', 'cane', 'Farmers', '["farmer_code", "full_name", "village", "mobile", "bank_status", "status"]'::jsonb, 20, 'Active'),
  ('cane_registrations', 'cane', 'Cane Registrations', '["farmer_code", "plot_no", "village", "area_acres", "variety", "expected_tonnage", "status"]'::jsonb, 21, 'Active'),
  ('harvest_plans', 'cane', 'Harvest Plans', '["plot_no", "planned_date", "contractor", "vehicle_no", "expected_tonnage", "status"]'::jsonb, 22, 'Active'),
  ('vehicles', 'cane', 'Vehicles', '["vehicle_no", "type", "driver", "gps_device", "capacity_ton", "status"]'::jsonb, 23, 'Active'),
  ('weighbridge_tickets', 'cane', 'Weighbridge Tickets', '["ticket_no", "vehicle_no", "farmer_code", "gross_weight", "tare_weight", "net_weight", "quality_status", "status"]'::jsonb, 24, 'Active'),
  ('farmer_payments', 'cane', 'Farmer Payments', '["payment_no", "farmer_code", "season", "tonnage", "rate", "amount", "status"]'::jsonb, 25, 'Active'),
  ('production_batches', 'manufacturing', 'Production Batches', '["batch_no", "date", "cane_crushed_ton", "sugar_bags", "recovery_percent", "molasses_ton", "power_kwh", "status"]'::jsonb, 26, 'Active'),
  ('boiler_logs', 'manufacturing', 'Boiler Logs', '["log_no", "shift", "steam_pressure", "bagasse_feed", "water_level", "operator", "status"]'::jsonb, 27, 'Active'),
  ('packaging_runs', 'manufacturing', 'Packaging Runs', '["run_no", "product", "bag_size", "bags_packed", "line", "supervisor", "status"]'::jsonb, 28, 'Active'),
  ('byproducts', 'manufacturing', 'Byproducts', '["lot_no", "type", "quantity", "storage_location", "quality_grade", "disposition", "status"]'::jsonb, 29, 'Active'),
  ('power_generation', 'manufacturing', 'Power Generation', '["shift", "date", "turbine", "generation_kwh", "export_kwh", "steam_pressure", "status"]'::jsonb, 30, 'Active'),
  ('distillery_batches', 'manufacturing', 'Distillery Batches', '["batch_no", "feedstock", "start_date", "wash_volume", "alcohol_percent", "yield_litre", "status"]'::jsonb, 31, 'Active'),
  ('ethanol_dispatches', 'manufacturing', 'Ethanol Dispatches', '["dispatch_no", "buyer", "litres", "grade", "tanker_no", "invoice_no", "status"]'::jsonb, 32, 'Active'),
  ('energy_meters', 'manufacturing', 'Energy Meters', '["meter_no", "area", "reading_date", "kwh", "operator", "variance", "status"]'::jsonb, 33, 'Active'),
  ('inventory_items', 'inventory', 'Inventory Items', '["item_code", "name", "category", "warehouse", "quantity", "reorder_level", "status"]'::jsonb, 34, 'Active'),
  ('warehouses', 'inventory', 'Warehouses', '["warehouse_code", "name", "type", "manager", "capacity", "utilization_percent", "status"]'::jsonb, 35, 'Active'),
  ('dispatches', 'inventory', 'Dispatches', '["dispatch_no", "customer", "product", "vehicle_no", "quantity", "gate_pass", "status"]'::jsonb, 36, 'Active'),
  ('assets', 'inventory', 'Assets', '["asset_code", "name", "department", "criticality", "last_service", "status"]'::jsonb, 37, 'Active'),
  ('purchase_orders', 'inventory', 'Purchase Orders', '["po_no", "supplier", "amount", "delivery_date", "department", "status"]'::jsonb, 38, 'Active'),
  ('quality_tests', 'quality', 'Quality Tests', '["sample_no", "source", "brix", "pol", "purity", "tested_by", "status"]'::jsonb, 39, 'Active'),
  ('lab_instruments', 'quality', 'Lab Instruments', '["instrument_code", "name", "lab_area", "calibration_due", "owner", "condition", "status"]'::jsonb, 40, 'Active'),
  ('compliance_register', 'quality', 'Compliance Register', '["compliance_no", "department", "law_or_standard", "owner", "due_date", "risk", "status"]'::jsonb, 41, 'Active'),
  ('documents', 'quality', 'Documents', '["document_no", "title", "category", "owner", "classification", "expiry_date", "status"]'::jsonb, 42, 'Active'),
  ('incidents', 'quality', 'Incidents', '["incident_no", "area", "severity", "reported_by", "summary", "corrective_action", "status"]'::jsonb, 43, 'Active'),
  ('maintenance_work_orders', 'maintenance', 'Maintenance Work Orders', '["work_order_no", "asset_code", "priority", "issue", "assigned_to", "due_date", "status"]'::jsonb, 44, 'Active'),
  ('assets', 'maintenance', 'Assets', '["asset_code", "name", "department", "criticality", "last_service", "status"]'::jsonb, 45, 'Active'),
  ('tasks', 'maintenance', 'Tasks', '["title", "owner", "department", "due_date", "priority", "status"]'::jsonb, 46, 'Active'),
  ('support_tickets', 'maintenance', 'Support Tickets', '["ticket_no", "requester", "category", "priority", "assigned_to", "summary", "status"]'::jsonb, 47, 'Active'),
  ('sales_orders', 'sales', 'Sales Orders', '["so_no", "customer", "product", "quantity", "amount", "dispatch_date", "status"]'::jsonb, 48, 'Active'),
  ('dispatches', 'sales', 'Dispatches', '["dispatch_no", "customer", "product", "vehicle_no", "quantity", "gate_pass", "status"]'::jsonb, 49, 'Active'),
  ('invoices', 'sales', 'Invoices', '["invoice_no", "party", "invoice_type", "amount", "due_date", "payment_status", "status"]'::jsonb, 50, 'Active'),
  ('customer_portal_requests', 'sales', 'Customer Portal Requests', '["request_no", "customer", "category", "summary", "assigned_to", "priority", "status"]'::jsonb, 51, 'Active'),
  ('approvals', 'admin', 'Approvals', '["request_type", "request_ref", "requested_by", "approver", "risk", "decision", "status"]'::jsonb, 52, 'Active'),
  ('documents', 'admin', 'Documents', '["document_no", "title", "category", "owner", "classification", "expiry_date", "status"]'::jsonb, 53, 'Active'),
  ('tasks', 'admin', 'Tasks', '["title", "owner", "department", "due_date", "priority", "status"]'::jsonb, 54, 'Active'),
  ('support_tickets', 'admin', 'Support Tickets', '["ticket_no", "requester", "category", "priority", "assigned_to", "summary", "status"]'::jsonb, 55, 'Active'),
  ('incidents', 'admin', 'Incidents', '["incident_no", "area", "severity", "reported_by", "summary", "corrective_action", "status"]'::jsonb, 56, 'Active')
on conflict (department_id, resource) do update set
  label = excluded.label,
  fields = excluded.fields,
  sort_order = excluded.sort_order,
  status = excluded.status,
  updated_at = now();

create index if not exists idx_employees_updated_at on public.employees(updated_at desc);
create index if not exists idx_attendance_updated_at on public.attendance(updated_at desc);
create index if not exists idx_leave_requests_updated_at on public.leave_requests(updated_at desc);
create index if not exists idx_shifts_updated_at on public.shifts(updated_at desc);
create index if not exists idx_departments_updated_at on public.departments(updated_at desc);
create index if not exists idx_payroll_runs_updated_at on public.payroll_runs(updated_at desc);
create index if not exists idx_recruitment_updated_at on public.recruitment(updated_at desc);
create index if not exists idx_performance_reviews_updated_at on public.performance_reviews(updated_at desc);
create index if not exists idx_training_records_updated_at on public.training_records(updated_at desc);
create index if not exists idx_expense_claims_updated_at on public.expense_claims(updated_at desc);
create index if not exists idx_visitor_passes_updated_at on public.visitor_passes(updated_at desc);
create index if not exists idx_invoices_updated_at on public.invoices(updated_at desc);
create index if not exists idx_purchase_orders_updated_at on public.purchase_orders(updated_at desc);
create index if not exists idx_sales_orders_updated_at on public.sales_orders(updated_at desc);
create index if not exists idx_budgets_updated_at on public.budgets(updated_at desc);
create index if not exists idx_tax_records_updated_at on public.tax_records(updated_at desc);
create index if not exists idx_farmer_payments_updated_at on public.farmer_payments(updated_at desc);
create index if not exists idx_approvals_updated_at on public.approvals(updated_at desc);
create index if not exists idx_farmers_updated_at on public.farmers(updated_at desc);
create index if not exists idx_cane_registrations_updated_at on public.cane_registrations(updated_at desc);
create index if not exists idx_harvest_plans_updated_at on public.harvest_plans(updated_at desc);
create index if not exists idx_vehicles_updated_at on public.vehicles(updated_at desc);
create index if not exists idx_weighbridge_tickets_updated_at on public.weighbridge_tickets(updated_at desc);
create index if not exists idx_production_batches_updated_at on public.production_batches(updated_at desc);
create index if not exists idx_boiler_logs_updated_at on public.boiler_logs(updated_at desc);
create index if not exists idx_packaging_runs_updated_at on public.packaging_runs(updated_at desc);
create index if not exists idx_byproducts_updated_at on public.byproducts(updated_at desc);
create index if not exists idx_power_generation_updated_at on public.power_generation(updated_at desc);
create index if not exists idx_distillery_batches_updated_at on public.distillery_batches(updated_at desc);
create index if not exists idx_ethanol_dispatches_updated_at on public.ethanol_dispatches(updated_at desc);
create index if not exists idx_energy_meters_updated_at on public.energy_meters(updated_at desc);
create index if not exists idx_inventory_items_updated_at on public.inventory_items(updated_at desc);
create index if not exists idx_warehouses_updated_at on public.warehouses(updated_at desc);
create index if not exists idx_dispatches_updated_at on public.dispatches(updated_at desc);
create index if not exists idx_assets_updated_at on public.assets(updated_at desc);
create index if not exists idx_quality_tests_updated_at on public.quality_tests(updated_at desc);
create index if not exists idx_lab_instruments_updated_at on public.lab_instruments(updated_at desc);
create index if not exists idx_compliance_register_updated_at on public.compliance_register(updated_at desc);
create index if not exists idx_documents_updated_at on public.documents(updated_at desc);
create index if not exists idx_incidents_updated_at on public.incidents(updated_at desc);
create index if not exists idx_maintenance_work_orders_updated_at on public.maintenance_work_orders(updated_at desc);
create index if not exists idx_tasks_updated_at on public.tasks(updated_at desc);
create index if not exists idx_support_tickets_updated_at on public.support_tickets(updated_at desc);
create index if not exists idx_customer_portal_requests_updated_at on public.customer_portal_requests(updated_at desc);

do $$
declare
  table_name text;
  table_names text[] := array[
    'records','erp_departments','erp_modules','app_users','uploaded_files','integration_events',
    'employees','attendance','leave_requests','shifts','departments','payroll_runs','recruitment',
    'performance_reviews','training_records','expense_claims','visitor_passes','invoices','purchase_orders',
    'sales_orders','budgets','tax_records','farmer_payments','approvals','farmers','cane_registrations',
    'harvest_plans','vehicles','weighbridge_tickets','production_batches','boiler_logs','packaging_runs',
    'byproducts','power_generation','distillery_batches','ethanol_dispatches','energy_meters','inventory_items',
    'warehouses','dispatches','assets','quality_tests','lab_instruments','compliance_register','documents',
    'incidents','maintenance_work_orders','tasks','support_tickets','customer_portal_requests'
  ];
begin
  foreach table_name in array table_names loop
    execute format('alter table public.%I enable row level security', table_name);
    execute format('drop trigger if exists trg_%I_updated_at on public.%I', table_name, table_name);
    execute format('create trigger trg_%I_updated_at before update on public.%I for each row execute function public.set_updated_at()', table_name, table_name);
  end loop;
end $$;
