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

type PriorityWork = {
  department: string;
  resource: string;
  title: string;
  status: string;
};

type Dashboard = {
  database: string;
  department_count: number;
  module_count: number;
  record_count: number;
  status_counts: Record<string, number>;
  departments: Department[];
  priority_work: PriorityWork[];
};

const DEPARTMENT_STYLES = [
  {
    badge: "border-teal-200 bg-teal-50 text-teal-800",
    line: "bg-teal-500",
    hover: "hover:border-teal-300 hover:shadow-teal-100",
  },
  {
    badge: "border-sky-200 bg-sky-50 text-sky-800",
    line: "bg-sky-500",
    hover: "hover:border-sky-300 hover:shadow-sky-100",
  },
  {
    badge: "border-emerald-200 bg-emerald-50 text-emerald-800",
    line: "bg-emerald-500",
    hover: "hover:border-emerald-300 hover:shadow-emerald-100",
  },
  {
    badge: "border-amber-200 bg-amber-50 text-amber-800",
    line: "bg-amber-500",
    hover: "hover:border-amber-300 hover:shadow-amber-100",
  },
  {
    badge: "border-rose-200 bg-rose-50 text-rose-800",
    line: "bg-rose-500",
    hover: "hover:border-rose-300 hover:shadow-rose-100",
  },
  {
    badge: "border-violet-200 bg-violet-50 text-violet-800",
    line: "bg-violet-500",
    hover: "hover:border-violet-300 hover:shadow-violet-100",
  },
  {
    badge: "border-cyan-200 bg-cyan-50 text-cyan-800",
    line: "bg-cyan-500",
    hover: "hover:border-cyan-300 hover:shadow-cyan-100",
  },
  {
    badge: "border-lime-200 bg-lime-50 text-lime-800",
    line: "bg-lime-500",
    hover: "hover:border-lime-300 hover:shadow-lime-100",
  },
];

const QUICK_LINKS = [
  { label: "HR Command", href: "/hr", style: "border-teal-200 bg-teal-50 text-teal-800 hover:border-teal-500" },
  { label: "Finance Payroll", href: "/finance", style: "border-sky-200 bg-sky-50 text-sky-800 hover:border-sky-500" },
  { label: "Reports", href: "/reports", style: "border-indigo-200 bg-indigo-50 text-indigo-800 hover:border-indigo-500" },
  { label: "Security", href: "/admin/security", style: "border-rose-200 bg-rose-50 text-rose-800 hover:border-rose-500" },
  { label: "Employee App", href: "/mobile", style: "border-amber-200 bg-amber-50 text-amber-800 hover:border-amber-500" },
];

function departmentInitials(name: string) {
  return name
    .split(/[\s&/-]+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toUpperCase();
}

function styleFor(index: number) {
  return DEPARTMENT_STYLES[index % DEPARTMENT_STYLES.length];
}

async function requestDashboard(token: string) {
  const response = await fetch(`${API_BASE}/api/dashboard`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok) throw new Error("Dashboard API failed");
  return (await response.json()) as Dashboard;
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

    requestDashboard(token)
      .then((data) => setDashboard(data))
      .catch((err) => setError(err instanceof Error ? err.message : "Dashboard API failed"));
  }, [router]);

  const departments = useMemo(() => {
    const value = query.trim().toLowerCase();
    if (!dashboard) return [];
    if (!value) return dashboard.departments;

    return dashboard.departments.filter((department) =>
      [department.name, department.description, ...department.modules.map((item) => item.label)]
        .join(" ")
        .toLowerCase()
        .includes(value),
    );
  }, [dashboard, query]);

  const priorityByDepartment = useMemo(() => {
    const items = new Map<string, number>();
    for (const item of dashboard?.priority_work || []) {
      items.set(item.department, (items.get(item.department) || 0) + 1);
    }
    return items;
  }, [dashboard]);

  const stats = [
    { label: "Departments", value: dashboard?.department_count || 0 },
    { label: "Modules", value: dashboard?.module_count || 0 },
    { label: "Live records", value: dashboard?.record_count || 0 },
    { label: "Priority work", value: dashboard?.priority_work.length || 0 },
  ];

  return (
    <main className="min-h-screen bg-[#f5f7fb] text-slate-950">
      <header className="sticky top-0 z-20 border-b border-slate-200 bg-white/95 backdrop-blur">
        <div className="mx-auto flex max-w-7xl flex-col gap-4 px-4 py-4 md:flex-row md:items-center md:justify-between">
          <div className="min-w-0">
            <p className="text-xs font-semibold uppercase text-teal-700">FactoryPulse ERP</p>
            <h1 className="mt-1 text-2xl font-semibold text-slate-950">Department workspaces</h1>
            <p className="mt-1 text-sm text-slate-500">Open every sugar factory department from one live command home.</p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <span className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm font-medium text-emerald-700">
              DB {dashboard?.database || "checking"}
            </span>
            {QUICK_LINKS.map((link) => (
              <Link key={link.href} className={`rounded-lg border px-3 py-2 text-sm font-medium ${link.style}`} href={link.href}>
                {link.label}
              </Link>
            ))}
            <button
              className="rounded-lg bg-slate-950 px-3 py-2 text-sm font-medium text-white hover:bg-slate-800"
              onClick={() => {
                localStorage.removeItem("factorypulse_token");
                router.push("/login");
              }}
            >
              Logout
            </button>
          </div>
        </div>
      </header>

      <section className="mx-auto max-w-7xl px-4 py-6">
        {error && <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</div>}

        <div className="grid gap-4 lg:grid-cols-[1.35fr_0.65fr]">
          <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
            <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
              <div>
                <p className="text-sm font-semibold text-teal-700">All departments</p>
                <h2 className="mt-2 text-3xl font-semibold text-slate-950">Choose a department card</h2>
                <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
                  Each card opens its complete workspace with modules, records, approvals, operational tracking, and live database-backed activity.
                </p>
              </div>
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-4 md:min-w-[440px]">
                {stats.map((item) => (
                  <div key={item.label} className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                    <div className="text-xs font-medium text-slate-500">{item.label}</div>
                    <div className="mt-1 text-2xl font-semibold text-slate-950">{item.value}</div>
                  </div>
                ))}
              </div>
            </div>

            <div className="mt-5 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Search department, module, or workflow"
                className="h-11 rounded-lg border border-slate-300 bg-white px-3 text-sm outline-none focus:border-teal-700 md:w-96"
              />
              <div className="flex flex-wrap gap-2">
                {Object.entries(dashboard?.status_counts || {})
                  .slice(0, 4)
                  .map(([status, count]) => (
                    <span key={status} className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-medium text-slate-700">
                      {status}: {count}
                    </span>
                  ))}
              </div>
            </div>
          </section>

          <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-sm font-semibold text-amber-700">Priority work</p>
                <h2 className="mt-1 text-xl font-semibold">Needs attention</h2>
              </div>
              <span className="rounded-lg bg-amber-50 px-3 py-2 text-sm font-semibold text-amber-800">
                {dashboard?.priority_work.length || 0}
              </span>
            </div>
            <div className="mt-4 space-y-3">
              {(dashboard?.priority_work || []).length === 0 ? (
                <p className="rounded-lg border border-slate-100 bg-slate-50 p-3 text-sm text-slate-500">No open priority work right now.</p>
              ) : (
                dashboard?.priority_work.slice(0, 4).map((item, index) => (
                  <div key={`${item.resource}-${index}`} className="rounded-lg border border-slate-100 bg-slate-50 p-3">
                    <div className="flex items-center justify-between gap-2">
                      <div className="truncate text-sm font-semibold text-slate-900">{item.title}</div>
                      <span className="rounded-lg bg-white px-2 py-1 text-xs font-semibold text-amber-800">{item.status}</span>
                    </div>
                    <div className="mt-1 truncate text-xs text-slate-500">
                      {item.department} / {item.resource.replaceAll("_", " ")}
                    </div>
                  </div>
                ))
              )}
            </div>
          </section>
        </div>

        <section className="mt-5 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {departments.map((department, index) => {
            const style = styleFor(index);
            const priorityCount = priorityByDepartment.get(department.name) || 0;
            const modulePreview = department.modules.slice(0, 6);

            return (
              <Link
                key={department.id}
                href={`/departments/${department.id}`}
                className={`group relative overflow-hidden rounded-lg border border-slate-200 bg-white p-4 shadow-sm transition hover:-translate-y-0.5 hover:shadow-lg ${style.hover}`}
              >
                <div className={`absolute left-0 top-0 h-1 w-full ${style.line}`} />
                <div className="flex items-start justify-between gap-3">
                  <div className="flex min-w-0 items-start gap-3">
                    <div className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-lg border text-sm font-black ${style.badge}`}>
                      {departmentInitials(department.name)}
                    </div>
                    <div className="min-w-0">
                      <h3 className="truncate text-lg font-semibold text-slate-950">{department.name}</h3>
                      <p className="mt-1 line-clamp-2 min-h-10 text-sm leading-5 text-slate-600">{department.description}</p>
                    </div>
                  </div>
                  <span className="rounded-lg bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-600">
                    {department.record_count}
                  </span>
                </div>

                <div className="mt-4 grid grid-cols-3 gap-2">
                  <div className="rounded-lg bg-slate-50 p-3">
                    <div className="text-xl font-semibold text-slate-950">{department.module_count}</div>
                    <div className="text-xs text-slate-500">Modules</div>
                  </div>
                  <div className="rounded-lg bg-slate-50 p-3">
                    <div className="text-xl font-semibold text-slate-950">{department.record_count}</div>
                    <div className="text-xs text-slate-500">Records</div>
                  </div>
                  <div className="rounded-lg bg-slate-50 p-3">
                    <div className="text-xl font-semibold text-slate-950">{priorityCount}</div>
                    <div className="text-xs text-slate-500">Priority</div>
                  </div>
                </div>

                <div className="mt-4 flex flex-wrap gap-2">
                  {modulePreview.map((module) => (
                    <span key={module.resource} className="max-w-full truncate rounded-lg border border-slate-100 bg-white px-2.5 py-1.5 text-xs font-medium text-slate-700">
                      {module.label} <span className="text-slate-400">{module.count}</span>
                    </span>
                  ))}
                  {department.modules.length > modulePreview.length && (
                    <span className="rounded-lg bg-slate-950 px-2.5 py-1.5 text-xs font-medium text-white">
                      +{department.modules.length - modulePreview.length} more
                    </span>
                  )}
                </div>

                <div className="mt-4 flex items-center justify-between border-t border-slate-100 pt-3 text-sm">
                  <span className="font-semibold text-teal-700">Open department</span>
                  <span className="text-slate-400 transition group-hover:translate-x-1 group-hover:text-teal-700">-&gt;</span>
                </div>
              </Link>
            );
          })}
        </section>

        {!dashboard && (
          <section className="mt-5 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {Array.from({ length: 6 }).map((_, index) => (
              <div key={index} className="h-64 animate-pulse rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
                <div className="h-12 w-12 rounded-lg bg-slate-100" />
                <div className="mt-4 h-4 w-2/3 rounded bg-slate-100" />
                <div className="mt-3 h-3 w-full rounded bg-slate-100" />
                <div className="mt-2 h-3 w-5/6 rounded bg-slate-100" />
                <div className="mt-6 grid grid-cols-3 gap-2">
                  <div className="h-16 rounded-lg bg-slate-100" />
                  <div className="h-16 rounded-lg bg-slate-100" />
                  <div className="h-16 rounded-lg bg-slate-100" />
                </div>
              </div>
            ))}
          </section>
        )}
      </section>
    </main>
  );
}
