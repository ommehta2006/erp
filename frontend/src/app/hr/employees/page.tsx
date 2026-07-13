"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8000";

type EmployeeBundle = {
  employee_code: string;
  employee: Record<string, string> | null;
  private_details: Record<string, string>[];
  bank_details: Record<string, string>[];
  documents: Record<string, string>[];
  emergency_contacts: Record<string, string>[];
  lifecycle: Record<string, string>[];
  salary_assignments: Record<string, string>[];
  location_assignments: Record<string, string>[];
  device_registrations: Record<string, string>[];
  biometric_enrollments: Record<string, string>[];
  profile_completeness: number;
  missing_sections: string[];
};

type EmployeesDashboard = {
  stats: Record<string, number>;
  employees: EmployeeBundle[];
  missing_private_or_sensitive_notice: string;
};

type FormState = {
  employee_code: string;
  full_name: string;
  department: string;
  role: string;
  phone: string;
  email: string;
  shift: string;
  date_of_birth: string;
  gender: string;
  nationality: string;
  tax_identifier_ref: string;
  bank_name: string;
  account_last4: string;
  ifsc_or_routing: string;
  document_type: string;
  document_no_masked: string;
  document_expiry_date: string;
  emergency_contact_name: string;
  emergency_relationship: string;
  emergency_phone: string;
  emergency_address: string;
  location_id: string;
  effective_start_date: string;
  effective_end_date: string;
  salary_structure_id: string;
  gross_salary: string;
  ctc: string;
  trusted_device_id: string;
  device_platform: string;
  device_name: string;
  app_version: string;
};

const EMPTY_FORM: FormState = {
  employee_code: "",
  full_name: "",
  department: "Manufacturing",
  role: "Operator",
  phone: "",
  email: "",
  shift: "General",
  date_of_birth: "",
  gender: "",
  nationality: "India",
  tax_identifier_ref: "",
  bank_name: "",
  account_last4: "",
  ifsc_or_routing: "",
  document_type: "",
  document_no_masked: "",
  document_expiry_date: "",
  emergency_contact_name: "",
  emergency_relationship: "",
  emergency_phone: "",
  emergency_address: "",
  location_id: "",
  effective_start_date: new Date().toISOString().slice(0, 10),
  effective_end_date: "",
  salary_structure_id: "DEFAULT",
  gross_salary: "",
  ctc: "",
  trusted_device_id: "",
  device_platform: "expo-mobile",
  device_name: "",
  app_version: "",
};

const FIELD_GROUPS: { title: string; fields: { key: keyof FormState; label: string; type?: string; required?: boolean }[] }[] = [
  {
    title: "Employee",
    fields: [
      { key: "employee_code", label: "Employee Code", required: true },
      { key: "full_name", label: "Full Name", required: true },
      { key: "email", label: "Email", type: "email", required: true },
      { key: "phone", label: "Phone" },
      { key: "department", label: "Department", required: true },
      { key: "role", label: "Designation / Role", required: true },
      { key: "shift", label: "Shift", required: true },
      { key: "effective_start_date", label: "Joining / Effective Date", type: "date" },
    ],
  },
  {
    title: "Private Details",
    fields: [
      { key: "date_of_birth", label: "Date Of Birth", type: "date" },
      { key: "gender", label: "Gender" },
      { key: "nationality", label: "Nationality" },
      { key: "tax_identifier_ref", label: "Tax Identifier Ref" },
    ],
  },
  {
    title: "Bank, Document, Emergency",
    fields: [
      { key: "bank_name", label: "Bank Name" },
      { key: "account_last4", label: "Account Last 4" },
      { key: "ifsc_or_routing", label: "IFSC / Routing" },
      { key: "document_type", label: "Document Type" },
      { key: "document_no_masked", label: "Document No Masked" },
      { key: "document_expiry_date", label: "Document Expiry", type: "date" },
      { key: "emergency_contact_name", label: "Emergency Contact" },
      { key: "emergency_relationship", label: "Relationship" },
      { key: "emergency_phone", label: "Emergency Phone" },
      { key: "emergency_address", label: "Emergency Address" },
    ],
  },
  {
    title: "Factory Control",
    fields: [
      { key: "location_id", label: "Work Location ID" },
      { key: "effective_end_date", label: "Assignment End Date", type: "date" },
      { key: "salary_structure_id", label: "Salary Structure" },
      { key: "gross_salary", label: "Gross Salary", type: "number" },
      { key: "ctc", label: "CTC", type: "number" },
      { key: "trusted_device_id", label: "Trusted Device ID" },
      { key: "device_platform", label: "Device Platform" },
      { key: "device_name", label: "Device Name" },
      { key: "app_version", label: "App Version" },
    ],
  },
];

async function requestEmployeesDashboard(token: string) {
  const response = await fetch(`${API_BASE}/api/v1/hr/employees-dashboard`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok) throw new Error("HR employees API failed");
  return (await response.json()) as EmployeesDashboard;
}

function labelFor(value: string) {
  return value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function money(value: string | undefined) {
  return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(Number(value || 0));
}

export default function HrEmployeesPage() {
  const router = useRouter();
  const [dashboard, setDashboard] = useState<EmployeesDashboard | null>(null);
  const [form, setForm] = useState<FormState>(EMPTY_FORM);
  const [query, setQuery] = useState("");
  const [selectedCode, setSelectedCode] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem("factorypulse_token");
    if (!token) {
      router.push("/login");
      return;
    }
    requestEmployeesDashboard(token)
      .then((data) => {
        setDashboard(data);
        setSelectedCode(data.employees[0]?.employee_code || "");
      })
      .catch((err) => setError(err instanceof Error ? err.message : "HR employees API failed"));
  }, [router]);

  const employees = useMemo(() => {
    const value = query.trim().toLowerCase();
    const list = dashboard?.employees || [];
    if (!value) return list;
    return list.filter((item) => [item.employee_code, item.employee?.full_name, item.employee?.department, item.employee?.role].join(" ").toLowerCase().includes(value));
  }, [dashboard, query]);

  const selected = employees.find((item) => item.employee_code === selectedCode) || employees[0] || null;

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError("");
    setNotice("");
    const token = localStorage.getItem("factorypulse_token");
    if (!token) {
      router.push("/login");
      return;
    }
    setSaving(true);
    try {
      const response = await fetch(`${API_BASE}/api/v1/hr/employees/onboard`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify(form),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.detail || "Employee onboarding failed");
      setNotice("Employee packet saved with lifecycle, salary, location, device, and audit records.");
      setForm(EMPTY_FORM);
      const nextDashboard = await requestEmployeesDashboard(token);
      setDashboard(nextDashboard);
      setSelectedCode(body.profile?.employee_code || nextDashboard.employees[0]?.employee_code || "");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Employee onboarding failed");
    } finally {
      setSaving(false);
    }
  }

  const stats = [
    ["Employees", dashboard?.stats.employees || 0],
    ["Active", dashboard?.stats.active || 0],
    ["Complete", dashboard?.stats.complete_profiles || 0],
    ["Need Data", dashboard?.stats.incomplete_profiles || 0],
    ["Biometric Ready", dashboard?.stats.biometric_ready || 0],
    ["Salary Assigned", dashboard?.stats.salary_assigned || 0],
  ];

  return (
    <main className="min-h-screen bg-slate-100 text-slate-950">
      <header className="sticky top-0 z-20 border-b border-slate-200 bg-white/95 backdrop-blur">
        <div className="mx-auto flex max-w-7xl flex-col gap-3 px-4 py-4 md:flex-row md:items-center md:justify-between">
          <div>
            <Link href="/hr" className="text-sm font-semibold text-teal-700">HR Command</Link>
            <h1 className="mt-1 text-2xl font-semibold">Employee Master</h1>
            <p className="text-sm text-slate-500">Onboard employees with profile, salary, location, emergency, lifecycle, and trusted-device records.</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link href="/departments/hr?module=employees" className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium hover:border-teal-600">Generic Employee Table</Link>
            <Link href="/finance" className="rounded-lg bg-slate-950 px-3 py-2 text-sm font-medium text-white hover:bg-slate-800">Finance Payroll</Link>
          </div>
        </div>
      </header>

      <section className="mx-auto max-w-7xl px-4 py-6">
        {error ? <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</div> : null}
        {notice ? <div className="mb-4 rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-700">{notice}</div> : null}

        <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <p className="text-sm font-semibold text-teal-700">HR employee control</p>
              <h2 className="mt-2 text-3xl font-semibold">Factory workforce records</h2>
              <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">{dashboard?.missing_private_or_sensitive_notice || "Loading HR employee controls."}</p>
            </div>
            <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search employee" className="h-11 rounded-lg border border-slate-300 px-3 text-sm outline-none focus:border-teal-700 lg:w-80" />
          </div>
          <div className="mt-5 grid grid-cols-2 gap-2 md:grid-cols-3 xl:grid-cols-6">
            {stats.map(([label, value]) => (
              <div key={label} className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                <div className="text-xs font-medium text-slate-500">{label}</div>
                <div className="mt-1 text-2xl font-semibold">{value}</div>
              </div>
            ))}
          </div>
        </section>

        <div className="mt-5 grid gap-4 xl:grid-cols-[1.05fr_0.95fr]">
          <form onSubmit={handleSubmit} className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h2 className="text-xl font-semibold">New employee packet</h2>
                <p className="mt-1 text-sm text-slate-500">Creates real HR records and audit history in one transaction-style workflow.</p>
              </div>
              <button disabled={saving} className="rounded-lg bg-teal-700 px-4 py-2 text-sm font-semibold text-white hover:bg-teal-800 disabled:bg-slate-400">
                {saving ? "Saving" : "Save Packet"}
              </button>
            </div>

            <div className="mt-5 space-y-5">
              {FIELD_GROUPS.map((group) => (
                <section key={group.title}>
                  <h3 className="text-sm font-semibold text-slate-700">{group.title}</h3>
                  <div className="mt-2 grid gap-3 md:grid-cols-2">
                    {group.fields.map((field) => (
                      <label key={field.key} className="text-sm font-medium text-slate-700">
                        {field.label} {field.required ? <span className="text-red-600">*</span> : null}
                        <input
                          type={field.type || "text"}
                          value={form[field.key]}
                          required={field.required}
                          onChange={(event) => setForm((current) => ({ ...current, [field.key]: event.target.value }))}
                          className="mt-1 h-10 w-full rounded-lg border border-slate-300 px-3 text-sm outline-none focus:border-teal-700"
                        />
                      </label>
                    ))}
                  </div>
                </section>
              ))}
            </div>
          </form>

          <section className="grid gap-4 lg:grid-cols-[360px_1fr] xl:grid-cols-1 2xl:grid-cols-[360px_1fr]">
            <div className="rounded-lg border border-slate-200 bg-white shadow-sm">
              <div className="border-b border-slate-200 p-4">
                <h2 className="font-semibold">Employees</h2>
                <p className="mt-1 text-sm text-slate-500">{employees.length} matching records</p>
              </div>
              <div className="max-h-[680px] overflow-auto p-2">
                {employees.length === 0 ? (
                  <p className="p-3 text-sm text-slate-500">No employees yet.</p>
                ) : employees.map((item) => (
                  <button
                    key={item.employee_code}
                    type="button"
                    onClick={() => setSelectedCode(item.employee_code)}
                    className={`mb-2 w-full rounded-lg border p-3 text-left transition ${selected?.employee_code === item.employee_code ? "border-teal-500 bg-teal-50" : "border-slate-100 bg-white hover:border-slate-300"}`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <div className="truncate text-sm font-semibold">{item.employee?.full_name || item.employee_code}</div>
                        <div className="mt-1 truncate text-xs text-slate-500">{item.employee_code} / {item.employee?.department || "Department"}</div>
                      </div>
                      <span className={`rounded-lg px-2 py-1 text-xs font-semibold ${item.profile_completeness === 100 ? "bg-emerald-100 text-emerald-800" : "bg-amber-100 text-amber-800"}`}>
                        {item.profile_completeness}%
                      </span>
                    </div>
                    <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-100">
                      <div className="h-full rounded-full bg-teal-600" style={{ width: `${item.profile_completeness}%` }} />
                    </div>
                  </button>
                ))}
              </div>
            </div>

            <EmployeeDetail employee={selected} />
          </section>
        </div>
      </section>
    </main>
  );
}

function EmployeeDetail({ employee }: { employee: EmployeeBundle | null }) {
  if (!employee) {
    return <div className="rounded-lg border border-slate-200 bg-white p-5 text-sm text-slate-500 shadow-sm">Select an employee to inspect the full packet.</div>;
  }

  const salary = employee.salary_assignments[0];
  const device = employee.device_registrations[0];
  const lifecycle = employee.lifecycle.slice(0, 5);
  const checks = [
    ["Private", employee.private_details.length],
    ["Bank", employee.bank_details.length],
    ["Document", employee.documents.length],
    ["Emergency", employee.emergency_contacts.length],
    ["Salary", employee.salary_assignments.length],
    ["Location", employee.location_assignments.length],
    ["Biometric", employee.biometric_enrollments.length],
  ];

  return (
    <aside className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div>
          <h2 className="text-xl font-semibold">{employee.employee?.full_name || employee.employee_code}</h2>
          <p className="mt-1 text-sm text-slate-500">{employee.employee_code} / {employee.employee?.role || "Role"} / {employee.employee?.shift || "Shift"}</p>
        </div>
        <span className="rounded-lg bg-teal-50 px-3 py-2 text-sm font-semibold text-teal-800">{employee.profile_completeness}% complete</span>
      </div>

      <div className="mt-4 grid grid-cols-2 gap-2 md:grid-cols-4">
        {checks.map(([label, count]) => (
          <div key={label} className={`rounded-lg border p-3 ${Number(count) > 0 ? "border-emerald-200 bg-emerald-50" : "border-amber-200 bg-amber-50"}`}>
            <div className="text-xs font-medium text-slate-600">{label}</div>
            <div className="mt-1 text-lg font-semibold">{Number(count) > 0 ? "Ready" : "Needed"}</div>
          </div>
        ))}
      </div>

      {employee.missing_sections.length > 0 ? (
        <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-3">
          <div className="text-sm font-semibold text-amber-900">Missing sections</div>
          <div className="mt-2 flex flex-wrap gap-2">
            {employee.missing_sections.map((item) => (
              <span key={item} className="rounded-lg bg-white px-2.5 py-1 text-xs font-semibold text-amber-800">{labelFor(item)}</span>
            ))}
          </div>
        </div>
      ) : null}

      <div className="mt-4 grid gap-3 md:grid-cols-2">
        <InfoCard title="Salary" lines={[`Gross ${money(salary?.gross_salary)}`, `CTC ${money(salary?.ctc)}`, `Status ${salary?.status || "Not assigned"}`]} />
        <InfoCard title="Trusted Device" lines={[device?.device_id || "Not enrolled", device?.platform || "Platform missing", employee.biometric_enrollments[0]?.privacy_notice || "No biometric metadata record"]} />
      </div>

      <section className="mt-4">
        <h3 className="text-sm font-semibold text-slate-700">Lifecycle</h3>
        <div className="mt-2 space-y-2">
          {lifecycle.length === 0 ? (
            <p className="rounded-lg border border-slate-100 bg-slate-50 p-3 text-sm text-slate-500">No lifecycle events yet.</p>
          ) : lifecycle.map((item, index) => (
            <div key={`${item.event_no}-${index}`} className="rounded-lg border border-slate-100 bg-slate-50 p-3">
              <div className="flex items-center justify-between gap-2">
                <div className="text-sm font-semibold">{item.event_type}</div>
                <span className="text-xs text-slate-500">{item.effective_date}</span>
              </div>
              <div className="mt-1 text-xs text-slate-500">{item.reason || item.new_value}</div>
            </div>
          ))}
        </div>
      </section>
    </aside>
  );
}

function InfoCard({ title, lines }: { title: string; lines: string[] }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
      <div className="text-sm font-semibold">{title}</div>
      <div className="mt-2 space-y-1">
        {lines.map((line, index) => (
          <div key={`${title}-${index}`} className="line-clamp-2 text-xs text-slate-600">{line}</div>
        ))}
      </div>
    </div>
  );
}
