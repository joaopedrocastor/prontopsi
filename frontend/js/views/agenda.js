// Agenda: visualizações Mês / Semana / Dia, com criação e edição de sessões.

import { api } from "../api.js";
import { h, clear, toast, confirmar, modal } from "../util.js";

const DOW = ["Domingo", "Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado"];
const DOW_S = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"];
const MES = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho",
  "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"];
const START_HOUR = 7, END_HOUR = 21, HOUR_H = 52;
const PALETTE = ["#0E7C8A", "#F0801A", "#6A5ACD", "#2E8B63", "#C4432F", "#2C7BE5", "#B5179E", "#C8791E"];

function pad(n) { return String(n).padStart(2, "0"); }
function ymd(d) { return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`; }
function isoLocal(d) { return `${ymd(d)}T${pad(d.getHours())}:${pad(d.getMinutes())}`; }
function parse(s) { return new Date(s); }
function minutesOf(s) { const d = parse(s); return d.getHours() * 60 + d.getMinutes(); }
function startOfWeek(d) { const x = new Date(d); x.setHours(0, 0, 0, 0); x.setDate(x.getDate() - x.getDay()); return x; }
function sameDay(a, b) { return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate(); }
function colorFor(a) {
  if (a.color) return a.color;
  const key = a.patient_name || a.title || a.id;
  let hsh = 0; for (const c of key) hsh = (hsh * 31 + c.charCodeAt(0)) >>> 0;
  return PALETTE[hsh % PALETTE.length];
}
function statusLabel(st) {
  return { agendada: "Agendada", confirmada: "Confirmada", realizada: "Realizada", cancelada: "Cancelada", faltou: "Faltou" }[st] || st;
}

let patientsCache = null;
async function getPatients() { if (!patientsCache) patientsCache = await api.listPatients().catch(() => []); return patientsCache; }

// Tela da Agenda: barra de controle (navegar/trocar visão/agendar) + o calendário.
export async function renderAgenda(container) {
  const state = { mode: localStorage.getItem("agendaMode") || "semana", ref: new Date() };

  const toolbar = h("div", { class: "cal-toolbar" });
  const body = h("div", {});
  container.appendChild(toolbar);
  container.appendChild(body);

  function setMode(m) { state.mode = m; localStorage.setItem("agendaMode", m); render(); }
  function go(delta) {
    const d = state.ref;
    if (state.mode === "mes") d.setMonth(d.getMonth() + delta);
    else if (state.mode === "dia") d.setDate(d.getDate() + delta);
    else d.setDate(d.getDate() + delta * 7);
    state.ref = new Date(d); render();
  }

  async function render() {
    clear(toolbar);
    toolbar.appendChild(h("div", { class: "cal-nav" }, [
      h("button", { onClick: () => go(-1), title: "Anterior" }, "‹"),
      h("button", { onClick: () => { state.ref = new Date(); render(); } }, "Hoje"),
      h("button", { onClick: () => go(1), title: "Próximo" }, "›"),
    ]));
    toolbar.appendChild(h("div", { class: "cal-title" }, periodLabel(state)));
    toolbar.appendChild(h("div", { class: "spacer", style: "flex:1" }));
    toolbar.appendChild(h("div", { class: "seg" }, [
      segBtn("Mês", "mes", state, setMode), segBtn("Semana", "semana", state, setMode), segBtn("Dia", "dia", state, setMode),
    ]));
    toolbar.appendChild(h("button", { class: "btn", onClick: () => openEditor(null, defaultStart(state), render) }, "＋ Agendar sessão"));

    clear(body);
    const loading = h("div", { class: "empty muted", style: "padding:30px" }, "Carregando agenda...");
    body.appendChild(loading);

    const [from, to] = rangeOf(state);
    let appts = [];
    try { appts = await api.listAppointments(isoLocal(from), isoLocal(to)); } catch (e) { toast(e.message, "err"); }
    clear(body);
    if (state.mode === "mes") body.appendChild(renderMonth(state, appts, render));
    else body.appendChild(renderTimeGrid(state, appts, render));
  }

  await render();
}

function segBtn(label, mode, state, setMode) {
  return h("button", { class: state.mode === mode ? "active" : "", onClick: () => setMode(mode) }, label);
}

function periodLabel(state) {
  const d = state.ref;
  if (state.mode === "dia") return `${DOW[d.getDay()]}, ${pad(d.getDate())} de ${MES[d.getMonth()]} de ${d.getFullYear()}`;
  if (state.mode === "mes") return `${MES[d.getMonth()]} de ${d.getFullYear()}`;
  const ws = startOfWeek(d), we = new Date(ws); we.setDate(we.getDate() + 6);
  return `${pad(ws.getDate())} ${MES[ws.getMonth()].slice(0, 3)} – ${pad(we.getDate())} ${MES[we.getMonth()].slice(0, 3)} ${we.getFullYear()}`;
}

function rangeOf(state) {
  const d = state.ref;
  if (state.mode === "dia") { const s = new Date(d); s.setHours(0, 0, 0, 0); const e = new Date(s); e.setDate(e.getDate() + 1); return [s, e]; }
  if (state.mode === "mes") {
    const first = new Date(d.getFullYear(), d.getMonth(), 1);
    const s = startOfWeek(first); const e = new Date(s); e.setDate(e.getDate() + 42); return [s, e];
  }
  const s = startOfWeek(d); const e = new Date(s); e.setDate(e.getDate() + 7); return [s, e];
}

function defaultStart(state) {
  const d = new Date(state.mode === "mes" ? new Date() : state.ref);
  if (state.mode === "semana") { /* usa hoje se dentro da semana, senão 1o dia */ }
  d.setHours(9, 0, 0, 0);
  return d;
}

// ---------- Semana / Dia (grade de horários) ----------
// Desenha a grade de horas x dias e posiciona cada consulta no seu horário.
function renderTimeGrid(state, appts, reload) {
  const days = state.mode === "dia" ? [new Date(state.ref)] : weekDays(state.ref);
  const today = new Date();
  const wrap = h("div", { class: "cal-wrap" });
  const grid = h("div", { class: "cal-week", style: `--cols:${days.length};--hour-h:${HOUR_H}px` });

  // cabeçalho
  grid.appendChild(h("div", { class: "cal-corner" }));
  for (const day of days) {
    grid.appendChild(h("div", { class: "cal-dayhead" + (sameDay(day, today) ? " today" : "") }, [
      h("div", { class: "dow" }, DOW_S[day.getDay()]),
      h("div", { class: "dnum" }, String(day.getDate())),
    ]));
  }

  // coluna de horas
  const timecol = h("div", { class: "cal-timecol" });
  for (let hIdx = START_HOUR; hIdx < END_HOUR; hIdx++) timecol.appendChild(h("div", { class: "cal-time" }, `${pad(hIdx)}:00`));
  grid.appendChild(timecol);

  // colunas de dias
  for (const day of days) {
    const col = h("div", { class: "cal-daycol" + (sameDay(day, today) ? " today" : "") });
    for (let hIdx = START_HOUR; hIdx < END_HOUR; hIdx++) col.appendChild(h("div", { class: "slot" }));
    // clique em espaço vazio cria sessão
    col.addEventListener("click", (e) => {
      if (e.target.closest(".cal-event")) return;
      const rect = col.getBoundingClientRect();
      const y = (e.clientY - rect.top) / (state.zoomFix || 1);
      let mins = START_HOUR * 60 + Math.round((y / HOUR_H) * 60 / 15) * 15;
      mins = Math.max(START_HOUR * 60, Math.min((END_HOUR - 1) * 60, mins));
      const start = new Date(day); start.setHours(Math.floor(mins / 60), mins % 60, 0, 0);
      openEditor(null, start, reload);
    });
    // eventos do dia
    const dayAppts = appts.filter((a) => sameDay(parse(a.start_at), day));
    for (const laid of layoutDay(dayAppts)) col.appendChild(eventBlock(laid, reload));
    grid.appendChild(col);
  }

  wrap.appendChild(grid);
  return wrap;
}

function weekDays(ref) { const s = startOfWeek(ref); return Array.from({ length: 7 }, (_, i) => { const d = new Date(s); d.setDate(d.getDate() + i); return d; }); }

// Calcula colunas lado a lado para consultas que se sobrepõem no mesmo dia.
function layoutDay(appts) {
  const evs = appts.map((a) => ({ a, s: minutesOf(a.start_at), e: Math.max(minutesOf(a.start_at) + 15, minutesOf(a.end_at)) }))
    .sort((x, y) => x.s - y.s || x.e - y.e);
  const out = [];
  let cluster = [], clusterEnd = -1;
  const flush = () => {
    const cols = [];
    for (const ev of cluster) {
      let placed = false;
      for (let ci = 0; ci < cols.length; ci++) { if (cols[ci] <= ev.s) { cols[ci] = ev.e; ev.col = ci; placed = true; break; } }
      if (!placed) { ev.col = cols.length; cols.push(ev.e); }
    }
    for (const ev of cluster) { ev.lanes = cols.length; out.push(ev); }
    cluster = []; clusterEnd = -1;
  };
  for (const ev of evs) {
    if (cluster.length && ev.s >= clusterEnd) flush();
    cluster.push(ev); clusterEnd = Math.max(clusterEnd, ev.e);
  }
  if (cluster.length) flush();
  return out;
}

function eventBlock(laid, reload) {
  const a = laid.a;
  const top = ((laid.s - START_HOUR * 60) / 60) * HOUR_H;
  const height = Math.max(20, ((laid.e - laid.s) / 60) * HOUR_H - 2);
  const widthPct = 100 / laid.lanes;
  const leftPct = laid.col * widthPct;
  const color = colorFor(a);
  const nome = a.patient_name || a.title || "Consulta";
  return h("div", {
    class: "cal-event st-" + a.status,
    style: `top:${top}px;height:${height}px;left:calc(${leftPct}% + 2px);width:calc(${widthPct}% - 5px);background:${color}`,
    title: `${nome} — ${hhmm(a.start_at)} às ${hhmm(a.end_at)}`,
    onClick: (e) => { e.stopPropagation(); openEditor(a.id, null, reload); },
  }, [
    h("div", { class: "ev-t" }, `${hhmm(a.start_at)}`),
    h("div", { class: "ev-n" }, nome),
  ]);
}
function hhmm(s) { const d = parse(s); return `${pad(d.getHours())}:${pad(d.getMinutes())}`; }

// ---------- Mês ----------
// Desenha a grade mensal (6 semanas) com chips resumidos por dia.
function renderMonth(state, appts, reload) {
  const wrap = h("div", { class: "cal-wrap" });
  const grid = h("div", { class: "cal-month" });
  for (const d of DOW_S) grid.appendChild(h("div", { class: "mh" }, d));
  const first = new Date(state.ref.getFullYear(), state.ref.getMonth(), 1);
  const start = startOfWeek(first);
  const today = new Date();
  const byDay = {};
  for (const a of appts) { const k = a.start_at.slice(0, 10); (byDay[k] = byDay[k] || []).push(a); }

  for (let i = 0; i < 42; i++) {
    const day = new Date(start); day.setDate(day.getDate() + i);
    const other = day.getMonth() !== state.ref.getMonth();
    const cell = h("div", { class: "mcell" + (other ? " other" : "") + (sameDay(day, today) ? " today" : "") });
    cell.addEventListener("click", (e) => { if (!e.target.closest(".mchip")) { const s = new Date(day); s.setHours(9, 0, 0, 0); openEditor(null, s, reload); } });
    cell.appendChild(h("div", { class: "mday" }, String(day.getDate())));
    const list = (byDay[ymd(day)] || []).sort((x, y) => x.start_at.localeCompare(y.start_at));
    list.slice(0, 3).forEach((a) => cell.appendChild(h("div", {
      class: "mchip", style: `background:${colorFor(a)}`,
      onClick: (e) => { e.stopPropagation(); openEditor(a.id, null, reload); },
    }, `${hhmm(a.start_at)} ${a.patient_name || a.title || "Consulta"}`)));
    if (list.length > 3) cell.appendChild(h("div", { class: "mmore" }, `+${list.length - 3} mais`));
    grid.appendChild(cell);
  }
  wrap.appendChild(grid);
  return wrap;
}

// ---------- Editor (criar/editar) ----------
// Abre o formulário (modal) para criar uma nova sessão ou editar/excluir uma existente.
async function openEditor(id, presetStart, reload) {
  const patients = await getPatients();
  let appt = null;
  if (id) { try { appt = await api.getAppointment(id); } catch (e) { toast(e.message, "err"); return; } }

  const start = appt ? parse(appt.start_at) : (presetStart || new Date());
  const end = appt ? parse(appt.end_at) : new Date(start.getTime() + 50 * 60000);

  const patSel = h("select", {}, [
    h("option", { value: "" }, "— Evento avulso (sem paciente) —"),
    ...patients.map((p) => h("option", { value: p.id }, p.name)),
  ]);
  if (appt && appt.patient_id) patSel.value = appt.patient_id;
  const titleI = h("input", { type: "text", placeholder: "Título (ex.: Palestra) — automático se escolher paciente", value: appt ? appt.title : "" });
  const dateI = h("input", { type: "date", value: ymd(start) });
  const startI = h("input", { type: "time", value: `${pad(start.getHours())}:${pad(start.getMinutes())}` });
  const endI = h("input", { type: "time", value: `${pad(end.getHours())}:${pad(end.getMinutes())}` });
  const modSel = h("select", {}, [
    h("option", { value: "" }, "—"), h("option", { value: "presencial" }, "Presencial"), h("option", { value: "online" }, "Online"),
  ]);
  if (appt && appt.modality) modSel.value = appt.modality;
  const statusSel = h("select", {}, ["agendada", "confirmada", "realizada", "cancelada", "faltou"].map((s) =>
    h("option", { value: s }, statusLabel(s))));
  statusSel.value = appt ? appt.status : "agendada";
  const notesI = h("textarea", { rows: "2", placeholder: "Observações" }, appt ? (appt.notes || "") : "");

  const content = h("div", {}, [
    h("div", { class: "field" }, [h("label", {}, "Paciente"), patSel]),
    h("div", { class: "field" }, [h("label", {}, "Título"), titleI]),
    h("div", { class: "form-row w-3" }, [
      h("div", { class: "field" }, [h("label", {}, "Data"), dateI]),
      h("div", { class: "field" }, [h("label", {}, "Início"), startI]),
      h("div", { class: "field" }, [h("label", {}, "Fim"), endI]),
    ]),
    h("div", { class: "form-row w-2" }, [
      h("div", { class: "field" }, [h("label", {}, "Modalidade"), modSel]),
      h("div", { class: "field" }, [h("label", {}, "Status"), statusSel]),
    ]),
    h("div", { class: "field" }, [h("label", {}, "Observações"), notesI]),
  ]);

  const actions = [];
  if (id) actions.push({
    label: "🗑 Excluir", class: "btn-danger",
    onClick: async (close) => {
      if (!(await confirmar({ title: "Excluir agendamento", message: "Excluir esta sessão da agenda?", okLabel: "Excluir", danger: true }))) return;
      try { await api.deleteAppointment(id); close(); toast("Agendamento excluído.", "ok"); reload(); } catch (e) { toast(e.message, "err"); }
    },
  });
  actions.push({ label: "Cancelar", class: "btn-ghost" });
  actions.push({
    label: "Salvar", class: "btn",
    onClick: async (close) => {
      if (!dateI.value || !startI.value) { toast("Informe data e horário.", "err"); return; }
      let endVal = endI.value || startI.value;
      if (endVal <= startI.value) { const [hh, mm] = startI.value.split(":").map(Number); endVal = `${pad(hh + 1)}:${pad(mm)}`; }
      const data = {
        patient_id: patSel.value || null,
        title: titleI.value.trim(),
        start_at: `${dateI.value}T${startI.value}`,
        end_at: `${dateI.value}T${endVal}`,
        modality: modSel.value || null,
        status: statusSel.value,
        notes: notesI.value.trim() || null,
      };
      try {
        if (id) await api.updateAppointment(id, data); else await api.createAppointment(data);
        close(); toast("Agendamento salvo.", "ok"); reload();
      } catch (e) { toast(e.message, "err"); }
    },
  });

  modal({ title: id ? "Editar sessão" : "Nova sessão", content, actions });
}
