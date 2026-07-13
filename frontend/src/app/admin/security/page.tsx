"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8000";

type SecurityUser = {
  email: string;
  full_name?: string;
  role: string;
  department_id?: string;
  status: string;
  failed_login_count?: number;
  locked_until?: number | null;
  bootstrap?: boolean;
};

type SecurityDashboard = {
  stats: Record<string, number>;
  users: SecurityUser[];
  roles: { role: string; permissions: string[] }[];
  recent_audit: { id: string; data: Record<string, string>; status: string }[];
  permission_denied: { id: string; data: Record<string, string>; status: string }[];
  device_integrity_events: { id: string; data: Record<string, string>; status: string }[];
  protected_surfaces: { surface: string; permission: string }[];
};

const EMPTY_USER = {
  email: "",
  password: "",
  full_name: "",
  role: "HR_ADMIN",
  department_id: "hr",
  status: "Active",
};

async function requestSecurityDashboard(token: string) {
  const response = await fetch(`${API_BASE}/api/v1/admin/security-dashboard`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok) throw new Error("Security dashboard API failed");
  return (await response.json()) as SecurityDashboard;
}

function roleTone(role: string) {
  if (["FACTORY_ADMIN", "SUPER_ADMIN"].includes(role)) return "bg-slate-950 text-white";
  if (role.includes("HR")) return "bg-teal-100 text-teal-800";
  if (role.includes("FINANCE")) return "bg-sky-100 text-sky-800";
  if (role.includes("AUDITOR")) return "bg-indigo-100 text-indigo-800";
  return "bg-amber-100 text-amber-800";
}

export default function AdminSecurityPage() {
  const router = useRouter();
  const [dashboard, setDashboard] = useState<SecurityDashboard | null>(null);
  const [form, setForm] = useState(EMPTY_USER);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem("factorypulse_token");
    if (!token) {
      router.push("/login");
      return;
    }
    requestSecurityDashboard(token)
      .then(setDashboard)
      .catch((err) => setError(err instanceof Error ? err.message : "Security dashboard API failed"));
  }, [router]);

  async function createUser(event: React.FormEvent) {
    event.preventDefault();
    setError("");
    setNotice("");
    const token = localStorage.getItem("factorypulse_token");
    if (!token) {
      router.push("/login");
      return;
    }
    setBusy(true);
    try {
      const response = await fetch(`${API_BASE}/api/v1/admin/users`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify(form),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.detail || "Create user failed");
      setNotice("RBAC user created and audited.");
      setForm(EMPTY_USER);
      setDashboard(await requestSecurityDashboard(token));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Create user failed");
    } finally {
      setBusy(false);
    }
  }

  const stats = [
    ["Users", dashboard?.stats.users || 0],
    ["Active", dashboard?.stats.active_users || 0],
    ["Locked", dashboard?.stats.locked_users || 0],
    ["Failed Login", dashboard?.stats.failed_login_users || 0],
    ["Roles", dashboard?.stats.roles || 0],
    ["Denied", dashboard?.stats.permission_denied_events || 0],
  ];

  return (
    <main className="min-h-screen bg-slate-100 text-slate-950">
      <header className="sticky top-0 z-20 border-b border-slate-200 bg-white/95 backdrop-blur">
        <div className="mx-auto flex max-w-7xl flex-col gap-3 px-4 py-4 md:flex-row md:items-center md:justify-between">
          <div>
            <Link href="/" className="text-sm font-semibold text-teal-700">All departments</Link>
            <h1 className="mt-1 text-2xl font-semibold">Security Center</h1>
            <p className="text-sm text-slate-500">RBAC roles, user access, permission denials, device risk, and audit visibility.</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link href="/reports" className="rounded-lg border border-indigo-200 bg-indigo-50 px-3 py-2 text-sm font-medium text-indigo-700 hover:border-indigo-600">Reports</Link>
            <Link href="/admin/audit" className="rounded-lg bg-slate-950 px-3 py-2 text-sm font-medium text-white hover:bg-slate-800">Audit Logs</Link>
          </div>
        </div>
      </header>

      <section className="mx-auto max-w-7xl px-4 py-6">
        {error ? <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</div> : null}
        {notice ? <div className="mb-4 rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-700">{notice}</div> : null}

        <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <div>
            <p className="text-sm font-semibold text-teal-700">Access governance</p>
            <h2 className="mt-2 text-3xl font-semibold">Role-based ERP control</h2>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">Sensitive HR, finance, reporting, and generic record writes now check backend permissions. Denied attempts are written to audit logs.</p>
          </div>
          <div className="mt-5 grid grid-cols-2 gap-2 md:grid-cols-3 xl:grid-cols-6">
            {stats.map(([label, value]) => (
              <div key={label} className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                <div className="text-xs font-medium text-slate-500">{label}</div>
                <div className="mt-1 text-2xl font-semibold">{value}</div>
              </div>
            ))}
          </div>
        </section>

        <div className="mt-5 grid gap-4 xl:grid-cols-[1fr_420px]">
          <section className="rounded-lg border border-slate-200 bg-white shadow-sm">
            <div className="border-b border-slate-200 p-4">
              <h2 className="text-xl font-semibold">Users</h2>
              <p className="mt-1 text-sm text-slate-500">Application users and current RBAC roles.</p>
            </div>
            <div className="overflow-auto">
              <table className="w-full min-w-[760px] text-left text-sm">
                <thead className="bg-slate-50 text-xs uppercase text-slate-500">
                  <tr><th className="p-3">User</th><th className="p-3">Role</th><th className="p-3">Department</th><th className="p-3">Status</th><th className="p-3">Failed</th></tr>
                </thead>
                <tbody>
                  {(dashboard?.users || []).length === 0 ? (
                    <tr><td className="p-6 text-slate-500" colSpan={5}>No app users found.</td></tr>
                  ) : dashboard?.users.map((user) => (
                    <tr key={`${user.email}-${user.role}`} className="border-t border-slate-100">
                      <td className="p-3"><div className="font-medium">{user.full_name || user.email}</div><div className="text-xs text-slate-500">{user.email}{user.bootstrap ? " / bootstrap" : ""}</div></td>
                      <td className="p-3"><span className={`rounded-lg px-2 py-1 text-xs font-semibold ${roleTone(user.role)}`}>{user.role}</span></td>
                      <td className="p-3">{user.department_id || "-"}</td>
                      <td className="p-3">{user.status}</td>
                      <td className="p-3">{user.failed_login_count || 0}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <aside className="space-y-4">
            <form onSubmit={createUser} className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
              <h2 className="font-semibold">Create User</h2>
              <div className="mt-3 grid gap-2">
                <Input label="Full Name" value={form.full_name} onChange={(value) => setForm((current) => ({ ...current, full_name: value }))} />
                <Input label="Email" type="email" value={form.email} onChange={(value) => setForm((current) => ({ ...current, email: value }))} />
                <Input label="Password" type="password" value={form.password} onChange={(value) => setForm((current) => ({ ...current, password: value }))} />
                <label className="text-sm font-medium text-slate-700">
                  Role
                  <select value={form.role} onChange={(event) => setForm((current) => ({ ...current, role: event.target.value }))} className="mt-1 h-10 w-full rounded-lg border border-slate-300 px-3 text-sm outline-none focus:border-teal-700">
                    {(dashboard?.roles || []).map((role) => <option key={role.role} value={role.role}>{role.role}</option>)}
                  </select>
                </label>
                <Input label="Department" value={form.department_id} onChange={(value) => setForm((current) => ({ ...current, department_id: value }))} />
                <button disabled={busy} className="rounded-lg bg-teal-700 px-3 py-2 text-sm font-semibold text-white disabled:opacity-50">{busy ? "Saving" : "Create User"}</button>
              </div>
            </form>

            <Panel title="Role Matrix">
              <div className="space-y-2">
                {(dashboard?.roles || []).map((role) => (
                  <div key={role.role} className="rounded-lg border border-slate-100 bg-slate-50 p-3">
                    <div className="text-sm font-semibold">{role.role}</div>
                    <div className="mt-2 flex flex-wrap gap-1.5">
                      {role.permissions.map((permission) => <span key={permission} className="rounded-lg bg-white px-2 py-1 text-xs text-slate-700">{permission}</span>)}
                    </div>
                  </div>
                ))}
              </div>
            </Panel>

            <Panel title="Protected Surfaces">
              <div className="space-y-2">
                {(dashboard?.protected_surfaces || []).map((item) => (
                  <div key={item.surface} className="flex items-center justify-between gap-2 rounded-lg border border-slate-100 bg-slate-50 p-3">
                    <span className="text-sm font-medium">{item.surface}</span>
                    <span className="rounded-lg bg-white px-2 py-1 text-xs text-slate-600">{item.permission}</span>
                  </div>
                ))}
              </div>
            </Panel>
          </aside>
        </div>
      </section>
    </main>
  );
}

function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <h2 className="font-semibold">{title}</h2>
      <div className="mt-3">{children}</div>
    </section>
  );
}

function Input({ label, value, onChange, type = "text" }: { label: string; value: string; onChange: (value: string) => void; type?: string }) {
  return (
    <label className="text-sm font-medium text-slate-700">
      {label}
      <input type={type} value={value} onChange={(event) => onChange(event.target.value)} className="mt-1 h-10 w-full rounded-lg border border-slate-300 px-3 text-sm outline-none focus:border-teal-700" />
    </label>
  );
}
