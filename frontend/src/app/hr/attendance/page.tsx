"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8000";

type AttendanceRecord = {
  id: string;
  attendance_record_id: string;
  employee_code: string;
  employee_name: string;
  department: string;
  attendance_date: string;
  shift: string;
  day_in_time: string;
  day_out_time: string;
  gross_work_minutes: string;
  attendance_status: string;
  approval_status: string;
  geofence_status: string;
  biometric_status: string;
  missing_day_out: boolean;
  evidence: { location_events: number; biometric_events: number; approvals: number };
};

type CorrectionRequest = {
  id: string;
  data: {
    request_id: string;
    employee_code: string;
    attendance_date: string;
    requested_day_in_time?: string;
    requested_day_out_time?: string;
    reason: string;
    final_status: string;
    status: string;
  };
  status: string;
};

type AttendanceDashboard = {
  stats: Record<string, number>;
  records: AttendanceRecord[];
  out_of_fence: AttendanceRecord[];
  missing_day_out: AttendanceRecord[];
  correction_requests: CorrectionRequest[];
  pending_corrections: CorrectionRequest[];
  failed_biometrics: { id: string; data: Record<string, string>; status: string }[];
};

async function requestAttendanceDashboard(token: string) {
  const response = await fetch(`${API_BASE}/api/v1/hr/attendance-dashboard`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok) throw new Error("Attendance dashboard API failed");
  return (await response.json()) as AttendanceDashboard;
}

function tone(status: string) {
  if (["Approved", "Present", "Attendance Corrected", "Passed"].includes(status)) return "bg-emerald-100 text-emerald-800";
  if (["Rejected", "Failed", "Outside Fence", "Accuracy Rejected", "Out of Fence"].includes(status)) return "bg-rose-100 text-rose-800";
  return "bg-amber-100 text-amber-800";
}

function minutes(value: string) {
  const total = Number(value || 0);
  if (!total) return "-";
  const hours = Math.floor(total / 60);
  const mins = total % 60;
  return `${hours}h ${mins}m`;
}

export default function HrAttendancePage() {
  const router = useRouter();
  const [dashboard, setDashboard] = useState<AttendanceDashboard | null>(null);
  const [query, setQuery] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState("");

  useEffect(() => {
    const token = localStorage.getItem("factorypulse_token");
    if (!token) {
      router.push("/login");
      return;
    }
    requestAttendanceDashboard(token)
      .then(setDashboard)
      .catch((err) => setError(err instanceof Error ? err.message : "Attendance dashboard API failed"));
  }, [router]);

  const records = useMemo(() => {
    const value = query.trim().toLowerCase();
    const rows = dashboard?.records || [];
    if (!value) return rows;
    return rows.filter((row) => [row.employee_code, row.employee_name, row.department, row.attendance_date, row.geofence_status, row.approval_status].join(" ").toLowerCase().includes(value));
  }, [dashboard, query]);

  async function refresh(token: string) {
    setDashboard(await requestAttendanceDashboard(token));
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

  function exportCsv() {
    const token = localStorage.getItem("factorypulse_token");
    if (!token) {
      router.push("/login");
      return;
    }
    fetch(`${API_BASE}/api/v1/hr/attendance/export`, { headers: { Authorization: `Bearer ${token}` } })
      .then((response) => {
        if (!response.ok) throw new Error("Export failed");
        return response.text();
      })
      .then((text) => {
        const blob = new Blob([text], { type: "text/csv;charset=utf-8" });
        const href = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = href;
        link.download = "attendance-report.csv";
        link.click();
        URL.revokeObjectURL(href);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Export failed"));
  }

  const stats = [
    ["Records", dashboard?.stats.attendance_records || 0],
    ["Pending", dashboard?.stats.pending_records || 0],
    ["Out Of Fence", dashboard?.stats.out_of_fence || 0],
    ["Missing Day Out", dashboard?.stats.missing_day_out || 0],
    ["Corrections", dashboard?.stats.correction_requests || 0],
    ["Failed Biometrics", dashboard?.stats.failed_biometrics || 0],
  ];

  return (
    <main className="min-h-screen bg-slate-100 text-slate-950">
      <header className="sticky top-0 z-20 border-b border-slate-200 bg-white/95 backdrop-blur">
        <div className="mx-auto flex max-w-7xl flex-col gap-3 px-4 py-4 md:flex-row md:items-center md:justify-between">
          <div>
            <Link href="/hr" className="text-sm font-semibold text-teal-700">HR Command</Link>
            <h1 className="mt-1 text-2xl font-semibold">Attendance Control</h1>
            <p className="text-sm text-slate-500">Review geofence exceptions, biometric evidence, missing day-out, approvals, and correction requests.</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button onClick={exportCsv} className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium hover:border-teal-600">Export CSV</button>
            <Link href="/departments/hr?module=attendance_records" className="rounded-lg bg-slate-950 px-3 py-2 text-sm font-medium text-white hover:bg-slate-800">Generic Attendance Table</Link>
          </div>
        </div>
      </header>

      <section className="mx-auto max-w-7xl px-4 py-6">
        {error ? <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</div> : null}
        {notice ? <div className="mb-4 rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-700">{notice}</div> : null}

        <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <p className="text-sm font-semibold text-teal-700">Live attendance review</p>
              <h2 className="mt-2 text-3xl font-semibold">Factory attendance evidence</h2>
              <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">Every decision creates approval history and audit records. Correction approvals can update attendance records while preserving the employee request.</p>
            </div>
            <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search attendance" className="h-11 rounded-lg border border-slate-300 px-3 text-sm outline-none focus:border-teal-700 lg:w-80" />
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
              <h2 className="text-xl font-semibold">Attendance Records</h2>
              <p className="mt-1 text-sm text-slate-500">{records.length} visible records with evidence counts.</p>
            </div>
            <div className="overflow-auto">
              <table className="w-full min-w-[980px] text-left text-sm">
                <thead className="bg-slate-50 text-xs uppercase text-slate-500">
                  <tr><th className="p-3">Employee</th><th className="p-3">Date</th><th className="p-3">Time</th><th className="p-3">Hours</th><th className="p-3">Fence</th><th className="p-3">Biometric</th><th className="p-3">Approval</th><th className="p-3">Evidence</th><th className="p-3">Action</th></tr>
                </thead>
                <tbody>
                  {records.length === 0 ? (
                    <tr><td className="p-6 text-slate-500" colSpan={9}>No attendance records yet.</td></tr>
                  ) : records.map((row) => (
                    <tr key={row.attendance_record_id || row.id} className="border-t border-slate-100">
                      <td className="p-3"><div className="font-medium">{row.employee_name}</div><div className="text-xs text-slate-500">{row.employee_code}</div></td>
                      <td className="p-3">{row.attendance_date}<div className="text-xs text-slate-500">{row.shift}</div></td>
                      <td className="p-3">{row.day_in_time || "-"} to {row.day_out_time || "-"}</td>
                      <td className="p-3">{minutes(row.gross_work_minutes)}</td>
                      <td className="p-3"><span className={`rounded-lg px-2 py-1 text-xs font-semibold ${tone(row.geofence_status)}`}>{row.geofence_status}</span></td>
                      <td className="p-3"><span className={`rounded-lg px-2 py-1 text-xs font-semibold ${tone(row.biometric_status)}`}>{row.biometric_status}</span></td>
                      <td className="p-3"><span className={`rounded-lg px-2 py-1 text-xs font-semibold ${tone(row.approval_status)}`}>{row.approval_status}</span></td>
                      <td className="p-3 text-xs text-slate-600">{row.evidence.location_events} loc / {row.evidence.biometric_events} bio / {row.evidence.approvals} approvals</td>
                      <td className="p-3">
                        <div className="flex gap-2">
                          <button disabled={Boolean(busy)} onClick={() => postJson("/api/v1/hr/attendance/decision", { attendance_record_id: row.attendance_record_id, decision: "Approved", comments: "Approved from HR Attendance Control" }, "Attendance approved.")} className="rounded-lg bg-teal-700 px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-50">Approve</button>
                          <button disabled={Boolean(busy)} onClick={() => postJson("/api/v1/hr/attendance/decision", { attendance_record_id: row.attendance_record_id, decision: "Rejected", comments: "Rejected from HR Attendance Control" }, "Attendance rejected.")} className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-1.5 text-xs font-semibold text-rose-700 disabled:opacity-50">Reject</button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <aside className="space-y-4">
            <Panel title="Pending Corrections">
              <div className="space-y-2">
                {(dashboard?.pending_corrections || []).length === 0 ? (
                  <p className="text-sm text-slate-500">No pending correction requests.</p>
                ) : dashboard?.pending_corrections.map((item) => (
                  <div key={item.data.request_id || item.id} className="rounded-lg border border-slate-100 bg-slate-50 p-3">
                    <div className="flex items-center justify-between gap-2">
                      <div className="text-sm font-semibold">{item.data.employee_code}</div>
                      <span className="rounded-lg bg-amber-100 px-2 py-1 text-xs font-semibold text-amber-800">{item.data.final_status || item.status}</span>
                    </div>
                    <div className="mt-1 text-xs text-slate-600">{item.data.attendance_date}: {item.data.reason}</div>
                    <div className="mt-2 text-xs text-slate-500">Requested {item.data.requested_day_in_time || "-"} to {item.data.requested_day_out_time || "-"}</div>
                    <div className="mt-3 flex gap-2">
                      <button disabled={Boolean(busy)} onClick={() => postJson("/api/v1/hr/attendance/correction-decision", { request_id: item.data.request_id || item.id, decision: "Approved", comments: "Correction approved by HR", apply_to_attendance: true }, "Correction approved and applied.")} className="rounded-lg bg-teal-700 px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-50">Apply</button>
                      <button disabled={Boolean(busy)} onClick={() => postJson("/api/v1/hr/attendance/correction-decision", { request_id: item.data.request_id || item.id, decision: "Rejected", comments: "Correction rejected by HR" }, "Correction rejected.")} className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-1.5 text-xs font-semibold text-rose-700 disabled:opacity-50">Reject</button>
                    </div>
                  </div>
                ))}
              </div>
            </Panel>

            <Panel title="Exception Queues">
              <Queue label="Out of fence" value={dashboard?.out_of_fence.length || 0} />
              <Queue label="Missing day out" value={dashboard?.missing_day_out.length || 0} />
              <Queue label="Failed biometrics" value={dashboard?.failed_biometrics.length || 0} />
              <Queue label="Pending corrections" value={dashboard?.pending_corrections.length || 0} />
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

function Queue({ label, value }: { label: string; value: number }) {
  return (
    <div className="mb-2 flex items-center justify-between rounded-lg border border-slate-100 bg-slate-50 p-3">
      <span className="text-sm font-medium">{label}</span>
      <span className="rounded-lg bg-white px-2 py-1 text-xs font-semibold text-slate-700">{value}</span>
    </div>
  );
}
