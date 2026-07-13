"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8000";

type HrSection = { resource: string; label: string; count: number; active: number; pending: number; failed: number };
type HrException = { resource: string; id: string; employee_code: string; status: string; reason: string };
type HrOverview = {
  stats: Record<string, number>;
  sections: HrSection[];
  exceptions: HrException[];
};

const CORE_ACTIONS = [
  { title: "Onboard Employee", body: "Create employee master, private details, salary, location, device, biometric metadata, and lifecycle records.", href: "/hr/employees" },
  { title: "Review Attendance", body: "Approve records, review geofence evidence, correct missing punches, and export attendance.", href: "/hr/attendance" },
  { title: "Manage Leave & Holidays", body: "Approve leave, allocate balances, create paid holidays, and protect payroll impact.", href: "/hr/leave" },
  { title: "Create Work Location", body: "Factory, warehouse, site, office, remote, and temporary approved locations.", href: "/departments/hr?module=work_locations" },
  { title: "Configure Geofence", body: "Circular or polygon boundaries with GPS accuracy, approval status, and versions.", href: "/departments/hr?module=geofences" },
  { title: "Assign Employee Location", body: "Primary, temporary, shift-specific, or date-specific work-location assignment.", href: "/departments/hr?module=employee_location_assignments" },
  { title: "Review Attendance Evidence", body: "Location events, biometric events, validation results, and audit logs.", href: "/departments/hr?module=attendance_validation_results" },
];

function statLabel(key: string) {
  return key.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function statusTone(section: HrSection) {
  if (section.failed > 0) return "border-rose-200 bg-rose-50 text-rose-800";
  if (section.pending > 0) return "border-amber-200 bg-amber-50 text-amber-800";
  return "border-emerald-200 bg-emerald-50 text-emerald-800";
}

export default function HrPage() {
  const router = useRouter();
  const [data, setData] = useState<HrOverview | null>(null);
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");

  useEffect(() => {
    const token = localStorage.getItem("factorypulse_token");
    if (!token) {
      router.push("/login");
      return;
    }
    fetch(`${API_BASE}/api/v1/hr/overview`, { headers: { Authorization: `Bearer ${token}` } })
      .then((response) => {
        if (!response.ok) throw new Error("HR overview API failed");
        return response.json();
      })
      .then((body) => setData(body))
      .catch((err) => setError(err instanceof Error ? err.message : "HR overview API failed"));
  }, [router]);

  const sections = useMemo(() => {
    const value = query.trim().toLowerCase();
    if (!value) return data?.sections || [];
    return (data?.sections || []).filter((section) => [section.label, section.resource].join(" ").toLowerCase().includes(value));
  }, [data, query]);

  const headlineStats = [
    "employees",
    "work_locations",
    "geofences",
    "location_assignments",
    "attendance_records",
    "out_of_fence_attempts",
    "pending_approvals",
    "biometric_events",
  ];

  return (
    <main className="min-h-screen bg-slate-100 text-slate-950">
      <header className="sticky top-0 z-20 border-b border-slate-200 bg-white/95 backdrop-blur">
        <div className="mx-auto flex max-w-7xl flex-col gap-3 px-4 py-4 md:flex-row md:items-center md:justify-between">
          <div>
            <Link href="/" className="text-sm font-semibold text-teal-700">All departments</Link>
            <h1 className="mt-1 text-2xl font-semibold">HR Command Center</h1>
            <p className="text-sm text-slate-500">Employee lifecycle, geofenced attendance, biometric evidence, leave, salary, and audit operations.</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link href="/hr/employees" className="rounded-lg border border-teal-200 bg-teal-50 px-3 py-2 text-sm font-medium text-teal-700 hover:border-teal-600">Employee Master</Link>
            <Link href="/hr/attendance" className="rounded-lg border border-indigo-200 bg-indigo-50 px-3 py-2 text-sm font-medium text-indigo-700 hover:border-indigo-600">Attendance</Link>
            <Link href="/hr/leave" className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm font-medium text-amber-700 hover:border-amber-600">Leave & Holidays</Link>
            <Link href="/departments/hr" className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium hover:border-teal-600">Full HR Modules</Link>
            <Link href="/finance" className="rounded-lg border border-sky-200 bg-sky-50 px-3 py-2 text-sm font-medium text-sky-700 hover:border-sky-600">Finance Payroll</Link>
            <Link href="/departments/finance?module=payroll_adjustments" className="rounded-lg bg-slate-950 px-3 py-2 text-sm font-medium text-white hover:bg-slate-800">Payroll Adjustments</Link>
          </div>
        </div>
      </header>

      <section className="mx-auto max-w-7xl px-4 py-6">
        {error ? <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</div> : null}

        <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <p className="text-sm font-semibold uppercase tracking-wide text-teal-700">Expert HR operations</p>
              <h2 className="mt-2 text-3xl font-semibold tracking-tight">Factory workforce control</h2>
              <p className="mt-2 max-w-3xl text-sm text-slate-600">Every card below reads live backend data. Configure work locations, geofences, employee assignments, attendance evidence, leave, payroll impact, and audit records from real Supabase-backed APIs.</p>
            </div>
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search HR section"
              className="h-11 rounded-lg border border-slate-300 bg-white px-3 text-sm outline-none focus:border-teal-700 lg:w-80"
            />
          </div>

          <div className="mt-5 grid grid-cols-2 gap-2 md:grid-cols-4">
            {headlineStats.map((key) => (
              <div key={key} className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                <div className="text-xs font-medium text-slate-500">{statLabel(key)}</div>
                <div className="mt-1 text-2xl font-semibold">{data?.stats[key] || 0}</div>
              </div>
            ))}
          </div>
        </div>

        <div className="mt-5 grid gap-4 lg:grid-cols-[1fr_360px]">
          <section className="grid gap-4 md:grid-cols-2">
            {sections.map((section) => (
              <Link key={section.resource} href={`/departments/hr?module=${section.resource}`} className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm transition hover:-translate-y-0.5 hover:border-teal-600 hover:shadow-md">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h3 className="text-lg font-semibold">{section.label}</h3>
                    <p className="mt-1 text-sm text-slate-500">/api/modules/{section.resource}</p>
                  </div>
                  <span className={`rounded-lg border px-2.5 py-1 text-xs font-semibold ${statusTone(section)}`}>
                    {section.failed > 0 ? "Needs review" : section.pending > 0 ? "Pending" : "Stable"}
                  </span>
                </div>
                <div className="mt-4 grid grid-cols-4 gap-2 border-t border-slate-100 pt-3">
                  <Metric label="Total" value={section.count} />
                  <Metric label="Active" value={section.active} />
                  <Metric label="Pending" value={section.pending} />
                  <Metric label="Issues" value={section.failed} />
                </div>
              </Link>
            ))}
          </section>

          <aside className="space-y-4">
            <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
              <h2 className="font-semibold">Critical Setup</h2>
              <div className="mt-3 space-y-2">
                {CORE_ACTIONS.map((action) => (
                  <Link key={action.title} href={action.href} className="block rounded-lg border border-slate-100 bg-slate-50 p-3 hover:border-teal-500 hover:bg-white">
                    <div className="text-sm font-semibold">{action.title}</div>
                    <div className="mt-1 text-xs leading-5 text-slate-600">{action.body}</div>
                  </Link>
                ))}
              </div>
            </div>

            <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
              <div className="flex items-center justify-between">
                <h2 className="font-semibold">Exceptions</h2>
                <span className="text-sm text-slate-500">{data?.exceptions.length || 0}</span>
              </div>
              <div className="mt-3 space-y-2">
                {(data?.exceptions || []).length === 0 ? (
                  <p className="text-sm text-slate-500">No out-of-fence, approval, or validation exceptions yet.</p>
                ) : data?.exceptions.map((item, index) => (
                  <div key={`${item.resource}-${item.id}-${index}`} className="rounded-lg border border-slate-100 p-3">
                    <div className="flex items-center justify-between gap-2">
                      <div className="truncate text-sm font-medium">{item.employee_code || "Unassigned"}</div>
                      <span className="rounded-lg bg-amber-100 px-2 py-1 text-xs font-semibold text-amber-800">{item.status}</span>
                    </div>
                    <div className="mt-1 line-clamp-2 text-xs text-slate-500">{item.reason || item.resource}</div>
                  </div>
                ))}
              </div>
            </div>
          </aside>
        </div>
      </section>
    </main>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <div className="text-lg font-semibold">{value}</div>
      <div className="text-xs text-slate-500">{label}</div>
    </div>
  );
}
