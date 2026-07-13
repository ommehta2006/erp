"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8000";

type LeaveApplication = {
  id: string;
  application_id: string;
  employee_code: string;
  leave_type: string;
  start_date: string;
  end_date: string;
  total_leave_days: string;
  reason: string;
  approval_status: string;
  payroll_impact: string;
};

type LeaveDashboard = {
  stats: Record<string, number>;
  applications: LeaveApplication[];
  pending: LeaveApplication[];
  balances: Record<string, string | number>[];
  holidays: Record<string, string>[];
  calendars: Record<string, string>[];
};

const CURRENT_YEAR = String(new Date().getFullYear());

async function requestLeaveDashboard(token: string) {
  const response = await fetch(`${API_BASE}/api/v1/hr/leave-dashboard`, { headers: { Authorization: `Bearer ${token}` } });
  if (!response.ok) throw new Error("Leave dashboard API failed");
  return (await response.json()) as LeaveDashboard;
}

function todayIso() {
  return new Date().toISOString().slice(0, 10);
}

export default function HrLeavePage() {
  const router = useRouter();
  const [dashboard, setDashboard] = useState<LeaveDashboard | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState("");
  const [query, setQuery] = useState("");
  const [allocation, setAllocation] = useState({ employee_code: "", leave_type: "Casual Leave", period: CURRENT_YEAR, allocated_days: "12", expiry_date: `${CURRENT_YEAR}-12-31` });
  const [holiday, setHoliday] = useState({ calendar_id: `CAL-${CURRENT_YEAR}`, holiday_name: "", holiday_date: todayIso(), holiday_type: "Company Holiday", paid_status: "Paid", optional_or_mandatory: "Mandatory", payroll_impact: "Paid", notes: "" });
  const [application, setApplication] = useState({ employee_code: "", leave_type: "Casual Leave", start_date: todayIso(), end_date: todayIso(), half_day: false, reason: "", payroll_impact: "Paid" });

  useEffect(() => {
    const token = localStorage.getItem("factorypulse_token");
    if (!token) {
      router.push("/login");
      return;
    }
    requestLeaveDashboard(token)
      .then(setDashboard)
      .catch((err) => setError(err instanceof Error ? err.message : "Leave dashboard API failed"));
  }, [router]);

  const applications = useMemo(() => {
    const value = query.trim().toLowerCase();
    const rows = dashboard?.applications || [];
    if (!value) return rows;
    return rows.filter((row) => [row.employee_code, row.leave_type, row.reason, row.approval_status].join(" ").toLowerCase().includes(value));
  }, [dashboard, query]);

  async function refresh(token: string) {
    setDashboard(await requestLeaveDashboard(token));
  }

  async function postJson(path: string, body: unknown, success: string) {
    setError("");
    setNotice("");
    const token = localStorage.getItem("factorypulse_token");
    if (!token) {
      router.push("/login");
      return;
    }
    setBusy(path);
    try {
      const response = await fetch(`${API_BASE}${path}`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify(body),
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(payload.detail || "API request failed");
      setNotice(success);
      await refresh(token);
    } catch (err) {
      setError(err instanceof Error ? err.message : "API request failed");
    } finally {
      setBusy("");
    }
  }

  async function decide(item: LeaveApplication, decision: "Approved" | "Rejected") {
    await postJson("/api/v1/hr/leave/decision", { application_id: item.application_id, decision, remarks: `${decision} from HR Leave Center`, payroll_impact: item.payroll_impact || "Paid" }, `Leave ${decision.toLowerCase()}.`);
  }

  const stats = [
    ["Applications", dashboard?.stats.applications || 0],
    ["Pending", dashboard?.stats.pending || 0],
    ["Approved", dashboard?.stats.approved || 0],
    ["Rejected", dashboard?.stats.rejected || 0],
    ["Balances", dashboard?.stats.balances || 0],
    ["Holidays", dashboard?.stats.holidays || 0],
  ];

  return (
    <main className="min-h-screen bg-slate-100 text-slate-950">
      <header className="sticky top-0 z-20 border-b border-slate-200 bg-white/95 backdrop-blur">
        <div className="mx-auto flex max-w-7xl flex-col gap-3 px-4 py-4 md:flex-row md:items-center md:justify-between">
          <div>
            <Link href="/hr" className="text-sm font-semibold text-teal-700">HR Command</Link>
            <h1 className="mt-1 text-2xl font-semibold">Leave & Holidays</h1>
            <p className="text-sm text-slate-500">Leave applications, balances, approvals, holiday calendars, and payroll impact.</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link href="/departments/hr?module=leave_applications" className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium hover:border-teal-600">Generic Leave Table</Link>
            <Link href="/finance" className="rounded-lg bg-slate-950 px-3 py-2 text-sm font-medium text-white hover:bg-slate-800">Payroll</Link>
          </div>
        </div>
      </header>

      <section className="mx-auto max-w-7xl px-4 py-6">
        {error ? <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</div> : null}
        {notice ? <div className="mb-4 rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-700">{notice}</div> : null}

        <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <p className="text-sm font-semibold text-teal-700">HR leave control</p>
              <h2 className="mt-2 text-3xl font-semibold">Approve, allocate, and protect payroll</h2>
              <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">Approved paid leave is included in payroll paid-day calculation. Rejected leave remains visible through approval history and audit logs.</p>
            </div>
            <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search leave records" className="h-11 rounded-lg border border-slate-300 px-3 text-sm outline-none focus:border-teal-700 lg:w-80" />
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

        <div className="mt-5 grid gap-4 xl:grid-cols-[1fr_420px]">
          <section className="rounded-lg border border-slate-200 bg-white shadow-sm">
            <div className="border-b border-slate-200 p-4">
              <h2 className="text-xl font-semibold">Applications</h2>
              <p className="mt-1 text-sm text-slate-500">Review employee leave requests with payroll impact.</p>
            </div>
            <div className="overflow-auto">
              <table className="w-full min-w-[820px] text-left text-sm">
                <thead className="bg-slate-50 text-xs uppercase text-slate-500">
                  <tr><th className="p-3">Employee</th><th className="p-3">Leave</th><th className="p-3">Dates</th><th className="p-3">Days</th><th className="p-3">Payroll</th><th className="p-3">Status</th><th className="p-3">Action</th></tr>
                </thead>
                <tbody>
                  {applications.length === 0 ? (
                    <tr><td className="p-6 text-slate-500" colSpan={7}>No leave applications found.</td></tr>
                  ) : applications.map((item) => (
                    <tr key={item.application_id || item.id} className="border-t border-slate-100">
                      <td className="p-3 font-medium">{item.employee_code}</td>
                      <td className="p-3">{item.leave_type}<div className="mt-1 line-clamp-1 text-xs text-slate-500">{item.reason}</div></td>
                      <td className="p-3">{item.start_date} to {item.end_date}</td>
                      <td className="p-3">{item.total_leave_days}</td>
                      <td className="p-3">{item.payroll_impact}</td>
                      <td className="p-3"><span className={`rounded-lg px-2 py-1 text-xs font-semibold ${item.approval_status === "Approved" ? "bg-emerald-100 text-emerald-800" : item.approval_status === "Rejected" ? "bg-rose-100 text-rose-800" : "bg-amber-100 text-amber-800"}`}>{item.approval_status}</span></td>
                      <td className="p-3">
                        {["Pending", "Open", "Pending Approval", "Draft"].includes(item.approval_status) ? (
                          <div className="flex gap-2">
                            <button disabled={Boolean(busy)} onClick={() => decide(item, "Approved")} className="rounded-lg bg-teal-700 px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-50">Approve</button>
                            <button disabled={Boolean(busy)} onClick={() => decide(item, "Rejected")} className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-1.5 text-xs font-semibold text-rose-700 disabled:opacity-50">Reject</button>
                          </div>
                        ) : "-"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <aside className="space-y-4">
            <Panel title="Apply Leave For Employee">
              <div className="grid gap-2">
                <Input label="Employee Code" value={application.employee_code} onChange={(value) => setApplication((current) => ({ ...current, employee_code: value }))} />
                <Input label="Leave Type" value={application.leave_type} onChange={(value) => setApplication((current) => ({ ...current, leave_type: value }))} />
                <div className="grid grid-cols-2 gap-2">
                  <Input label="Start" type="date" value={application.start_date} onChange={(value) => setApplication((current) => ({ ...current, start_date: value }))} />
                  <Input label="End" type="date" value={application.end_date} onChange={(value) => setApplication((current) => ({ ...current, end_date: value }))} />
                </div>
                <Input label="Reason" value={application.reason} onChange={(value) => setApplication((current) => ({ ...current, reason: value }))} />
                <button disabled={Boolean(busy)} onClick={() => postJson("/api/v1/hr/leave/applications", application, "Leave application saved.")} className="rounded-lg bg-teal-700 px-3 py-2 text-sm font-semibold text-white disabled:opacity-50">Create Application</button>
              </div>
            </Panel>

            <Panel title="Allocate Leave">
              <div className="grid gap-2">
                <Input label="Employee Code" value={allocation.employee_code} onChange={(value) => setAllocation((current) => ({ ...current, employee_code: value }))} />
                <div className="grid grid-cols-2 gap-2">
                  <Input label="Leave Type" value={allocation.leave_type} onChange={(value) => setAllocation((current) => ({ ...current, leave_type: value }))} />
                  <Input label="Days" type="number" value={allocation.allocated_days} onChange={(value) => setAllocation((current) => ({ ...current, allocated_days: value }))} />
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <Input label="Period" value={allocation.period} onChange={(value) => setAllocation((current) => ({ ...current, period: value }))} />
                  <Input label="Expiry" type="date" value={allocation.expiry_date} onChange={(value) => setAllocation((current) => ({ ...current, expiry_date: value }))} />
                </div>
                <button disabled={Boolean(busy)} onClick={() => postJson("/api/v1/hr/leave/allocations", { ...allocation, allocated_days: Number(allocation.allocated_days || 0) }, "Leave allocation saved.")} className="rounded-lg bg-slate-950 px-3 py-2 text-sm font-semibold text-white disabled:opacity-50">Save Allocation</button>
              </div>
            </Panel>

            <Panel title="Create Holiday">
              <div className="grid gap-2">
                <Input label="Holiday Name" value={holiday.holiday_name} onChange={(value) => setHoliday((current) => ({ ...current, holiday_name: value }))} />
                <div className="grid grid-cols-2 gap-2">
                  <Input label="Date" type="date" value={holiday.holiday_date} onChange={(value) => setHoliday((current) => ({ ...current, holiday_date: value }))} />
                  <Input label="Calendar" value={holiday.calendar_id} onChange={(value) => setHoliday((current) => ({ ...current, calendar_id: value }))} />
                </div>
                <Input label="Notes" value={holiday.notes} onChange={(value) => setHoliday((current) => ({ ...current, notes: value }))} />
                <button disabled={Boolean(busy)} onClick={() => postJson("/api/v1/hr/holidays", holiday, "Holiday saved.")} className="rounded-lg bg-amber-600 px-3 py-2 text-sm font-semibold text-white disabled:opacity-50">Save Holiday</button>
              </div>
            </Panel>

            <Panel title="Balances">
              <div className="space-y-2">
                {(dashboard?.balances || []).slice(0, 5).map((item, index) => (
                  <div key={`${item.employee_code}-${index}`} className="rounded-lg border border-slate-100 bg-slate-50 p-3">
                    <div className="flex items-center justify-between gap-2">
                      <div className="text-sm font-semibold">{item.employee_code}</div>
                      <span className="text-xs text-slate-500">{item.period}</span>
                    </div>
                    <div className="mt-1 text-xs text-slate-600">{item.leave_type}: {item.available_days} available / {item.allocated_days} allocated</div>
                  </div>
                ))}
              </div>
            </Panel>
          </aside>
        </div>
      </section>
    </main>
  );
}

function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <h2 className="font-semibold">{title}</h2>
      <div className="mt-3">{children}</div>
    </section>
  );
}

function Input({ label, value, onChange, type = "text" }: { label: string; value: string; onChange: (value: string) => void; type?: string }) {
  return (
    <label className="text-sm font-medium text-slate-700">
      {label}
      <input type={type} value={value} onChange={(event) => onChange(event.target.value)} className="mt-1 h-10 w-full rounded-lg border border-slate-300 px-3 text-sm outline-none focus:border-teal-700" />
    </label>
  );
}
