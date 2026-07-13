"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8000";

type ErpRecord = { id: string; data: Record<string, string>; status: string };
type SettingsDashboard = {
  active_policy: Record<string, string>;
  policies: ErpRecord[];
  shifts: ErpRecord[];
  shift_assignments: ErpRecord[];
  stats: Record<string, number | string>;
  rules: Record<string, string>;
};

const DEFAULT_POLICY = {
  policy_name: "Default Attendance Policy",
  late_after_time: "09:15",
  grace_minutes: "0",
  tracking_interval_minutes: "5",
  background_location_required: true,
};

const DEFAULT_SHIFT = {
  name: "",
  start_time: "09:00",
  end_time: "18:00",
  department: "All",
  supervisor: "",
};

function authHeaders() {
  const token = localStorage.getItem("factorypulse_token") || "";
  return { Authorization: `Bearer ${token}` };
}

function numeric(value: string) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

function tone(status: string) {
  if (["Active", "Approved"].includes(status)) return "border-emerald-200 bg-emerald-50 text-emerald-800";
  if (["Inactive", "Closed"].includes(status)) return "border-slate-200 bg-slate-50 text-slate-700";
  return "border-amber-200 bg-amber-50 text-amber-800";
}

export default function HrSettingsPage() {
  const router = useRouter();
  const [dashboard, setDashboard] = useState<SettingsDashboard | null>(null);
  const [policy, setPolicy] = useState(DEFAULT_POLICY);
  const [shift, setShift] = useState(DEFAULT_SHIFT);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const load = () => {
    const token = localStorage.getItem("factorypulse_token");
    if (!token) {
      router.push("/login");
      return;
    }
    fetch(`${API_BASE}/api/v1/hr/settings-dashboard`, { headers: authHeaders() })
      .then((response) => {
        if (!response.ok) throw new Error("HR settings API failed");
        return response.json();
      })
      .then((body: SettingsDashboard) => {
        setDashboard(body);
        setPolicy({
          policy_name: body.active_policy.policy_name || DEFAULT_POLICY.policy_name,
          late_after_time: body.active_policy.late_after_time || DEFAULT_POLICY.late_after_time,
          grace_minutes: body.active_policy.grace_minutes || DEFAULT_POLICY.grace_minutes,
          tracking_interval_minutes: body.active_policy.tracking_interval_minutes || DEFAULT_POLICY.tracking_interval_minutes,
          background_location_required: body.active_policy.background_location_required !== "No",
        });
      })
      .catch((err) => setError(err instanceof Error ? err.message : "HR settings API failed"));
  };

  useEffect(load, [router]);

  async function postJson(path: string, payload: unknown, success: string) {
    setBusy(path);
    setError("");
    setNotice("");
    try {
      const response = await fetch(`${API_BASE}${path}`, {
        method: "POST",
        headers: { ...authHeaders(), "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.detail || "Request failed");
      setNotice(success);
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setBusy("");
    }
  }

  const activePolicy = dashboard?.active_policy || {};
  const stats = [
    ["Late After", String(dashboard?.stats.late_after_time || activePolicy.late_after_time || "09:15")],
    ["Tracking", `${dashboard?.stats.tracking_interval_minutes || activePolicy.tracking_interval_minutes || "5"} min`],
    ["Policies", String(dashboard?.stats.policies || 0)],
    ["Shifts", String(dashboard?.stats.shifts || 0)],
    ["Active Shifts", String(dashboard?.stats.active_shifts || 0)],
    ["Assignments", String(dashboard?.stats.assignments || 0)],
  ];

  return (
    <main className="min-h-screen bg-slate-100 text-slate-950">
      <header className="sticky top-0 z-20 border-b border-slate-200 bg-white/95 backdrop-blur">
        <div className="mx-auto flex max-w-7xl flex-col gap-3 px-4 py-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <Link href="/hr" className="text-sm font-semibold text-teal-700">HR Command Center</Link>
            <h1 className="mt-1 text-2xl font-semibold">Attendance Policy & Shift Settings</h1>
            <p className="text-sm text-slate-500">Control late marks, background location expectations, tracking interval, and factory shift definitions.</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link href="/hr/attendance" className="rounded-lg border border-indigo-200 bg-indigo-50 px-3 py-2 text-sm font-medium text-indigo-700 hover:border-indigo-600">Attendance</Link>
            <Link href="/hr/locations" className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm font-medium text-emerald-700 hover:border-emerald-600">Locations</Link>
            <Link href="/departments/hr?module=attendance_policies" className="rounded-lg bg-slate-950 px-3 py-2 text-sm font-medium text-white hover:bg-slate-800">Raw Policies</Link>
          </div>
        </div>
      </header>

      <section className="mx-auto max-w-7xl px-4 py-6">
        {error ? <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</div> : null}
        {notice ? <div className="mb-4 rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-700">{notice}</div> : null}

        <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <p className="text-sm font-semibold text-teal-700">Active attendance rule</p>
              <h2 className="mt-2 text-3xl font-semibold">Late mark after {activePolicy.late_after_time || "09:15"}</h2>
              <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
                Employee Day In is evaluated by the backend using this HR policy. Background location and GPS checks remain controlled by live API policy values.
              </p>
            </div>
            <div className="rounded-lg border border-teal-200 bg-teal-50 p-3 text-sm text-teal-800">
              {dashboard?.rules.employee_app_effect || "Employee app uses the active HR attendance policy."}
            </div>
          </div>
          <div className="mt-5 grid grid-cols-2 gap-2 md:grid-cols-3 xl:grid-cols-6">
            {stats.map(([label, value]) => (
              <div key={label} className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                <div className="text-xs font-medium text-slate-500">{label}</div>
                <div className="mt-1 text-xl font-semibold">{value}</div>
              </div>
            ))}
          </div>
        </section>

        <div className="mt-5 grid gap-4 xl:grid-cols-[420px_1fr]">
          <aside className="space-y-4">
            <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
              <h2 className="font-semibold">Set Attendance Policy</h2>
              <div className="mt-3 space-y-3">
                <Input label="Policy Name" value={policy.policy_name} onChange={(value) => setPolicy({ ...policy, policy_name: value })} />
                <div className="grid grid-cols-2 gap-3">
                  <Input label="Late After" value={policy.late_after_time} onChange={(value) => setPolicy({ ...policy, late_after_time: value })} />
                  <Input label="Grace Minutes" value={policy.grace_minutes} onChange={(value) => setPolicy({ ...policy, grace_minutes: value })} />
                </div>
                <Input label="Tracking Interval Minutes" value={policy.tracking_interval_minutes} onChange={(value) => setPolicy({ ...policy, tracking_interval_minutes: value })} />
                <label className="flex items-center gap-3 rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm">
                  <input type="checkbox" checked={policy.background_location_required} onChange={(event) => setPolicy({ ...policy, background_location_required: event.target.checked })} />
                  Background location required during working hours
                </label>
              </div>
              <button
                disabled={busy === "/api/v1/hr/attendance-policy"}
                onClick={() => postJson("/api/v1/hr/attendance-policy", {
                  ...policy,
                  grace_minutes: numeric(policy.grace_minutes),
                  tracking_interval_minutes: numeric(policy.tracking_interval_minutes),
                }, "Attendance policy saved and applied.")}
                className="mt-4 w-full rounded-lg bg-slate-950 px-3 py-2 text-sm font-semibold text-white hover:bg-slate-800 disabled:opacity-50"
              >
                {busy === "/api/v1/hr/attendance-policy" ? "Saving..." : "Save policy"}
              </button>
            </section>

            <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
              <h2 className="font-semibold">Create Shift</h2>
              <div className="mt-3 space-y-3">
                <Input label="Shift Name" value={shift.name} onChange={(value) => setShift({ ...shift, name: value })} />
                <div className="grid grid-cols-2 gap-3">
                  <Input label="Start Time" value={shift.start_time} onChange={(value) => setShift({ ...shift, start_time: value })} />
                  <Input label="End Time" value={shift.end_time} onChange={(value) => setShift({ ...shift, end_time: value })} />
                </div>
                <Input label="Department" value={shift.department} onChange={(value) => setShift({ ...shift, department: value })} />
                <Input label="Supervisor" value={shift.supervisor} onChange={(value) => setShift({ ...shift, supervisor: value })} />
              </div>
              <button
                disabled={busy === "/api/v1/hr/shifts"}
                onClick={() => postJson("/api/v1/hr/shifts", shift, "Shift saved.")}
                className="mt-4 w-full rounded-lg bg-slate-950 px-3 py-2 text-sm font-semibold text-white hover:bg-slate-800 disabled:opacity-50"
              >
                {busy === "/api/v1/hr/shifts" ? "Saving..." : "Save shift"}
              </button>
            </section>
          </aside>

          <section className="space-y-4">
            <Table title="Attendance Policies" empty="No policy records yet." rows={dashboard?.policies || []} columns={["policy_name", "late_after_time", "grace_minutes", "tracking_interval_minutes", "background_location_required"]} />
            <Table title="Shift Definitions" empty="No shifts yet." rows={dashboard?.shifts || []} columns={["name", "start_time", "end_time", "department", "supervisor"]} />
          </section>
        </div>
      </section>
    </main>
  );
}

function Input({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  return (
    <label className="block">
      <span className="text-xs font-medium text-slate-500">{label}</span>
      <input value={value} onChange={(event) => onChange(event.target.value)} className="mt-1 h-10 w-full rounded-lg border border-slate-300 px-3 text-sm outline-none focus:border-teal-700" />
    </label>
  );
}

function Table({ title, empty, rows, columns }: { title: string; empty: string; rows: ErpRecord[]; columns: string[] }) {
  return (
    <section className="rounded-lg border border-slate-200 bg-white shadow-sm">
      <div className="border-b border-slate-200 p-4">
        <h2 className="text-lg font-semibold">{title}</h2>
        <p className="mt-1 text-sm text-slate-500">{rows.length} records</p>
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full text-left text-sm">
          <thead className="bg-slate-50 text-xs uppercase text-slate-500">
            <tr>
              {columns.map((column) => <th key={column} className="p-3">{column.replaceAll("_", " ")}</th>)}
              <th className="p-3">Status</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr><td className="p-4 text-slate-500" colSpan={columns.length + 1}>{empty}</td></tr>
            ) : rows.map((row) => (
              <tr key={row.id} className="border-t border-slate-100">
                {columns.map((column) => <td key={column} className="p-3">{row.data[column] || "-"}</td>)}
                <td className="p-3"><span className={`rounded-lg border px-2 py-1 text-xs font-semibold ${tone(row.status)}`}>{row.status}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
