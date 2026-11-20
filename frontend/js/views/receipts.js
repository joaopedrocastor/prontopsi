// Tela Recibos: lista os pagamentos recebidos do mês (receitas pagas do
// Financeiro) e gera o recibo em PDF de cada um, o recibo mensal de um
// cliente (soma do mês) ou um recibo avulso. Não guarda nada novo no banco:
// os recibos são gerados a partir dos lançamentos.

import { api } from "../api.js";
import { h, clear, toast, fmtData } from "../util.js";
import { gerarRecibo } from "../documents.js";

const MESES = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
  "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"];

const state = { ano: 0, mes: 0, patientId: "", patients: null };

function pad(n) { return String(n).padStart(2, "0"); }
function periodo() {
  const start = `${state.ano}-${pad(state.mes + 1)}-01`;
  const ultimo = new Date(state.ano, state.mes + 1, 0).getDate();
  return { start, end: `${state.ano}-${pad(state.mes + 1)}-${pad(ultimo)}` };
}
function fmtMoeda(v) { return (v || 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" }); }

// Pagador padrão: responsável principal do cliente; senão, o próprio cliente.
async function pagadorDe(patientId, fallback) {
  if (!patientId) return fallback || "";
  try {
    const gs = await api.listGuardians(patientId);
    const g = gs.find((x) => x.is_primary) || null;
    if (g && g.name) return g.name;
  } catch {}
  return fallback || "";
}

// Ponto de entrada da rota #/recibos.
export async function renderReceipts(container) {
  if (!state.ano) { const d = new Date(); state.ano = d.getFullYear(); state.mes = d.getMonth(); }
  if (state.patients == null) state.patients = await api.listPatients().catch(() => []);
  await draw(container);
}

async function draw(container) {
  clear(container);
  const { start, end } = periodo();

  const patSel = h("select", { class: "inp", style: "width:auto;min-width:220px;max-width:320px" }, [
    h("option", { value: "" }, "Todos os clientes"),
    ...(state.patients || []).map((p) => h("option", { value: p.id, ...(p.id === state.patientId ? { selected: "selected" } : {}) }, p.name)),
  ]);
  patSel.addEventListener("change", () => { state.patientId = patSel.value; draw(container); });

  container.appendChild(h("div", { class: "fin-bar" }, [
    h("div", { class: "cal-nav" }, [
      h("button", { class: "btn-ghost btn-sm", title: "Mês anterior", onClick: () => mudarMes(container, -1) }, "‹"),
      h("span", { class: "cal-title" }, `${MESES[state.mes]} ${state.ano}`),
      h("button", { class: "btn-ghost btn-sm", title: "Próximo mês", onClick: () => mudarMes(container, 1) }, "›"),
      h("button", { class: "btn-ghost btn-sm", onClick: () => irHoje(container) }, "Hoje"),
    ]),
    patSel,
    h("div", { style: "margin-left:auto" }, [
      h("button", { class: "btn", onClick: () => gerarRecibo({}) }, "＋ Recibo avulso"),
    ]),
  ]));

  const body = h("div", {}, [h("div", { class: "empty muted", style: "padding:30px" }, "Carregando...")]);
  container.appendChild(body);

  let items = [];
  try {
    items = await api.listFinance({ kind: "receita", paid: true, start, end, patient_id: state.patientId || null });
  } catch {
    clear(body); body.appendChild(h("div", { class: "empty muted" }, "Erro ao carregar. Tente novamente.")); return;
  }
  clear(body);

  // Recibo mensal do cliente selecionado (soma de todos os pagamentos do mês).
  if (state.patientId && items.length) {
    const p = (state.patients || []).find((x) => x.id === state.patientId);
    const total = items.reduce((s, e) => s + (e.amount || 0), 0);
    const n = items.length;
    body.appendChild(h("div", { class: "card", style: "display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin-bottom:16px" }, [
      h("div", { style: "flex:1;min-width:200px" }, [
        h("div", { style: "font-weight:600" }, `Recibo do mês — ${p ? p.name : ""}`),
        h("div", { class: "fin-sub" }, `${n} pagamento${n > 1 ? "s" : ""} em ${MESES[state.mes].toLowerCase()} · total ${fmtMoeda(total)}`),
      ]),
      h("button", { class: "btn", onClick: async () => {
        gerarRecibo({
          patient_id: state.patientId,
          payer: await pagadorDe(state.patientId, p ? p.name : ""),
          amount: Math.round(total * 100) / 100,
          reference: `${n} ${n > 1 ? "sessões" : "sessão"} de atendimento psicológico em ${MESES[state.mes].toLowerCase()}/${state.ano}`
            + (p ? ` (cliente: ${p.name})` : ""),
          when: end < hojeISO() ? end : hojeISO(),
        });
      } }, "🧾 Gerar recibo do mês"),
    ]));
  }

  if (!items.length) {
    body.appendChild(h("div", { class: "empty" }, [
      h("div", { class: "empty-icon" }, "🧾"),
      h("div", { class: "muted" }, "Nenhum pagamento recebido neste mês."),
      h("div", { class: "muted", style: "font-size:13px;margin-top:4px" },
        "Os recibos saem das receitas marcadas como pagas no Financeiro. Use “Recibo avulso” para outros casos."),
    ]));
    return;
  }

  const rows = items.map((e) => h("tr", {}, [
    h("td", {}, fmtData(e.paid_date || e.due_date)),
    h("td", {}, e.patient_name || h("span", { class: "muted" }, "—")),
    h("td", {}, e.description || h("span", { class: "muted" }, "(sem descrição)")),
    h("td", { class: "fin-val rec" }, fmtMoeda(e.amount)),
    h("td", { class: "row-actions" }, [
      h("button", { class: "btn-ghost btn-sm", title: "Gerar recibo deste pagamento", onClick: async () => {
        gerarRecibo({
          patient_id: e.patient_id,
          payer: await pagadorDe(e.patient_id, e.patient_name),
          amount: e.amount,
          reference: (e.description || "atendimento psicológico") + (e.patient_name ? ` (cliente: ${e.patient_name})` : ""),
          when: e.paid_date || e.due_date,
        });
      } }, "🧾 Recibo"),
    ]),
  ]));

  const total = items.reduce((s, e) => s + (e.amount || 0), 0);
  body.appendChild(h("div", { class: "table-wrap" }, [
    h("table", { class: "ctable fin-table" }, [
      h("thead", {}, h("tr", {}, [
        h("th", {}, "Pago em"), h("th", {}, "Cliente"), h("th", {}, "Descrição"),
        h("th", {}, "Valor"), h("th", {}, ""),
      ])),
      h("tbody", {}, rows),
    ]),
  ]));
  body.appendChild(h("div", { class: "muted", style: "text-align:right;margin-top:10px;font-size:13px" },
    `${items.length} pagamento${items.length > 1 ? "s" : ""} · total recebido ${fmtMoeda(total)}`));
}

function hojeISO() { const d = new Date(); return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`; }
function mudarMes(container, delta) {
  let m = state.mes + delta, y = state.ano;
  if (m < 0) { m = 11; y--; } else if (m > 11) { m = 0; y++; }
  state.mes = m; state.ano = y; draw(container);
}
function irHoje(container) { const d = new Date(); state.ano = d.getFullYear(); state.mes = d.getMonth(); draw(container); }
