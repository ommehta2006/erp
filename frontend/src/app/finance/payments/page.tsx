"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8000";

type RecordItem = { id: string; data: Record<string, string>; status: string };
type PaymentDashboard = {
  stats: Record<string, number>;
  ready_runs: RecordItem[];
  payment_batches: RecordItem[];
  salary_slips: RecordItem[];
  payment_methods: string[];
};

function money(value: string | number | undefined) {
  const amount = Number(value || 0);
  return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(amount);
}

function today() {
  return new Date().toISOString().slice(0, 10);
}

function statusClass(status: string) {
  const value = status.toLowerCase();
  if (value.includes("paid")) return "border-emerald-200 bg-emerald-50 text-emerald-700";
  if (value.includes("processing")) return "border-sky-200 bg-sky-50 text-sky-700";
  if (value.includes("cancel") || value.includes("reverse")) return "border-red-200 bg-red-50 text-red-700";
  if (value.includes("lock") || value.includes("approved")) return "border-amber-200 bg-amber-50 text-amber-700";
  return "border-slate-200 bg-slate-50 text-slate-600";
}

async function fetchJson(path: string, options: RequestInit = {}) {
  const token = localStorage.getItem("factorypulse_token");
  if (!token) throw new Error("Login required");
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      ...(options.headers || {}),
    },
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.detail || "Payment API failed");
  return body;
}

export default function FinancePaymentsPage() {
  const router = useRouter();
  const [dashboard, setDashboard] = useState<PaymentDashboard | null>(null);
  const [selectedRun, setSelectedRun] = useState("");
  const [paymentDate, setPaymentDate] = useState(today());
  const [paymentMethod, setPaymentMethod] = useState("Bank Transfer");
  const [bankFileReference, setBankFileReference] = useState("");
  const [markSalarySlips, setMarkSalarySlips] = useState(true);
  const [busy, setBusy] = useState("");
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");

  const readyRuns = dashboard?.ready_runs || [];
  const batches = dashboard?.payment_batches || [];
  const slips = dashboard?.salary_slips || [];

  const stats = useMemo(() => [
    ["Ready Runs", dashboard?.stats.ready_runs || 0],
    ["Processing", dashboard?.stats.processing_batches || 0],
    ["Paid Batches", dashboard?.stats.paid_batches || 0],
    ["Paid Slips", dashboard?.stats.paid_slips || 0],
  ], [dashboard]);

  async function loadDashboard() {
    const token = localStorage.getItem("factorypulse_token");
    if (!token) {
      router.push("/login");
      return;
    }
    const body = await fetchJson("/api/v1/finance/payment-dashboard");
    setDashboard(body);
    if (!selectedRun && body.ready_runs?.[0]?.data?.run_no) {
      setSelectedRun(body.ready_runs[0].data.run_no);
    }
  }

  useEffect(() => {
    const timer = window.setTimeout(() => {
      loadDashboard().catch((err) => setError(err instanceof Error ? err.message : "Payment dashboard failed"));
    }, 0);
    return () => window.clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [router]);

  async function createBatch() {
    setBusy("create");
    setError("");
    setNotice("");
    try {
      const body = await fetchJson("/api/v1/finance/payment-batches", {
        method: "POST",
        body: JSON.stringify({
          payroll_run: selectedRun,
          payment_date: paymentDate,
          payment_method: paymentMethod,
          bank_file_reference: bankFileReference,
          mark_salary_slips: markSalarySlips,
        }),
      });
      setDashboard(body.dashboard);
      setNotice(`Payment batch ${body.item?.data?.batch_id || ""} created and salary slips moved to payment processing.`);
      setBankFileReference("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Payment batch creation failed");
    } finally {
      setBusy("");
    }
  }

  async function decideBatch(batchId: string, decision: string) {
    setBusy(`${batchId}:${decision}`);
    setError("");
    setNotice("");
    try {
      const body = await fetchJson("/api/v1/finance/payment-batches/decision", {
        method: "POST",
        body: JSON.stringify({ batch_id: batchId, decision, remarks: `${decision} from Finance Payments` }),
      });
      setDashboard(body.dashboard);
      setNotice(`${batchId} marked ${decision}. ${body.updated_salary_slips || 0} salary slips updated.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Payment decision failed");
    } finally {
      setBusy("");
    }
  }

  async function exportBatch(batchId: string) {
    setBusy(`${batchId}:export`);
    setError("");
    try {
      const token = localStorage.getItem("factorypulse_token");
      if (!token) throw new Error("Login required");
      const response = await fetch(`${API_BASE}/api/v1/finance/payment-batches/${encodeURIComponent(batchId)}/export`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) throw new Error("Payment export failed");
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `${batchId}.csv`;
      anchor.click();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Payment export failed");
    } finally {
      setBusy("");
    }
  }

  return (
    <main className="min-h-screen bg-slate-100 text-slate-950">
      <header className="sticky top-0 z-20 border-b border-slate-200 bg-white/95 backdrop-blur">
        <div className="mx-auto flex max-w-7xl flex-col gap-3 px-4 py-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <Link href="/finance" className="text-sm font-semibold text-teal-700">Finance Payroll Center</Link>
            <h1 className="mt-1 text-2xl font-semibold">Payroll Payment Batches</h1>
            <p className="text-sm text-slate-500">Release approved payroll, update salary slip payment status, and export bank-ready files.</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link href="/finance/salary" className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm font-medium text-emerald-700 hover:border-emerald-600">Salary</Link>
            <Link href="/finance/adjustments" className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium hover:border-teal-600">Adjustments</Link>
            <Link href="/finance/settings" className="rounded-lg border border-sky-200 bg-sky-50 px-3 py-2 text-sm font-medium text-sky-700 hover:border-sky-600">Policy</Link>
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
            <div className="flex items-start justify-between gap-3">
              <div>
                <h2 className="text-lg font-semibold">Create Payment Batch</h2>
                <p className="mt-1 text-sm text-slate-500">Only approved, locked, or processing payroll runs are eligible.</p>
              </div>
              <div className="rounded-lg border border-teal-200 bg-teal-50 px-3 py-2 text-right">
                <div className="text-xs text-teal-700">Processing value</div>
                <div className="font-semibold text-teal-800">{money(dashboard?.stats.total_processing)}</div>
              </div>
            </div>

            <div className="mt-5 space-y-3">
              <label className="block text-sm font-medium text-slate-700">
                Payroll run
                <select value={selectedRun} onChange={(event) => setSelectedRun(event.target.value)} className="mt-1 h-11 w-full rounded-lg border border-slate-300 bg-white px-3 outline-none focus:border-teal-700">
                  <option value="">Select run</option>
                  {readyRuns.map((run) => (
                    <option key={run.id} value={run.data.run_no || run.id}>{run.data.run_no || run.id} - {run.data.period} - {money(run.data.net_pay)}</option>
                  ))}
                </select>
              </label>
              <label className="block text-sm font-medium text-slate-700">
                Payment date
                <input type="date" value={paymentDate} onChange={(event) => setPaymentDate(event.target.value)} className="mt-1 h-11 w-full rounded-lg border border-slate-300 px-3 outline-none focus:border-teal-700" />
              </label>
              <label className="block text-sm font-medium text-slate-700">
                Payment method
                <select value={paymentMethod} onChange={(event) => setPaymentMethod(event.target.value)} className="mt-1 h-11 w-full rounded-lg border border-slate-300 bg-white px-3 outline-none focus:border-teal-700">
                  {(dashboard?.payment_methods || ["Bank Transfer"]).map((method) => <option key={method}>{method}</option>)}
                </select>
              </label>
              <label className="block text-sm font-medium text-slate-700">
                Bank file reference
                <input value={bankFileReference} onChange={(event) => setBankFileReference(event.target.value)} placeholder="Auto-generated if blank" className="mt-1 h-11 w-full rounded-lg border border-slate-300 px-3 outline-none focus:border-teal-700" />
              </label>
              <label className="flex items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 px-3 py-3 text-sm font-medium text-slate-700">
                <input type="checkbox" checked={markSalarySlips} onChange={(event) => setMarkSalarySlips(event.target.checked)} className="h-4 w-4 accent-teal-700" />
                Update salary slips with payment status
              </label>
              <button disabled={busy === "create" || !selectedRun} onClick={createBatch} className="h-11 w-full rounded-lg bg-teal-700 px-4 text-sm font-semibold text-white hover:bg-teal-800 disabled:cursor-not-allowed disabled:opacity-50">
                {busy === "create" ? "Creating..." : "Create Batch"}
              </button>
            </div>
          </section>

          <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
            <div className="flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
              <div>
                <h2 className="text-lg font-semibold">Payment Batches</h2>
                <p className="mt-1 text-sm text-slate-500">Mark payment completion only after bank confirmation.</p>
              </div>
              <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm font-semibold text-emerald-700">
                Paid value {money(dashboard?.stats.total_paid)}
              </div>
            </div>

            <div className="mt-4 overflow-auto">
              <table className="w-full min-w-[820px] text-left text-sm">
                <thead className="text-xs uppercase text-slate-500">
                  <tr>
                    <th className="p-2">Batch</th>
                    <th className="p-2">Run</th>
                    <th className="p-2">Date</th>
                    <th className="p-2">Method</th>
                    <th className="p-2 text-right">Amount</th>
                    <th className="p-2">Status</th>
                    <th className="p-2 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {batches.length === 0 ? (
                    <tr><td colSpan={7} className="p-5 text-center text-slate-500">No payment batches yet.</td></tr>
                  ) : batches.map((batch) => {
                    const batchId = batch.data.batch_id || batch.id;
                    const status = batch.data.payment_status || batch.status;
                    return (
                      <tr key={batch.id} className="border-t border-slate-200">
                        <td className="p-2 font-semibold">{batchId}</td>
                        <td className="p-2">{batch.data.payroll_run}</td>
                        <td className="p-2">{batch.data.payment_date}</td>
                        <td className="p-2">{batch.data.payment_method}</td>
                        <td className="p-2 text-right font-semibold">{money(batch.data.total_amount)}</td>
                        <td className="p-2"><span className={`rounded-full border px-2 py-1 text-xs font-semibold ${statusClass(status)}`}>{status}</span></td>
                        <td className="p-2">
                          <div className="flex justify-end gap-2">
                            <button onClick={() => exportBatch(batchId)} disabled={busy === `${batchId}:export`} className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-semibold hover:border-teal-600 disabled:opacity-50">CSV</button>
                            <button onClick={() => decideBatch(batchId, "Paid")} disabled={status === "Paid" || busy === `${batchId}:Paid`} className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs font-semibold text-emerald-700 hover:border-emerald-600 disabled:opacity-50">Paid</button>
                            <button onClick={() => decideBatch(batchId, "Cancelled")} disabled={["Paid", "Cancelled", "Reversed"].includes(status) || busy === `${batchId}:Cancelled`} className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs font-semibold text-red-700 hover:border-red-500 disabled:opacity-50">Cancel</button>
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

        <div className="mt-4 grid gap-4 lg:grid-cols-2">
          <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
            <h2 className="text-lg font-semibold">Ready Payroll Runs</h2>
            <div className="mt-4 grid gap-3 md:grid-cols-2">
              {readyRuns.length === 0 ? (
                <p className="text-sm text-slate-500">No approved or locked payroll runs are waiting for payment.</p>
              ) : readyRuns.slice(0, 8).map((run) => (
                <button key={run.id} onClick={() => setSelectedRun(run.data.run_no || run.id)} className={`rounded-lg border p-4 text-left transition ${selectedRun === (run.data.run_no || run.id) ? "border-teal-600 bg-teal-50" : "border-slate-200 bg-white hover:border-teal-500"}`}>
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <div className="font-semibold">{run.data.run_no || run.id}</div>
                      <div className="mt-1 text-xs text-slate-500">{run.data.period} - {run.data.department || "All departments"}</div>
                    </div>
                    <span className={`rounded-full border px-2 py-1 text-xs font-semibold ${statusClass(run.data.approval_status || run.status)}`}>{run.data.approval_status || run.status}</span>
                  </div>
                  <div className="mt-3 text-xl font-semibold text-teal-700">{money(run.data.net_pay)}</div>
                </button>
              ))}
            </div>
          </section>

          <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
            <h2 className="text-lg font-semibold">Salary Slip Payment Status</h2>
            <div className="mt-4 overflow-auto">
              <table className="w-full min-w-[560px] text-left text-sm">
                <thead className="text-xs uppercase text-slate-500">
                  <tr>
                    <th className="p-2">Employee</th>
                    <th className="p-2">Period</th>
                    <th className="p-2 text-right">Net Pay</th>
                    <th className="p-2">Payment Date</th>
                    <th className="p-2">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {slips.length === 0 ? (
                    <tr><td colSpan={5} className="p-5 text-center text-slate-500">No salary slips found.</td></tr>
                  ) : slips.slice(0, 12).map((slip) => {
                    const status = slip.data.status || slip.status;
                    return (
                      <tr key={slip.id} className="border-t border-slate-200">
                        <td className="p-2 font-medium">{slip.data.employee_code}</td>
                        <td className="p-2">{slip.data.period}</td>
                        <td className="p-2 text-right font-semibold">{money(slip.data.net_pay)}</td>
                        <td className="p-2">{slip.data.payment_date || "-"}</td>
                        <td className="p-2"><span className={`rounded-full border px-2 py-1 text-xs font-semibold ${statusClass(status)}`}>{status}</span></td>
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
