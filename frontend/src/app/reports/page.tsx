"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8000";

type ReportCard = {
  id: string;
  title: string;
  domain: string;
  description: string;
  row_count: number;
  sample: Record<string, string | number | boolean | null>[];
};

type ReportsDashboard = {
  stats: Record<string, number>;
  reports: ReportCard[];
};

type ReportDetail = ReportCard & {
  rows: Record<string, string | number | boolean | null>[];
};

async function requestReportsDashboard(token: string) {
  const response = await fetch(`${API_BASE}/api/v1/reports/dashboard`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok) throw new Error("Reports dashboard API failed");
  return (await response.json()) as ReportsDashboard;
}

async function requestReportDetail(token: string, reportId: string) {
  const response = await fetch(`${API_BASE}/api/v1/reports/${reportId}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok) throw new Error("Report API failed");
  return (await response.json()) as ReportDetail;
}

function domainTone(domain: string) {
  if (domain === "Payroll" || domain === "Finance") return "border-sky-200 bg-sky-50 text-sky-800";
  if (domain === "Geofence") return "border-indigo-200 bg-indigo-50 text-indigo-800";
  if (domain === "Leave") return "border-amber-200 bg-amber-50 text-amber-800";
  return "border-teal-200 bg-teal-50 text-teal-800";
}

function labelFor(value: string) {
  return value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export default function ReportsPage() {
  const router = useRouter();
  const [dashboard, setDashboard] = useState<ReportsDashboard | null>(null);
  const [detail, setDetail] = useState<ReportDetail | null>(null);
  const [query, setQuery] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");

  useEffect(() => {
    const token = localStorage.getItem("factorypulse_token");
    if (!token) {
      router.push("/login");
      return;
    }
    requestReportsDashboard(token)
      .then((data) => {
        setDashboard(data);
        const first = data.reports[0];
        if (first) {
          setBusy(first.id);
          requestReportDetail(token, first.id)
            .then(setDetail)
            .catch((err) => setError(err instanceof Error ? err.message : "Report API failed"))
            .finally(() => setBusy(""));
        }
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Reports dashboard API failed"));
  }, [router]);

  const reports = useMemo(() => {
    const value = query.trim().toLowerCase();
    const items = dashboard?.reports || [];
    if (!value) return items;
    return items.filter((report) => [report.title, report.domain, report.description].join(" ").toLowerCase().includes(value));
  }, [dashboard, query]);

  async function openReport(reportId: string) {
    const token = localStorage.getItem("factorypulse_token");
    if (!token) {
      router.push("/login");
      return;
    }
    setError("");
    setBusy(reportId);
    try {
      setDetail(await requestReportDetail(token, reportId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Report API failed");
    } finally {
      setBusy("");
    }
  }

  async function exportReport(reportId: string) {
    const token = localStorage.getItem("factorypulse_token");
    if (!token) {
      router.push("/login");
      return;
    }
    setError("");
    try {
      const response = await fetch(`${API_BASE}/api/v1/reports/${reportId}/export`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) throw new Error("Export failed");
      const text = await response.text();
      const blob = new Blob([text], { type: "text/csv;charset=utf-8" });
      const href = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = href;
      link.download = `${reportId}.csv`;
      link.click();
      URL.revokeObjectURL(href);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Export failed");
    }
  }

  const stats = [
    ["Reports", dashboard?.stats.reports || 0],
    ["Attendance", dashboard?.stats.attendance_records || 0],
    ["Leave", dashboard?.stats.leave_applications || 0],
    ["Payroll", dashboard?.stats.payroll_results || 0],
    ["Geofence", dashboard?.stats.geofence_validations || 0],
    ["Audit Logs", dashboard?.stats.audit_events || 0],
  ];

  const detailRows = detail?.rows || [];
  const headers = Array.from(new Set(detailRows.flatMap((row) => Object.keys(row).filter((key) => !["raw", "evidence"].includes(key))))).slice(0, 8);

  return (
    <main className="min-h-screen bg-slate-100 text-slate-950">
      <header className="sticky top-0 z-20 border-b border-slate-200 bg-white/95 backdrop-blur">
        <div className="mx-auto flex max-w-7xl flex-col gap-3 px-4 py-4 md:flex-row md:items-center md:justify-between">
          <div>
            <Link href="/" className="text-sm font-semibold text-teal-700">All departments</Link>
            <h1 className="mt-1 text-2xl font-semibold">ERP Reports</h1>
            <p className="text-sm text-slate-500">Attendance, geofence, leave, payroll, lifecycle, and finance reports from live ERP records.</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link href="/hr/attendance" className="rounded-lg border border-indigo-200 bg-indigo-50 px-3 py-2 text-sm font-medium text-indigo-700 hover:border-indigo-600">Attendance</Link>
            <Link href="/finance" className="rounded-lg bg-slate-950 px-3 py-2 text-sm font-medium text-white hover:bg-slate-800">Payroll</Link>
          </div>
        </div>
      </header>

      <section className="mx-auto max-w-7xl px-4 py-6">
        {error ? <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</div> : null}

        <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <p className="text-sm font-semibold text-teal-700">Reporting manager workspace</p>
              <h2 className="mt-2 text-3xl font-semibold">Factory analytics library</h2>
              <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">Each report is generated by the backend from authenticated live records and can be exported as CSV for audit or management review.</p>
            </div>
            <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search reports" className="h-11 rounded-lg border border-slate-300 px-3 text-sm outline-none focus:border-teal-700 lg:w-80" />
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

        <div className="mt-5 grid gap-4 xl:grid-cols-[420px_1fr]">
          <section className="rounded-lg border border-slate-200 bg-white shadow-sm">
            <div className="border-b border-slate-200 p-4">
              <h2 className="font-semibold">Report Catalog</h2>
              <p className="mt-1 text-sm text-slate-500">{reports.length} reports</p>
            </div>
            <div className="max-h-[760px] overflow-auto p-2">
              {reports.map((report) => (
                <button key={report.id} onClick={() => openReport(report.id)} className={`mb-2 w-full rounded-lg border p-3 text-left transition ${detail?.id === report.id ? "border-teal-500 bg-teal-50" : "border-slate-100 bg-white hover:border-slate-300"}`}>
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <div className="text-sm font-semibold">{report.title}</div>
                      <p className="mt-1 line-clamp-2 text-xs leading-5 text-slate-500">{report.description}</p>
                    </div>
                    <span className={`rounded-lg border px-2 py-1 text-xs font-semibold ${domainTone(report.domain)}`}>{report.domain}</span>
                  </div>
                  <div className="mt-3 flex items-center justify-between text-xs text-slate-500">
                    <span>{report.row_count} rows</span>
                    <span>{busy === report.id ? "Loading" : "Open"}</span>
                  </div>
                </button>
              ))}
            </div>
          </section>

          <section className="rounded-lg border border-slate-200 bg-white shadow-sm">
            <div className="flex flex-col gap-3 border-b border-slate-200 p-4 md:flex-row md:items-center md:justify-between">
              <div>
                <h2 className="text-xl font-semibold">{detail?.title || "Select a report"}</h2>
                <p className="mt-1 text-sm text-slate-500">{detail?.description || "Open a report from the catalog."}</p>
              </div>
              {detail ? (
                <button onClick={() => exportReport(detail.id)} className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-semibold hover:border-teal-600">Export CSV</button>
              ) : null}
            </div>

            <div className="overflow-auto">
              <table className="w-full min-w-[860px] text-left text-sm">
                <thead className="bg-slate-50 text-xs uppercase text-slate-500">
                  <tr>
                    {headers.length === 0 ? <th className="p-3">Result</th> : headers.map((header) => <th key={header} className="p-3">{labelFor(header)}</th>)}
                  </tr>
                </thead>
                <tbody>
                  {!detail ? (
                    <tr><td className="p-6 text-slate-500">No report selected.</td></tr>
                  ) : detailRows.length === 0 ? (
                    <tr><td className="p-6 text-slate-500" colSpan={Math.max(headers.length, 1)}>No rows yet. The report will populate as ERP records are created.</td></tr>
                  ) : detailRows.slice(0, 100).map((row, index) => (
                    <tr key={`${detail.id}-${index}`} className="border-t border-slate-100">
                      {headers.map((header) => (
                        <td key={header} className="max-w-56 truncate p-3">{String(row[header] ?? "-")}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </div>
      </section>
    </main>
  );
}
