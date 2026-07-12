"use client";

import { useState } from "react";
import Link from "next/link";

const DEPARTMENTS = [
  { id: "hr", name: "Human Resources", icon: "👥", color: "from-pink-500 to-rose-500", desc: "Manage employees, attendance, and leave" },
  { id: "finance", name: "Finance", icon: "💰", color: "from-emerald-400 to-cyan-500", desc: "Invoices, payroll, and expenses" },
  { id: "operations", name: "Operations", icon: "⚙️", color: "from-blue-500 to-indigo-600", desc: "Production, incidents, and maintenance" },
  { id: "inventory", name: "Inventory", icon: "📦", color: "from-amber-400 to-orange-500", desc: "Stock levels, warehouses, and orders" },
  { id: "sales", name: "Sales & CRM", icon: "📈", color: "from-violet-500 to-fuchsia-500", desc: "Leads, customers, and opportunities" },
];

export default function DashboardPage() {
  const [hovered, setHovered] = useState<string | null>(null);

  return (
    <main className="min-h-screen bg-slate-950 text-white p-6 relative overflow-x-hidden">
      {/* Decorative Background */}
      <div className="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] bg-indigo-600/20 rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute bottom-[-20%] right-[-10%] w-[50%] h-[50%] bg-fuchsia-600/20 rounded-full blur-[120px] pointer-events-none" />

      {/* Header */}
      <header className="flex justify-between items-center mb-12 glass-dark px-8 py-4 rounded-2xl sticky top-4 z-50">
        <div>
          <h1 className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-indigo-400 to-cyan-400">
            FactoryPulse Global
          </h1>
          <p className="text-xs text-gray-400 uppercase tracking-widest mt-1">Enterprise Dashboard</p>
        </div>
        <div className="flex items-center gap-4">
          <div className="text-right">
            <p className="text-sm font-semibold">Admin User</p>
            <p className="text-xs text-emerald-400">Online</p>
          </div>
          <div className="w-10 h-10 rounded-full bg-gradient-to-tr from-purple-500 to-indigo-500 flex items-center justify-center font-bold shadow-lg">
            A
          </div>
          <Link href="/login" className="ml-4 px-4 py-2 bg-white/10 hover:bg-white/20 rounded-lg text-sm transition-colors">
            Logout
          </Link>
        </div>
      </header>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto z-10 relative">
        <h2 className="text-4xl font-light mb-2">Welcome back, Admin.</h2>
        <p className="text-gray-400 mb-10 text-lg">Select a department to access its specialized modules.</p>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {DEPARTMENTS.map((dept) => (
            <Link href={`/departments/${dept.id}`} key={dept.id}>
              <div 
                className={`group relative glass p-6 rounded-3xl overflow-hidden cursor-pointer transition-all duration-500 ease-out hover:shadow-2xl hover:shadow-${dept.color.split("-")[1]}/20 transform hover:-translate-y-2`}
                onMouseEnter={() => setHovered(dept.id)}
                onMouseLeave={() => setHovered(null)}
              >
                <div className={`absolute inset-0 bg-gradient-to-br ${dept.color} opacity-0 group-hover:opacity-10 transition-opacity duration-500`} />
                
                <div className="flex justify-between items-start mb-12">
                  <span className="text-4xl">{dept.icon}</span>
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center bg-white/5 border border-white/10 group-hover:bg-white/20 transition-colors`}>
                    <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" /></svg>
                  </div>
                </div>

                <h3 className="text-2xl font-bold mb-2 group-hover:text-white transition-colors">{dept.name}</h3>
                <p className="text-gray-400 group-hover:text-gray-300 text-sm transition-colors">{dept.desc}</p>
                
                {/* Decorative line */}
                <div className={`h-1 w-12 rounded-full mt-6 bg-gradient-to-r ${dept.color} transform origin-left transition-all duration-500 ${hovered === dept.id ? 'scale-x-150' : ''}`} />
              </div>
            </Link>
          ))}
        </div>
      </div>
    </main>
  );
}
