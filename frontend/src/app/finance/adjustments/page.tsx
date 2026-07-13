"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8000";

type RecordItem = { id: string; data: Record<string, string>; status: string };
type Dashboard = {
  stats: Record<string, number>;
  limit: number;
  pending: RecordItem[];
  recent: RecordItem[];
  payroll_runs: RecordItem[];
  allowed_types: string[];
  allowed_directions: string[];
};

const DEFAULT_FORM = {
  employee_code: "",
  payroll_month: new Date().toISOString().slice(0, 7),
  adjustment_type: "Bonus",
  addition_or_deduction: "Addition",
  amount: "",
  calculation_method: "Manual",
  quantity: "1",
  rate: "",
  reason: "",
  policy_reference: "",
  supporting_attachment: "",
};

function currency(value: number | string | undefined) {
  const amount = Number(value || 0);
  return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(amount);
}

function authHeaders() {
  const token = localStorage.getItem("factorypulse_token") || "";
  return { "Content-Type": "application/json", Authorization: `Bearer ${token}` };
}

async function requestDashboard() {
  const response = await fetch(`${API_BASE}/api/v1/finance/adjustments-dashboard`, { headers: authHeaders() });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.detail || "Adjustments dashboard API failed");
  return body as Dashboard;
}

function tone(status: string) {
  if (status === "Approved" || status === "Paid" || status === "Locked") return "border-emerald-200 bg-emerald-50 text-emerald-800";
  if (status === "Rejected" || status === "Cancelled") return "border-rose-200 bg-rose-50 text-rose-800";
  if (status === "Reversed") return "border-slate-200 bg-slate-100 text-slate-700";
  return "border-amber-200 bg-amber-50 text-amber-800";
}

export default function PayrollAdjustmentsPage() {
  const router = useRouter();
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [form, setForm] = useState(DEFAULT_FORM);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  useEffect(() => {
    if (!localStorage.getItem("factorypulse_token")) {
      router.push("/login");
      return;
    }
    requestDashboard().then(setDashboard).catch((err) => setError(err instanceof Error ? err.message : "Adjustments dashboard API failed"));
  }, [router]);

  const stats = useMemo(() => [
    ["Pending", dashboard?.stats.pending || 0],
    ["Approved", dashboard?.stats.approved || 0],
    ["Rejected", dashboard?.stats.rejected || 0],
    ["Reversed", dashboard?.stats.reversed || 0],
  ], [dashboard]);

  async function postJson(path: string, payload: Record<string, unknown>, success: string) {
    setBusy(path);
    setError("");
    setNotice("");
    try {
      const response = await fetch(`${API_BASE}${path}`, {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify(payload),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.detail || "Request failed");
      setDashboard(body.dashboard || await requestDashboard());
      setNotice(success);
      return body;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed");
      return null;
    } finally {
      setBusy("");
    }
  }

  async function createAdjustment() {
    const body = await postJson("/api/v1/finance/payroll-adjustments", {
      ...form,
      amount: Number(form.amount),
      quantity: Number(form.quantity || 1),
      rate: form.rate ? Number(form.rate) : undefined,
    }, "Adjustment submitted for maker-checker approval.");
    if (body) setForm({ ...DEFAULT_FORM, payroll_month: form.payroll_month });
  }

  function decide(adjustmentId: string, decision: string) {
    return postJson("/api/v1/finance/payroll-adjustments/decision", {
      adjustment_id: adjustmentId,
      decision,
      remarks: `${decision} from Finance Payroll Adjustments`,
    }, `Adjustment ${decision.toLowerCase()}.`);
  }

  function decideRun(runNo: string, decision: string) {
    return postJson("/api/v1/finance/payroll-runs/decision", {
      run_no: runNo,
      decision,
      remarks: `${decision} from Finance Payroll Adjustments`,
    }, `Payroll run marked ${decision.toLowerCase()}.`);
  }

  return (
    <main className="min-h-screen bg-slate-100 text-slate-950">
      <header className="sticky top-0 z-20 border-b border-slate-200 bg-white/95 backdrop-blur">
        <div className="mx-auto flex max-w-7xl flex-col gap-3 px-4 py-4 md:flex-row md:items-center md:justify-between">
          <div>
            <Link href="/finance" className="text-sm font-semibold text-teal-700">Finance Payroll Center</Link>
            <h1 className="mt-1 text-2xl font-semibold">Payroll Adjustments</h1>
            <p className="text-sm text-slate-500">Maker-checker salary additions, deductions, reversals, audit, and payroll lock controls.</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link href="/departments/finance?module=payroll_adjustments" className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium hover:border-teal-600">Raw Table</Link>
            <Link href="/finance" className="rounded-lg bg-slate-950 px-3 py-2 text-sm font-medium text-white hover:bg-slate-800">Payroll</Link>
          </div>
        </div>
      </header>

      <section className="mx-auto max-w-7xl px-4 py-6">
        {error ? <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</div> : null}
        {notice ? <div className="mb-4 rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-700">{notice}</div> : null}

        <section className="grid gap-4 lg:grid-cols-[1fr_380px]">
          <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
            <div className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
              <div>
                <p className="text-sm font-semibold text-teal-700">Controlled finance workflow</p>
                <h2 className="mt-2 text-3xl font-semibold tracking-tight">Create adjustment request</h2>
                <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
                  Adjustments require reason, policy reference, duplicate detection, amount limit, and approval before payroll calculation includes them.
                </p>
              </div>
              <div className="rounded-lg border border-sky-200 bg-sky-50 p-4">
                <div className="text-xs font-semibold uppercase text-sky-700">Configured limit</div>
                <div className="mt-1 text-2xl font-semibold text-sky-900">{currency(dashboard?.limit)}</div>
              </div>
            </div>

            <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
              <Input label="Employee Code" value={form.employee_code} onChange={(value) => setForm({ ...form, employee_code: value })} />
              <Input label="Payroll Month" value={form.payroll_month} onChange={(value) => setForm({ ...form, payroll_month: value })} placeholder="YYYY-MM" />
              <Select label="Type" value={form.adjustment_type} options={dashboard?.allowed_types || [DEFAULT_FORM.adjustment_type]} onChange={(value) => setForm({ ...form, adjustment_type: value })} />
              <Select label="Direction" value={form.addition_or_deduction} options={dashboard?.allowed_directions || ["Addition", "Deduction"]} onChange={(value) => setForm({ ...form, addition_or_deduction: value })} />
              <Input label="Amount" value={form.amount} onChange={(value) => setForm({ ...form, amount: value, rate: form.rate || value })} />
              <Input label="Calculation Method" value={form.calculation_method} onChange={(value) => setForm({ ...form, calculation_method: value })} />
              <Input label="Quantity" value={form.quantity} onChange={(value) => setForm({ ...form, quantity: value })} />
              <Input label="Rate" value={form.rate} onChange={(value) => setForm({ ...form, rate: value })} />
              <Input label="Policy Reference" value={form.policy_reference} onChange={(value) => setForm({ ...form, policy_reference: value })} />
              <label className="text-sm font-medium text-slate-700 md:col-span-2 xl:col-span-3">
                Reason
                <textarea value={form.reason} onChange={(event) => setForm({ ...form, reason: event.target.value })} className="mt-1 min-h-24 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-teal-700" />
              </label>
              <Input label="Supporting Attachment Reference" value={form.supporting_attachment} onChange={(value) => setForm({ ...form, supporting_attachment: value })} />
            </div>
            <button disabled={Boolean(busy)} onClick={createAdjustment} className="mt-4 rounded-lg bg-teal-700 px-4 py-2 text-sm font-semibold text-white hover:bg-teal-800 disabled:opacity-50">
              {busy === "/api/v1/finance/payroll-adjustments" ? "Submitting..." : "Submit Adjustment"}
            </button>
          </div>

          <aside className="space-y-4">
            <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
              <h2 className="font-semibold">Adjustment totals</h2>
              <div className="mt-3 grid grid-cols-2 gap-2">
                {stats.map(([label, value]) => (
                  <div key={label} className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                    <div className="text-xl font-semibold">{value}</div>
                    <div className="text-xs text-slate-500">{label}</div>
                  </div>
                ))}
              </div>
              <div className="mt-3 rounded-lg border border-teal-200 bg-teal-50 p-3">
                <div className="text-xs font-semibold text-teal-700">Approved net adjustment</div>
                <div className="mt-1 text-2xl font-semibold text-teal-900">{currency(dashboard?.stats.net_adjustment)}</div>
              </div>
            </div>
          </aside>
        </section>

        <section className="mt-5 grid gap-4 xl:grid-cols-[1fr_420px]">
          <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-sm font-semibold text-amber-700">Approval queue</p>
                <h2 className="mt-1 text-xl font-semibold">Pending maker-checker decisions</h2>
              </div>
              <span className="rounded-lg bg-amber-50 px-3 py-2 text-sm font-semibold text-amber-800">{dashboard?.pending.length || 0}</span>
            </div>
            <div className="mt-4 overflow-auto">
              <table className="w-full min-w-[760px] text-left text-sm">
                <thead className="text-xs uppercase text-slate-500">
                  <tr><th className="p-3">Employee</th><th className="p-3">Month</th><th className="p-3">Type</th><th className="p-3">Amount</th><th className="p-3">Policy</th><th className="p-3">Action</th></tr>
                </thead>
                <tbody>
                  {(dashboard?.pending || []).length === 0 ? (
                    <tr><td className="p-6 text-slate-500" colSpan={6}>No pending adjustments.</td></tr>
                  ) : dashboard?.pending.map((item) => {
                    const id = item.data.adjustment_id || item.id;
                    return (
                      <tr key={item.id} className="border-t border-slate-100">
                        <td className="p-3 font-medium">{item.data.employee_code}</td>
                        <td className="p-3">{item.data.payroll_month}</td>
                        <td className="p-3">{item.data.adjustment_type}<div className="text-xs text-slate-500">{item.data.addition_or_deduction}</div></td>
                        <td className="p-3 font-semibold">{currency(item.data.amount)}</td>
                        <td className="p-3">{item.data.policy_reference}<div className="line-clamp-1 text-xs text-slate-500">{item.data.reason}</div></td>
                        <td className="p-3">
                          <div className="flex flex-wrap gap-2">
                            <button disabled={Boolean(busy)} onClick={() => decide(id, "Approved")} className="rounded-lg bg-teal-700 px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-50">Approve</button>
                            <button disabled={Boolean(busy)} onClick={() => decide(id, "Rejected")} className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-1.5 text-xs font-semibold text-rose-700 disabled:opacity-50">Reject</button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
            <h2 className="font-semibold">Payroll run locks</h2>
            <p className="mt-1 text-sm text-slate-500">Approve, lock, or mark payroll paid after finance review.</p>
            <div className="mt-4 space-y-3">
              {(dashboard?.payroll_runs || []).length === 0 ? (
                <p className="rounded-lg border border-slate-100 bg-slate-50 p-3 text-sm text-slate-500">No payroll runs yet.</p>
              ) : dashboard?.payroll_runs.slice(0, 8).map((run) => {
                const runNo = run.data.run_no || run.id;
                const status = run.data.approval_status || run.status;
                return (
                  <div key={run.id} className="rounded-lg border border-slate-100 bg-slate-50 p-3">
                    <div className="flex items-center justify-between gap-2">
                      <div className="text-sm font-semibold">{runNo}</div>
                      <span className={`rounded-lg border px-2 py-1 text-xs font-semibold ${tone(status)}`}>{status}</span>
                    </div>
                    <div className="mt-1 text-xs text-slate-500">{run.data.period} / Net {currency(run.data.net_pay)}</div>
                    <div className="mt-3 flex flex-wrap gap-2">
                      {["Approved", "Locked", "Paid"].map((decision) => (
                        <button key={decision} disabled={Boolean(busy)} onClick={() => decideRun(runNo, decision)} className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold hover:border-teal-600 disabled:opacity-50">{decision}</button>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </section>

        <section className="mt-5 rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="font-semibold">Recent adjustment history</h2>
          <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {(dashboard?.recent || []).slice(0, 12).map((item) => {
              const status = item.data.approval_status || item.status;
              const id = item.data.adjustment_id || item.id;
              return (
                <div key={item.id} className="rounded-lg border border-slate-100 bg-slate-50 p-3">
                  <div className="flex items-center justify-between gap-2">
                    <div className="truncate text-sm font-semibold">{item.data.employee_code} / {item.data.payroll_month}</div>
                    <span className={`rounded-lg border px-2 py-1 text-xs font-semibold ${tone(status)}`}>{status}</span>
                  </div>
                  <div className="mt-2 text-sm">{item.data.adjustment_type} - {currency(item.data.amount)}</div>
                  <div className="mt-1 line-clamp-2 text-xs text-slate-500">{item.data.reason}</div>
                  {status === "Approved" ? (
                    <button disabled={Boolean(busy)} onClick={() => decide(id, "Reversed")} className="mt-3 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold hover:border-teal-600 disabled:opacity-50">Reverse</button>
                  ) : null}
                </div>
              );
            })}
          </div>
        </section>
      </section>
    </main>
  );
}

function Input({ label, value, onChange, placeholder }: { label: string; value: string; onChange: (value: string) => void; placeholder?: string }) {
  return (
    <label className="text-sm font-medium text-slate-700">
      {label}
      <input value={value} placeholder={placeholder} onChange={(event) => onChange(event.target.value)} className="mt-1 h-11 w-full rounded-lg border border-slate-300 px-3 text-sm outline-none focus:border-teal-700" />
    </label>
  );
}

function Select({ label, value, options, onChange }: { label: string; value: string; options: string[]; onChange: (value: string) => void }) {
  return (
    <label className="text-sm font-medium text-slate-700">
      {label}
      <select value={value} onChange={(event) => onChange(event.target.value)} className="mt-1 h-11 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm outline-none focus:border-teal-700">
        {options.map((option) => <option key={option} value={option}>{option}</option>)}
      </select>
    </label>
  );
}
