"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8000";

type RecordItem = { id: string; data: Record<string, string>; status: string };
type Dashboard = {
  stats: Record<string, number>;
  rules: RecordItem[];
  tax_records: RecordItem[];
  deduction_types: string[];
  calculation_bases: string[];
};

const DEFAULT_SLAB = '[{"up_to":25000,"rate":0},{"up_to":50000,"rate":5},{"rate":10}]';
const DEFAULT_FORM = {
  rule_name: "",
  component_name: "Professional Tax",
  deduction_type: "Percentage",
  calculation_base: "Gross Pay",
  rate_percent: "1",
  fixed_amount: "",
  monthly_cap: "",
  annual_exemption: "",
  employee_min_gross: "",
  employee_max_gross: "",
  slab_config: "",
  jurisdiction: "Company Policy",
  employer_contribution: false,
  employee_contribution: true,
  effective_start_date: "",
  effective_end_date: "",
  approval_status: "Approved",
  status: "Active",
};

function money(value: string | number | undefined) {
  return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(Number(value || 0));
}

function authHeaders() {
  const token = localStorage.getItem("factorypulse_token") || "";
  return { "Content-Type": "application/json", Authorization: `Bearer ${token}` };
}

function statusTone(status: string) {
  const value = status.toLowerCase();
  if (value.includes("approved") || value.includes("active")) return "border-emerald-200 bg-emerald-50 text-emerald-700";
  if (value.includes("pending") || value.includes("draft")) return "border-amber-200 bg-amber-50 text-amber-700";
  if (value.includes("reject") || value.includes("inactive")) return "border-red-200 bg-red-50 text-red-700";
  return "border-slate-200 bg-slate-50 text-slate-600";
}

async function requestDashboard() {
  const response = await fetch(`${API_BASE}/api/v1/finance/statutory-dashboard`, { headers: authHeaders() });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.detail || "Statutory payroll API failed");
  return body as Dashboard;
}

export default function FinanceStatutoryPage() {
  const router = useRouter();
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [form, setForm] = useState(DEFAULT_FORM);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  useEffect(() => {
    const timer = window.setTimeout(() => {
      if (!localStorage.getItem("factorypulse_token")) {
        router.push("/login");
        return;
      }
      requestDashboard()
        .then(setDashboard)
        .catch((err) => setError(err instanceof Error ? err.message : "Statutory payroll API failed"));
    }, 0);
    return () => window.clearTimeout(timer);
  }, [router]);

  function numberOrUndefined(value: string) {
    return value.trim() ? Number(value) : undefined;
  }

  async function saveRule() {
    setBusy("save");
    setError("");
    setNotice("");
    try {
      const response = await fetch(`${API_BASE}/api/v1/finance/statutory-rules`, {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({
          ...form,
          rate_percent: Number(form.rate_percent || 0),
          fixed_amount: Number(form.fixed_amount || 0),
          monthly_cap: numberOrUndefined(form.monthly_cap),
          annual_exemption: Number(form.annual_exemption || 0),
          employee_min_gross: numberOrUndefined(form.employee_min_gross),
          employee_max_gross: numberOrUndefined(form.employee_max_gross),
          slab_config: form.deduction_type === "Slab" ? (form.slab_config || DEFAULT_SLAB) : form.slab_config,
        }),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.detail || "Could not save statutory rule");
      setDashboard(body.dashboard);
      setForm(DEFAULT_FORM);
      setNotice("Statutory payroll rule saved and will be applied by payroll validation/generation.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save statutory rule");
    } finally {
      setBusy("");
    }
  }

  async function decide(ruleId: string, decision: string) {
    setBusy(`${ruleId}:${decision}`);
    setError("");
    setNotice("");
    try {
      const response = await fetch(`${API_BASE}/api/v1/finance/statutory-rules/decision`, {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({ rule_id: ruleId, decision, remarks: `${decision} from statutory payroll controls` }),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.detail || "Could not update statutory rule");
      setDashboard(body.dashboard);
      setNotice(`${ruleId} updated to ${decision}.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update statutory rule");
    } finally {
      setBusy("");
    }
  }

  const stats = [
    ["Rules", dashboard?.stats.rules || 0],
    ["Active", dashboard?.stats.active_rules || 0],
    ["Approved", dashboard?.stats.approved_rules || 0],
    ["Pending", dashboard?.stats.pending_rules || 0],
  ];

  return (
    <main className="min-h-screen bg-slate-100 text-slate-950">
      <header className="sticky top-0 z-20 border-b border-slate-200 bg-white/95 backdrop-blur">
        <div className="mx-auto flex max-w-7xl flex-col gap-3 px-4 py-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <Link href="/finance" className="text-sm font-semibold text-teal-700">Finance Payroll Center</Link>
            <h1 className="mt-1 text-2xl font-semibold">Statutory Payroll Rules</h1>
            <p className="text-sm text-slate-500">Configure tax, employee deductions, and employer contribution rules used by payroll calculation.</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link href="/finance/settings" className="rounded-lg border border-sky-200 bg-sky-50 px-3 py-2 text-sm font-medium text-sky-700 hover:border-sky-600">Payroll Policy</Link>
            <Link href="/finance/payments" className="rounded-lg border border-violet-200 bg-violet-50 px-3 py-2 text-sm font-medium text-violet-700 hover:border-violet-600">Payments</Link>
            <Link href="/departments/finance?module=payroll_statutory_rules" className="rounded-lg bg-slate-950 px-3 py-2 text-sm font-medium text-white hover:bg-slate-800">Raw Rules</Link>
          </div>
        </div>
      </header>

      <section className="mx-auto max-w-7xl px-4 py-6">
        {error ? <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</div> : null}
        {notice ? <div className="mb-4 rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-700">{notice}</div> : null}

        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {stats.map(([label, value]) => (
            <div key={label} className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
              <div className="text-2xl font-semibold">{value}</div>
              <div className="mt-1 text-xs uppercase tracking-wide text-slate-500">{label}</div>
            </div>
          ))}
        </div>

        <div className="mt-4 grid gap-4 xl:grid-cols-[420px_1fr]">
          <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
            <h2 className="text-lg font-semibold">Create Rule</h2>
            <p className="mt-1 text-sm text-slate-500">Rules are applied only when active, approved, and effective for the payroll period.</p>
            <div className="mt-5 space-y-3">
              <Input label="Rule Name" value={form.rule_name} onChange={(value) => setForm({ ...form, rule_name: value })} />
              <Input label="Component Name" value={form.component_name} onChange={(value) => setForm({ ...form, component_name: value })} />
              <div className="grid gap-3 sm:grid-cols-2">
                <Select label="Deduction Type" value={form.deduction_type} options={dashboard?.deduction_types || ["Percentage"]} onChange={(value) => setForm({ ...form, deduction_type: value, slab_config: value === "Slab" ? DEFAULT_SLAB : form.slab_config })} />
                <Select label="Calculation Base" value={form.calculation_base} options={dashboard?.calculation_bases || ["Gross Pay"]} onChange={(value) => setForm({ ...form, calculation_base: value })} />
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                <Input label="Rate Percent" value={form.rate_percent} onChange={(value) => setForm({ ...form, rate_percent: value })} />
                <Input label="Fixed Amount" value={form.fixed_amount} onChange={(value) => setForm({ ...form, fixed_amount: value })} />
                <Input label="Monthly Cap" value={form.monthly_cap} onChange={(value) => setForm({ ...form, monthly_cap: value })} />
                <Input label="Annual Exemption" value={form.annual_exemption} onChange={(value) => setForm({ ...form, annual_exemption: value })} />
                <Input label="Min Gross" value={form.employee_min_gross} onChange={(value) => setForm({ ...form, employee_min_gross: value })} />
                <Input label="Max Gross" value={form.employee_max_gross} onChange={(value) => setForm({ ...form, employee_max_gross: value })} />
              </div>
              <Input label="Jurisdiction / Policy" value={form.jurisdiction} onChange={(value) => setForm({ ...form, jurisdiction: value })} />
              {form.deduction_type === "Slab" ? (
                <label className="block text-sm font-medium text-slate-700">
                  Slab JSON
                  <textarea value={form.slab_config || DEFAULT_SLAB} onChange={(event) => setForm({ ...form, slab_config: event.target.value })} className="mt-1 min-h-24 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-teal-700" />
                </label>
              ) : null}
              <div className="grid gap-3 sm:grid-cols-2">
                <Input label="Effective Start" value={form.effective_start_date} onChange={(value) => setForm({ ...form, effective_start_date: value })} placeholder="YYYY-MM-DD" />
                <Input label="Effective End" value={form.effective_end_date} onChange={(value) => setForm({ ...form, effective_end_date: value })} placeholder="Optional" />
              </div>
              <label className="flex items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 px-3 py-3 text-sm font-medium text-slate-700">
                <input type="checkbox" checked={form.employee_contribution} onChange={(event) => setForm({ ...form, employee_contribution: event.target.checked })} className="h-4 w-4 accent-teal-700" />
                Deduct from employee net pay
              </label>
              <label className="flex items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 px-3 py-3 text-sm font-medium text-slate-700">
                <input type="checkbox" checked={form.employer_contribution} onChange={(event) => setForm({ ...form, employer_contribution: event.target.checked })} className="h-4 w-4 accent-teal-700" />
                Track employer contribution line
              </label>
              <button disabled={busy === "save" || !form.rule_name || !form.component_name} onClick={saveRule} className="h-11 w-full rounded-lg bg-teal-700 px-4 text-sm font-semibold text-white hover:bg-teal-800 disabled:cursor-not-allowed disabled:opacity-50">
                {busy === "save" ? "Saving..." : "Save Rule"}
              </button>
            </div>
          </section>

          <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
            <h2 className="text-lg font-semibold">Configured Rules</h2>
            <div className="mt-4 overflow-auto">
              <table className="w-full min-w-[860px] text-left text-sm">
                <thead className="text-xs uppercase text-slate-500">
                  <tr>
                    <th className="p-2">Rule</th>
                    <th className="p-2">Type</th>
                    <th className="p-2">Base</th>
                    <th className="p-2">Rate / Fixed</th>
                    <th className="p-2">Cap</th>
                    <th className="p-2">Status</th>
                    <th className="p-2 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {(dashboard?.rules || []).length === 0 ? (
                    <tr><td colSpan={7} className="p-5 text-center text-slate-500">No statutory payroll rules configured.</td></tr>
                  ) : dashboard?.rules.map((rule) => {
                    const data = rule.data;
                    const ruleId = data.rule_id || rule.id;
                    const approval = data.approval_status || "Approved";
                    const status = data.status || rule.status;
                    return (
                      <tr key={rule.id} className="border-t border-slate-200">
                        <td className="p-2">
                          <div className="font-semibold">{data.rule_name}</div>
                          <div className="text-xs text-slate-500">{ruleId} / {data.component_name}</div>
                        </td>
                        <td className="p-2">{data.deduction_type}</td>
                        <td className="p-2">{data.calculation_base}</td>
                        <td className="p-2">{data.deduction_type === "Fixed" ? money(data.fixed_amount) : `${Number(data.rate_percent || 0)}%`}</td>
                        <td className="p-2">{data.monthly_cap ? money(data.monthly_cap) : "-"}</td>
                        <td className="p-2">
                          <div className="flex flex-col gap-1">
                            <span className={`w-fit rounded-full border px-2 py-1 text-xs font-semibold ${statusTone(status)}`}>{status}</span>
                            <span className={`w-fit rounded-full border px-2 py-1 text-xs font-semibold ${statusTone(approval)}`}>{approval}</span>
                          </div>
                        </td>
                        <td className="p-2">
                          <div className="flex justify-end gap-2">
                            <button onClick={() => decide(ruleId, "Approved")} disabled={approval === "Approved" || busy === `${ruleId}:Approved`} className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs font-semibold text-emerald-700 hover:border-emerald-600 disabled:opacity-50">Approve</button>
                            <button onClick={() => decide(ruleId, status === "Active" ? "Inactive" : "Active")} disabled={busy.startsWith(`${ruleId}:`)} className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-semibold hover:border-teal-600 disabled:opacity-50">{status === "Active" ? "Disable" : "Activate"}</button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </section>
        </div>
      </section>
    </main>
  );
}

function Input({ label, value, onChange, placeholder }: { label: string; value: string; onChange: (value: string) => void; placeholder?: string }) {
  return (
    <label className="block text-sm font-medium text-slate-700">
      {label}
      <input value={value} placeholder={placeholder} onChange={(event) => onChange(event.target.value)} className="mt-1 h-11 w-full rounded-lg border border-slate-300 px-3 text-sm outline-none focus:border-teal-700" />
    </label>
  );
}

function Select({ label, value, options, onChange }: { label: string; value: string; options: string[]; onChange: (value: string) => void }) {
  return (
    <label className="block text-sm font-medium text-slate-700">
      {label}
      <select value={value} onChange={(event) => onChange(event.target.value)} className="mt-1 h-11 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm outline-none focus:border-teal-700">
        {options.map((option) => <option key={option} value={option}>{option}</option>)}
      </select>
    </label>
  );
}
