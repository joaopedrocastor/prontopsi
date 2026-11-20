// Painel inicial: saudação, atalhos, indicadores e alerta de próximas consultas.

import { api } from "../api.js";
import { store, isConfigured } from "../store.js";
import { h, iniciais } from "../util.js";
import { fazerBackup, restaurarBackup, exportarDados, importarDados } from "../systemActions.js";

const DOW = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"];

function pad(n) { return String(n).padStart(2, "0"); }
function isoLocal(d) { return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`; }

function labelData(startAt) {
  const d = new Date(startAt);
  const hoje = new Date(); hoje.setHours(0, 0, 0, 0);
  const alvo = new Date(d); alvo.setHours(0, 0, 0, 0);
  const diff = Math.round((alvo - hoje) / 86400000);
  if (diff === 0) return "Hoje";
  if (diff === 1) return "Amanhã";
  return `${DOW[d.getDay()]} ${pad(d.getDate())}/${pad(d.getMonth() + 1)}`;
}
function hora(startAt) { const d = new Date(startAt); return `${pad(d.getHours())}:${pad(d.getMinutes())}`; }

// Monta o painel inicial: saudação, indicadores, próximas consultas e atalhos.
export async function renderPainel(container) {
  const s = store.settings || {};

  container.appendChild(h("div", { class: "hello" }, [
    h("h1", {}, `Olá${s.professional_name ? ", " + s.professional_name.split(" ")[0] : ""}! 👋`),
    h("div", { class: "sub" }, "Bem-vinda ao ProntoPsi — aqui está o resumo da sua prática."),
  ]));

  if (!isConfigured()) {
    container.appendChild(h("div", { class: "notice", style: "margin-top:16px" }, [
      h("div", { class: "notice-text" }, [
        h("strong", {}, "Configure seu consultório. "),
        "Adicione sua logo, nome e CRP para aparecerem nas fichas e PDFs.",
      ]),
      h("button", { class: "btn", onClick: () => (location.hash = "#/config") }, "Configurar agora"),
    ]));
  }

  // Indicadores
  const statRow = h("div", { class: "stat-row" });
  container.appendChild(statRow);

  // Layout: próximas consultas (grande) + atalhos
  const upPanel = h("div", { class: "panel" }, [
    h("div", { class: "panel-head" }, [
      h("h2", {}, "🔔 Próximas consultas"),
      h("button", { class: "btn btn-sm", onClick: () => (location.hash = "#/agenda") }, "Ver agenda"),
    ]),
    h("div", { class: "panel-body", id: "up-body" }, [h("div", { class: "empty muted", style: "padding:24px" }, "Carregando...")]),
  ]);

  const actions = h("div", { class: "panel" }, [
    h("div", { class: "panel-head" }, [h("h2", {}, "Atalhos")]),
    h("div", { class: "panel-body", style: "padding:16px;display:flex;flex-direction:column;gap:10px" }, [
      h("button", { class: "btn btn-block", onClick: () => (location.hash = "#/agenda") }, "＋ Agendar sessão"),
      h("button", { class: "btn-outline btn-block", onClick: () => (location.hash = "#/pacientes?nova=1") }, "📝 Nova anamnese"),
      h("button", { class: "btn-outline btn-block", onClick: () => (location.hash = "#/exportar") }, "📄 Exportar PDF"),
      h("hr", { style: "border:none;border-top:1px solid var(--line);margin:4px 0" }),
      h("button", { class: "btn-ghost btn-block", onClick: fazerBackup }, "💾 Fazer backup"),
      h("button", { class: "btn-ghost btn-block", onClick: () => exportarDados("zip") }, "⬇ Exportar dados"),
      h("button", { class: "btn-ghost btn-block", onClick: () => importarDados(() => location.reload()) }, "⬆ Importar dados"),
    ]),
  ]);

  container.appendChild(h("div", { class: "grid grid-2", style: "grid-template-columns:1.6fr 1fr;align-items:start" }, [upPanel, actions]));

  // Carrega dados
  await Promise.all([loadStats(statRow), loadUpcoming(document.getElementById("up-body"))]);
}

// Busca e preenche os 4 indicadores (pacientes, sessões hoje, próximos 7 dias, rascunhos).
async function loadStats(row) {
  const now = new Date();
  const startDay = new Date(now); startDay.setHours(0, 0, 0, 0);
  const endDay = new Date(startDay); endDay.setDate(endDay.getDate() + 1);
  const in7 = new Date(startDay); in7.setDate(in7.getDate() + 7);

  const [patients, hoje, semana, fichas] = await Promise.all([
    api.listPatients().catch(() => []),
    api.listAppointments(isoLocal(startDay), isoLocal(endDay)).catch(() => []),
    api.listAppointments(isoLocal(now), isoLocal(in7)).catch(() => []),
    api.listAnamneses().catch(() => []),
  ]);
  const rascunhos = fichas.filter((f) => f.status !== "concluida").length;

  const stat = (label, value, accent) => h("div", { class: "stat" + (accent ? " accent" : "") }, [
    h("div", { class: "st-label" }, label),
    h("div", { class: "st-value" }, String(value)),
  ]);
  row.appendChild(stat("Pacientes cadastrados", patients.length));
  row.appendChild(stat("Sessões hoje", hoje.filter((a) => a.status !== "cancelada").length, true));
  row.appendChild(stat("Próximos 7 dias", semana.filter((a) => a.status !== "cancelada").length));
  row.appendChild(stat("Fichas em rascunho", rascunhos));
}

// Carrega e exibe a lista das próximas consultas (o alerta do painel).
async function loadUpcoming(body) {
  let items = [];
  try { items = await api.upcoming(8); } catch { body.innerHTML = ""; body.appendChild(h("div", { class: "empty muted" }, "Erro ao carregar.")); return; }
  body.innerHTML = "";
  if (!items.length) {
    body.appendChild(h("div", { class: "empty" }, [
      h("div", { class: "empty-icon" }, "🗓️"),
      h("div", { class: "muted" }, "Nenhuma consulta agendada."),
      h("button", { class: "btn btn-sm", style: "margin-top:10px", onClick: () => (location.hash = "#/agenda") }, "Agendar agora"),
    ]));
    return;
  }
  for (const a of items) {
    const nome = a.patient_name || a.title || "Consulta";
    const meta = [a.modality ? cap(a.modality) : null, statusLabel(a.status)].filter(Boolean).join("  ·  ");
    body.appendChild(h("div", { class: "up-item", onClick: () => (location.hash = "#/agenda") }, [
      h("div", { class: "up-bar", style: a.color ? `background:${a.color}` : "" }),
      h("div", { class: "up-when" }, [h("div", { class: "d" }, labelData(a.start_at)), h("div", { class: "t" }, hora(a.start_at))]),
      h("div", { class: "up-main" }, [h("div", { class: "nm" }, nome), h("div", { class: "meta" }, meta)]),
      h("span", { class: "avatar" }, iniciais(nome)),
    ]));
  }
}

function cap(s) { return s ? s[0].toUpperCase() + s.slice(1) : s; }
function statusLabel(st) {
  return { agendada: "Agendada", confirmada: "Confirmada", realizada: "Realizada", cancelada: "Cancelada", faltou: "Faltou" }[st] || st;
}
