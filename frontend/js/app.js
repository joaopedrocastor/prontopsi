// Ponto de entrada: carrega config, controla senha/recuperacao, barra lateral,
// topo e roteamento.

import { api } from "./api.js";
import { store, loadSettings } from "./store.js";
import { toast } from "./util.js";
import { logoHorizontal, logoStacked } from "./logo.js";

import { renderPainel } from "./views/painel.js";
import { renderSettings } from "./views/settings.js";
import { renderPatients, renderPatientForm, renderPatientDetail } from "./views/patients.js";
import { renderAnamnesis } from "./views/anamnese.js";
import { renderAgenda } from "./views/agenda.js";
import { renderExport } from "./views/export.js";
import { renderSoon } from "./views/soon.js";

const routes = [
  { re: /^#?\/?$/, view: renderPainel, nav: "#/painel", title: "Painel" },
  { re: /^#\/painel$/, view: renderPainel, nav: "#/painel", title: "Painel" },
  { re: /^#\/agenda$/, view: renderAgenda, nav: "#/agenda", title: "Agenda" },
  { re: /^#\/pacientes$/, view: renderPatients, nav: "#/pacientes", title: "Clientes" },
  { re: /^#\/paciente\/novo$/, view: (c) => renderPatientForm(c, null), nav: "#/pacientes", title: "Clientes" },
  { re: /^#\/paciente\/([^/]+)\/editar$/, view: (c, m) => renderPatientForm(c, m[1]), nav: "#/pacientes", title: "Clientes" },
  { re: /^#\/paciente\/([^/]+)$/, view: (c, m) => renderPatientDetail(c, m[1]), nav: "#/pacientes", title: "Clientes" },
  { re: /^#\/ficha\/([^/]+)$/, view: (c, m) => renderAnamnesis(c, m[1]), nav: "#/pacientes", title: "Ficha de Anamnese" },
  { re: /^#\/financeiro$/, view: (c) => renderSoon(c, "Financeiro", "💰"), nav: "#/financeiro", title: "Financeiro" },
  { re: /^#\/relatorios$/, view: (c) => renderSoon(c, "Relatórios", "📊"), nav: "#/relatorios", title: "Relatórios" },
  { re: /^#\/config$/, view: renderSettings, nav: "#/config", title: "Configuração" },
  { re: /^#\/exportar$/, view: renderExport, nav: "#/painel", title: "Exportar PDF" },
];

let leaveHook = null;
// Permite a uma tela registrar uma ação a executar ao sair dela (ex.: salvar rascunho).
export function setLeaveHook(fn) { leaveHook = fn; }
// Define o título mostrado na barra de topo.
export function setTitle(t) { const el = document.getElementById("topbar-title"); if (el) el.textContent = t; }

// Roteador: lê o #hash, encontra a tela correspondente e a renderiza.
async function router() {
  if (leaveHook) { const fn = leaveHook; leaveHook = null; try { await fn(); } catch {} }
  const hash = location.hash || "#/painel";
  const path = hash.split("?")[0];
  const view = document.getElementById("view");
  for (const r of routes) {
    const m = path.match(r.re);
    if (m) {
      setActiveNav(r.nav);
      setTitle(r.title);
      view.innerHTML = "";
      try { await r.view(view, m); } catch (e) { toast(e.message || "Erro ao abrir a tela", "err"); }
      window.scrollTo(0, 0);
      return;
    }
  }
  location.hash = "#/painel";
}

function setActiveNav(nav) {
  document.querySelectorAll(".side-item").forEach((b) =>
    b.classList.toggle("active", b.dataset.route === nav));
}

// Atualiza a logo/identidade na barra lateral e no topo a partir das configurações.
export function refreshHeader() {
  const s = store.settings || {};
  // Barra lateral: logo do ProntoPsi (software).
  document.getElementById("sidebar-logo").innerHTML = logoHorizontal(38);

  // Rodapé da barra: mini identidade da clínica (logo/nome da psicóloga).
  const mini = document.getElementById("clinic-mini");
  const badge = document.getElementById("prof-badge");
  const nome = s.professional_name || "";
  const av = iniciais(nome || "PP");
  if (s.logo_path) {
    mini.innerHTML = `<img src="/api/settings/logo/image?t=${Date.now()}" alt=""><span>${escapeHtml(nome)}</span>`;
    badge.innerHTML = `<img src="/api/settings/logo/image?t=${Date.now()}" alt="">`;
  } else {
    mini.innerHTML = `<span class="cm-badge">${av}</span><span>${escapeHtml(nome || "Consultório")}</span>`;
    badge.innerHTML = `<span class="pb-av">${av}</span><span>${escapeHtml(nome || "")}</span>`;
  }
}

function escapeHtml(s) { return String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c])); }
function iniciais(nome) {
  const p = (nome || "").trim().split(/\s+/).filter(Boolean);
  if (!p.length) return "PP";
  return ((p[0][0] || "") + (p[1]?.[0] || "")).toUpperCase();
}

// ---- Zoom ----
const ZOOM_MIN = 0.8, ZOOM_MAX = 1.8, ZOOM_STEP = 0.1;
function getZoom() { return parseFloat(localStorage.getItem("zoom") || "1") || 1; }
function applyZoom(z) {
  z = Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, Math.round(z * 10) / 10));
  localStorage.setItem("zoom", String(z));
  document.documentElement.style.zoom = z;
  const val = document.getElementById("zoom-val");
  if (val) val.textContent = Math.round(z * 100) + "%";
}
function initZoom() {
  const out = document.getElementById("zoom-out"), inc = document.getElementById("zoom-in");
  if (out) out.addEventListener("click", () => applyZoom(getZoom() - ZOOM_STEP));
  if (inc) inc.addEventListener("click", () => applyZoom(getZoom() + ZOOM_STEP));
  applyZoom(getZoom());
}

// Mostra a interface principal, liga a navegação lateral e inicia o roteador.
function startApp() {
  document.getElementById("app").classList.remove("hidden");
  document.querySelectorAll(".side-item").forEach((b) =>
    b.addEventListener("click", () => { location.hash = b.dataset.route; }));
  initZoom();
  refreshHeader();
  window.addEventListener("hashchange", router);
  router();
}

// ---- Tela de senha + recuperacao ----
// Monta a tela de bloqueio: login por senha e o fluxo "esqueci minha senha".
function setupLock() {
  const lock = document.getElementById("lock");
  const input = document.getElementById("lock-input");
  const errorEl = document.getElementById("lock-error");
  document.getElementById("lock-logo").innerHTML = logoStacked(70, false);

  async function unlock() {
    const ok = (await api.verifyPassword(input.value)).ok;
    if (ok) { lock.classList.add("hidden"); startApp(); }
    else { errorEl.classList.remove("hidden"); input.value = ""; input.focus(); }
  }
  document.getElementById("lock-btn").addEventListener("click", unlock);
  input.addEventListener("keydown", (e) => { if (e.key === "Enter") unlock(); });

  // Recuperacao
  const main = document.getElementById("lock-main");
  const rec = document.getElementById("recover");
  const emailI = document.getElementById("recover-email");
  const codeWrap = document.getElementById("recover-code-wrap");
  const codeI = document.getElementById("recover-code");
  const newI = document.getElementById("recover-newpass");
  const msg = document.getElementById("recover-msg");
  const recBtn = document.getElementById("recover-btn");
  const hint = document.getElementById("recover-hint");
  let stage = "email"; // email -> reset

  document.getElementById("lock-forgot").addEventListener("click", () => {
    main.classList.add("hidden"); rec.classList.remove("hidden"); stage = "email"; emailI.focus();
  });
  document.getElementById("recover-back").addEventListener("click", () => {
    rec.classList.add("hidden"); main.classList.remove("hidden"); resetRecover();
  });
  function resetRecover() {
    stage = "email"; emailI.value = ""; codeI.value = ""; newI.value = "";
    codeWrap.classList.add("hidden"); newI.classList.add("hidden"); msg.classList.add("hidden");
    recBtn.textContent = "Enviar"; hint.textContent = "Informe o e-mail de recuperação cadastrado.";
  }
  function showMsg(t, ok) { msg.textContent = t; msg.style.color = ok ? "var(--ok)" : "var(--danger)"; msg.classList.remove("hidden"); }

  recBtn.addEventListener("click", async () => {
    try {
      if (stage === "email") {
        const r = await api.resetRequest(emailI.value.trim());
        stage = "reset";
        newI.classList.remove("hidden");
        recBtn.textContent = "Redefinir senha";
        if (r.direct) { hint.textContent = "E-mail confirmado. Defina uma nova senha."; }
        else { codeWrap.classList.remove("hidden"); hint.textContent = `Enviamos um código para ${r.email}. Digite-o e a nova senha.`; }
        msg.classList.add("hidden"); newI.focus();
      } else {
        if (!newI.value) { showMsg("Digite a nova senha.", false); return; }
        await api.resetConfirm(codeI.value.trim(), newI.value);
        showMsg("Senha redefinida! Faça login.", true);
        setTimeout(() => { rec.classList.add("hidden"); main.classList.remove("hidden"); resetRecover(); input.focus(); }, 1400);
      }
    } catch (e) { showMsg(e.message, false); }
  });

  lock.classList.remove("hidden");
  input.focus();
}

// Início de tudo: carrega configurações e decide entre tela de senha ou app.
async function boot() {
  applyZoom(getZoom());
  try { await loadSettings(); } catch { toast("Falha ao carregar configurações.", "err"); }
  if (store.settings && store.settings.has_password) setupLock();
  else startApp();
}

boot();
