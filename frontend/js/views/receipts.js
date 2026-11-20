// Tela Recibos.
//  • Aba "Recibos emitidos": todos os recibos salvos (nº automático e contínuo),
//    com opção de baixar o PDF de novo ou editar e regerar mantendo o número.
//  • Aba "Pagamentos recebidos": receitas pagas do Financeiro no mês, para gerar
//    o recibo de um pagamento ou o recibo do mês de um paciente.

import { api } from "../api.js";
import { h, clear, fmtData } from "../util.js";
import { gerarRecibo, baixarRecibo } from "../documents.js";

const MESES = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
  "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"];

const state = { ano: 0, mes: 0, patientId: "", patients: null, tab: "emitidos" };

function pad(n) { return String(n).padStart(2, "0"); }
function periodo() {
  const start = `${state.ano}-${pad(state.mes + 1)}-01`;
  const ultimo = new Date(state.ano, state.mes + 1, 0).getDate();
  return { start, end: `${state.ano}-${pad(state.mes + 1)}-${pad(ultimo)}` };
}
function fmtMoeda(v) { return (v || 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" }); }
const num3 = (n) => String(n).padStart(3, "0");

// Ponto de entrada da rota #/recibos.
export async function renderReceipts(container) {
  if (!state.ano) { const d = new Date(); state.ano = d.getFullYear(); state.mes = d.getMonth(); }
  state.patients = await api.listPatients().catch(() => state.patients || []);
  await draw(container);
}

async function draw(container) {
  clear(container);
  const redesenhar = () => draw(container);

  const patSel = h("select", { class: "inp", style: "width:auto;min-width:220px;max-width:320px" }, [
    h("option", { value: "" }, "Todos os pacientes"),
    ...(state.patients || []).map((p) => h("option", { value: p.id, ...(p.id === state.patientId ? { selected: "selected" } : {}) }, p.name)),
  ]);
  patSel.addEventListener("change", () => { state.patientId = patSel.value; redesenhar(); });

  container.appendChild(h("div", { class: "fin-bar" }, [
    h("div", { class: "cal-nav" }, [
      h("button", { class: "btn-ghost btn-sm", title: "Mês anterior", onClick: () => mudarMes(container, -1) }, "‹"),
      h("span", { class: "cal-title" }, `${MESES[state.mes]} ${state.ano}`),
      h("button", { class: "btn-ghost btn-sm", title: "Próximo mês", onClick: () => mudarMes(container, 1) }, "›"),
      h("button", { class: "btn-ghost btn-sm", onClick: () => irHoje(container) }, "Hoje"),
    ]),
    patSel,
    h("div", { style: "margin-left:auto" }, [
      h("button", { class: "btn", onClick: () => gerarRecibo({ patient_id: state.patientId || null, onSaved: () => { state.tab = "emitidos"; redesenhar(); } }) }, "＋ Novo recibo"),
    ]),
  ]));

  container.appendChild(h("div", { class: "seg fin-tabs", style: "margin-bottom:16px" }, [
    tabBtn(container, "emitidos", "Recibos emitidos"),
    tabBtn(container, "pagamentos", "Pagamentos recebidos"),
  ]));

  const body = h("div", {}, [h("div", { class: "empty muted", style: "padding:30px" }, "Carregando...")]);
  container.appendChild(body);
  if (state.tab === "emitidos") await drawEmitidos(body, redesenhar);
  else await drawPagamentos(body, redesenhar);
}

function tabBtn(container, id, label) {
  return h("button", {
    class: "seg-btn" + (state.tab === id ? " active" : ""),
    onClick: () => { if (state.tab !== id) { state.tab = id; draw(container); } },
  }, label);
}

function erro(body) { clear(body); body.appendChild(h("div", { class: "empty muted" }, "Erro ao carregar. Tente novamente.")); }

// ---- Aba: recibos emitidos (salvos) ----
async function drawEmitidos(body, redesenhar) {
  const { start, end } = periodo();
  let items = [];
  try { items = await api.listReceipts({ start, end, patient_id: state.patientId || null }); } catch { erro(body); return; }
  clear(body);

  if (!items.length) {
    body.appendChild(h("div", { class: "empty" }, [
      h("div", { class: "empty-icon" }, "🧾"),
      h("div", { class: "muted" }, "Nenhum recibo emitido neste mês."),
      h("div", { class: "muted", style: "font-size:13px;margin-top:4px" },
        "Use “Novo recibo” ou gere a partir da aba “Pagamentos recebidos”. Todo recibo gerado fica salvo aqui."),
    ]));
    return;
  }

  const rows = items.map((r) => h("tr", {}, [
    h("td", { style: "font-weight:700" }, num3(r.number)),
    h("td", {}, fmtData(r.issued_on)),
    h("td", {}, r.patient_name || h("span", { class: "muted" }, "—")),
    h("td", {}, [h("div", {}, r.payer), r.city ? h("div", { class: "fin-sub" }, r.city) : null]),
    h("td", {}, `${r.sessions || r.session_dates.length || 1}`),
    h("td", { class: "fin-val rec" }, fmtMoeda(r.amount)),
    h("td", { class: "row-actions" }, [
      h("button", { class: "btn-ghost btn-sm", title: "Baixar o PDF de novo", onClick: () => baixarRecibo(r) }, "📄 PDF"),
      h("button", { class: "btn-ghost btn-sm", title: "Corrigir e gerar novamente (mesmo número)", onClick: () => gerarRecibo({ receipt: r, onSaved: redesenhar }) }, "✎ Editar"),
    ]),
  ]));
  const total = items.reduce((s, r) => s + (r.amount || 0), 0);
  body.appendChild(h("div", { class: "table-wrap" }, [
    h("table", { class: "ctable fin-table" }, [
      h("thead", {}, h("tr", {}, [
        h("th", {}, "Nº"), h("th", {}, "Data"), h("th", {}, "Paciente"), h("th", {}, "Pagador"),
        h("th", {}, "Sessões"), h("th", {}, "Valor"), h("th", {}, ""),
      ])),
      h("tbody", {}, rows),
    ]),
  ]));
  body.appendChild(h("div", { class: "muted", style: "text-align:right;margin-top:10px;font-size:13px" },
    `${items.length} recibo${items.length > 1 ? "s" : ""} · total ${fmtMoeda(total)}`));
}

// ---- Aba: pagamentos recebidos (Financeiro) ----
async function drawPagamentos(body, redesenhar) {
  const { start, end } = periodo();
  const salvo = () => { state.tab = "emitidos"; redesenhar(); };
  let items = [];
  try {
    items = await api.listFinance({ kind: "receita", paid: true, start, end, patient_id: state.patientId || null });
  } catch { erro(body); return; }
  clear(body);

  // Recibo do mês do paciente selecionado (soma de todos os pagamentos do mês).
  if (state.patientId && items.length) {
    const p = (state.patients || []).find((x) => x.id === state.patientId);
    const total = items.reduce((s, e) => s + (e.amount || 0), 0);
    const n = items.length;
    body.appendChild(h("div", { class: "card", style: "display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin-bottom:16px" }, [
      h("div", { style: "flex:1;min-width:200px" }, [
        h("div", { style: "font-weight:600" }, `Recibo do mês — ${p ? p.name : ""}`),
        h("div", { class: "fin-sub" }, `${n} pagamento${n > 1 ? "s" : ""} em ${MESES[state.mes].toLowerCase()} · total ${fmtMoeda(total)}`),
      ]),
      h("button", { class: "btn", onClick: () => gerarRecibo({
        patient_id: state.patientId,
        amount: Math.round(total * 100) / 100,
        dates: items.map((e) => e.appointment_date || e.due_date),
        onSaved: salvo,
      }) }, "🧾 Gerar recibo do mês"),
    ]));
  }

  if (!items.length) {
    body.appendChild(h("div", { class: "empty" }, [
      h("div", { class: "empty-icon" }, "💰"),
      h("div", { class: "muted" }, "Nenhum pagamento recebido neste mês."),
      h("div", { class: "muted", style: "font-size:13px;margin-top:4px" },
        "Aqui aparecem as receitas marcadas como pagas no Financeiro."),
    ]));
    return;
  }

  const rows = items.map((e) => h("tr", {}, [
    h("td", {}, fmtData(e.appointment_date || e.due_date)),
    h("td", {}, fmtData(e.paid_date || e.due_date)),
    h("td", {}, e.patient_name || h("span", { class: "muted" }, "—")),
    h("td", {}, e.description || h("span", { class: "muted" }, "(sem descrição)")),
    h("td", { class: "fin-val rec" }, fmtMoeda(e.amount)),
    h("td", { class: "row-actions" }, [
      h("button", { class: "btn-ghost btn-sm", title: "Gerar recibo deste pagamento", onClick: () => gerarRecibo({
        patient_id: e.patient_id, amount: e.amount, dates: [e.appointment_date || e.due_date], onSaved: salvo,
      }) }, "🧾 Recibo"),
    ]),
  ]));

  const total = items.reduce((s, e) => s + (e.amount || 0), 0);
  body.appendChild(h("div", { class: "table-wrap" }, [
    h("table", { class: "ctable fin-table" }, [
      h("thead", {}, h("tr", {}, [
        h("th", {}, "Sessão"), h("th", {}, "Pago em"), h("th", {}, "Paciente"), h("th", {}, "Descrição"),
        h("th", {}, "Valor"), h("th", {}, ""),
      ])),
      h("tbody", {}, rows),
    ]),
  ]));
  body.appendChild(h("div", { class: "muted", style: "text-align:right;margin-top:10px;font-size:13px" },
    `${items.length} pagamento${items.length > 1 ? "s" : ""} · total recebido ${fmtMoeda(total)}`));
}

function mudarMes(container, delta) {
  let m = state.mes + delta, y = state.ano;
  if (m < 0) { m = 11; y--; } else if (m > 11) { m = 0; y++; }
  state.mes = m; state.ano = y; draw(container);
}
function irHoje(container) { const d = new Date(); state.ano = d.getFullYear(); state.mes = d.getMonth(); draw(container); }
