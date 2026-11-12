import { CONFIG } from "./config.js";

const sb = window.supabase.createClient(CONFIG.SUPABASE_URL, CONFIG.SUPABASE_ANON_KEY);
const $ = (s) => document.querySelector(s);
const $$ = (s) => [...document.querySelectorAll(s)];
const money = (n) => new Intl.NumberFormat(CONFIG.LOCALE, { style: "currency", currency: CONFIG.CURRENCY }).format(n);
const thisMonth = () => new Date().toISOString().slice(0, 7);
// All dynamic text goes through textContent (never innerHTML) to prevent XSS.
const el = (tag, cls, ...kids) => { const e = document.createElement(tag); if (cls) e.className = cls; e.append(...kids); return e; };
let cats = { income: [], expense: [] }, chart, mfaFactor, recovering = location.hash.includes("type=recovery");

function toast(msg, bad) {
  const t = $("#toast"); t.textContent = msg; t.className = bad ? "bad show" : "show";
  clearTimeout(toast.t); toast.t = setTimeout(() => (t.className = ""), 4500);
}
const run = (fn) => async (e) => {
  e?.preventDefault?.();
  try { await fn(e); } catch (err) { toast(err.message || "Something went wrong", true); }
};

async function api(path, { method = "GET", body, raw } = {}) {
  const { data: { session } } = await sb.auth.getSession();
  if (!session) throw new Error("Please sign in again");
  const res = await fetch(CONFIG.API_BASE_URL + path, {
    method,
    headers: { Authorization: "Bearer " + session.access_token, ...(body ? { "Content-Type": "application/json" } : {}) },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error((await res.json().catch(() => ({}))).error || "Request failed (" + res.status + ")");
  if (res.status === 204) return null;
  return raw ? res.text() : res.json();
}

// ---------- theme ----------
const setTheme = (t) => { document.documentElement.dataset.theme = t; try { localStorage.setItem("theme", t); } catch {} };
let saved; try { saved = localStorage.getItem("theme"); } catch {}
setTheme(saved || (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light"));
$("#themeBtn").onclick = () => setTheme(document.documentElement.dataset.theme === "dark" ? "light" : "dark");

// ---------- auth ----------
function showAuth(name) {
  $("#app").hidden = true; $("#auth").hidden = false;
  $$("[data-auth]").forEach((s) => (s.hidden = s.dataset.auth !== name));
}
$$("[data-go]").forEach((a) => (a.onclick = (e) => { e.preventDefault(); showAuth(a.dataset.go); }));

$("#loginForm").onsubmit = run(async () => {
  const { error } = await sb.auth.signInWithPassword({ email: $("#loginEmail").value.trim(), password: $("#loginPass").value });
  if (error) throw error;
  $("#loginPass").value = "";
  await enter();
});
$("#registerForm").onsubmit = run(async () => {
  const { error } = await sb.auth.signUp({
    email: $("#regEmail").value.trim(), password: $("#regPass").value,
    options: { data: { full_name: $("#regName").value.trim() }, emailRedirectTo: location.origin },
  });
  if (error) throw error;
  toast("Check your inbox and verify your email, then sign in.");
  showAuth("login");
});
$("#forgotForm").onsubmit = run(async () => {
  const { error } = await sb.auth.resetPasswordForEmail($("#forgotEmail").value.trim(), { redirectTo: location.origin });
  if (error) throw error;
  toast("If that email exists, a reset link is on its way.");
  showAuth("login");
});
$("#resetForm").onsubmit = run(async () => {
  const { error } = await sb.auth.updateUser({ password: $("#resetPass").value });
  if (error) throw error;
  recovering = false; history.replaceState(null, "", location.pathname);
  toast("Password updated.");
  await enter();
});
$("#mfaForm").onsubmit = run(async () => {
  const { data: f, error: e0 } = await sb.auth.mfa.listFactors(); if (e0) throw e0;
  const factor = f.totp[0]; if (!factor) throw new Error("No authenticator set up");
  const { data: c, error: e1 } = await sb.auth.mfa.challenge({ factorId: factor.id }); if (e1) throw e1;
  const { error } = await sb.auth.mfa.verify({ factorId: factor.id, challengeId: c.id, code: $("#mfaLoginCode").value.trim() });
  if (error) throw error;
  $("#mfaLoginCode").value = "";
  await enter();
});
$("#logoutBtn").onclick = run(async () => { await sb.auth.signOut(); showAuth("login"); });
sb.auth.onAuthStateChange((ev) => {
  if (ev === "PASSWORD_RECOVERY") { recovering = true; showAuth("reset"); }
  if (ev === "SIGNED_OUT") showAuth("login");
});

async function enter() {
  const { data: a } = await sb.auth.mfa.getAuthenticatorAssuranceLevel();
  if (a && a.nextLevel === "aal2" && a.currentLevel !== "aal2") return showAuth("mfa");
  $("#auth").hidden = true; $("#app").hidden = false;
  cats = await api("/categories");
  $("#txDate").value = new Date().toISOString().slice(0, 10);
  $("#bMonth").value = $("#rMonth").value = $("#fMonth").value = thisMonth();
  fillCats($("#bCat"), cats.expense);
  fillTxCats();
  nav("dashboard");
}

// ---------- navigation ----------
const loaders = { dashboard: () => loadDash(), transactions: () => loadTx(), budgets: () => loadBudgets(), reports: () => loadReport(), profile: () => loadProfile() };
function nav(view) {
  $$(".view").forEach((s) => (s.hidden = s.id !== "v-" + view));
  $$("[data-view]").forEach((b) => b.classList.toggle("on", b.dataset.view === view));
  run(loaders[view])();
}
$$("[data-view]").forEach((b) => (b.onclick = () => nav(b.dataset.view)));

// ---------- shared helpers ----------
function fillCats(select, list) {
  select.replaceChildren(el("option", "", "Uncategorised"), ...list.map((c) => Object.assign(el("option", "", c.name), { value: c.id })));
  select.firstChild.value = "";
}
const fillTxCats = () => fillCats($("#txCat"), cats[$("#txType").value]);
const catName = (r) => (r.income_categories || r.expense_categories || {}).name || "Uncategorised";

function fillTx(tbody, rows, withActions) {
  tbody.replaceChildren(...rows.map((r) => {
    const amt = el("td", "num " + (r.type === "income" ? "inc" : "exp"), (r.type === "income" ? "+" : "−") + money(r.amount));
    const tr = el("tr", "", el("td", "", r.tx_date), el("td", "", catName(r)), el("td", "", r.description || ""), amt);
    if (withActions) {
      const edit = el("button", "ghost", "Edit"), del = el("button", "ghost", "Delete");
      edit.onclick = () => editTx(r);
      del.onclick = run(async () => { if (confirm("Delete this transaction? This cannot be undone.")) { await api("/transactions/" + r.id, { method: "DELETE" }); toast("Deleted"); await loadTx(); } });
      tr.append(el("td", "num", edit, del));
    }
    return tr;
  }));
  if (!rows.length) tbody.append(el("tr", "", Object.assign(el("td", "", "Nothing here yet."), { colSpan: 5 })));
}

// ---------- dashboard ----------
async function loadDash() {
  const [s, tx] = await Promise.all([api("/summary"), api("/transactions?limit=5")]);
  $("#kBal").textContent = money(s.balance); $("#kInc").textContent = money(s.income); $("#kExp").textContent = money(s.expenses);
  chart?.destroy();
  chart = new Chart($("#chart"), {
    type: "bar",
    data: { labels: s.monthly.map((m) => m.month), datasets: [
      { label: "Income", data: s.monthly.map((m) => m.income), backgroundColor: "#0fb5ae" },
      { label: "Expenses", data: s.monthly.map((m) => m.expenses), backgroundColor: "#5b7bd5" }] },
    options: { responsive: true, maintainAspectRatio: false },
  });
  fillTx($("#recent"), tx, false);
}

// ---------- transactions ----------
async function loadTx() {
  const p = new URLSearchParams({ limit: "200" });
  if ($("#fType").value) p.set("type", $("#fType").value);
  if ($("#fMonth").value) p.set("month", $("#fMonth").value);
  if ($("#fQ").value.trim()) p.set("q", $("#fQ").value.trim());
  fillTx($("#txBody"), await api("/transactions?" + p), true);
}
["fType", "fMonth"].forEach((id) => ($("#" + id).onchange = run(loadTx)));
$("#fQ").oninput = (() => { let t; return () => { clearTimeout(t); t = setTimeout(run(loadTx), 350); }; })();
$("#txType").onchange = fillTxCats;

function resetTxForm() {
  $("#txForm").reset(); $("#txId").value = ""; $("#txTitle").textContent = "Add transaction";
  $("#txCancel").hidden = true; $("#txDate").value = new Date().toISOString().slice(0, 10); fillTxCats();
}
function editTx(r) {
  $("#txId").value = r.id; $("#txType").value = r.type; fillTxCats();
  $("#txAmount").value = r.amount; $("#txDate").value = r.tx_date; $("#txDesc").value = r.description || "";
  $("#txCat").value = r.income_category_id || r.expense_category_id || "";
  $("#txTitle").textContent = "Edit transaction"; $("#txCancel").hidden = false; scrollTo({ top: 0, behavior: "smooth" });
}
$("#txCancel").onclick = resetTxForm;
$("#txForm").onsubmit = run(async () => {
  const id = $("#txId").value;
  const body = { type: $("#txType").value, amount: $("#txAmount").value, tx_date: $("#txDate").value,
                 category_id: $("#txCat").value || null, description: $("#txDesc").value };
  await api(id ? "/transactions/" + id : "/transactions", { method: id ? "PUT" : "POST", body });
  toast(id ? "Transaction updated" : "Transaction added");
  resetTxForm(); await loadTx();
});

// ---------- budgets ----------
async function loadBudgets() {
  const list = await api("/budgets?month=" + ($("#bMonth").value || thisMonth()));
  $("#budgetList").replaceChildren(...(list.length ? list : [{ empty: true }]).map((b) => {
    if (b.empty) return el("p", "", "No budgets for this month yet.");
    const bar = Object.assign(el("progress", b.spent > b.limit ? "over" : ""), { max: b.limit, value: Math.min(b.spent, b.limit) });
    const del = el("button", "ghost", "Remove");
    del.onclick = run(async () => { await api("/budgets/" + b.id, { method: "DELETE" }); await loadBudgets(); });
    const left = b.limit - b.spent;
    return el("div", "", el("div", "row", el("strong", "", b.category), el("span", "", `${money(b.spent)} of ${money(b.limit)}` + (left < 0 ? ` — over by ${money(-left)}` : ` — ${money(left)} left`)), del), bar);
  }));
}
$("#bMonth").onchange = run(loadBudgets);
$("#budgetForm").onsubmit = run(async () => {
  if (!$("#bCat").value) throw new Error("Choose an expense category");
  await api("/budgets", { method: "POST", body: { month: $("#bMonth").value, category_id: $("#bCat").value, amount_limit: $("#bLimit").value } });
  toast("Budget saved"); $("#bLimit").value = ""; await loadBudgets();
});

// ---------- reports ----------
async function loadReport() {
  const r = await api("/reports/monthly?month=" + ($("#rMonth").value || thisMonth()));
  $("#rInc").textContent = money(r.income); $("#rExp").textContent = money(r.expenses); $("#rBal").textContent = money(r.balance);
  $("#rCats").replaceChildren(...(r.by_category.length ? r.by_category : [{ category: "No expenses this month", total: 0 }])
    .map((c) => el("li", "", el("span", "", c.category), el("strong", "", money(c.total)))));
}
$("#rMonth").onchange = run(loadReport);
$("#rExport").onclick = run(async () => {
  const csv = await api("/reports/export?month=" + $("#rMonth").value, { raw: true });
  const a = Object.assign(document.createElement("a"), { href: URL.createObjectURL(new Blob([csv], { type: "text/csv" })), download: `finance-dev-${$("#rMonth").value}.csv` });
  a.click(); URL.revokeObjectURL(a.href);
});

// ---------- profile & MFA ----------
async function loadProfile() { $("#pName").value = (await api("/profile")).full_name || ""; }
$("#profileForm").onsubmit = run(async () => { await api("/profile", { method: "PUT", body: { full_name: $("#pName").value } }); toast("Profile saved"); });
$("#mfaEnroll").onclick = run(async () => {
  const { data, error } = await sb.auth.mfa.enroll({ factorType: "totp" }); if (error) throw error;
  mfaFactor = data.id; $("#mfaQr").src = data.totp.qr_code; $("#mfaSecret").textContent = data.totp.secret; $("#mfaBox").hidden = false;
});
$("#mfaConfirm").onclick = run(async () => {
  const { data: c, error: e1 } = await sb.auth.mfa.challenge({ factorId: mfaFactor }); if (e1) throw e1;
  const { error } = await sb.auth.mfa.verify({ factorId: mfaFactor, challengeId: c.id, code: $("#mfaCode").value.trim() });
  if (error) throw error;
  toast("Two-factor authentication enabled"); $("#mfaBox").hidden = true; $("#mfaCode").value = "";
});

// ---------- start ----------
(async () => {
  if (CONFIG.SUPABASE_URL.includes("YOUR-PROJECT")) { showAuth("login"); return toast("Set your Supabase URL and anon key in frontend/js/config.js", true); }
  const { data: { session } } = await sb.auth.getSession();
  if (recovering) return showAuth("reset");
  session ? run(enter)() : showAuth("login");
})();
