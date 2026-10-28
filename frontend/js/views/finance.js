// Módulo Financeiro: receitas e despesas, totais por período, análise por
// categoria e recorrências. Fala só com a API (/api/finance).

import { api } from "../api.js";
import { h, clear, toast, modal, confirmar, fmtData } from "../util.js";

const MESES = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
  "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"];

// Estado local da tela (período exibido, aba e filtro de tipo).
const state = { ano: 0, mes: 0, tab: "lancamentos", filtro: "", patients: null };

function pad(n) { return String(n).padStart(2, "0"); }
// Primeiro e último dia do mês atual do estado, em ISO 'YYYY-MM-DD'.
function periodo() {
  const start = `${state.ano}-${pad(state.mes + 1)}-01`;
  const ultimo = new Date(state.ano, state.mes + 1, 0).getDate();
  const end = `${state.ano}-${pad(state.mes + 1)}-${pad(ultimo)}`;
  return { start, end };
}
function fmtMoeda(v) {
  return (v || 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}
function hojeISO() { const d = new Date(); return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`; }

// Ponto de entrada da rota #/financeiro.
export async function renderFinance(container) {
  if (!state.ano) { const d = new Date(); state.ano = d.getFullYear(); state.mes = d.getMonth(); }
  if (state.patients == null) state.patients = await api.listPatients().catch(() => []);
  await draw(container);
}

// Redesenha a tela inteira a partir do estado atual.
async function draw(container) {
  clear(container);
  const { start, end } = periodo();

  // Barra de período + botões de novo lançamento.
  container.appendChild(h("div", { class: "fin-bar" }, [
    h("div", { class: "cal-nav" }, [
      h("button", { class: "btn-ghost btn-sm", onClick: () => mudarMes(container, -1) }, "‹"),
      h("span", { class: "cal-title" }, `${MESES[state.mes]} ${state.ano}`),
      h("button", { class: "btn-ghost btn-sm", onClick: () => mudarMes(container, 1) }, "›"),
      h("button", { class: "btn-ghost btn-sm", onClick: () => irHoje(container) }, "Hoje"),
    ]),
    h("div", { style: "margin-left:auto;display:flex;gap:8px" }, [
      h("button", { class: "btn", onClick: () => abrirModal(container, { kind: "receita" }) }, "＋ Receita"),
      h("button", { class: "btn-accent", onClick: () => abrirModal(container, { kind: "despesa" }) }, "＋ Despesa"),
    ]),
  ]));

  // Indicadores (KPIs) do período.
  const statRow = h("div", { class: "stat-row fin-kpis" });
  container.appendChild(statRow);

  // Abas.
  container.appendChild(h("div", { class: "seg fin-tabs" }, [
    tabBtn(container, "lancamentos", "Lançamentos"),
    tabBtn(container, "analise", "Análise"),
    tabBtn(container, "recorrencias", "Recorrências"),
  ]));

  const body = h("div", { id: "fin-body", style: "margin-top:16px" }, [
    h("div", { class: "empty muted", style: "padding:30px" }, "Carregando..."),
  ]);
  container.appendChild(body);

  // Carrega KPIs e corpo da aba em paralelo.
  const [totals] = await Promise.all([
    api.financeTotals(start, end).catch(() => null),
    drawTab(body, start, end),
  ]);
  if (totals) preencherKpis(statRow, totals);
}

function tabBtn(container, id, label) {
  return h("button", {
    class: "seg-btn" + (state.tab === id ? " active" : ""),
    onClick: () => { if (state.tab !== id) { state.tab = id; draw(container); } },
  }, label);
}

function mudarMes(container, delta) {
  let m = state.mes + delta, y = state.ano;
  if (m < 0) { m = 11; y--; } else if (m > 11) { m = 0; y++; }
  state.mes = m; state.ano = y; draw(container);
}
function irHoje(container) { const d = new Date(); state.ano = d.getFullYear(); state.mes = d.getMonth(); draw(container); }

function preencherKpis(row, t) {
  clear(row);
  const kpi = (label, value, cls, hint) => h("div", { class: "stat fin-kpi " + (cls || "") }, [
    h("div", { class: "st-label" }, label),
    h("div", { class: "st-value" }, fmtMoeda(value)),
    hint ? h("div", { class: "fin-hint" }, hint) : null,
  ]);
  row.appendChild(kpi("Saldo projetado", t.forecast, t.forecast < 0 ? "neg" : "pos", "Receitas menos despesas"));
  row.appendChild(kpi("Receitas", t.income_received + t.income_pending, "rec",
    t.income_pending ? `${fmtMoeda(t.income_pending)} a receber` : "Tudo recebido"));
  row.appendChild(kpi("Despesas", t.expense_paid + t.expense_open, "desp",
    t.expense_open ? `${fmtMoeda(t.expense_open)} em aberto` : "Tudo pago"));
  row.appendChild(kpi("Vencidas", t.overdue, t.overdue > 0 ? "alert" : "",
    t.overdue > 0 ? "Contas passadas do vencimento" : "Em dia"));
}

async function drawTab(body, start, end) {
  if (state.tab === "lancamentos") return drawLancamentos(body, start, end);
  if (state.tab === "analise") return drawAnalise(body, start, end);
  return drawRecorrencias(body);
}

// ---- Aba Lançamentos ----
async function drawLancamentos(body, start, end) {
  const params = { start, end };
  if (state.filtro) params.kind = state.filtro;
  let items = [];
  try { items = await api.listFinance(params); } catch { body.innerHTML = ""; body.appendChild(erro()); return; }

  clear(body);
  const container = body.parentElement;
  body.appendChild(h("div", { class: "toolbar" }, [
    chip(container, "", "Todos"),
    chip(container, "receita", "Receitas"),
    chip(container, "despesa", "Despesas"),
  ]));

  if (!items.length) {
    body.appendChild(h("div", { class: "empty" }, [
      h("div", { class: "empty-icon" }, "💰"),
      h("div", { class: "muted" }, "Nenhum lançamento neste mês."),
    ]));
    return;
  }

  const rows = items.map((e) => {
    const venc = e.due_date < hojeISO() && !e.paid;
    return h("tr", {}, [
      h("td", {}, fmtData(e.due_date)),
      h("td", {}, [
        h("div", { style: "font-weight:600" }, e.description || "(sem descrição)"),
        e.patient_name ? h("div", { class: "fin-sub" }, e.patient_name) : null,
      ]),
      h("td", {}, e.category ? h("span", { class: "badge badge-cat" }, e.category) : h("span", { class: "muted" }, "—")),
      h("td", { class: "fin-val " + (e.kind === "receita" ? "rec" : "desp") },
        (e.kind === "receita" ? "+ " : "− ") + fmtMoeda(e.amount)),
      h("td", {}, statusBadge(e, venc)),
      h("td", { class: "row-actions" }, [
        h("button", { class: "icon-btn", title: e.paid ? "Marcar como não pago" : "Marcar como pago", onClick: () => togglePago(container, e) }, e.paid ? "↩" : "✓"),
        h("button", { class: "icon-btn", title: "Editar", onClick: () => abrirModal(container, e) }, "✎"),
        h("button", { class: "icon-btn", title: "Excluir", onClick: () => excluir(container, e) }, "🗑"),
      ]),
    ]);
  });

  body.appendChild(h("div", { class: "table-wrap" }, [
    h("table", { class: "ctable fin-table" }, [
      h("thead", {}, h("tr", {}, [
        h("th", {}, "Vencimento"), h("th", {}, "Descrição"), h("th", {}, "Categoria"),
        h("th", {}, "Valor"), h("th", {}, "Situação"), h("th", {}, ""),
      ])),
      h("tbody", {}, rows),
    ]),
  ]));
}

function chip(container, value, label) {
  return h("button", {
    class: "chip-filter" + (state.filtro === value ? " active" : ""),
    onClick: () => { state.filtro = value; draw(container); },
  }, label);
}

function statusBadge(e, venc) {
  if (e.paid) return h("span", { class: "badge badge-done" }, e.kind === "receita" ? "Recebido" : "Pago");
  if (venc) return h("span", { class: "badge badge-missing" }, "Vencida");
  return h("span", { class: "badge badge-draft" }, "Em aberto");
}

async function togglePago(container, e) {
  try { await api.updateFinance(e.id, { paid: !e.paid }); draw(container); }
  catch (err) { toast(err.message, "err"); }
}
async function excluir(container, e) {
  const ok = await confirmar({ title: "Excluir lançamento", message: `Excluir "${e.description || "lançamento"}"?`, okLabel: "Excluir", danger: true });
  if (!ok) return;
  try { await api.deleteFinance(e.id); toast("Lançamento excluído."); draw(container); }
  catch (err) { toast(err.message, "err"); }
}

// ---- Aba Análise ----
async function drawAnalise(body, start, end) {
  let despesas = [], receitas = [];
  try {
    [despesas, receitas] = await Promise.all([
      api.financeByCategory("despesa", start, end),
      api.financeByCategory("receita", start, end),
    ]);
  } catch { body.innerHTML = ""; body.appendChild(erro()); return; }

  clear(body);
  if (!despesas.length && !receitas.length) {
    body.appendChild(h("div", { class: "empty" }, [
      h("div", { class: "empty-icon" }, "📊"),
      h("div", { class: "muted" }, "Sem dados para analisar neste mês."),
    ]));
    return;
  }
  body.appendChild(h("div", { class: "grid grid-2", style: "align-items:start" }, [
    cardCategorias("Despesas por categoria", despesas, "desp"),
    cardCategorias("Receitas por categoria", receitas, "rec"),
  ]));
}

function cardCategorias(titulo, dados, cls) {
  const max = Math.max(1, ...dados.map((d) => d.total));
  const total = dados.reduce((s, d) => s + d.total, 0);
  return h("div", { class: "card" }, [
    h("div", { class: "panel-head", style: "padding:0 0 12px;border:none" }, [
      h("h2", { style: "font-size:15px" }, titulo),
      h("span", { class: "muted", style: "margin-left:auto;font-size:13px" }, fmtMoeda(total)),
    ]),
    dados.length ? h("div", { class: "fin-chart" }, dados.map((d) => h("div", { class: "fin-chart-row" }, [
      h("div", { class: "fin-chart-label" }, d.category),
      h("div", { class: "fin-chart-track" }, [
        h("div", { class: "fin-chart-fill " + cls, style: `width:${Math.max(4, (d.total / max) * 100)}%` }),
      ]),
      h("div", { class: "fin-chart-val" }, fmtMoeda(d.total)),
    ]))) : h("div", { class: "muted", style: "padding:10px 0" }, "Nada neste mês."),
  ]);
}

// ---- Aba Recorrências ----
async function drawRecorrencias(body) {
  let items = [];
  try { items = await api.listFinance({ recurring: true }); } catch { body.innerHTML = ""; body.appendChild(erro()); return; }
  clear(body);
  if (!items.length) {
    body.appendChild(h("div", { class: "empty" }, [
      h("div", { class: "empty-icon" }, "🔁"),
      h("div", { class: "muted" }, "Nenhum lançamento recorrente."),
      h("div", { class: "muted", style: "font-size:13px;margin-top:4px" }, "Marque a recorrência ao criar uma receita ou despesa."),
    ]));
    return;
  }
  const container = body.parentElement;
  const labelRec = { semanal: "Semanal", mensal: "Mensal", anual: "Anual" };
  body.appendChild(h("div", { class: "list" }, items.map((e) => h("div", { class: "list-item", onClick: () => abrirModal(container, e) }, [
    h("div", { style: "flex:1" }, [
      h("div", { style: "font-weight:600" }, e.description || "(sem descrição)"),
      h("div", { class: "fin-sub" }, [labelRec[e.recurrence] || e.recurrence, e.category ? " · " + e.category : ""].join("")),
    ]),
    h("span", { class: "fin-val " + (e.kind === "receita" ? "rec" : "desp") }, (e.kind === "receita" ? "+ " : "− ") + fmtMoeda(e.amount)),
  ]))));
}

// ---- Modal de lançamento (novo/editar) ----
async function abrirModal(container, entry) {
  const edit = !!entry.id;
  const cats = await api.financeCategories().catch(() => []);
  const v = {
    kind: entry.kind || "receita",
    description: entry.description || "",
    amount: entry.amount != null ? entry.amount : "",
    category: entry.category || "",
    due_date: entry.due_date || hojeISO(),
    paid: !!entry.paid,
    recurrence: entry.recurrence || "nenhuma",
    patient_id: entry.patient_id || "",
    notes: entry.notes || "",
  };

  const field = (label, control) => h("div", { class: "field" }, [h("label", {}, label), control]);
  const inp = (attrs) => h("input", { class: "inp", ...attrs });

  const fKind = h("div", { class: "seg" }, [
    segOpt("receita", "Receita", v), segOpt("despesa", "Despesa", v),
  ]);
  const fDesc = inp({ value: v.description, placeholder: "Ex.: Sessão, aluguel, material..." });
  const fAmount = inp({ type: "number", step: "0.01", min: "0", value: v.amount, placeholder: "0,00" });
  const fCat = inp({ value: v.category, placeholder: "Ex.: Consultas, Aluguel...", list: "fin-cats" });
  const dlCats = h("datalist", { id: "fin-cats" }, cats.map((c) => h("option", { value: c })));
  const fDate = inp({ type: "date", value: v.due_date });
  const fPaid = h("label", { class: "choice" }, [
    h("input", { type: "checkbox", ...(v.paid ? { checked: "checked" } : {}) }),
    h("span", {}, "Já pago / recebido"),
  ]);
  const fRec = h("select", { class: "inp" }, [
    opt("nenhuma", "Não se repete", v.recurrence),
    opt("semanal", "Semanal", v.recurrence),
    opt("mensal", "Mensal", v.recurrence),
    opt("anual", "Anual", v.recurrence),
  ]);
  const fPat = h("select", { class: "inp" }, [
    h("option", { value: "" }, "— Nenhum —"),
    ...(state.patients || []).map((p) => opt(p.id, p.name, v.patient_id)),
  ]);

  const close = modal({
    title: edit ? "Editar lançamento" : "Novo lançamento",
    content: h("div", {}, [
      field("Tipo", fKind),
      field("Descrição", fDesc),
      h("div", { class: "grid grid-2" }, [field("Valor (R$)", fAmount), field("Vencimento", fDate)]),
      field("Categoria", h("div", {}, [fCat, dlCats])),
      h("div", { class: "grid grid-2" }, [field("Repetição", fRec), field("Paciente (opcional)", fPat)]),
      field("", fPaid),
    ]),
    actions: [
      { label: "Cancelar", class: "btn-ghost" },
      {
        label: edit ? "Salvar" : "Adicionar", class: "btn",
        onClick: async (c) => {
          const data = {
            kind: fKind.dataset.kind || v.kind,
            description: fDesc.value.trim(),
            amount: parseFloat(fAmount.value) || 0,
            category: fCat.value.trim(),
            due_date: fDate.value,
            paid: fPaid.querySelector("input").checked,
            recurrence: fRec.value,
            patient_id: fPat.value || null,
          };
          if (!data.due_date) { toast("Informe o vencimento.", "err"); return; }
          if (!data.amount) { toast("Informe o valor.", "err"); return; }
          try {
            if (edit) await api.updateFinance(entry.id, data);
            else await api.createFinance(data);
            c(); toast(edit ? "Lançamento salvo." : "Lançamento adicionado."); draw(container);
          } catch (err) { toast(err.message, "err"); }
        },
      },
    ],
  });
  fKind.dataset.kind = v.kind;
}

function segOpt(value, label, v) {
  const b = h("button", { class: "seg-btn" + (v.kind === value ? " active" : "") }, label);
  b.addEventListener("click", () => {
    v.kind = value;
    const seg = b.parentElement;
    seg.dataset.kind = value;
    seg.querySelectorAll(".seg-btn").forEach((x) => x.classList.remove("active"));
    b.classList.add("active");
  });
  return b;
}
function opt(value, label, sel) {
  return h("option", { value, ...(String(sel) === String(value) ? { selected: "selected" } : {}) }, label);
}
function erro() { return h("div", { class: "empty muted" }, "Erro ao carregar. Tente novamente."); }
