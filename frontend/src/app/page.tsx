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
            <p className="text-sm text-slate-500">Factory command center connected to live API and Supabase.</p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <span className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700">DB {dashboard?.database || "checking"}</span>
            <Link className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium" href="/mobile">Mobile view</Link>
            <button className="rounded-lg bg-slate-950 px-3 py-2 text-sm font-medium text-white" onClick={() => { localStorage.removeItem("factorypulse_token"); router.push("/login"); }}>Logout</button>
          </div>
        </div>
      </header>

      <section className="mx-auto max-w-7xl px-4 py-6">
        {error && <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</div>}

        <div className="grid gap-3 md:grid-cols-4">
          {stats.map(([label, value]) => (
            <div key={label} className="rounded-lg border border-slate-200 bg-white p-4">
              <div className="text-sm text-slate-500">{label}</div>
              <div className="mt-2 text-2xl font-semibold">{value}</div>
            </div>
          ))}
        </div>

        <div className="mt-5 grid gap-5 lg:grid-cols-[1fr_360px]">
          <section>
            <div className="mb-3 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
              <div>
                <h2 className="text-2xl font-semibold">Department Workspaces</h2>
                <p className="text-sm text-slate-600">Search modules, open a department, and create validated production records.</p>
              </div>
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Search department or module"
                className="h-10 rounded-lg border border-slate-300 bg-white px-3 text-sm outline-none focus:border-teal-700 md:w-72"
              />
            </div>

            <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
              {departments.map((department) => (
                <Link key={department.id} href={`/departments/${department.id}`} className="rounded-lg border border-slate-200 bg-white p-4 transition hover:border-teal-600 hover:shadow-sm">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <h3 className="text-lg font-semibold">{department.name}</h3>
                      <p className="mt-1 text-sm text-slate-600">{department.description}</p>
                    </div>
                    <span className="rounded-lg bg-slate-100 px-2.5 py-1 text-xs text-slate-600">{department.record_count} records</span>
                  </div>
                  <div className="mt-4 grid grid-cols-2 gap-2 text-sm">
                    {department.modules.slice(0, 6).map((module) => (
                      <div key={module.resource} className="rounded-lg bg-slate-50 px-3 py-2">
                        <div className="truncate font-medium">{module.label}</div>
                        <div className="text-xs text-slate-500">{module.count} rows</div>
                      </div>
                    ))}
                  </div>
                </Link>
              ))}
            </div>
          </section>

          <aside className="space-y-4">
            <div className="rounded-lg border border-slate-200 bg-white p-4">
              <h2 className="font-semibold">Priority Work</h2>
              <div className="mt-3 space-y-2">
                {(dashboard?.priority_work || []).length === 0 ? (
                  <p className="text-sm text-slate-500">No open priority work yet.</p>
                ) : dashboard?.priority_work.map((item, index) => (
                  <div key={`${item.resource}-${index}`} className="rounded-lg border border-slate-100 p-3">
                    <div className="flex items-center justify-between gap-2">
                      <div className="truncate text-sm font-medium">{item.title}</div>
                      <span className="rounded-lg bg-amber-50 px-2 py-1 text-xs text-amber-700">{item.status}</span>
                    </div>
                    <div className="mt-1 text-xs text-slate-500">{item.department} / {item.resource.replaceAll("_", " ")}</div>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-lg border border-slate-200 bg-white p-4">
              <h2 className="font-semibold">Status Mix</h2>
              <div className="mt-3 space-y-2">
                {Object.entries(dashboard?.status_counts || {}).length === 0 ? (
                  <p className="text-sm text-slate-500">Status chart appears after records are created.</p>
                ) : Object.entries(dashboard?.status_counts || {}).map(([status, count]) => (
                  <div key={status} className="flex items-center justify-between text-sm">
                    <span>{status}</span>
                    <span className="font-semibold">{count}</span>
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
