"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8000";

type Department = {
  id: string;
  name: string;
  description: string;
  module_count: number;
  record_count: number;
  modules: { resource: string; label: string; count: number }[];
};
type PriorityWork = { department: string; resource: string; title: string; status: string };
type Dashboard = {
  database: string;
  department_count: number;
  module_count: number;
  record_count: number;
  status_counts: Record<string, number>;
  departments: Department[];
  priority_work: PriorityWork[];
};

const DEPARTMENT_ACCENTS = [
  "border-teal-200 bg-teal-50 text-teal-800",
  "border-sky-200 bg-sky-50 text-sky-800",
  "border-emerald-200 bg-emerald-50 text-emerald-800",
  "border-amber-200 bg-amber-50 text-amber-800",
  "border-rose-200 bg-rose-50 text-rose-800",
  "border-indigo-200 bg-indigo-50 text-indigo-800",
  "border-cyan-200 bg-cyan-50 text-cyan-800",
  "border-lime-200 bg-lime-50 text-lime-800",
];

function departmentInitials(name: string) {
  return name
    .split(/[\s&]+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toUpperCase();
}

function accentFor(index: number) {
  return DEPARTMENT_ACCENTS[index % DEPARTMENT_ACCENTS.length];
}

export default function HomePage() {
  const router = useRouter();
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [query, setQuery] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    const token = localStorage.getItem("factorypulse_token");
    if (!token) {
      router.push("/login");
      return;
    }
    fetch(`${API_BASE}/api/dashboard`, { headers: { Authorization: `Bearer ${token}` } })
      .then((response) => {
        if (!response.ok) throw new Error("Dashboard API failed");
        return response.json();
      })
      .then((data) => setDashboard(data))
      .catch((err) => setError(err instanceof Error ? err.message : "Dashboard API failed"));
  }, [router]);

  const departments = useMemo(() => {
    const value = query.trim().toLowerCase();
    if (!dashboard || !value) return dashboard?.departments || [];
    return dashboard.departments.filter((department) =>
      [department.name, department.description, ...department.modules.map((item) => item.label)]
        .join(" ")
        .toLowerCase()
        .includes(value)
    );
  }, [dashboard, query]);

  const stats = [
    ["Departments", dashboard?.department_count || 0],
    ["Live modules", dashboard?.module_count || 0],
    ["Records", dashboard?.record_count || 0],
    ["Priority items", dashboard?.priority_work.length || 0],
  ];

  return (
    <main className="min-h-screen bg-slate-100 text-slate-950">
      <header className="sticky top-0 z-20 border-b border-slate-200 bg-white/95 backdrop-blur">
        <div className="mx-auto flex max-w-7xl flex-col gap-4 px-4 py-4 md:flex-row md:items-center md:justify-between">
          <div>
            <h1 className="text-xl font-semibold">FactoryPulse ERP</h1>
            <p className="text-sm text-slate-500">Live department control center for sugar factory operations.</p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <span className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm font-medium text-emerald-700">DB {dashboard?.database || "checking"}</span>
            <Link className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium hover:border-teal-600" href="/mobile">Mobile view</Link>
            <button className="rounded-lg bg-slate-950 px-3 py-2 text-sm font-medium text-white hover:bg-slate-800" onClick={() => { localStorage.removeItem("factorypulse_token"); router.push("/login"); }}>Logout</button>
          </div>
        </div>
      </header>

      <section className="mx-auto max-w-7xl px-4 py-6">
        {error && <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</div>}

        <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <p className="text-sm font-semibold uppercase tracking-wide text-teal-700">ERP command dashboard</p>
              <h2 className="mt-2 text-3xl font-semibold tracking-tight text-slate-950">All departments</h2>
              <p className="mt-2 max-w-2xl text-sm text-slate-600">Open any department card to manage live records, modules, approvals, employee workflows, production, finance, cane, security, environment, IT, and projects.</p>
            </div>
            <div className="grid grid-cols-2 gap-2 md:grid-cols-4 lg:min-w-[520px]">
              {stats.map(([label, value]) => (
                <div key={label} className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                  <div className="text-xs font-medium text-slate-500">{label}</div>
                  <div className="mt-1 text-2xl font-semibold">{value}</div>
                </div>
              ))}
            </div>
          </div>

          <div className="mt-5 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <div className="flex flex-wrap gap-2">
              {Object.entries(dashboard?.status_counts || {}).slice(0, 6).map(([status, count]) => (
                <span key={status} className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-medium text-slate-700">
                  {status}: {count}
                </span>
              ))}
              {Object.keys(dashboard?.status_counts || {}).length === 0 && (
                <span className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-medium text-slate-500">Status mix appears after records are created</span>
              )}
            </div>
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search department or module"
              className="h-11 rounded-lg border border-slate-300 bg-white px-3 text-sm outline-none focus:border-teal-700 md:w-80"
            />
          </div>
        </div>

        <div className="mt-5 grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {departments.map((department, index) => {
            const accent = accentFor(index);
            const priorityCount = (dashboard?.priority_work || []).filter((item) => item.department === department.name).length;
            return (
              <Link
                key={department.id}
                href={`/departments/${department.id}`}
                className="group rounded-lg border border-slate-200 bg-white p-4 shadow-sm transition hover:-translate-y-0.5 hover:border-teal-500 hover:shadow-md"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex min-w-0 items-start gap-3">
                    <div className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-lg border text-sm font-black ${accent}`}>
                      {departmentInitials(department.name)}
                    </div>
                    <div className="min-w-0">
                      <h3 className="truncate text-lg font-semibold text-slate-950">{department.name}</h3>
                      <p className="mt-1 line-clamp-2 min-h-10 text-sm text-slate-600">{department.description}</p>
                    </div>
                  </div>
                  <span className="rounded-lg bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-600">{department.record_count}</span>
                </div>

                <div className="mt-4 grid grid-cols-3 gap-2 border-y border-slate-100 py-3">
                  <div>
                    <div className="text-lg font-semibold">{department.module_count}</div>
                    <div className="text-xs text-slate-500">Modules</div>
                  </div>
                  <div>
                    <div className="text-lg font-semibold">{department.record_count}</div>
                    <div className="text-xs text-slate-500">Records</div>
                  </div>
                  <div>
                    <div className="text-lg font-semibold">{priorityCount}</div>
                    <div className="text-xs text-slate-500">Priority</div>
                  </div>
                </div>

                <div className="mt-3 flex flex-wrap gap-2">
                  {department.modules.slice(0, 7).map((module) => (
                    <span key={module.resource} className="max-w-full truncate rounded-lg bg-slate-50 px-2.5 py-1.5 text-xs font-medium text-slate-700">
                      {module.label} <span className="text-slate-400">{module.count}</span>
                    </span>
                  ))}
                  {department.modules.length > 7 && (
                    <span className="rounded-lg bg-slate-900 px-2.5 py-1.5 text-xs font-medium text-white">+{department.modules.length - 7} more</span>
                  )}
                </div>

                <div className="mt-4 flex items-center justify-between text-sm">
                  <span className="font-medium text-teal-700">Open workspace</span>
                  <span className="text-slate-400 transition group-hover:translate-x-1 group-hover:text-teal-700">-&gt;</span>
                </div>
              </Link>
            );
          })}
        </div>

        <section className="mt-5 rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
          <div className="flex items-center justify-between gap-3">
            <h2 className="font-semibold">Priority Work</h2>
            <span className="text-sm text-slate-500">{dashboard?.priority_work.length || 0} active</span>
          </div>
          <div className="mt-3 grid gap-2 md:grid-cols-2 xl:grid-cols-4">
            {(dashboard?.priority_work || []).length === 0 ? (
              <p className="text-sm text-slate-500">No open priority work yet.</p>
            ) : dashboard?.priority_work.slice(0, 8).map((item, index) => (
              <div key={`${item.resource}-${index}`} className="rounded-lg border border-slate-100 bg-slate-50 p-3">
                <div className="flex items-center justify-between gap-2">
                  <div className="truncate text-sm font-medium">{item.title}</div>
                  <span className="rounded-lg bg-amber-100 px-2 py-1 text-xs font-semibold text-amber-800">{item.status}</span>
                </div>
                <div className="mt-1 truncate text-xs text-slate-500">{item.department} / {item.resource.replaceAll("_", " ")}</div>
              </div>
            ))}
          </div>
        </section>
      </section>
    </main>
  );
}
