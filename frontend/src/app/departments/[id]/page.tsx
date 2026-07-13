"use client";

import Link from "next/link";
import { use, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8000";

type Module = { resource: string; label: string; fields: string[]; count: number; items: { id: string; data: Record<string, string>; status: string }[] };

type Department = { id: string; name: string; modules: Module[] };

async function requestDepartment(departmentId: string, token: string) {
  const response = await fetch(`${API_BASE}/api/departments/${departmentId}`, { headers: { Authorization: `Bearer ${token}` } });
  if (!response.ok) throw new Error("Department API failed");
  return await response.json() as Department;
}

export default function DepartmentPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const router = useRouter();
  const [department, setDepartment] = useState<Department | null>(null);
  const [active, setActive] = useState("");
  const [formData, setFormData] = useState<Record<string, string>>({});
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [saving, setSaving] = useState(false);

  function applyDepartment(data: Department) {
    setDepartment(data);
    setActive((current) => current && data.modules.some((item) => item.resource === current) ? current : data.modules?.[0]?.resource || "");
  }

  useEffect(() => {
    const token = localStorage.getItem("factorypulse_token");
    if (!token) {
      router.push("/login");
      return;
    }
    requestDepartment(id, token)
      .then((data) => applyDepartment(data))
      .catch((err) => setError(err.message));
  }, [id, router]);

  const activeModule = department?.modules.find((item) => item.resource === active);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!activeModule) return;
    setError("");
    setNotice("");
    const token = localStorage.getItem("factorypulse_token");
    if (!token) {
      router.push("/login");
      return;
    }
    const data = Object.fromEntries(activeModule.fields.map((field) => [field, formData[field] || ""]).filter(([, value]) => value.trim() !== ""));
    if (Object.keys(data).length === 0) {
      setError("Enter at least one field before saving.");
      return;
    }
    setSaving(true);
    try {
      const response = await fetch(`${API_BASE}/api/modules/${activeModule.resource}`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ data }),
      });
      if (!response.ok) throw new Error("Create API failed");
      setNotice("Record saved to database.");
      setFormData({});
      applyDepartment(await requestDepartment(id, token));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Create API failed");
    } finally {
      setSaving(false);
    }
  }

  return (
    <main className="min-h-screen bg-[#f6f7f9] text-[#17202a]">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
          <div>
            <Link className="text-sm text-teal-700" href="/">All departments</Link>
            <h1 className="mt-1 text-2xl font-semibold">{department?.name || "Department"}</h1>
          </div>
          <span className="rounded-full bg-white px-3 py-1 text-sm text-slate-600">API connected</span>
        </div>
      </header>

      <section className="mx-auto grid max-w-7xl gap-4 px-6 py-6 lg:grid-cols-[280px_1fr]">
        <aside className="rounded-xl border border-slate-200 bg-white p-3 shadow-sm">
          <h2 className="px-2 pb-2 text-sm font-semibold uppercase tracking-wide text-slate-500">Modules</h2>
          <div className="grid gap-1">
            {department?.modules.map((item) => (
              <button key={item.resource} onClick={() => { setActive(item.resource); setNotice(""); setError(""); }} className={`rounded-lg px-3 py-2 text-left text-sm ${active === item.resource ? "bg-teal-700 text-white" : "hover:bg-slate-100"}`}>
                <div className="font-medium">{item.label}</div>
                <div className="text-xs opacity-75">{item.count} records</div>
              </button>
            ))}
          </div>
        </aside>

        <section className="rounded-xl border border-slate-200 bg-white shadow-sm">
          {error && <div className="m-4 rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">{error}</div>}
          {notice && <div className="m-4 rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-emerald-700">{notice}</div>}
          {activeModule && (
            <>
              <div className="flex items-center justify-between border-b border-slate-200 p-4">
                <div>
                  <h2 className="text-xl font-semibold">{activeModule.label}</h2>
                  <p className="text-sm text-slate-500">Connected resource: /api/modules/{activeModule.resource}</p>
                </div>
                <span className="rounded-full bg-slate-100 px-3 py-1 text-sm text-slate-600">{activeModule.count} records</span>
              </div>
              <form onSubmit={handleCreate} className="border-b border-slate-200 p-4">
                <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                  {activeModule.fields.map((field) => (
                    <label key={field} className="text-sm font-medium text-slate-700">
                      {field.replaceAll("_", " ")}
                      <input
                        value={formData[field] || ""}
                        onChange={(event) => setFormData((current) => ({ ...current, [field]: event.target.value }))}
                        className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-teal-600"
                      />
                    </label>
                  ))}
                </div>
                <div className="mt-4 flex justify-end">
                  <button disabled={saving} className="rounded-lg bg-teal-700 px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:bg-slate-400">
                    {saving ? "Saving" : "Save record"}
                  </button>
                </div>
              </form>
              <div className="overflow-auto">
                <table className="w-full min-w-[760px] text-left text-sm">
                  <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                    <tr>{activeModule.fields.slice(0, 6).map((field) => <th key={field} className="p-3">{field.replaceAll("_", " ")}</th>)}</tr>
                  </thead>
                  <tbody>
                    {activeModule.items.length === 0 ? (
                      <tr><td className="p-6 text-slate-500" colSpan={6}>No records yet. This is an empty deploy-ready module connected to the backend database.</td></tr>
                    ) : activeModule.items.map((row) => (
                      <tr key={row.id} className="border-t border-slate-100">
                        {activeModule.fields.slice(0, 6).map((field) => <td key={field} className="p-3">{row.data[field] || "-"}</td>)}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </section>
      </section>
    </main>
  );
}

