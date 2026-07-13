"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8000";

type AuditEvent = {
  id: string;
  audit_id: string;
  actor: string;
  action: string;
  entity_type: string;
  entity_id: string;
  reason: string;
  ip_address: string;
  device_info: string;
  approval_reference: string;
  status: string;
  new_values: string;
  previous_values: string;
};

type AuditDashboard = {
  stats: Record<string, number>;
  events: AuditEvent[];
  permission_denied: AuditEvent[];
  sensitive_events: AuditEvent[];
  actions: { label: string; count: number }[];
  actors: { label: string; count: number }[];
  entities: { label: string; count: number }[];
};

async function requestAuditDashboard(token: string) {
  const response = await fetch(`${API_BASE}/api/v1/admin/audit-dashboard`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok) throw new Error("Audit dashboard API failed");
  return (await response.json()) as AuditDashboard;
}

function tone(action: string) {
  if (action === "permission_denied") return "border-rose-200 bg-rose-50 text-rose-800";
  if (action.includes("payroll") || action.includes("attendance")) return "border-amber-200 bg-amber-50 text-amber-800";
  if (action.includes("create") || action.includes("onboard")) return "border-emerald-200 bg-emerald-50 text-emerald-800";
  return "border-slate-200 bg-slate-50 text-slate-700";
}

export default function AdminAuditPage() {
  const router = useRouter();
  const [dashboard, setDashboard] = useState<AuditDashboard | null>(null);
  const [query, setQuery] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    const token = localStorage.getItem("factorypulse_token");
    if (!token) {
      router.push("/login");
      return;
    }
    requestAuditDashboard(token)
      .then(setDashboard)
      .catch((err) => setError(err instanceof Error ? err.message : "Audit dashboard API failed"));
  }, [router]);

  const events = useMemo(() => {
    const value = query.trim().toLowerCase();
    const rows = dashboard?.events || [];
    if (!value) return rows;
    return rows.filter((row) =>
      [row.audit_id, row.actor, row.action, row.entity_type, row.entity_id, row.reason, row.status].join(" ").toLowerCase().includes(value),
    );
  }, [dashboard, query]);

  function exportCsv() {
    const token = localStorage.getItem("factorypulse_token");
    if (!token) {
      router.push("/login");
      return;
    }
    fetch(`${API_BASE}/api/v1/admin/audit/export`, { headers: { Authorization: `Bearer ${token}` } })
      .then((response) => {
        if (!response.ok) throw new Error("Audit export failed");
        return response.text();
      })
      .then((text) => {
        const blob = new Blob([text], { type: "text/csv;charset=utf-8" });
        const href = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = href;
        link.download = "audit-logs.csv";
        link.click();
        URL.revokeObjectURL(href);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Audit export failed"));
  }

  const stats = [
    ["Events", dashboard?.stats.events || 0],
    ["Denied", dashboard?.stats.permission_denied || 0],
    ["Sensitive", dashboard?.stats.sensitive_events || 0],
    ["Actors", dashboard?.stats.actors || 0],
    ["Actions", dashboard?.stats.actions || 0],
    ["Entities", dashboard?.stats.entities || 0],
  ];

  return (
    <main className="min-h-screen bg-slate-100 text-slate-950">
      <header className="sticky top-0 z-20 border-b border-slate-200 bg-white/95 backdrop-blur">
        <div className="mx-auto flex max-w-7xl flex-col gap-3 px-4 py-4 md:flex-row md:items-center md:justify-between">
          <div>
            <Link href="/admin/security" className="text-sm font-semibold text-teal-700">Security Center</Link>
            <h1 className="mt-1 text-2xl font-semibold">Audit Center</h1>
            <p className="text-sm text-slate-500">Trace sensitive ERP actions, permission denials, approvals, payroll, attendance, and HR changes.</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button onClick={exportCsv} className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium hover:border-teal-600">Export CSV</button>
            <Link href="/reports" className="rounded-lg border border-indigo-200 bg-indigo-50 px-3 py-2 text-sm font-medium text-indigo-700 hover:border-indigo-600">Reports</Link>
            <Link href="/departments/admin?module=audit_logs" className="rounded-lg bg-slate-950 px-3 py-2 text-sm font-medium text-white hover:bg-slate-800">Raw Table</Link>
          </div>
        </div>
      </header>

      <section className="mx-auto max-w-7xl px-4 py-6">
        {error ? <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</div> : null}

        <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <p className="text-sm font-semibold text-teal-700">Audit governance</p>
              <h2 className="mt-2 text-3xl font-semibold">ERP evidence trail</h2>
              <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">Every sensitive action below is read from backend audit records. Use search and export for internal audit, HR review, and finance control evidence.</p>
            </div>
            <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search actor, action, entity, reason" className="h-11 rounded-lg border border-slate-300 px-3 text-sm outline-none focus:border-teal-700 lg:w-96" />
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

        <div className="mt-5 grid gap-4 xl:grid-cols-[1fr_380px]">
          <section className="rounded-lg border border-slate-200 bg-white shadow-sm">
            <div className="border-b border-slate-200 p-4">
              <h2 className="text-xl font-semibold">Audit Events</h2>
              <p className="mt-1 text-sm text-slate-500">{events.length} visible events.</p>
            </div>
            <div className="overflow-auto">
              <table className="w-full min-w-[980px] text-left text-sm">
                <thead className="bg-slate-50 text-xs uppercase text-slate-500">
                  <tr><th className="p-3">Action</th><th className="p-3">Actor</th><th className="p-3">Entity</th><th className="p-3">Reason</th><th className="p-3">Status</th></tr>
                </thead>
                <tbody>
                  {events.length === 0 ? (
                    <tr><td className="p-6 text-slate-500" colSpan={5}>No audit events found.</td></tr>
                  ) : events.map((row) => (
                    <tr key={row.audit_id || row.id} className="border-t border-slate-100">
                      <td className="p-3"><span className={`rounded-lg border px-2 py-1 text-xs font-semibold ${tone(row.action)}`}>{row.action || "-"}</span></td>
                      <td className="p-3">{row.actor || "-"}</td>
                      <td className="p-3"><div className="font-medium">{row.entity_type || "-"}</div><div className="text-xs text-slate-500">{row.entity_id || row.audit_id}</div></td>
                      <td className="p-3"><div className="line-clamp-2 max-w-md">{row.reason || "-"}</div></td>
                      <td className="p-3">{row.status || "-"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <aside className="space-y-4">
            <Queue title="Permission Denied" rows={dashboard?.permission_denied || []} />
            <Queue title="Sensitive Events" rows={dashboard?.sensitive_events || []} />
            <Breakdown title="Top Actions" rows={dashboard?.actions || []} />
            <Breakdown title="Top Actors" rows={dashboard?.actors || []} />
            <Breakdown title="Top Entities" rows={dashboard?.entities || []} />
          </aside>
        </div>
      </section>
    </main>
  );
}

function Queue({ title, rows }: { title: string; rows: AuditEvent[] }) {
  return (
    <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-center justify-between">
        <h2 className="font-semibold">{title}</h2>
        <span className="text-sm text-slate-500">{rows.length}</span>
      </div>
      <div className="mt-3 space-y-2">
        {rows.length === 0 ? <p className="text-sm text-slate-500">No matching audit events.</p> : rows.slice(0, 6).map((row) => (
          <div key={`${title}-${row.audit_id || row.id}`} className="rounded-lg border border-slate-100 bg-slate-50 p-3">
            <div className="text-sm font-semibold">{row.action || "-"}</div>
            <div className="mt-1 text-xs text-slate-500">{row.actor || "-"} / {row.entity_type || "-"}</div>
          </div>
        ))}
      </div>
    </section>
  );
}

function Breakdown({ title, rows }: { title: string; rows: { label: string; count: number }[] }) {
  return (
    <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <h2 className="font-semibold">{title}</h2>
      <div className="mt-3 space-y-2">
        {rows.length === 0 ? <p className="text-sm text-slate-500">No data yet.</p> : rows.slice(0, 6).map((row) => (
          <div key={`${title}-${row.label}`} className="flex items-center justify-between gap-2 rounded-lg border border-slate-100 bg-slate-50 p-3">
            <span className="truncate text-sm font-medium">{row.label || "unknown"}</span>
            <span className="rounded-lg bg-white px-2 py-1 text-xs font-semibold text-slate-700">{row.count}</span>
          </div>
        ))}
      </div>
    </section>
  );
}
