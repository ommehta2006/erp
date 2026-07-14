"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8000";

type RecordItem = { id: string; data: Record<string, string>; status: string };
type Dashboard = {
  active_policy: Record<string, string>;
  policies: RecordItem[];
  stats: Record<string, number>;
  allowed_proration_methods: string[];
  default_adjustment_categories: string[];
};

const DEFAULT_FORM = {
  policy_name: "Default Payroll Policy",
  proration_method: "Calendar Day",
  fixed_divisor: "",
  rounding_rule: "Round 2 Decimals",
  max_adjustment_amount: "50000",
  role_adjustment_limits: "",
  retroactive_months_allowed: "2",
  approval_required: true,
  lock_after_approval: true,
  allow_reversal_after_lock: true,
  adjustment_categories: [] as string[],
  statutory_notes: "",
  effective_start_date: "",
  effective_end_date: "",
  approval_status: "Approved",
  status: "Active",
};

function currency(value: number | string | undefined) {
  const amount = Number(value || 0);
  return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(amount);
}

function authHeaders() {
  const token = localStorage.getItem("factorypulse_token") || "";
  return { "Content-Type": "application/json", Authorization: `Bearer ${token}` };
}

function parseBool(value: string | undefined, fallback = true) {
  if (!value) return fallback;
  return value.toLowerCase() === "true";
}

function parseCategories(value: string | undefined) {
  return (value || "").split(",").map((item) => item.trim()).filter(Boolean);
}

async function requestDashboard() {
  const response = await fetch(`${API_BASE}/api/v1/finance/settings-dashboard`, { headers: authHeaders() });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.detail || "Payroll settings API failed");
  return body as Dashboard;
}

export default function FinanceSettingsPage() {
  const router = useRouter();
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [form, setForm] = useState(DEFAULT_FORM);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  useEffect(() => {
    if (!localStorage.getItem("factorypulse_token")) {
      router.push("/login");
      return;
    }
    requestDashboard()
      .then((body) => {
        setDashboard(body);
        const policy = body.active_policy || {};
        const categories = parseCategories(policy.adjustment_categories);
        setForm({
          policy_name: policy.policy_name || DEFAULT_FORM.policy_name,
          proration_method: policy.proration_method || DEFAULT_FORM.proration_method,
          fixed_divisor: policy.fixed_divisor || "",
          rounding_rule: policy.rounding_rule || DEFAULT_FORM.rounding_rule,
          max_adjustment_amount: policy.max_adjustment_amount || String(body.stats.max_adjustment_amount || 50000),
          role_adjustment_limits: policy.role_adjustment_limits || "",
          retroactive_months_allowed: policy.retroactive_months_allowed || String(body.stats.retroactive_months_allowed || 2),
          approval_required: parseBool(policy.approval_required, true),
          lock_after_approval: parseBool(policy.lock_after_approval, true),
          allow_reversal_after_lock: parseBool(policy.allow_reversal_after_lock, true),
          adjustment_categories: categories.length ? categories : body.default_adjustment_categories,
          statutory_notes: policy.statutory_notes || "",
          effective_start_date: policy.effective_start_date || "",
          effective_end_date: policy.effective_end_date || "",
          approval_status: policy.approval_status || "Approved",
          status: policy.status || "Active",
        });
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Payroll settings API failed"));
  }, [router]);

  async function savePolicy() {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const response = await fetch(`${API_BASE}/api/v1/finance/payroll-policy`, {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({
          ...form,
          fixed_divisor: form.fixed_divisor ? Number(form.fixed_divisor) : undefined,
          max_adjustment_amount: Number(form.max_adjustment_amount),
          retroactive_months_allowed: Number(form.retroactive_months_allowed),
          adjustment_categories: form.adjustment_categories.join(", "),
        }),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.detail || "Could not save payroll policy");
      setDashboard(body.dashboard || await requestDashboard());
      setNotice("Payroll policy saved and activated.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save payroll policy");
    } finally {
      setBusy(false);
    }
  }

  function toggleCategory(category: string) {
    const hasCategory = form.adjustment_categories.includes(category);
    setForm({
      ...form,
      adjustment_categories: hasCategory
        ? form.adjustment_categories.filter((item) => item !== category)
        : [...form.adjustment_categories, category],
    });
  }

  const statRows = [
    ["Policies", dashboard?.stats.policies || 0],
    ["Active", dashboard?.stats.active_policies || 0],
    ["Adjustments", dashboard?.stats.adjustments || 0],
    ["Locked Runs", dashboard?.stats.locked_runs || 0],
  ];

  return (
    <main className="min-h-screen bg-slate-100 text-slate-950">
      <header className="sticky top-0 z-20 border-b border-slate-200 bg-white/95 backdrop-blur">
        <div className="mx-auto flex max-w-7xl flex-col gap-3 px-4 py-4 md:flex-row md:items-center md:justify-between">
          <div>
            <Link href="/finance" className="text-sm font-semibold text-teal-700">Finance Payroll Center</Link>
            <h1 className="mt-1 text-2xl font-semibold">Payroll Policy Settings</h1>
            <p className="text-sm text-slate-500">Configure salary proration, adjustment limits, retroactive rules, approvals, and payroll lock behavior.</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link href="/finance/adjustments" className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium hover:border-teal-600">Adjustments</Link>
            <Link href="/departments/finance?module=payroll_policies" className="rounded-lg bg-slate-950 px-3 py-2 text-sm font-medium text-white hover:bg-slate-800">Raw Policies</Link>
          </div>
        </div>
      </header>

      <section className="mx-auto max-w-7xl px-4 py-6">
        {error ? <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</div> : null}
        {notice ? <div className="mb-4 rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-700">{notice}</div> : null}

        <section className="grid gap-4 lg:grid-cols-[1fr_360px]">
          <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
            <p className="text-sm font-semibold text-teal-700">Active payroll control</p>
            <h2 className="mt-2 text-3xl font-semibold tracking-tight">Policy configuration</h2>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
              These values are read by payroll validation, payroll generation, and payroll adjustment approval checks.
            </p>

            <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
              <Input label="Policy Name" value={form.policy_name} onChange={(value) => setForm({ ...form, policy_name: value })} />
              <Select label="Proration Method" value={form.proration_method} options={dashboard?.allowed_proration_methods || ["Calendar Day"]} onChange={(value) => setForm({ ...form, proration_method: value })} />
              <Input label="Fixed Divisor" value={form.fixed_divisor} onChange={(value) => setForm({ ...form, fixed_divisor: value })} placeholder="Required for Fixed Divisor" />
              <Input label="Max Adjustment Amount" value={form.max_adjustment_amount} onChange={(value) => setForm({ ...form, max_adjustment_amount: value })} />
              <Input label="Retroactive Months Allowed" value={form.retroactive_months_allowed} onChange={(value) => setForm({ ...form, retroactive_months_allowed: value })} />
              <Input label="Rounding Rule" value={form.rounding_rule} onChange={(value) => setForm({ ...form, rounding_rule: value })} />
              <Input label="Effective Start Date" value={form.effective_start_date} onChange={(value) => setForm({ ...form, effective_start_date: value })} placeholder="YYYY-MM-DD" />
              <Input label="Effective End Date" value={form.effective_end_date} onChange={(value) => setForm({ ...form, effective_end_date: value })} placeholder="Optional" />
              <Input label="Role Adjustment Limits JSON" value={form.role_adjustment_limits} onChange={(value) => setForm({ ...form, role_adjustment_limits: value })} placeholder='{"FINANCE_ADMIN":50000}' />
            </div>

            <div className="mt-5 grid gap-3 md:grid-cols-3">
              <Toggle label="Approval Required" checked={form.approval_required} onChange={(checked) => setForm({ ...form, approval_required: checked })} />
              <Toggle label="Lock After Approval" checked={form.lock_after_approval} onChange={(checked) => setForm({ ...form, lock_after_approval: checked })} />
              <Toggle label="Allow Reversal After Lock" checked={form.allow_reversal_after_lock} onChange={(checked) => setForm({ ...form, allow_reversal_after_lock: checked })} />
            </div>

            <div className="mt-5">
              <h3 className="text-sm font-semibold text-slate-800">Allowed adjustment categories</h3>
              <div className="mt-3 grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
                {(dashboard?.default_adjustment_categories || []).map((category) => (
                  <label key={category} className="flex items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm">
                    <input type="checkbox" checked={form.adjustment_categories.includes(category)} onChange={() => toggleCategory(category)} />
                    <span>{category}</span>
                  </label>
                ))}
              </div>
            </div>

            <label className="mt-5 block text-sm font-medium text-slate-700">
              Statutory / company policy notes
              <textarea value={form.statutory_notes} onChange={(event) => setForm({ ...form, statutory_notes: event.target.value })} className="mt-1 min-h-24 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-teal-700" />
            </label>

            <button disabled={busy} onClick={savePolicy} className="mt-4 rounded-lg bg-teal-700 px-4 py-2 text-sm font-semibold text-white hover:bg-teal-800 disabled:opacity-50">
              {busy ? "Saving..." : "Save Payroll Policy"}
            </button>
          </div>

          <aside className="space-y-4">
            <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
              <h2 className="font-semibold">Policy summary</h2>
              <div className="mt-3 grid grid-cols-2 gap-2">
                {statRows.map(([label, value]) => (
                  <div key={label} className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                    <div className="text-xl font-semibold">{value}</div>
                    <div className="text-xs text-slate-500">{label}</div>
                  </div>
                ))}
              </div>
              <div className="mt-3 rounded-lg border border-teal-200 bg-teal-50 p-3">
                <div className="text-xs font-semibold text-teal-700">Adjustment limit</div>
                <div className="mt-1 text-2xl font-semibold text-teal-900">{currency(dashboard?.stats.max_adjustment_amount)}</div>
              </div>
            </div>

            <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
              <h2 className="font-semibold">Active policy</h2>
              <div className="mt-3 space-y-2 text-sm">
                <Line label="Policy" value={dashboard?.active_policy.policy_name || "Default Payroll Policy"} />
                <Line label="Proration" value={dashboard?.active_policy.proration_method || "Calendar Day"} />
                <Line label="Rounding" value={dashboard?.active_policy.rounding_rule || "Round 2 Decimals"} />
                <Line label="Retro Months" value={dashboard?.active_policy.retroactive_months_allowed || "2"} />
              </div>
            </div>
          </aside>
        </section>

        <section className="mt-5 rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="font-semibold">Policy history</h2>
          <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {(dashboard?.policies || []).length === 0 ? (
              <p className="text-sm text-slate-500">No saved policy rows yet. The default policy is currently active.</p>
            ) : dashboard?.policies.map((item) => (
              <div key={item.id} className="rounded-lg border border-slate-100 bg-slate-50 p-3">
                <div className="flex items-center justify-between gap-2">
                  <div className="truncate text-sm font-semibold">{item.data.policy_name}</div>
                  <span className="rounded-lg border border-slate-200 bg-white px-2 py-1 text-xs font-semibold text-slate-700">{item.status}</span>
                </div>
                <div className="mt-2 text-xs text-slate-500">{item.data.proration_method} / Limit {currency(item.data.max_adjustment_amount)}</div>
                <div className="mt-1 line-clamp-2 text-xs text-slate-500">{item.data.adjustment_categories}</div>
              </div>
            ))}
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

function Toggle({ label, checked, onChange }: { label: string; checked: boolean; onChange: (checked: boolean) => void }) {
  return (
    <label className="flex items-center justify-between gap-3 rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm font-medium text-slate-700">
      {label}
      <input type="checkbox" checked={checked} onChange={(event) => onChange(event.target.checked)} />
    </label>
  );
}

function Line({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-3 border-b border-slate-100 pb-2">
      <span className="text-slate-500">{label}</span>
      <span className="text-right font-semibold text-slate-900">{value}</span>
    </div>
  );
}
