"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8000";

type RecordItem = { id: string; data: Record<string, string>; status: string };
type PayrollDashboard = {
  stats: Record<string, number>;
  payroll_runs: RecordItem[];
  employee_results: RecordItem[];
  adjustments: RecordItem[];
};
type PayrollResult = {
  run_no: string;
  period: string;
  dry_run: boolean;
  totals: { gross_pay: number; deductions: number; net_pay: number; employees: number };
  results: { employee_code: string; paid_days: string; gross_pay: string; deductions: string; net_pay: string; validation_status: string }[];
  validation_errors: string[];
};

function currency(value: number | string | undefined) {
  const amount = Number(value || 0);
  return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(amount);
}

function monthDefaults() {
  const now = new Date();
  const start = new Date(now.getFullYear(), now.getMonth(), 1);
  const end = new Date(now.getFullYear(), now.getMonth() + 1, 0);
  const iso = (value: Date) => value.toISOString().slice(0, 10);
  return {
    period: `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`,
    start: iso(start),
    end: iso(end),
  };
}

async function requestPayrollDashboard(token: string) {
  const response = await fetch(`${API_BASE}/api/v1/finance/payroll-dashboard`, { headers: { Authorization: `Bearer ${token}` } });
  if (!response.ok) throw new Error("Payroll dashboard API failed");
  return await response.json() as PayrollDashboard;
}

export default function FinancePage() {
  const router = useRouter();
  const defaults = useMemo(() => monthDefaults(), []);
  const [dashboard, setDashboard] = useState<PayrollDashboard | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [periodName, setPeriodName] = useState(defaults.period);
  const [startDate, setStartDate] = useState(defaults.start);
  const [endDate, setEndDate] = useState(defaults.end);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<PayrollResult | null>(null);

  useEffect(() => {
    const token = localStorage.getItem("factorypulse_token");
    if (!token) {
      router.push("/login");
      return;
    }
    requestPayrollDashboard(token)
      .then((body) => setDashboard(body))
      .catch((err) => setError(err instanceof Error ? err.message : "Payroll dashboard API failed"));
  }, [router]);

  async function runPayroll(dryRun: boolean) {
    setBusy(true);
    setError("");
    setNotice("");
    const token = localStorage.getItem("factorypulse_token");
    if (!token) {
      router.push("/login");
      return;
    }
    try {
      const response = await fetch(`${API_BASE}/api/v1/payroll/${dryRun ? "validate" : "generate"}`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ period_name: periodName, start_date: startDate, end_date: endDate, dry_run: dryRun }),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.detail || "Payroll generation failed");
      setResult(body);
      setNotice(dryRun ? "Payroll validation completed from live attendance, leave, salary, and adjustment records." : "Draft payroll generated and saved to ERP.");
      setDashboard(await requestPayrollDashboard(token));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Payroll generation failed");
    } finally {
      setBusy(false);
    }
  }

  const stats = [
    ["Payroll Runs", dashboard?.stats.payroll_runs || 0],
    ["Employee Results", dashboard?.stats.employee_results || 0],
    ["Adjustments", dashboard?.stats.adjustments || 0],
    ["Salary Slips", dashboard?.stats.salary_slips || 0],
  ];

  return (
    <main className="min-h-screen bg-slate-100 text-slate-950">
      <header className="sticky top-0 z-20 border-b border-slate-200 bg-white/95 backdrop-blur">
        <div className="mx-auto flex max-w-7xl flex-col gap-3 px-4 py-4 md:flex-row md:items-center md:justify-between">
          <div>
            <Link href="/" className="text-sm font-semibold text-teal-700">All departments</Link>
            <h1 className="mt-1 text-2xl font-semibold">Finance Payroll Center</h1>
            <p className="text-sm text-slate-500">Generate draft payroll from salary assignments, attendance, leave, and approved adjustments.</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link href="/finance/salary" className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm font-medium text-emerald-700 hover:border-emerald-600">Salary Structures</Link>
            <Link href="/finance/adjustments" className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium hover:border-teal-600">Adjustments</Link>
            <Link href="/finance/payments" className="rounded-lg border border-violet-200 bg-violet-50 px-3 py-2 text-sm font-medium text-violet-700 hover:border-violet-600">Payments</Link>
            <Link href="/finance/statutory" className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm font-medium text-amber-700 hover:border-amber-600">Statutory</Link>
            <Link href="/finance/settings" className="rounded-lg border border-sky-200 bg-sky-50 px-3 py-2 text-sm font-medium text-sky-700 hover:border-sky-600">Policy Settings</Link>
            <Link href="/departments/finance?module=payroll_runs" className="rounded-lg bg-slate-950 px-3 py-2 text-sm font-medium text-white hover:bg-slate-800">Payroll Runs</Link>
          </div>
        </div>
      </header>

      <section className="mx-auto max-w-7xl px-4 py-6">
        {error ? <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</div> : null}
        {notice ? <div className="mb-4 rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-700">{notice}</div> : null}

        <div className="grid gap-4 lg:grid-cols-[1fr_380px]">
          <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
            <p className="text-sm font-semibold uppercase tracking-wide text-teal-700">Payroll engine</p>
            <h2 className="mt-2 text-3xl font-semibold tracking-tight">Monthly payroll generation</h2>
            <p className="mt-2 max-w-3xl text-sm text-slate-600">The backend calculates paid days, prorated gross pay, additions, deductions, net pay, calculation lines, salary slips, and audit entries. Use validation first, then generate draft payroll.</p>

            <div className="mt-5 grid gap-3 md:grid-cols-3">
              <label className="text-sm font-medium text-slate-700">
                Payroll period
                <input value={periodName} onChange={(event) => setPeriodName(event.target.value)} className="mt-1 h-11 w-full rounded-lg border border-slate-300 px-3 outline-none focus:border-teal-700" />
              </label>
              <label className="text-sm font-medium text-slate-700">
                Start date
                <input type="date" value={startDate} onChange={(event) => setStartDate(event.target.value)} className="mt-1 h-11 w-full rounded-lg border border-slate-300 px-3 outline-none focus:border-teal-700" />
              </label>
              <label className="text-sm font-medium text-slate-700">
                End date
                <input type="date" value={endDate} onChange={(event) => setEndDate(event.target.value)} className="mt-1 h-11 w-full rounded-lg border border-slate-300 px-3 outline-none focus:border-teal-700" />
              </label>
            </div>

            <div className="mt-4 flex flex-wrap gap-2">
              <button disabled={busy} onClick={() => runPayroll(true)} className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-semibold hover:border-teal-600 disabled:opacity-50">Validate Payroll</button>
              <button disabled={busy} onClick={() => runPayroll(false)} className="rounded-lg bg-teal-700 px-4 py-2 text-sm font-semibold text-white hover:bg-teal-800 disabled:opacity-50">Generate Draft Payroll</button>
            </div>

            {result ? (
              <div className="mt-5 rounded-lg border border-slate-200 bg-slate-50 p-4">
                <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                  <div>
                    <h3 className="font-semibold">{result.dry_run ? "Validation" : "Draft payroll"} {result.run_no}</h3>
                    <p className="text-sm text-slate-500">{result.period} - {result.totals.employees} employees</p>
                  </div>
                  <div className="text-right">
                    <div className="text-2xl font-semibold text-teal-700">{currency(result.totals.net_pay)}</div>
                    <div className="text-xs text-slate-500">Net salary</div>
                  </div>
                </div>
                {result.validation_errors.length > 0 ? (
                  <div className="mt-3 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
                    {result.validation_errors.map((item) => <div key={item}>{item}</div>)}
                  </div>
                ) : null}
                <div className="mt-3 overflow-auto">
                  <table className="w-full min-w-[640px] text-left text-sm">
                    <thead className="text-xs uppercase text-slate-500">
                      <tr><th className="p-2">Employee</th><th className="p-2">Paid Days</th><th className="p-2">Gross</th><th className="p-2">Deductions</th><th className="p-2">Net</th></tr>
                    </thead>
                    <tbody>
                      {result.results.slice(0, 8).map((row) => (
                        <tr key={row.employee_code} className="border-t border-slate-200">
                          <td className="p-2 font-medium">{row.employee_code}</td>
                          <td className="p-2">{row.paid_days}</td>
                          <td className="p-2">{currency(row.gross_pay)}</td>
                          <td className="p-2">{currency(row.deductions)}</td>
                          <td className="p-2 font-semibold">{currency(row.net_pay)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            ) : null}
          </section>

          <aside className="space-y-4">
            <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
              <h2 className="font-semibold">Live Totals</h2>
              <div className="mt-3 grid grid-cols-2 gap-2">
                {stats.map(([label, value]) => (
                  <div key={label} className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                    <div className="text-xl font-semibold">{value}</div>
                    <div className="text-xs text-slate-500">{label}</div>
                  </div>
                ))}
              </div>
              <div className="mt-3 rounded-lg border border-teal-200 bg-teal-50 p-3">
                <div className="text-xs font-medium text-teal-700">Current Net Payroll</div>
                <div className="mt-1 text-2xl font-semibold text-teal-800">{currency(dashboard?.stats.total_net)}</div>
              </div>
            </div>

            <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
              <h2 className="font-semibold">Recent Runs</h2>
              <div className="mt-3 space-y-2">
                {(dashboard?.payroll_runs || []).length === 0 ? (
                  <p className="text-sm text-slate-500">No payroll runs generated yet.</p>
                ) : dashboard?.payroll_runs.slice(0, 6).map((run) => (
                  <div key={run.id} className="rounded-lg border border-slate-100 p-3">
                    <div className="text-sm font-semibold">{run.data.run_no || run.id}</div>
                    <div className="mt-1 text-xs text-slate-500">{run.data.period} - {run.status}</div>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
              <h2 className="font-semibold">Pending Adjustments</h2>
              <div className="mt-3 space-y-2">
                {(dashboard?.adjustments || []).filter((item) => ["Open", "Pending", "Pending Approval", "Draft"].includes(item.status)).slice(0, 5).map((item) => (
                  <Link key={item.id} href="/finance/adjustments" className="block rounded-lg border border-amber-100 bg-amber-50 p-3">
                    <div className="text-sm font-semibold">{item.data.employee_code || "Employee"}</div>
                    <div className="mt-1 text-xs text-amber-800">{item.data.adjustment_type} - {currency(item.data.amount)}</div>
                  </Link>
                ))}
              </div>
            </div>
          </aside>
        </div>
      </section>
    </main>
  );
}
