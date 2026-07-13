"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8000";

type MobileSummary = {
  database: string;
  stats: { departments: number; modules: number; records: number };
  priority_work: { department: string; resource: string; title: string; status: string }[];
  departments: { id: string; name: string; record_count: number; module_count: number }[];
};

export default function MobilePage() {
  const router = useRouter();
  const [summary, setSummary] = useState<MobileSummary | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    const token = localStorage.getItem("factorypulse_token");
    if (!token) {
      router.push("/login");
      return;
    }
    fetch(`${API_BASE}/api/mobile/summary`, { headers: { Authorization: `Bearer ${token}` } })
      .then((response) => {
        if (!response.ok) throw new Error("Mobile API failed");
        return response.json();
      })
      .then((data) => setSummary(data))
      .catch((err) => setError(err instanceof Error ? err.message : "Mobile API failed"));
  }, [router]);

  return (
    <main className="min-h-screen bg-slate-950 text-white">
      <header className="sticky top-0 z-10 border-b border-white/10 bg-slate-950/95 px-4 py-4 backdrop-blur">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-lg font-semibold">FactoryPulse Mobile</h1>
            <p className="text-xs text-slate-400">Shift-ready operations view</p>
          </div>
          <Link className="rounded-lg bg-white px-3 py-2 text-sm font-medium text-slate-950" href="/">Desk</Link>
        </div>
      </header>

      <section className="space-y-4 px-4 py-5">
        {error && <div className="rounded-lg border border-red-400/40 bg-red-500/10 p-3 text-sm text-red-100">{error}</div>}

        <div className="rounded-lg border border-white/10 bg-white/5 p-4">
          <div className="text-sm text-slate-400">Connection</div>
          <div className="mt-1 text-xl font-semibold">API live / {summary?.database || "checking"}</div>
        </div>

        <div className="grid grid-cols-3 gap-2">
          <div className="rounded-lg bg-white/10 p-3"><div className="text-xs text-slate-400">Dept</div><div className="text-xl font-semibold">{summary?.stats.departments || 0}</div></div>
          <div className="rounded-lg bg-white/10 p-3"><div className="text-xs text-slate-400">Modules</div><div className="text-xl font-semibold">{summary?.stats.modules || 0}</div></div>
          <div className="rounded-lg bg-white/10 p-3"><div className="text-xs text-slate-400">Rows</div><div className="text-xl font-semibold">{summary?.stats.records || 0}</div></div>
        </div>

        <section>
          <h2 className="mb-2 text-sm font-semibold uppercase text-slate-400">Priority work</h2>
          <div className="space-y-2">
            {(summary?.priority_work || []).length === 0 ? (
              <div className="rounded-lg bg-white/5 p-4 text-sm text-slate-300">No priority items yet.</div>
            ) : summary?.priority_work.map((item, index) => (
              <div key={`${item.resource}-${index}`} className="rounded-lg border border-white/10 bg-white/5 p-3">
                <div className="flex items-start justify-between gap-2">
                  <div className="text-sm font-medium">{item.title}</div>
                  <span className="rounded-lg bg-amber-400/15 px-2 py-1 text-xs text-amber-200">{item.status}</span>
                </div>
                <div className="mt-1 text-xs text-slate-400">{item.department}</div>
              </div>
            ))}
          </div>
        </section>

        <section>
          <h2 className="mb-2 text-sm font-semibold uppercase text-slate-400">Departments</h2>
          <div className="space-y-2">
            {summary?.departments.map((department) => (
              <Link key={department.id} href={`/departments/${department.id}`} className="flex items-center justify-between rounded-lg border border-white/10 bg-white/5 p-3">
                <div>
                  <div className="font-medium">{department.name}</div>
                  <div className="text-xs text-slate-400">{department.module_count} modules</div>
                </div>
                <div className="text-sm text-slate-300">{department.record_count}</div>
              </Link>
            ))}
          </div>
        </section>
      </section>
    </main>
  );
}
