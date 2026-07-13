"use client";

import Link from "next/link";
import { use, useCallback, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8000";
const STATUSES = ["Open", "Active", "Inactive", "Pending", "Approved", "Rejected", "Completed", "Closed", "On Hold", "Critical", "Draft", "Locked", "Paid", "Cancelled", "Reversed", "Present", "Absent", "Half Day", "Late", "Early Exit", "Overtime", "Out of Fence", "Pending Approval", "Attendance Corrected", "Failed", "Passed"];
const NUMERIC_FIELD_WORDS = new Set(["accuracy", "acres", "amount", "available", "balance", "budget", "capacity", "deductions", "distance", "gross", "hours", "latitude", "litres", "longitude", "minutes", "net", "opening", "pay", "percent", "quantity", "radius", "rate", "score", "speed", "spent", "tonnage", "used", "weight"]);

type Module = { resource: string; label: string; fields: string[]; count: number; items: { id: string; data: Record<string, string>; status: string }[] };
type Department = { id: string; name: string; modules: Module[] };

async function requestDepartment(departmentId: string, token: string) {
  const response = await fetch(`${API_BASE}/api/departments/${departmentId}`, { headers: { Authorization: `Bearer ${token}` } });
  if (!response.ok) throw new Error("Department API failed");
  return await response.json() as Department;
}

function fieldType(field: string) {
  const lowered = field.toLowerCase();
  if (lowered.includes("email")) return "email";
  if (lowered.includes("date") || lowered.includes("until") || lowered.includes("due")) return "date";
  if (lowered.split("_").some((word) => NUMERIC_FIELD_WORDS.has(word))) return "number";
  return "text";
}

function labelFor(field: string) {
  return field.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export default function DepartmentPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const router = useRouter();
  const searchParams = useSearchParams();
  const moduleParam = searchParams.get("module");
  const [department, setDepartment] = useState<Department | null>(null);
  const [active, setActive] = useState("");
  const [formData, setFormData] = useState<Record<string, string>>({ status: "Open" });
  const [query, setQuery] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [saving, setSaving] = useState(false);

  const applyDepartment = useCallback((data: Department) => {
    setDepartment(data);
    setActive((current) => {
      if (moduleParam && data.modules.some((item) => item.resource === moduleParam)) return moduleParam;
      return current && data.modules.some((item) => item.resource === current) ? current : data.modules?.[0]?.resource || "";
    });
  }, [moduleParam]);

  useEffect(() => {
    const token = localStorage.getItem("factorypulse_token");
    if (!token) {
      router.push("/login");
      return;
    }
    requestDepartment(id, token)
      .then((data) => applyDepartment(data))
      .catch((err) => setError(err instanceof Error ? err.message : "Department API failed"));
  }, [id, router, applyDepartment]);

  const activeModule = department?.modules.find((item) => item.resource === active);
  const rows = useMemo(() => {
    if (!activeModule || !query.trim()) return activeModule?.items || [];
    const value = query.toLowerCase();
    return activeModule.items.filter((row) => Object.values(row.data).join(" ").toLowerCase().includes(value));
  }, [activeModule, query]);

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
    setSaving(true);
    try {
      const response = await fetch(`${API_BASE}/api/modules/${activeModule.resource}`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ data }),
      });
      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(body.detail || "Create API failed");
      }
      setNotice("Record saved to the production database.");
      setFormData({ status: "Open" });
      applyDepartment(await requestDepartment(id, token));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Create API failed");
    } finally {
      setSaving(false);
    }
  }

  return (
    <main className="min-h-screen bg-slate-100 text-slate-950">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-7xl flex-col gap-3 px-4 py-4 md:flex-row md:items-center md:justify-between">
          <div>
            <Link className="text-sm font-medium text-teal-700" href="/">All departments</Link>
            <h1 className="mt-1 text-2xl font-semibold">{department?.name || "Department"}</h1>
          </div>
          <div className="flex items-center gap-2">
            <Link className="rounded-lg border border-slate-300 px-3 py-2 text-sm" href="/mobile">Mobile view</Link>
            <span className="rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-700">API connected</span>
          </div>
        </div>
      </header>

      <section className="mx-auto grid max-w-7xl gap-4 px-4 py-5 lg:grid-cols-[300px_1fr]">
        <aside className="rounded-lg border border-slate-200 bg-white p-3">
          <h2 className="px-2 pb-2 text-xs font-semibold uppercase text-slate-500">Modules</h2>
          <div className="grid gap-1">
            {department?.modules.map((item) => (
              <button key={item.resource} onClick={() => { setActive(item.resource); setNotice(""); setError(""); setQuery(""); }} className={`rounded-lg px-3 py-2 text-left text-sm ${active === item.resource ? "bg-slate-950 text-white" : "hover:bg-slate-100"}`}>
                <div className="font-medium">{item.label}</div>
                <div className="text-xs opacity-75">{item.count} records</div>
              </button>
            ))}
          </div>
        </aside>

        <section className="rounded-lg border border-slate-200 bg-white">
          {error && <div className="m-4 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</div>}
          {notice && <div className="m-4 rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-700">{notice}</div>}
          {activeModule && (
            <>
              <div className="flex flex-col gap-3 border-b border-slate-200 p-4 md:flex-row md:items-center md:justify-between">
                <div>
                  <h2 className="text-xl font-semibold">{activeModule.label}</h2>
                  <p className="text-sm text-slate-500">Resource /api/modules/{activeModule.resource}</p>
                </div>
                <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search rows" className="h-10 rounded-lg border border-slate-300 px-3 text-sm outline-none focus:border-teal-700 md:w-64" />
              </div>

              <form onSubmit={handleCreate} className="border-b border-slate-200 p-4">
                <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                  {activeModule.fields.map((field, index) => (
                    <label key={field} className="text-sm font-medium text-slate-700">
                      {labelFor(field)} {index < 2 && field !== "status" ? <span className="text-red-600">*</span> : null}
                      {field === "status" ? (
                        <select value={formData[field] || "Open"} onChange={(event) => setFormData((current) => ({ ...current, [field]: event.target.value }))} className="mt-1 h-10 w-full rounded-lg border border-slate-300 px-3 text-sm outline-none focus:border-teal-700">
                          {STATUSES.map((status) => <option key={status} value={status}>{status}</option>)}
                        </select>
                      ) : (
                        <input
                          type={fieldType(field)}
                          value={formData[field] || ""}
                          onChange={(event) => setFormData((current) => ({ ...current, [field]: event.target.value }))}
                          className="mt-1 h-10 w-full rounded-lg border border-slate-300 px-3 text-sm outline-none focus:border-teal-700"
                        />
                      )}
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
                <table className="w-full min-w-[820px] text-left text-sm">
                  <thead className="bg-slate-50 text-xs uppercase text-slate-500">
                    <tr>{activeModule.fields.slice(0, 7).map((field) => <th key={field} className="p-3">{labelFor(field)}</th>)}</tr>
                  </thead>
                  <tbody>
                    {rows.length === 0 ? (
                      <tr><td className="p-6 text-slate-500" colSpan={7}>No matching records yet. Create the first validated record above.</td></tr>
                    ) : rows.map((row) => (
                      <tr key={row.id} className="border-t border-slate-100">
                        {activeModule.fields.slice(0, 7).map((field) => <td key={field} className="max-w-48 truncate p-3">{row.data[field] || "-"}</td>)}
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
