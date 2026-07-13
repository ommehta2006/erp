"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8000";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("admin@factorypulse.local");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    const response = await fetch(`${API_BASE}/api/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    if (!response.ok) {
      setError("Invalid credentials or backend unavailable");
      return;
    }
    const data = await response.json();
    localStorage.setItem("factorypulse_token", data.token);
    router.push("/");
  }

  return (
    <main className="min-h-screen flex items-center justify-center bg-[#f6f7f9] p-4 text-[#17202a]">
      <div className="w-full max-w-md rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
        <div className="mb-8">
          <h1 className="text-2xl font-bold">FactoryPulse ERP</h1>
          <p className="mt-1 text-sm text-slate-600">Sign in to the global factory workspace.</p>
        </div>
        {error && <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>}
        <form onSubmit={handleLogin} className="space-y-4">
          <label className="block text-sm font-medium">Email
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2" required />
          </label>
          <label className="block text-sm font-medium">Password
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2" required />
          </label>
          <button type="submit" className="w-full rounded-lg bg-teal-700 px-4 py-2 font-semibold text-white">Sign in</button>
        </form>
      </div>
    </main>
  );
}
