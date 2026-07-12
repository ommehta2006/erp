# FactoryPulse Frappe Module Catalog

Generated from the verified standalone API catalog.

## Employees
- Resource key: `employees`
- Frappe DocType: `FactoryPulse Employees`
- Fields: `employee_code`, `full_name`, `department`, `role`, `phone`, `email`, `shift`, `status`

## Attendance
- Resource key: `attendance`
- Frappe DocType: `FactoryPulse Attendance`
- Fields: `employee_code`, `date`, `shift`, `check_in`, `check_out`, `gps_area`, `status`

## Leave
- Resource key: `leave_requests`
- Frappe DocType: `FactoryPulse Leave`
- Fields: `employee_code`, `leave_type`, `from_date`, `to_date`, `reason`, `status`

## Shifts
- Resource key: `shifts`
- Frappe DocType: `FactoryPulse Shifts`
- Fields: `name`, `start_time`, `end_time`, `department`, `supervisor`, `status`

## Departments
- Resource key: `departments`
- Frappe DocType: `FactoryPulse Departments`
- Fields: `name`, `head`, `cost_center`, `location`, `status`

## Farmers
- Resource key: `farmers`
- Frappe DocType: `FactoryPulse Farmers`
- Fields: `farmer_code`, `full_name`, `village`, `mobile`, `bank_status`, `status`

## Cane Registration
- Resource key: `cane_registrations`
- Frappe DocType: `FactoryPulse Cane Registration`
- Fields: `farmer_code`, `plot_no`, `village`, `area_acres`, `variety`, `expected_tonnage`, `status`

## Harvest Plans
- Resource key: `harvest_plans`
- Frappe DocType: `FactoryPulse Harvest Plans`
- Fields: `plot_no`, `planned_date`, `contractor`, `vehicle_no`, `expected_tonnage`, `status`

## Vehicles
- Resource key: `vehicles`
- Frappe DocType: `FactoryPulse Vehicles`
- Fields: `vehicle_no`, `type`, `driver`, `gps_device`, `capacity_ton`, `status`

## Weighbridge
- Resource key: `weighbridge_tickets`
- Frappe DocType: `FactoryPulse Weighbridge`
- Fields: `ticket_no`, `vehicle_no`, `farmer_code`, `gross_weight`, `tare_weight`, `net_weight`, `quality_status`, `status`

## Production
- Resource key: `production_batches`
- Frappe DocType: `FactoryPulse Production`
- Fields: `batch_no`, `date`, `cane_crushed_ton`, `sugar_bags`, `recovery_percent`, `molasses_ton`, `power_kwh`, `status`

## Quality Lab
- Resource key: `quality_tests`
- Frappe DocType: `FactoryPulse Quality Lab`
- Fields: `sample_no`, `source`, `brix`, `pol`, `purity`, `tested_by`, `status`

## Maintenance
- Resource key: `maintenance_work_orders`
- Frappe DocType: `FactoryPulse Maintenance`
- Fields: `work_order_no`, `asset_code`, `priority`, `issue`, `assigned_to`, `due_date`, `status`

## Assets
- Resource key: `assets`
- Frappe DocType: `FactoryPulse Assets`
- Fields: `asset_code`, `name`, `department`, `criticality`, `last_service`, `status`

## Inventory
- Resource key: `inventory_items`
- Frappe DocType: `FactoryPulse Inventory`
- Fields: `item_code`, `name`, `category`, `warehouse`, `quantity`, `reorder_level`, `status`

## Purchasing
- Resource key: `purchase_orders`
- Frappe DocType: `FactoryPulse Purchasing`
- Fields: `po_no`, `supplier`, `amount`, `delivery_date`, `department`, `status`

## Sales
- Resource key: `sales_orders`
- Frappe DocType: `FactoryPulse Sales`
- Fields: `so_no`, `customer`, `product`, `quantity`, `amount`, `dispatch_date`, `status`

## Finance
- Resource key: `invoices`
- Frappe DocType: `FactoryPulse Finance`
- Fields: `invoice_no`, `party`, `invoice_type`, `amount`, `due_date`, `payment_status`, `status`

## Safety
- Resource key: `incidents`
- Frappe DocType: `FactoryPulse Safety`
- Fields: `incident_no`, `area`, `severity`, `reported_by`, `summary`, `corrective_action`, `status`

## Tasks
- Resource key: `tasks`
- Frappe DocType: `FactoryPulse Tasks`
- Fields: `title`, `owner`, `department`, `due_date`, `priority`, `status`

## Approvals
- Resource key: `approvals`
- Frappe DocType: `FactoryPulse Approvals`
- Fields: `request_type`, `request_ref`, `requested_by`, `approver`, `risk`, `decision`, `status`

## Payroll
- Resource key: `payroll_runs`
- Frappe DocType: `FactoryPulse Payroll`
- Fields: `run_no`, `period`, `department`, `gross_pay`, `deductions`, `net_pay`, `approval_status`, `status`

## Training
- Resource key: `training_records`
- Frappe DocType: `FactoryPulse Training`
- Fields: `training_no`, `employee_code`, `course`, `trainer`, `completion_date`, `score`, `status`

## Visitors
- Resource key: `visitor_passes`
- Frappe DocType: `FactoryPulse Visitors`
- Fields: `pass_no`, `visitor_name`, `company`, `host_employee`, `area`, `check_in`, `check_out`, `status`

## Documents
- Resource key: `documents`
- Frappe DocType: `FactoryPulse Documents`
- Fields: `document_no`, `title`, `category`, `owner`, `classification`, `expiry_date`, `status`

## Dispatch
- Resource key: `dispatches`
- Frappe DocType: `FactoryPulse Dispatch`
- Fields: `dispatch_no`, `customer`, `product`, `vehicle_no`, `quantity`, `gate_pass`, `status`

## Warehouses
- Resource key: `warehouses`
- Frappe DocType: `FactoryPulse Warehouses`
- Fields: `warehouse_code`, `name`, `type`, `manager`, `capacity`, `utilization_percent`, `status`

## Power Plant
- Resource key: `power_generation`
- Frappe DocType: `FactoryPulse Power Plant`
- Fields: `shift`, `date`, `turbine`, `generation_kwh`, `export_kwh`, `steam_pressure`, `status`

## Distillery
- Resource key: `distillery_batches`
- Frappe DocType: `FactoryPulse Distillery`
- Fields: `batch_no`, `feedstock`, `start_date`, `wash_volume`, `alcohol_percent`, `yield_litre`, `status`

## Ethanol
- Resource key: `ethanol_dispatches`
- Frappe DocType: `FactoryPulse Ethanol`
- Fields: `dispatch_no`, `buyer`, `litres`, `grade`, `tanker_no`, `invoice_no`, `status`

## By-products
- Resource key: `byproducts`
- Frappe DocType: `FactoryPulse By-products`
- Fields: `lot_no`, `type`, `quantity`, `storage_location`, `quality_grade`, `disposition`, `status`

## Boiler
- Resource key: `boiler_logs`
- Frappe DocType: `FactoryPulse Boiler`
- Fields: `log_no`, `shift`, `steam_pressure`, `bagasse_feed`, `water_level`, `operator`, `status`

## Packaging
- Resource key: `packaging_runs`
- Frappe DocType: `FactoryPulse Packaging`
- Fields: `run_no`, `product`, `bag_size`, `bags_packed`, `line`, `supervisor`, `status`

## Help Desk
- Resource key: `support_tickets`
- Frappe DocType: `FactoryPulse Help Desk`
- Fields: `ticket_no`, `requester`, `category`, `priority`, `assigned_to`, `summary`, `status`
