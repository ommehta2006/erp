"use client";

import { use } from "react";
import Link from "next/link";
import { useEffect, useState } from "react";

const DEPARTMENTS = {
  "hr": { name: "Human Resources", color: "from-pink-500 to-rose-500", api: "hr/employees", columns: ["ID", "Name", "Role"] },
  "finance": { name: "Finance", color: "from-emerald-400 to-cyan-500", api: "finance/invoices", columns: ["ID", "Amount", "Status"] },
  "operations": { name: "Operations", color: "from-blue-500 to-indigo-600", api: "operations/incidents", columns: ["ID", "Type", "Severity"] },
  "inventory": { name: "Inventory", color: "from-amber-400 to-orange-500", api: "inventory/items", columns: ["ID", "Item", "Quantity"] },
  "sales": { name: "Sales & CRM", color: "from-violet-500 to-fuchsia-500", api: "sales/leads", columns: ["ID", "Lead Name", "Stage"] },
};

export default function DepartmentPage({ params }: { params: Promise<{ id: string }> }) {
  const resolvedParams = use(params);
  const deptId = resolvedParams.id as keyof typeof DEPARTMENTS;
  const dept = DEPARTMENTS[deptId];
  
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Simulated fetch from our FastAPI backend
    // In production: fetch(`http://localhost:8000/api/${dept?.api}`)
    setTimeout(() => {
      setData([
        { id: "1", col1: "Sample Data A", col2: "Active" },
        { id: "2", col1: "Sample Data B", col2: "Pending" },
        { id: "3", col1: "Sample Data C", col2: "Completed" },
      ]);
      setLoading(false);
    }, 1000);
  }, [deptId]);

  if (!dept) {
    return <div className="p-8 text-white">Department not found</div>;
  }

  return (
    <main className="min-h-screen bg-slate-950 text-white p-6">
      <div className={`absolute top-0 left-0 w-full h-64 bg-gradient-to-b ${dept.color} opacity-20 mask-image-b`} />
      
      <div className="max-w-7xl mx-auto relative z-10">
        <Link href="/" className="inline-flex items-center text-gray-400 hover:text-white mb-8 transition-colors">
          <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" /></svg>
          Back to Dashboard
        </Link>
        
        <div className="flex justify-between items-end mb-12">
          <div>
            <h1 className="text-5xl font-extrabold mb-2 bg-clip-text text-transparent bg-gradient-to-r from-white to-gray-400">
              {dept.name}
            </h1>
            <p className="text-gray-400">Manage all {dept.name.toLowerCase()} operations efficiently.</p>
          </div>
          <button className={`px-6 py-3 rounded-xl bg-gradient-to-r ${dept.color} text-white font-bold shadow-lg transform transition hover:scale-105 active:scale-95`}>
            + Add Record
          </button>
        </div>

        <div className="glass-dark rounded-3xl overflow-hidden border border-white/5">
          {loading ? (
            <div className="p-12 flex justify-center items-center">
              <div className="w-12 h-12 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin"></div>
            </div>
          ) : (
            <table className="w-full text-left">
              <thead>
                <tr className="border-b border-white/10 bg-white/5 text-sm uppercase tracking-wider text-gray-400">
                  {dept.columns.map((col, idx) => (
                    <th key={idx} className="p-6 font-medium">{col}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {data.map((row, i) => (
                  <tr key={i} className="border-b border-white/5 hover:bg-white/5 transition-colors">
                    <td className="p-6 font-mono text-gray-300">{row.id}</td>
                    <td className="p-6 text-white font-medium">{row.col1}</td>
                    <td className="p-6">
                      <span className="px-3 py-1 rounded-full bg-white/10 text-xs font-semibold">{row.col2}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </main>
  );
}
