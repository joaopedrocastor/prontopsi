// Relatórios: indicadores e gráficos a partir de finanças, agenda e clientes.
// Somente leitura. Gráficos em SVG/CSS (sem dependências).

import { api } from "../api.js";
import { h, clear, toast } from "../util.js";

const STATUS_CLI = {
  ativo: { label: "Ativos", color: "#2E8B63" },
  espera: { label: "Lista de espera", color: "#C8791E" },
  alta: { label: "Alta", color: "#0E7C8A" },
  desativado: { label: "Desativados", color: "#7E8B93" },
  desistente: { label: "Desistentes", color: "#C4432F" },
};
const STATUS_SESS = {
  realizada: { label: "Realizadas", color: "#2E8B63" },
  agendada: { label: "Agendadas", color: "#A24A2A" },
  confirmada: { label: "Confirmadas", color: "#2C7BE5" },
  faltou: { label: "Faltas", color: "#C8791E" },
  cancelada: { label: "Canceladas", color: "#7E8B93" },
};

function fmtMoeda(v) { return (v || 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" }); }
function mesLabel(ym) { const [y, m] = ym.split("-"); return ["", "Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"][+m] + "/" + y.slice(2); }

let months = 6;

export async function renderReports(container) {
  clear(container);
  container.appendChild(h("div", { class: "page-head" }, [
    h("h1", {}, "Relatórios"),
    h("div", { class: "spacer", style: "flex:1" }),
    periodoSel(container),
  ]));

  const body = h("div", {}, [h("div", { class: "empty muted", style: "padding:30px" }, "Carregando...")]);
  container.appendChild(body);

  let d;
  try { d = await api.reportsOverview(months); } catch (e) { clear(body); body.appendChild(h("div", { class: "empty muted" }, "Erro ao carregar: " + e.message)); return; }
  clear(body);

  const t = d.totals;
  // KPIs gerais
  const row = h("div", { class: "stat-row fin-kpis" });
  row.appendChild(kpi("Recebido no período", fmtMoeda(t.recebido), "var(--ok)"));
  row.appendChild(kpi("Despesas no período", fmtMoeda(t.despesa), "var(--accent)"));
  row.appendChild(kpi("Saldo", fmtMoeda(t.saldo), t.saldo < 0 ? "var(--danger)" : "var(--navy)"));
  row.appendChild(kpi("A receber", fmtMoeda(t.a_receber), "var(--warn)"));
  body.appendChild(row);

  const row2 = h("div", { class: "stat-row", style: "grid-template-columns:repeat(3,1fr)" });
  row2.appendChild(kpi("Sessões realizadas", String(t.sessoes_realizadas), "var(--navy)"));
  row2.appendChild(kpi("Clientes", String(t.clientes), "var(--navy)"));
  row2.appendChild(kpi("Clientes ativos", String(t.clientes_ativos), "var(--ok)"));
  body.appendChild(row2);

  // Gráfico financeiro mensal (receita x despesa)
  body.appendChild(h("div", { class: "card", style: "margin-bottom:16px" }, [
    cardHead("Receita x Despesa por mês", "Valores realizados (pagos/recebidos)"),
    barrasDuplas(d.finance_monthly),
  ]));

  // Sessões por mês + distribuições
  body.appendChild(h("div", { class: "grid grid-2", style: "align-items:start" }, [
    h("div", { class: "card" }, [cardHead("Sessões realizadas por mês"), barrasSimples(d.sessions_monthly.map((s) => ({ label: mesLabel(s.month), value: s.realizadas })), "var(--ok)")]),
    h("div", { class: "card" }, [cardHead("Sessões por situação", "No período"), distrib(d.sessions_status, STATUS_SESS)]),
  ]));

  body.appendChild(h("div", { class: "card", style: "margin-top:16px" }, [
    cardHead("Clientes por situação"),
    distrib(d.clients_status, STATUS_CLI),
  ]));
}

function periodoSel(container) {
  const sel = h("select", { style: "width:auto;min-width:150px" }, [
    opt(3, "Últimos 3 meses"), opt(6, "Últimos 6 meses"), opt(12, "Últimos 12 meses"),
  ]);
  sel.value = String(months);
  sel.addEventListener("change", () => { months = +sel.value; renderReports(container); });
  return sel;
}
function opt(v, l) { return h("option", { value: v, ...(v === months ? { selected: "selected" } : {}) }, l); }

function kpi(label, value, color) {
  return h("div", { class: "stat" }, [
    h("div", { class: "st-label" }, label),
    h("div", { class: "st-value", style: `font-size:20px;color:${color}` }, value),
  ]);
}
function cardHead(titulo, sub) {
  return h("div", { style: "margin-bottom:12px" }, [
    h("h2", { style: "font-size:15px;color:var(--navy);margin:0" }, titulo),
    sub ? h("div", { class: "muted", style: "font-size:12px" }, sub) : null,
  ]);
}

// Barras duplas (receita verde / despesa âmbar) por mês.
function barrasDuplas(serie) {
  const max = Math.max(1, ...serie.flatMap((s) => [s.receita, s.despesa]));
  const H = 150;
  return h("div", {}, [
    h("div", { class: "rep-bars" }, serie.map((s) => h("div", { class: "rep-bar-group" }, [
      h("div", { class: "rep-bar-pair" }, [
        h("div", { class: "rep-bar", style: `height:${(s.receita / max) * H}px;background:var(--ok)`, title: "Receita: " + fmtMoeda(s.receita) }),
        h("div", { class: "rep-bar", style: `height:${(s.despesa / max) * H}px;background:var(--accent)`, title: "Despesa: " + fmtMoeda(s.despesa) }),
      ]),
      h("div", { class: "rep-bar-label" }, mesLabel(s.month)),
    ]))),
    h("div", { class: "rep-legend" }, [
      legenda("var(--ok)", "Receita"), legenda("var(--accent)", "Despesa"),
    ]),
  ]);
}

// Barras simples verticais.
function barrasSimples(serie, color) {
  const max = Math.max(1, ...serie.map((s) => s.value));
  const H = 130;
  if (!serie.some((s) => s.value > 0)) return h("div", { class: "muted", style: "padding:14px 0" }, "Sem dados no período.");
  return h("div", { class: "rep-bars" }, serie.map((s) => h("div", { class: "rep-bar-group" }, [
    h("div", { class: "rep-bar-val" }, s.value || ""),
    h("div", { class: "rep-bar", style: `height:${(s.value / max) * H}px;background:${color};width:26px`, title: s.label + ": " + s.value }),
    h("div", { class: "rep-bar-label" }, s.label),
  ])));
}

// Distribuição por categoria (barras horizontais + total).
function distrib(dados, mapa) {
  const total = dados.reduce((s, d) => s + d.count, 0);
  if (!total) return h("div", { class: "muted", style: "padding:14px 0" }, "Sem dados.");
  return h("div", { class: "fin-chart" }, dados.sort((a, b) => b.count - a.count).map((d) => {
    const info = mapa[d.status] || { label: d.status, color: "var(--muted)" };
    return h("div", { class: "fin-chart-row" }, [
      h("div", { class: "fin-chart-label" }, info.label),
      h("div", { class: "fin-chart-track" }, [h("div", { class: "fin-chart-fill", style: `width:${Math.max(4, (d.count / total) * 100)}%;background:${info.color}` })]),
      h("div", { class: "fin-chart-val" }, `${d.count} (${Math.round((d.count / total) * 100)}%)`),
    ]);
  }));
}

function legenda(color, label) {
  return h("span", { class: "rep-leg-item" }, [h("span", { class: "rep-leg-dot", style: `background:${color}` }), label]);
}
