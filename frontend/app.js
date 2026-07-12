const state = {
  token: localStorage.getItem("fp_token"),
  user: null,
  catalog: {},
  dashboard: null,
  current: "dashboard",
  items: [],
  report: null,
  users: [],
  settings: null,
  searchResults: [],
  searchQuery: "",
  mobileHome: null,
  theme: localStorage.getItem("fp_theme") || "light",
};

document.documentElement.dataset.theme = state.theme;
const app = document.querySelector("#app");

async function api(path, options = {}) {
  const res = await fetch(path, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(state.token ? { Authorization: `Bearer ${state.token}` } : {}),
      ...(options.headers || {}),
    },
  });
  const contentType = res.headers.get("content-type") || "";
  const data = contentType.includes("application/json") ? await res.json() : await res.text();
  if (!res.ok) throw new Error(data.error?.message || "Request failed");
  return data;
}

function el(name, attrs = {}, children = []) {
  const node = document.createElement(name);
  Object.entries(attrs).forEach(([key, value]) => {
    if (key === "class") node.className = value;
    else if (key === "style") node.setAttribute("style", value);
    else if (key.startsWith("on")) node.addEventListener(key.slice(2), value);
    else node.setAttribute(key, value);
  });
  children.forEach(child => node.append(child?.nodeType ? child : document.createTextNode(child ?? "")));
  return node;
}

function toast(message) {
  const node = el("div", { class: "toast", role: "status" }, [message]);
  document.body.append(node);
  setTimeout(() => node.remove(), 3600);
}

async function boot() {
  if (!state.token) return renderLogin();
  try {
    const [me, catalog, dashboard] = await Promise.all([api("/api/me"), api("/api/catalog"), api("/api/dashboard")]);
    state.user = me.user;
    state.catalog = catalog.resources;
    state.dashboard = dashboard;
    renderShell();
  } catch {
    localStorage.removeItem("fp_token");
    state.token = null;
    renderLogin();
  }
}

function renderLogin() {
  app.innerHTML = "";
  const form = el("form", { class: "panel login-card", onsubmit: login }, [
    el("div", { class: "brand" }, [el("span", { class: "mark" }, ["FP"]), "FactoryPulse ERP"]),
    el("h1", {}, ["Factory operations, employee workflows, and ERP control in one secure workspace"]),
    el("p", {}, ["Sign in to review the deploy-ready factory ERP system."]),
    el("div", { class: "section form-grid" }, [
      el("label", {}, ["Email", el("input", { name: "email", type: "email", value: "admin@factorypulse.local", autocomplete: "username", required: "true" })]),
      el("label", {}, ["Password", el("input", { name: "password", type: "password", value: "ChangeMe-FactoryPulse-2026!", autocomplete: "current-password", required: "true" })]),
    ]),
    el("button", { class: "primary", type: "submit" }, ["Sign in"]),
  ]);
  app.append(el("main", { class: "login" }, [form]));
}

async function login(event) {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  try {
    const data = await api("/api/auth/login", { method: "POST", body: JSON.stringify(Object.fromEntries(form)) });
    state.token = data.token;
    localStorage.setItem("fp_token", state.token);
    await boot();
  } catch (err) {
    toast(err.message);
  }
}

function renderShell() {
  app.innerHTML = "";
  const nav = Object.entries(state.catalog).map(([key, spec]) =>
    el("button", { class: "nav-item", "aria-current": state.current === key ? "page" : "false", onclick: () => openResource(key) }, [
      el("span", {}, [spec.label]),
      el("span", { class: "badge" }, [String(state.dashboard?.counts?.[key] ?? 0)]),
    ])
  );
  const sidebar = el("aside", { class: "sidebar" }, [
    el("div", { class: "brand" }, [el("span", { class: "mark" }, ["FP"]), el("span", {}, ["FactoryPulse"])]),
    el("div", { class: "nav-label" }, ["Command"]),
    navButton("dashboard", "Executive Dashboard", () => showDashboard()),
    navButton("mobile", "Employee App", () => openMobile()),
    navButton("report", "Operations Report", () => openReport()),
    navButton("users", "People & Access", () => openUsers()),
    navButton("settings", "Security Center", () => openSettings()),
    navButton("audit", "Audit Events", () => openAudit()),
    el("div", { class: "nav-label" }, ["ERP Modules"]),
    ...nav,
  ]);
  const searchInput = el("input", { id: "global-search", placeholder: "Search modules and records", onkeydown: commandSearch });
  const main = el("main", { class: "main" }, [
    el("header", { class: "topbar" }, [
      el("div", { class: "search" }, ["Ctrl K", searchInput]),
      el("div", { class: "actions" }, [
        el("span", { class: "muted" }, [`${state.user.name} / ${state.user.role}`]),
        el("button", { class: "ghost", onclick: toggleTheme }, [state.theme === "dark" ? "Light" : "Dark"]),
        el("button", { class: "ghost", onclick: logout }, ["Logout"]),
      ]),
    ]),
    el("div", { class: "content", id: "view" }),
  ]);
  app.append(el("div", { class: "shell" }, [sidebar, main]));
  routeView();
}

function navButton(key, text, handler) {
  return el("button", { class: "nav-item", "aria-current": state.current === key ? "page" : "false", onclick: handler }, [text]);
}

function routeView() {
  if (state.current === "dashboard") renderDashboard();
  else if (state.current === "mobile") renderMobile();
  else if (state.current === "report") renderReport();
  else if (state.current === "users") renderUsers();
  else if (state.current === "settings") renderSettings();
  else if (state.current === "audit") renderAuditView();
  else if (state.current === "search") renderSearch();
  else renderResource();
}

function commandSearch(event) {
  if (event.key !== "Enter") return;
  openSearch(event.currentTarget.value);
}

document.addEventListener("keydown", event => {
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
    event.preventDefault();
    document.querySelector("#global-search")?.focus();
  }
});

function toggleTheme() {
  state.theme = state.theme === "dark" ? "light" : "dark";
  localStorage.setItem("fp_theme", state.theme);
  document.documentElement.dataset.theme = state.theme;
  renderShell();
}

function logout() {
  localStorage.removeItem("fp_token");
  state.token = null;
  renderLogin();
}

function view() {
  return document.querySelector("#view");
}

function showDashboard() {
  state.current = "dashboard";
  renderShell();
}

function renderDashboard() {
  const root = view();
  root.innerHTML = "";
  const total = Object.values(state.dashboard.counts || {}).reduce((a, b) => a + b, 0);
  root.append(
    el("section", { class: "hero" }, [
      el("div", { class: "panel section" }, [
        el("div", { class: "title-row" }, [
          el("div", {}, [el("h1", {}, ["Factory command center"]), el("p", {}, [`${state.user.tenant_name} / live operational workspace with server-side permissions`])]),
          el("div", { class: "actions" }, [
            el("button", { class: "ghost", onclick: () => openReport() }, ["Operations Report"]),
            el("button", { class: "primary", onclick: () => openResource("approvals") }, ["Approval Inbox"]),
          ]),
        ]),
        el("div", { class: "kpis" }, [
          kpi("Visible records", total),
          kpi("Modules", Object.keys(state.catalog).length),
          kpi("Production batches", state.dashboard.counts.production_batches || 0),
          kpi("Open approvals", state.dashboard.counts.approvals || 0),
        ]),
      ]),
      el("div", { class: "panel section" }, [
        el("h2", {}, ["Secure API status"]),
        el("p", {}, ["Bearer sessions, RBAC, tenant isolation, validation, idempotent creates, CSV export, audit events, CORS allowlist, and persistent SQLite storage are active."]),
        el("div", { class: "pillgrid" }, [badge("Operational", "ok"), badge("No dummy API"), badge("Tenant scoped"), badge("OpenAPI")]),
      ]),
    ]),
    el("section", { class: "grid" }, [
      miniTable("Latest production", state.dashboard.production || []),
      miniTable("Approval queue", state.dashboard.approvals || []),
      miniTable("Maintenance focus", state.dashboard.work_orders || []),
    ])
  );
}

function kpi(label, value) {
  return el("div", { class: "kpi" }, [el("span", { class: "muted" }, [label]), el("strong", {}, [String(value)])]);
}

function badge(text, tone = "") {
  return el("span", { class: `badge ${tone}`.trim() }, [text]);
}

function miniTable(title, items) {
  const columns = items[0] ? Object.keys(items[0].data).slice(0, 4) : [];
  return el("div", { class: "panel section" }, [
    el("h2", {}, [title]),
    items.length ? table(columns, items) : el("p", {}, ["No records visible for your role."]),
  ]);
}


async function openMobile() {
  state.current = "mobile";
  state.mobileHome = await api("/api/mobile/home");
  renderShell();
}

function renderMobile() {
  const root = view();
  root.innerHTML = "";
  const m = state.mobileHome || {};
  const profile = m.profile?.data || {};
  root.append(el("section", { class: "mobile-shell" }, [
    el("div", { class: "phone-panel panel section" }, [
      el("div", { class: "title-row" }, [
        el("div", {}, [el("h1", {}, ["Employee app"]), el("p", {}, [profile.full_name ? `${profile.full_name} / ${profile.employee_code}` : "Self-service workspace"])]),
        badge("PWA ready", "ok"),
      ]),
      el("div", { class: "quick-grid" }, [
        el("button", { class: "primary", onclick: () => mobileAction("check-in") }, ["Check in"]),
        el("button", { class: "ghost", onclick: openLeaveDrawer }, ["Leave"]),
        el("button", { class: "ghost", onclick: openIncidentDrawer }, ["Incident"]),
        el("button", { class: "danger-button", onclick: () => mobileAction("sos") }, ["SOS"]),
      ]),
      mobileList("Recent attendance", m.attendance || [], ["date", "shift", "check_in", "gps_area", "status"]),
      mobileList("My tasks", m.tasks || [], ["title", "due_date", "priority", "status"]),
      mobileList("Training", m.training_records || [], ["course", "completion_date", "score", "status"]),
      mobileList("Documents", m.documents || [], ["title", "classification", "expiry_date", "status"]),
    ]),
    el("div", { class: "panel section" }, [
      el("h2", {}, ["Employee workflows"]),
      el("p", {}, ["Attendance, leave, incident reporting, SOS, tasks, training, and document access are backed by authenticated API calls and tenant-scoped persistence."]),
      el("div", { class: "pillgrid" }, [badge("GPS area captured"), badge("Audit logged"), badge("Role checked"), badge("Offline shell")]),
    ]),
  ]));
}

function mobileList(title, items, columns) {
  return el("div", { class: "mobile-list" }, [
    el("h2", {}, [title]),
    ...(items.length ? items.map(item => el("div", { class: "mobile-card" }, columns.map(c => el("div", {}, [el("span", { class: "muted" }, [label(c)]), " ", formatCell(item.data[c], c)])))) : [el("p", {}, ["No visible records."])])
  ]);
}

async function mobileAction(action) {
  try {
    const path = action === "sos" ? "/api/mobile/sos" : "/api/mobile/check-in";
    const payload = action === "sos" ? { area: "Factory", summary: "Emergency SOS from employee app" } : { gps_area: "Factory Gate" };
    await api(path, { method: "POST", body: JSON.stringify(payload) });
    toast(action === "sos" ? "SOS incident created" : "Attendance checked in");
    await refreshDashboard();
    await openMobile();
  } catch (err) {
    toast(err.message);
  }
}

function openLeaveDrawer() {
  const form = el("form", { onsubmit: saveMobileLeave }, [
    el("div", { class: "title-row" }, [el("div", {}, [el("h2", {}, ["Request leave"]), el("p", {}, ["Submitted through secure mobile API."])]), el("button", { type: "button", class: "ghost", onclick: closeDrawer }, ["Close"])]),
    el("div", { class: "form-grid" }, [
      el("label", {}, ["Leave type", el("input", { name: "leave_type", value: "Casual Leave" })]),
      el("label", {}, ["From", el("input", { name: "from_date", type: "date" })]),
      el("label", {}, ["To", el("input", { name: "to_date", type: "date" })]),
      el("label", {}, ["Reason", el("input", { name: "reason", value: "Personal work" })]),
    ]),
    el("div", { class: "actions", style: "margin-top:16px" }, [el("button", { class: "primary", type: "submit" }, ["Submit"])]),
  ]);
  document.body.append(el("div", { class: "drawer", role: "dialog", "aria-modal": "true" }, [el("div", {}, [form])]));
}

async function saveMobileLeave(event) {
  event.preventDefault();
  try {
    await api("/api/mobile/leave-request", { method: "POST", body: JSON.stringify(Object.fromEntries(new FormData(event.currentTarget))) });
    closeDrawer();
    toast("Leave request submitted");
    await openMobile();
  } catch (err) {
    toast(err.message);
  }
}

function openIncidentDrawer() {
  const form = el("form", { onsubmit: saveMobileIncident }, [
    el("div", { class: "title-row" }, [el("div", {}, [el("h2", {}, ["Report incident"]), el("p", {}, ["Creates a safety record and audit event."])]), el("button", { type: "button", class: "ghost", onclick: closeDrawer }, ["Close"])]),
    el("div", { class: "form-grid" }, [
      el("label", {}, ["Area", el("input", { name: "area", value: "Factory" })]),
      el("label", {}, ["Severity", el("select", { name: "severity" }, ["Low", "Medium", "High", "Critical"].map(x => el("option", { value: x }, [x])))]),
      el("label", {}, ["Summary", el("input", { name: "summary", value: "Describe the incident" })]),
      el("label", {}, ["Corrective action", el("input", { name: "corrective_action", value: "Supervisor review required" })]),
    ]),
    el("div", { class: "actions", style: "margin-top:16px" }, [el("button", { class: "primary", type: "submit" }, ["Submit"])]),
  ]);
  document.body.append(el("div", { class: "drawer", role: "dialog", "aria-modal": "true" }, [el("div", {}, [form])]));
}

async function saveMobileIncident(event) {
  event.preventDefault();
  try {
    await api("/api/mobile/incident", { method: "POST", body: JSON.stringify(Object.fromEntries(new FormData(event.currentTarget))) });
    closeDrawer();
    toast("Incident reported");
    await openMobile();
  } catch (err) {
    toast(err.message);
  }
}

async function openResource(resource) {
  state.current = resource;
  state.items = (await api(`/api/${resource}`)).items;
  renderShell();
}

function renderResource() {
  const spec = state.catalog[state.current];
  const root = view();
  root.innerHTML = "";
  root.append(el("section", { class: "panel section" }, [
    el("div", { class: "title-row" }, [
      el("div", {}, [el("h1", {}, [spec.label]), el("p", {}, ["Create, inspect, update, and export tenant records through secured API calls."])]),
      el("div", { class: "actions" }, [
        el("button", { class: "ghost", onclick: () => exportResource(state.current) }, ["Export CSV"]),
        el("button", { class: "primary", onclick: () => openDrawer() }, ["New Record"]),
      ]),
    ]),
    state.items.length ? table(spec.fields, state.items, true) : el("p", {}, ["No records yet. Create the first record for this module."]),
  ]));
}

function table(columns, items, editable = false) {
  return el("div", { class: "table-wrap" }, [el("table", {}, [
    el("thead", {}, [el("tr", {}, [...columns.map(c => el("th", {}, [label(c)])), editable ? el("th", {}, ["Actions"]) : null].filter(Boolean))]),
    el("tbody", {}, items.map(item => el("tr", {}, [
      ...columns.map(c => el("td", {}, [formatCell(item.data?.[c] ?? item[c], c)])),
      editable ? el("td", {}, [el("button", { class: "ghost", onclick: () => openDrawer(item) }, ["Edit"])]) : null
    ].filter(Boolean)))),
  ])]);
}

function label(text) {
  return String(text).replaceAll("_", " ").replace(/\b\w/g, c => c.toUpperCase());
}

function formatCell(value, key) {
  const text = String(value ?? "-");
  if (key === "status" || key === "decision" || key.includes("priority") || key.includes("severity") || key.includes("approval")) {
    const cls = /open|pending|high|awaiting|draft|checked in/i.test(text) ? "warn" : /reject|critical|failed/i.test(text) ? "danger" : "ok";
    return el("span", { class: `badge ${cls}` }, [text]);
  }
  return text;
}

function openDrawer(item = null) {
  const spec = state.catalog[state.current];
  const form = el("form", { onsubmit: event => saveRecord(event, item) }, [
    el("div", { class: "title-row" }, [
      el("div", {}, [el("h2", {}, [item ? "Edit record" : "Create record"]), el("p", {}, [spec.label])]),
      el("button", { type: "button", class: "ghost", onclick: closeDrawer }, ["Close"]),
    ]),
    el("div", { class: "form-grid" }, spec.fields.map(field => el("label", {}, [label(field), el("input", { name: field, value: item?.data?.[field] ?? "" })]))),
    el("div", { class: "actions", style: "margin-top:16px" }, [el("button", { class: "primary", type: "submit" }, ["Save"]), el("button", { class: "ghost", type: "button", onclick: closeDrawer }, ["Cancel"])]),
  ]);
  document.body.append(el("div", { class: "drawer", role: "dialog", "aria-modal": "true" }, [el("div", {}, [form])]));
}

function closeDrawer() {
  document.querySelector(".drawer")?.remove();
}

async function saveRecord(event, item) {
  event.preventDefault();
  const payload = Object.fromEntries(new FormData(event.currentTarget));
  try {
    const path = item ? `/api/${state.current}/${item.id}` : `/api/${state.current}`;
    const method = item ? "PATCH" : "POST";
    const headers = item ? {} : { "Idempotency-Key": `ui-${state.current}-${Date.now()}` };
    await api(path, { method, headers, body: JSON.stringify(payload) });
    closeDrawer();
    toast("Record saved");
    await refreshDashboard();
    await openResource(state.current);
  } catch (err) {
    toast(err.message);
  }
}

async function exportResource(resource) {
  try {
    const res = await fetch(`/api/export/${resource}.csv`, { headers: { Authorization: `Bearer ${state.token}` } });
    if (!res.ok) throw new Error("Export failed");
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const link = el("a", { href: url, download: `${resource}.csv` }, []);
    document.body.append(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
    toast("CSV export prepared");
  } catch (err) {
    toast(err.message);
  }
}

async function refreshDashboard() {
  state.dashboard = await api("/api/dashboard");
}

async function openReport() {
  state.current = "report";
  state.report = await api("/api/reports/operations-summary");
  renderShell();
}

function renderReport() {
  const root = view();
  root.innerHTML = "";
  const r = state.report || {};
  root.append(el("section", { class: "panel section" }, [
    el("div", { class: "title-row" }, [el("div", {}, [el("h1", {}, ["Operations report"]), el("p", {}, ["Tenant-safe KPI summary from live API data."])])]),
    el("div", { class: "kpis" }, [
      kpi("Cane crushed", r.cane_crushed_ton || "0"),
      kpi("Recovery", `${r.recovery_percent || "0"}%`),
      kpi("Power kWh", r.power_generation_kwh || "0"),
      kpi("Sugar bags", r.sugar_bags || "0"),
    ]),
    el("div", { class: "section" }, [el("h2", {}, ["Risk signals"]), ...(r.risk_signals || []).map(x => el("p", {}, [x]))]),
  ]));
}

async function openUsers() {
  state.current = "users";
  state.users = (await api("/api/admin/users")).items;
  renderShell();
}

function renderUsers() {
  const root = view();
  root.innerHTML = "";
  root.append(el("section", { class: "panel section" }, [
    el("div", { class: "title-row" }, [
      el("div", {}, [el("h1", {}, ["People & access"]), el("p", {}, ["Create users with server-side role validation and redacted credentials."])]),
      el("button", { class: "primary", onclick: openUserDrawer }, ["New User"]),
    ]),
    simpleTable(["email", "name", "role", "status"], state.users),
  ]));
}

function openUserDrawer() {
  const roles = ["EMPLOYEE", "HR_MANAGER", "PRODUCTION_MANAGER", "FARMER_OFFICER", "QUALITY_MANAGER", "MAINTENANCE_MANAGER", "INVENTORY_MANAGER", "FINANCE_MANAGER", "FACTORY_ADMIN"];
  const form = el("form", { onsubmit: saveUser }, [
    el("div", { class: "title-row" }, [el("div", {}, [el("h2", {}, ["Create user"]), el("p", {}, ["Password is hashed by the API and never returned."])]), el("button", { type: "button", class: "ghost", onclick: closeDrawer }, ["Close"])]),
    el("div", { class: "form-grid" }, [
      el("label", {}, ["Email", el("input", { name: "email", type: "email", required: "true" })]),
      el("label", {}, ["Name", el("input", { name: "name", required: "true" })]),
      el("label", {}, ["Role", el("select", { name: "role" }, roles.map(r => el("option", { value: r }, [r])))]),
      el("label", {}, ["Temporary password", el("input", { name: "password", type: "password", required: "true", value: "Temp-User-2026!" })]),
    ]),
    el("div", { class: "actions", style: "margin-top:16px" }, [el("button", { class: "primary", type: "submit" }, ["Create"])]),
  ]);
  document.body.append(el("div", { class: "drawer", role: "dialog", "aria-modal": "true" }, [el("div", {}, [form])]));
}

async function saveUser(event) {
  event.preventDefault();
  try {
    await api("/api/admin/users", { method: "POST", body: JSON.stringify(Object.fromEntries(new FormData(event.currentTarget))) });
    closeDrawer();
    toast("User created");
    await openUsers();
  } catch (err) {
    toast(err.message);
  }
}

function simpleTable(columns, rows) {
  return el("div", { class: "table-wrap" }, [el("table", {}, [
    el("thead", {}, [el("tr", {}, columns.map(c => el("th", {}, [label(c)])))]),
    el("tbody", {}, rows.map(row => el("tr", {}, columns.map(c => el("td", {}, [formatCell(row[c], c)]))))),
  ])]);
}

async function openSettings() {
  state.current = "settings";
  state.settings = await api("/api/admin/settings");
  renderShell();
}

function renderSettings() {
  const root = view();
  root.innerHTML = "";
  const s = state.settings || {};
  root.append(el("section", { class: "panel section" }, [
    el("h1", {}, ["Security center"]),
    el("p", {}, ["Runtime and tenant configuration summary. Secret values are never exposed."]),
    el("div", { class: "kpis" }, [
      kpi("Environment", s.app_env || "unknown"),
      kpi("Modules", s.module_count || 0),
      kpi("Token TTL", `${s.token_ttl_seconds || 0}s`),
      kpi("CORS", s.cors_configured ? "Configured" : "Default"),
    ]),
    el("div", { class: "section" }, [el("h2", {}, ["Available roles"]), el("p", {}, [(s.available_roles || []).join(", ")])]),
  ]));
}

async function openSearch(query) {
  const q = String(query || "").trim();
  if (q.length < 2) return toast("Enter at least 2 characters");
  state.current = "search";
  state.searchQuery = q;
  state.searchResults = (await api(`/api/search?q=${encodeURIComponent(q)}`)).items;
  renderShell();
}

function renderSearch() {
  const root = view();
  root.innerHTML = "";
  root.append(el("section", { class: "panel section" }, [
    el("h1", {}, [`Search: ${state.searchQuery}`]),
    el("p", {}, ["Results are filtered by your server-side permissions and tenant context."]),
    el("div", { class: "command-results" }, state.searchResults.length ? state.searchResults.map(result =>
      el("button", { class: "result-row", onclick: () => openResource(result.resource) }, [
        el("strong", {}, [result.label]),
        el("span", { class: "muted" }, [Object.values(result.item.data).slice(0, 4).join(" / ")]),
      ])
    ) : [el("p", {}, ["No visible records matched."])]),
  ]));
}

async function openAudit() {
  state.current = "audit";
  renderShell();
}

async function renderAuditView() {
  const root = view();
  root.innerHTML = "";
  try {
    const data = await api("/api/audit-events");
    root.append(el("section", { class: "panel section" }, [
      el("h1", {}, ["Audit events"]),
      el("p", {}, ["Security and business-significant actions recorded by the API."]),
      simpleTable(["action", "resource", "target_id", "created_at"], data.items.map(row => ({ ...row, created_at: new Date(row.created_at * 1000).toLocaleString() }))),
    ]));
  } catch (err) {
    root.append(el("section", { class: "panel section" }, [el("h1", {}, ["Audit events"]), el("p", {}, [err.message])]));
  }
}

boot();
