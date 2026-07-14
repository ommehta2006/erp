"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8000";

type ErpRecord = { id: string; data: Record<string, string>; status: string };
type JobDefinition = { job_type: string; title: string; description: string };
type AttendanceRecord = {
  attendance_record_id: string;
  employee_code: string;
  employee_name: string;
  attendance_date: string;
  geofence_status: string;
  approval_status: string;
  attendance_status: string;
};
type OperationsDashboard = {
  stats: Record<string, number>;
  jobs: ErpRecord[];
  available_jobs: JobDefinition[];
  attendance_exceptions: {
    missing_day_out: AttendanceRecord[];
    out_of_fence: AttendanceRecord[];
    high_risk_attendance: AttendanceRecord[];
    high_risk_devices: ErpRecord[];
    pending_corrections: Record<string, unknown>[];
  };
};

async function requestOperationsDashboard(token: string) {
  const response = await fetch(`${API_BASE}/api/v1/admin/operations-dashboard`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok) throw new Error("Operations dashboard API failed");
  return (await response.json()) as OperationsDashboard;
}

function statusTone(status: string) {
  if (status === "Completed") return "border-emerald-200 bg-emerald-50 text-emerald-800";
  if (status === "Draft") return "border-amber-200 bg-amber-50 text-amber-800";
  if (status === "Failed") return "border-rose-200 bg-rose-50 text-rose-800";
  return "border-slate-200 bg-slate-50 text-slate-700";
}

export default function AdminOperationsPage() {
  const router = useRouter();
  const [dashboard, setDashboard] = useState<OperationsDashboard | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState("");
  const [lastResult, setLastResult] = useState<Record<string, unknown> | null>(null);

  const load = () => {
    const token = localStorage.getItem("factorypulse_token");
    if (!token) {
      router.push("/login");
      return;
    }
    requestOperationsDashboard(token)
      .then(setDashboard)
      .catch((err) => setError(err instanceof Error ? err.message : "Operations dashboard API failed"));
  };

  useEffect(load, [router]);

  async function runJob(jobType: string, dryRun: boolean) {
    const token = localStorage.getItem("factorypulse_token");
    if (!token) {
      router.push("/login");
      return;
    }
    setError("");
    setNotice("");
    setBusy(`${jobType}-${dryRun ? "dry" : "run"}`);
    try {
      const response = await fetch(`${API_BASE}/api/v1/admin/operations/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ job_type: jobType, dry_run: dryRun }),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.detail || "Job run failed");
      setNotice(dryRun ? "Dry run completed." : "Operations job completed and audited.");
      setLastResult(body.result || null);
      setDashboard(body.dashboard || await requestOperationsDashboard(token));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Job run failed");
    } finally {
      setBusy("");
    }
  }

  const stats = [
    ["Jobs", dashboard?.stats.jobs || 0],
    ["Completed", dashboard?.stats.completed_jobs || 0],
    ["Dry Runs", dashboard?.stats.dry_runs || 0],
    ["Open Notifications", dashboard?.stats.notifications_open || 0],
    ["Missing Day Out", dashboard?.stats.missing_day_out || 0],
    ["Pending Attendance", dashboard?.stats.pending_attendance || 0],
    ["High Risk", dashboard?.stats.high_risk_attendance || 0],
  ];

  return (
    <main className="min-h-screen bg-slate-100 text-slate-950">
      <header className="sticky top-0 z-20 border-b border-slate-200 bg-white/95 backdrop-blur">
        <div className="mx-auto flex max-w-7xl flex-col gap-3 px-4 py-4 md:flex-row md:items-center md:justify-between">
          <div>
            <Link href="/admin/security" className="text-sm font-semibold text-teal-700">Security Center</Link>
            <h1 className="mt-1 text-2xl font-semibold">Operations Jobs</h1>
            <p className="text-sm text-slate-500">Run auditable background jobs for attendance exceptions, notifications, and payroll preparation.</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link href="/admin/audit" className="rounded-lg border border-indigo-200 bg-indigo-50 px-3 py-2 text-sm font-medium text-indigo-700 hover:border-indigo-600">Audit Center</Link>
            <Link href="/departments/it?module=automation_jobs" className="rounded-lg bg-slate-950 px-3 py-2 text-sm font-medium text-white hover:bg-slate-800">Raw Jobs</Link>
          </div>
        </div>
      </header>

      <section className="mx-auto max-w-7xl px-4 py-6">
        {error ? <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</div> : null}
        {notice ? <div className="mb-4 rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-700">{notice}</div> : null}

        <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <div>
            <p className="text-sm font-semibold text-teal-700">Background operations</p>
            <h2 className="mt-2 text-3xl font-semibold">Factory job control</h2>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">Dry-run a job before executing it. Completed jobs create automation records and audit history, and employee-impacting jobs create notifications.</p>
          </div>
          <div className="mt-5 grid grid-cols-2 gap-2 md:grid-cols-3 xl:grid-cols-7">
            {stats.map(([label, value]) => (
              <div key={label} className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                <div className="text-xs font-medium text-slate-500">{label}</div>
                <div className="mt-1 text-2xl font-semibold">{value}</div>
              </div>
            ))}
          </div>
        </section>

        <div className="mt-5 grid gap-4 xl:grid-cols-[1fr_380px]">
          <section className="grid gap-4 md:grid-cols-2">
            {(dashboard?.available_jobs || []).map((job) => (
              <div key={job.job_type} className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h3 className="text-lg font-semibold">{job.title}</h3>
                    <p className="mt-1 text-sm leading-6 text-slate-600">{job.description}</p>
                  </div>
                  <span className="rounded-lg bg-slate-100 px-2 py-1 text-xs font-semibold text-slate-600">Manual</span>
                </div>
                <div className="mt-4 flex flex-wrap gap-2">
                  <button disabled={Boolean(busy)} onClick={() => runJob(job.job_type, true)} className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-semibold hover:border-teal-600 disabled:opacity-50">
                    {busy === `${job.job_type}-dry` ? "Checking" : "Dry Run"}
                  </button>
                  <button disabled={Boolean(busy)} onClick={() => runJob(job.job_type, false)} className="rounded-lg bg-slate-950 px-3 py-2 text-sm font-semibold text-white hover:bg-slate-800 disabled:opacity-50">
                    {busy === `${job.job_type}-run` ? "Running" : "Run Job"}
                  </button>
                </div>
              </div>
            ))}
          </section>

          <aside className="space-y-4">
            {lastResult ? (
              <section className="rounded-lg border border-teal-200 bg-teal-50 p-4 shadow-sm">
                <h2 className="font-semibold text-teal-900">Last Result</h2>
                <pre className="mt-3 max-h-64 overflow-auto whitespace-pre-wrap rounded-lg bg-white p-3 text-xs text-slate-700">{JSON.stringify(lastResult, null, 2)}</pre>
              </section>
            ) : null}
            <Queue title="Missing Day Out" rows={dashboard?.attendance_exceptions.missing_day_out || []} />
            <Queue title="Out Of Fence" rows={dashboard?.attendance_exceptions.out_of_fence || []} />
            <Queue title="High Risk Attendance" rows={dashboard?.attendance_exceptions.high_risk_attendance || []} />
            <DeviceQueue rows={dashboard?.attendance_exceptions.high_risk_devices || []} />
            <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
              <h2 className="font-semibold">Recent Jobs</h2>
              <div className="mt-3 space-y-2">
                {(dashboard?.jobs || []).length === 0 ? <p className="text-sm text-slate-500">No automation jobs have run yet.</p> : dashboard?.jobs.slice(0, 8).map((job) => (
                  <div key={job.id} className="rounded-lg border border-slate-100 bg-slate-50 p-3">
                    <div className="flex items-center justify-between gap-2">
                      <div className="truncate text-sm font-semibold">{job.data.job_type || "Job"}</div>
                      <span className={`rounded-lg border px-2 py-1 text-xs font-semibold ${statusTone(job.status)}`}>{job.status}</span>
                    </div>
                    <div className="mt-1 text-xs text-slate-500">{job.data.last_run || "-"} / {job.data.owner || "-"}</div>
                  </div>
                ))}
              </div>
            </section>
          </aside>
        </div>
      </section>
    </main>
  );
}

function DeviceQueue({ rows }: { rows: ErpRecord[] }) {
  return (
    <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-center justify-between">
        <h2 className="font-semibold">High Risk Devices</h2>
        <span className="text-sm text-slate-500">{rows.length}</span>
      </div>
      <div className="mt-3 space-y-2">
        {rows.length === 0 ? <p className="text-sm text-slate-500">No device risk events.</p> : rows.slice(0, 6).map((row) => (
          <div key={row.id} className="rounded-lg border border-slate-100 bg-slate-50 p-3">
            <div className="text-sm font-semibold">{row.data.employee_code || "Employee"}</div>
            <div className="mt-1 text-xs text-slate-500">Risk {row.data.risk_score || 0} / {row.data.risk_flags || "none"}</div>
          </div>
        ))}
      </div>
    </section>
  );
}

function Queue({ title, rows }: { title: string; rows: AttendanceRecord[] }) {
  return (
    <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-center justify-between">
        <h2 className="font-semibold">{title}</h2>
        <span className="text-sm text-slate-500">{rows.length}</span>
      </div>
      <div className="mt-3 space-y-2">
        {rows.length === 0 ? <p className="text-sm text-slate-500">No records in this queue.</p> : rows.slice(0, 6).map((row) => (
          <div key={`${title}-${row.attendance_record_id}`} className="rounded-lg border border-slate-100 bg-slate-50 p-3">
            <div className="text-sm font-semibold">{row.employee_name || row.employee_code}</div>
            <div className="mt-1 text-xs text-slate-500">{row.attendance_date} / {row.attendance_status || row.geofence_status}</div>
          </div>
        ))}
      </div>
    </section>
  );
}
