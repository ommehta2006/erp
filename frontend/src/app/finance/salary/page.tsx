"use client";

import Link from "next/link";
import { type ReactNode, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8000";

type RecordItem = { id: string; data: Record<string, string>; status: string };
type Dashboard = {
  stats: Record<string, number>;
  structures: RecordItem[];
  components: RecordItem[];
  assignments: RecordItem[];
  pending_revisions: RecordItem[];
  recent_revisions: RecordItem[];
};

const today = new Date().toISOString().slice(0, 10);
const DEFAULT_STRUCTURE = { structure_name: "", currency: "INR", payment_frequency: "Monthly", proration_method: "Payroll Policy", basic_salary: "", allowances: "", deductions: "", employer_contributions: "", employee_contributions: "" };
const DEFAULT_COMPONENT = { structure_id: "", component_name: "", component_type: "Earning", calculation_method: "Fixed", amount: "", percentage_of: "", taxable: true, payroll_impact: "Gross" };
const DEFAULT_ASSIGNMENT = { employee_code: "", structure_id: "", effective_date: today, basic_salary: "", allowances: "", deductions: "", employer_contributions: "", employee_contributions: "", currency: "INR", payment_frequency: "Monthly" };
const DEFAULT_REVISION = { employee_code: "", structure_id: "", effective_date: today, basic_salary: "", allowances: "", deductions: "", revision_type: "Salary Revision", reason: "", supporting_document: "" };

function currency(value: number | string | undefined) {
  const amount = Number(value || 0);
  return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(amount);
}

function num(value: string) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

function authHeaders() {
  const token = localStorage.getItem("factorypulse_token") || "";
  return { "Content-Type": "application/json", Authorization: `Bearer ${token}` };
}

async function requestDashboard() {
  const response = await fetch(`${API_BASE}/api/v1/finance/salary-dashboard`, { headers: authHeaders() });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.detail || "Salary dashboard API failed");
  return body as Dashboard;
}

function tone(status: string) {
  if (status === "Approved" || status === "Active") return "border-emerald-200 bg-emerald-50 text-emerald-800";
  if (status === "Rejected" || status === "Inactive") return "border-rose-200 bg-rose-50 text-rose-800";
  return "border-amber-200 bg-amber-50 text-amber-800";
}

export default function FinanceSalaryPage() {
  const router = useRouter();
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [structure, setStructure] = useState(DEFAULT_STRUCTURE);
  const [component, setComponent] = useState(DEFAULT_COMPONENT);
  const [assignment, setAssignment] = useState(DEFAULT_ASSIGNMENT);
  const [revision, setRevision] = useState(DEFAULT_REVISION);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  useEffect(() => {
    if (!localStorage.getItem("factorypulse_token")) {
      router.push("/login");
      return;
    }
    requestDashboard().then((body) => {
      setDashboard(body);
      const first = body.structures[0]?.data.structure_id || "";
      setComponent((current) => ({ ...current, structure_id: current.structure_id || first }));
      setAssignment((current) => ({ ...current, structure_id: current.structure_id || first }));
      setRevision((current) => ({ ...current, structure_id: current.structure_id || first }));
    }).catch((err) => setError(err instanceof Error ? err.message : "Salary dashboard API failed"));
  }, [router]);

  const structureOptions = useMemo(() => (dashboard?.structures || []).map((item) => item.data.structure_id).filter(Boolean), [dashboard]);
  const stats = [
    ["Structures", dashboard?.stats.structures || 0],
    ["Components", dashboard?.stats.components || 0],
    ["Assignments", dashboard?.stats.active_assignments || 0],
    ["Pending Revisions", dashboard?.stats.pending_revisions || 0],
  ];

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

  function saveStructure() {
    return postJson("/api/v1/finance/salary-structures", {
      ...structure,
      basic_salary: num(structure.basic_salary),
      allowances: num(structure.allowances),
      deductions: num(structure.deductions),
      employer_contributions: num(structure.employer_contributions),
      employee_contributions: num(structure.employee_contributions),
    }, "Salary structure saved.");
  }

  function saveComponent() {
    return postJson("/api/v1/finance/salary-components", {
      ...component,
      amount: num(component.amount),
    }, "Salary component saved.");
  }

  function saveAssignment() {
    return postJson("/api/v1/finance/salary-assignments", {
      ...assignment,
      basic_salary: num(assignment.basic_salary),
      allowances: num(assignment.allowances),
      deductions: num(assignment.deductions),
      employer_contributions: num(assignment.employer_contributions),
      employee_contributions: num(assignment.employee_contributions),
    }, "Employee salary assignment saved.");
  }

  function requestRevision() {
    return postJson("/api/v1/finance/salary-revisions", {
      ...revision,
      basic_salary: num(revision.basic_salary),
      allowances: num(revision.allowances),
      deductions: num(revision.deductions),
    }, "Salary revision submitted for approval.");
  }

  function decideRevision(revisionId: string, decision: string) {
    return postJson("/api/v1/finance/salary-revisions/decision", {
      revision_id: revisionId,
      decision,
      remarks: `${decision} from salary control center`,
    }, `Salary revision ${decision.toLowerCase()}.`);
  }

  return (
    <main className="min-h-screen bg-slate-100 text-slate-950">
      <header className="sticky top-0 z-20 border-b border-slate-200 bg-white/95 backdrop-blur">
        <div className="mx-auto flex max-w-7xl flex-col gap-3 px-4 py-4 md:flex-row md:items-center md:justify-between">
          <div>
            <Link href="/finance" className="text-sm font-semibold text-teal-700">Finance Payroll Center</Link>
            <h1 className="mt-1 text-2xl font-semibold">Salary Structures</h1>
            <p className="text-sm text-slate-500">Configure salary templates, components, employee assignments, and immutable salary revision approvals.</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link href="/finance/settings" className="rounded-lg border border-sky-200 bg-sky-50 px-3 py-2 text-sm font-medium text-sky-700 hover:border-sky-600">Payroll Policy</Link>
            <Link href="/departments/finance?module=salary_structures" className="rounded-lg bg-slate-950 px-3 py-2 text-sm font-medium text-white hover:bg-slate-800">Raw Tables</Link>
          </div>
        </div>
      </header>

      <section className="mx-auto max-w-7xl px-4 py-6">
        {error ? <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</div> : null}
        {notice ? <div className="mb-4 rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-700">{notice}</div> : null}

        <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <p className="text-sm font-semibold text-teal-700">Salary control</p>
              <h2 className="mt-2 text-3xl font-semibold tracking-tight">Effective-dated salary records</h2>
              <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
                Payroll generation uses active employee salary assignments. Approved revisions create new assignments and preserve revision history.
              </p>
            </div>
            <div className="rounded-lg border border-teal-200 bg-teal-50 p-4">
              <div className="text-xs font-semibold uppercase text-teal-700">Current active CTC</div>
              <div className="mt-1 text-2xl font-semibold text-teal-900">{currency(dashboard?.stats.current_ctc)}</div>
            </div>
          </div>
          <div className="mt-5 grid grid-cols-2 gap-2 md:grid-cols-4">
            {stats.map(([label, value]) => (
              <div key={label} className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                <div className="text-xs font-medium text-slate-500">{label}</div>
                <div className="mt-1 text-xl font-semibold">{value}</div>
              </div>
            ))}
          </div>
        </section>

        <section className="mt-5 grid gap-4 xl:grid-cols-[430px_1fr]">
          <aside className="space-y-4">
            <Panel title="Create Structure" action="Save structure" busy={busy === "/api/v1/finance/salary-structures"} onSubmit={saveStructure}>
              <Input label="Structure Name" value={structure.structure_name} onChange={(value) => setStructure({ ...structure, structure_name: value })} />
              <div className="grid grid-cols-2 gap-3">
                <Input label="Currency" value={structure.currency} onChange={(value) => setStructure({ ...structure, currency: value })} />
                <Select label="Frequency" value={structure.payment_frequency} options={["Monthly", "Weekly", "Daily"]} onChange={(value) => setStructure({ ...structure, payment_frequency: value })} />
              </div>
              <Input label="Basic Salary" value={structure.basic_salary} onChange={(value) => setStructure({ ...structure, basic_salary: value })} />
              <Input label="Allowances" value={structure.allowances} onChange={(value) => setStructure({ ...structure, allowances: value })} />
              <Input label="Deductions" value={structure.deductions} onChange={(value) => setStructure({ ...structure, deductions: value })} />
              <Input label="Employer Contributions" value={structure.employer_contributions} onChange={(value) => setStructure({ ...structure, employer_contributions: value })} />
              <Input label="Employee Contributions" value={structure.employee_contributions} onChange={(value) => setStructure({ ...structure, employee_contributions: value })} />
            </Panel>

            <Panel title="Add Component" action="Save component" busy={busy === "/api/v1/finance/salary-components"} onSubmit={saveComponent}>
              <Select label="Structure" value={component.structure_id} options={["", ...structureOptions]} onChange={(value) => setComponent({ ...component, structure_id: value })} />
              <Input label="Component Name" value={component.component_name} onChange={(value) => setComponent({ ...component, component_name: value })} />
              <Select label="Type" value={component.component_type} options={["Earning", "Deduction", "Employer Contribution", "Employee Contribution"]} onChange={(value) => setComponent({ ...component, component_type: value })} />
              <Select label="Method" value={component.calculation_method} options={["Fixed", "Percent", "Formula"]} onChange={(value) => setComponent({ ...component, calculation_method: value })} />
              <Input label="Amount" value={component.amount} onChange={(value) => setComponent({ ...component, amount: value })} />
              <Input label="Percentage Of" value={component.percentage_of} onChange={(value) => setComponent({ ...component, percentage_of: value })} />
              <label className="flex items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm">
                <input type="checkbox" checked={component.taxable} onChange={(event) => setComponent({ ...component, taxable: event.target.checked })} />
                Taxable component
              </label>
            </Panel>

            <Panel title="Assign Employee Salary" action="Save assignment" busy={busy === "/api/v1/finance/salary-assignments"} onSubmit={saveAssignment}>
              <Input label="Employee Code" value={assignment.employee_code} onChange={(value) => setAssignment({ ...assignment, employee_code: value })} />
              <Select label="Structure" value={assignment.structure_id} options={["", ...structureOptions]} onChange={(value) => setAssignment({ ...assignment, structure_id: value })} />
              <Input label="Effective Date" value={assignment.effective_date} onChange={(value) => setAssignment({ ...assignment, effective_date: value })} />
              <Input label="Basic Salary" value={assignment.basic_salary} onChange={(value) => setAssignment({ ...assignment, basic_salary: value })} />
              <Input label="Allowances" value={assignment.allowances} onChange={(value) => setAssignment({ ...assignment, allowances: value })} />
              <Input label="Deductions" value={assignment.deductions} onChange={(value) => setAssignment({ ...assignment, deductions: value })} />
            </Panel>

            <Panel title="Request Salary Revision" action="Submit revision" busy={busy === "/api/v1/finance/salary-revisions"} onSubmit={requestRevision}>
              <Input label="Employee Code" value={revision.employee_code} onChange={(value) => setRevision({ ...revision, employee_code: value })} />
              <Select label="Structure" value={revision.structure_id} options={["", ...structureOptions]} onChange={(value) => setRevision({ ...revision, structure_id: value })} />
              <Input label="Effective Date" value={revision.effective_date} onChange={(value) => setRevision({ ...revision, effective_date: value })} />
              <Input label="Basic Salary" value={revision.basic_salary} onChange={(value) => setRevision({ ...revision, basic_salary: value })} />
              <Input label="Allowances" value={revision.allowances} onChange={(value) => setRevision({ ...revision, allowances: value })} />
              <Input label="Deductions" value={revision.deductions} onChange={(value) => setRevision({ ...revision, deductions: value })} />
              <Input label="Reason" value={revision.reason} onChange={(value) => setRevision({ ...revision, reason: value })} />
              <Input label="Supporting Document" value={revision.supporting_document} onChange={(value) => setRevision({ ...revision, supporting_document: value })} />
            </Panel>
          </aside>

          <section className="space-y-4">
            <Queue rows={dashboard?.pending_revisions || []} onDecision={decideRevision} />
            <Table title="Salary Structures" rows={dashboard?.structures || []} columns={["structure_id", "structure_name", "gross_salary", "ctc", "net_salary_estimate"]} />
            <Table title="Active Assignments" rows={dashboard?.assignments || []} columns={["employee_code", "structure_id", "effective_date", "gross_salary", "ctc", "approval_status"]} />
            <Table title="Salary Components" rows={dashboard?.components || []} columns={["structure_id", "component_name", "component_type", "amount", "taxable"]} />
            <Table title="Revision History" rows={dashboard?.recent_revisions || []} columns={["employee_code", "effective_date", "previous_salary", "new_salary", "increase_percent", "approval_status"]} />
          </section>
        </section>
      </section>
    </main>
  );
}

function Panel({ title, action, busy, onSubmit, children }: { title: string; action: string; busy: boolean; onSubmit: () => void; children: ReactNode }) {
  return (
    <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <h2 className="font-semibold">{title}</h2>
      <div className="mt-3 space-y-3">{children}</div>
      <button disabled={busy} onClick={onSubmit} className="mt-4 w-full rounded-lg bg-slate-950 px-3 py-2 text-sm font-semibold text-white hover:bg-slate-800 disabled:opacity-50">
        {busy ? "Saving..." : action}
      </button>
    </section>
  );
}

function Input({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  return (
    <label className="block">
      <span className="text-xs font-medium text-slate-500">{label}</span>
      <input value={value} onChange={(event) => onChange(event.target.value)} className="mt-1 h-10 w-full rounded-lg border border-slate-300 px-3 text-sm outline-none focus:border-teal-700" />
    </label>
  );
}

function Select({ label, value, options, onChange }: { label: string; value: string; options: string[]; onChange: (value: string) => void }) {
  return (
    <label className="block">
      <span className="text-xs font-medium text-slate-500">{label}</span>
      <select value={value} onChange={(event) => onChange(event.target.value)} className="mt-1 h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm outline-none focus:border-teal-700">
        {options.map((option) => <option key={option || "blank"} value={option}>{option || "Select"}</option>)}
      </select>
    </label>
  );
}

function Queue({ rows, onDecision }: { rows: RecordItem[]; onDecision: (revisionId: string, decision: string) => void }) {
  return (
    <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-center justify-between gap-3">
        <h2 className="font-semibold">Pending Salary Revisions</h2>
        <span className="rounded-lg bg-amber-50 px-3 py-1 text-sm font-semibold text-amber-800">{rows.length}</span>
      </div>
      <div className="mt-3 space-y-3">
        {rows.length === 0 ? <p className="text-sm text-slate-500">No pending revisions.</p> : rows.map((item) => {
          const id = item.data.revision_id || item.id;
          return (
            <div key={item.id} className="rounded-lg border border-slate-100 bg-slate-50 p-3">
              <div className="flex items-center justify-between gap-2">
                <div className="text-sm font-semibold">{item.data.employee_code}</div>
                <span className={`rounded-lg border px-2 py-1 text-xs font-semibold ${tone(item.status)}`}>{item.status}</span>
              </div>
              <div className="mt-1 text-xs text-slate-500">{item.data.effective_date} / {currency(item.data.previous_salary)} to {currency(item.data.new_salary)}</div>
              <div className="mt-1 text-sm text-slate-600">{item.data.reason}</div>
              <div className="mt-3 flex flex-wrap gap-2">
                <button onClick={() => onDecision(id, "Approved")} className="rounded-lg bg-teal-700 px-3 py-1.5 text-xs font-semibold text-white">Approve</button>
                <button onClick={() => onDecision(id, "Rejected")} className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-1.5 text-xs font-semibold text-rose-700">Reject</button>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}

function Table({ title, rows, columns }: { title: string; rows: RecordItem[]; columns: string[] }) {
  return (
    <section className="rounded-lg border border-slate-200 bg-white shadow-sm">
      <div className="border-b border-slate-200 p-4">
        <h2 className="font-semibold">{title}</h2>
        <p className="mt-1 text-sm text-slate-500">{rows.length} records</p>
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full text-left text-sm">
          <thead className="bg-slate-50 text-xs uppercase text-slate-500">
            <tr>
              {columns.map((column) => <th key={column} className="p-3">{column.replaceAll("_", " ")}</th>)}
              <th className="p-3">Status</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr><td className="p-4 text-slate-500" colSpan={columns.length + 1}>No records yet.</td></tr>
            ) : rows.map((row) => (
              <tr key={row.id} className="border-t border-slate-100">
                {columns.map((column) => <td key={column} className="p-3">{column.includes("salary") || column.includes("ctc") ? currency(row.data[column]) : row.data[column] || "-"}</td>)}
                <td className="p-3"><span className={`rounded-lg border px-2 py-1 text-xs font-semibold ${tone(row.data.approval_status || row.status)}`}>{row.data.approval_status || row.status}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
