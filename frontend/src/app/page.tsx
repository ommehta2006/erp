"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8000";

type Department = { id: string; name: string; modules: string[] };

export default function HomePage() {
  const router = useRouter();
  const [departments, setDepartments] = useState<Department[]>([]);
  const [database, setDatabase] = useState("checking");
  const [error, setError] = useState("");

  useEffect(() => {
    const token = localStorage.getItem("factorypulse_token");
    if (!token) {
      router.push("/login");
      return;
    }
    Promise.all([
      fetch(`${API_BASE}/api/departments`, { headers: { Authorization: `Bearer ${token}` } }).then((r) => {
        if (!r.ok) throw new Error("Department API failed");
        return r.json();
      }),
      fetch(`${API_BASE}/api/catalog`, { headers: { Authorization: `Bearer ${token}` } }).then((r) => r.json()),
    ])
      .then(([deptData, catalog]) => {
        setDepartments(deptData.items || []);
        setDatabase(catalog.database || "connected");
      })
      .catch((err) => setError(err.message));
  }, [router]);

  return (
    <main className="min-h-screen bg-[#f6f7f9] text-[#17202a]">
      <header className="sticky top-0 z-20 border-b border-slate-200 bg-white/90 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
          <div>
            <h1 className="text-xl font-bold">FactoryPulse ERP</h1>
            <p className="text-xs uppercase tracking-wide text-slate-500">Global factory command workspace</p>
          </div>
          <div className="flex items-center gap-3">
            <span className="rounded-full bg-emerald-50 px-3 py-1 text-sm text-emerald-700">DB: {database}</span>
            <button className="rounded-lg border border-slate-300 px-3 py-2 text-sm" onClick={() => { localStorage.removeItem("factorypulse_token"); router.push("/login"); }}>Logout</button>
          </div>
        </div>
      </header>

      <section className="mx-auto max-w-7xl px-6 py-8">
        <div className="mb-6 flex flex-col justify-between gap-3 md:flex-row md:items-end">
          <div>
            <h2 className="text-3xl font-semibold">Departments</h2>
            <p className="mt-1 text-slate-600">Open a department to work with live ERP modules connected to the backend API and database.</p>
          </div>
          <Link className="rounded-lg bg-teal-700 px-4 py-2 text-sm font-semibold text-white" href="/departments/hr">Open HR</Link>
        </div>

        {error && <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">{error}</div>}

        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {departments.map((dept) => (
            <Link key={dept.id} href={`/departments/${dept.id}`} className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm transition hover:border-teal-500 hover:shadow-md">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <h3 className="text-lg font-semibold">{dept.name}</h3>
                  <p className="mt-2 text-sm text-slate-600">{dept.modules.length} modules</p>
                </div>
                <span className="rounded-full bg-slate-100 px-3 py-1 text-xs text-slate-600">Open</span>
              </div>
              <div className="mt-4 flex flex-wrap gap-2">
                {dept.modules.slice(0, 6).map((module) => <span key={module} className="rounded-full bg-teal-50 px-2.5 py-1 text-xs text-teal-700">{module.replaceAll("_", " ")}</span>)}
              </div>
            </Link>
          ))}
        </div>
      </section>
    </main>
  );
}
