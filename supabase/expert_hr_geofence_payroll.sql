-- FactoryPulse expert HR, geofence, attendance, leave, payroll, audit schema.
-- Run in Supabase SQL Editor after the base schema.
-- The API can write these tables directly when Railway uses a service-role key,
-- or through the records RPC fallback when direct table writes are not available.

create schema if not exists extensions;
create extension if not exists pgcrypto with schema extensions;

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

do $$
declare
  module record;
  field_name text;
begin
  for module in
    select * from (values
      ('companies', array['company_code','name','country','tax_id','status']),
      ('branches', array['branch_code','company','name','city','state','status']),
      ('designations', array['designation_code','department','title','grade','status']),
      ('employee_private_details', array['employee_code','date_of_birth','gender','nationality','tax_identifier_ref','status']),
      ('employee_bank_details', array['employee_code','bank_name','account_last4','ifsc_or_routing','verification_status','status']),
      ('employee_documents', array['employee_code','document_type','document_no_masked','expiry_date','verification_status','status']),
      ('employee_emergency_contacts', array['employee_code','contact_name','relationship','phone','address','status']),
      ('employee_lifecycle_events', array['event_no','employee_code','event_type','effective_date','previous_value','new_value','reason','approved_by','status']),
      ('work_locations', array['location_id','company','branch','location_name','location_type','full_address','city','state','country','latitude','longitude','geofence_type','geofence_radius_meters','allowed_gps_accuracy_meters','time_zone','approval_status','status']),
      ('geofences', array['geofence_id','location_id','geofence_type','center_latitude','center_longitude','radius_meters','polygon_coordinates','allowed_accuracy_meters','boundary_version','effective_start_date','effective_end_date','approval_status','status']),
      ('geofence_versions', array['version_id','geofence_id','boundary_version','change_summary','changed_by','approved_by','effective_date','status']),
      ('geofence_polygon_points', array['point_id','geofence_id','boundary_version','point_order','latitude','longitude','status']),
      ('employee_location_assignments', array['assignment_id','employee_code','location_id','shift','effective_start_date','effective_end_date','assignment_type','approval_status','status']),
      ('employee_shift_assignments', array['assignment_id','employee_code','shift','effective_start_date','effective_end_date','approval_status','status']),
      ('shift_rosters', array['roster_id','employee_code','shift','roster_date','location_id','status']),
      ('attendance_policies', array['policy_name','late_after_time','grace_minutes','tracking_interval_minutes','background_location_required','status']),
      ('attendance_records', array['attendance_record_id','employee_code','employee_name','department','designation','company','branch','work_location','shift','attendance_date','day_in_time','day_out_time','day_in_latitude','day_in_longitude','day_out_latitude','day_out_longitude','day_in_accuracy','day_out_accuracy','day_in_distance','day_out_distance','day_in_geofence_status','day_out_geofence_status','day_in_biometric_result','day_out_biometric_result','late_duration_minutes','early_exit_minutes','gross_work_minutes','net_work_minutes','overtime_minutes','attendance_status','payroll_status','approval_status','employee_remarks','hr_remarks','source','status']),
      ('attendance_location_events', array['event_id','attendance_record_id','employee_code','event_type','latitude','longitude','accuracy','altitude','speed','provider','captured_at','received_at','device_time','server_time','geofence_id','geofence_version','distance_meters','inside_fence','tolerance_applied','mock_location_indicator','risk_score','validation_result','failure_reason','device_id','ip_address','app_version','status']),
      ('attendance_biometric_events', array['event_id','attendance_record_id','employee_code','event_type','verification_method','verification_result','assertion_reference','trusted_device_id','failure_reason','risk_flags','verified_at','status']),
      ('attendance_validation_results', array['validation_id','employee_code','event_type','location_id','geofence_id','employee_latitude','employee_longitude','geofence_latitude','geofence_longitude','distance_meters','radius_meters','inside_fence','accuracy_meters','allowed_accuracy_meters','geofence_status','validation_reason','risk_flags','server_validated_at','status']),
      ('attendance_correction_requests', array['request_id','employee_code','attendance_date','requested_day_in_time','requested_day_out_time','reason','current_record','requested_changes','manager_approval','hr_approval','final_status','status']),
      ('attendance_approvals', array['approval_id','attendance_record_id','employee_code','approval_type','approver','decision','comments','decided_at','status']),
      ('device_registrations', array['device_id','employee_code','platform','device_name','app_version','restricted_device','registered_at','approval_status','status']),
      ('device_integrity_events', array['event_id','employee_code','device_id','signal_type','risk_score','risk_flags','observed_at','status']),
      ('leave_types', array['leave_type','paid_status','requires_attachment','allow_half_day','allow_hourly','status']),
      ('leave_policies', array['policy_name','leave_type','accrual_rule','carry_forward_rule','negative_balance_allowed','approval_levels','payroll_impact','status']),
      ('leave_allocations', array['allocation_id','employee_code','leave_type','period','allocated_days','used_days','available_days','expiry_date','status']),
      ('leave_applications', array['application_id','employee_code','leave_type','start_date','end_date','half_day','total_leave_days','reason','approver','approval_status','payroll_impact','status']),
      ('leave_approvals', array['approval_id','application_id','approver','decision','remarks','decided_at','status']),
      ('holiday_calendars', array['calendar_id','company','country','state','branch','location_id','effective_year','status']),
      ('holidays', array['holiday_id','calendar_id','holiday_name','holiday_date','holiday_type','paid_status','optional_or_mandatory','payroll_impact','notes','status']),
      ('salary_structures', array['structure_id','structure_name','currency','payment_frequency','proration_method','approval_status','status']),
      ('salary_structure_components', array['component_id','structure_id','component_name','component_type','calculation_method','amount','taxable','status']),
      ('employee_salary_assignments', array['assignment_id','employee_code','structure_id','effective_date','gross_salary','ctc','approval_status','status']),
      ('salary_revision_history', array['revision_id','employee_code','structure_id','effective_date','basic_salary','allowances','deductions','gross_salary','ctc','net_salary_estimate','revision_type','previous_salary','new_salary','increase_amount','increase_percent','reason','approved_by','status']),
      ('payroll_periods', array['period_id','period_name','start_date','end_date','company','branch','attendance_close_status','payroll_status','status']),
      ('payroll_employee_results', array['result_id','payroll_run','employee_code','paid_days','present_days','paid_leave_days','unpaid_leave_days','gross_pay','deductions','net_pay','validation_status','status']),
      ('payroll_calculation_lines', array['line_id','result_id','component_name','component_type','quantity','rate','amount','formula','source','status']),
      ('payroll_adjustments', array['adjustment_id','employee_code','payroll_month','adjustment_type','addition_or_deduction','amount','calculation_method','quantity','rate','reason','policy_reference','requested_by','approval_status','approved_by','approval_remarks','payroll_inclusion_status','status']),
      ('payroll_approvals', array['approval_id','payroll_run','approver','decision','remarks','decided_at','status']),
      ('payment_batches', array['batch_id','payroll_run','payment_date','payment_method','total_amount','bank_file_reference','payment_status','status']),
      ('notifications', array['notification_id','recipient_employee_code','recipient_email','notification_type','title','message','read_status','delivery_status','status']),
      ('attachments', array['attachment_id','entity_type','entity_id','file_name','storage_path','content_type','uploaded_by','status']),
      ('audit_logs', array['audit_id','actor','action','entity_type','entity_id','previous_values','new_values','reason','ip_address','device_info','approval_reference','status'])
    ) as modules(resource, fields)
  loop
    execute format(
      'create table if not exists public.%I (id uuid primary key default extensions.gen_random_uuid(), status text not null default ''Open'', created_at timestamptz not null default now(), updated_at timestamptz not null default now())',
      module.resource
    );

    foreach field_name in array module.fields loop
      if field_name <> 'status' then
        execute format('alter table public.%I add column if not exists %I text', module.resource, field_name);
      end if;
    end loop;

    execute format('alter table public.%I enable row level security', module.resource);
    execute format('drop trigger if exists trg_%I_updated_at on public.%I', module.resource, module.resource);
    execute format('create trigger trg_%I_updated_at before update on public.%I for each row execute function public.set_updated_at()', module.resource, module.resource);

    if 'employee_code' = any(module.fields) then
      execute format('create index if not exists idx_%I_employee_code on public.%I(employee_code)', module.resource, module.resource);
    end if;
    if 'attendance_date' = any(module.fields) then
      execute format('create index if not exists idx_%I_attendance_date on public.%I(attendance_date)', module.resource, module.resource);
    end if;
    if 'location_id' = any(module.fields) then
      execute format('create index if not exists idx_%I_location_id on public.%I(location_id)', module.resource, module.resource);
    end if;
    execute format('create index if not exists idx_%I_status_updated on public.%I(status, updated_at desc)', module.resource, module.resource);
  end loop;
end $$;

create index if not exists idx_attendance_validation_employee_event on public.attendance_validation_results(employee_code, event_type, updated_at desc);
create index if not exists idx_attendance_location_employee_event on public.attendance_location_events(employee_code, event_type, updated_at desc);
create index if not exists idx_payroll_adjustments_employee_month on public.payroll_adjustments(employee_code, payroll_month);

