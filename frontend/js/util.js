// Utilidades de interface (DOM, formatacao, toast, modais).

// Cria elemento: h('div', {class:'x', onclick:fn}, [filhos | texto])
export function h(tag, attrs = {}, children = []) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v == null || v === false) continue;
    if (k === "class") el.className = v;
    else if (k === "html") el.innerHTML = v;
    else if (k.startsWith("on") && typeof v === "function") {
      el.addEventListener(k.slice(2).toLowerCase(), v);
    } else if (k === "value") el.value = v;
    else el.setAttribute(k, v);
  }
  const kids = Array.isArray(children) ? children : [children];
  for (const c of kids) {
    if (c == null || c === false) continue;
    el.appendChild(typeof c === "string" || typeof c === "number"
      ? document.createTextNode(String(c)) : c);
  }
  return el;
}

export function clear(node) { while (node.firstChild) node.removeChild(node.firstChild); }

export function iniciais(nome) {
  const parts = (nome || "").trim().split(/\s+/).filter(Boolean);
  if (!parts.length) return "?";
  return (parts[0][0] + (parts.length > 1 ? parts[parts.length - 1][0] : "")).toUpperCase();
}

// Data ISO 'YYYY-MM-DD' -> 'DD/MM/AAAA'
export function fmtData(iso) {
  if (!iso) return "";
  const [y, m, d] = String(iso).slice(0, 10).split("-");
  return d && m && y ? `${d}/${m}/${y}` : iso;
}

// Data/hora ISO -> 'DD/MM/AAAA'
export function fmtDataHora(iso) {
  if (!iso) return "";
  const dt = new Date(iso);
  if (isNaN(dt)) return fmtData(iso);
  return dt.toLocaleDateString("pt-BR");
}

export function calcIdade(iso) {
  if (!iso) return "";
  const nasc = new Date(iso + "T00:00:00");
  if (isNaN(nasc)) return "";
  const hoje = new Date();
  if (nasc > hoje) return "";
  let anos = hoje.getFullYear() - nasc.getFullYear();
  let meses = hoje.getMonth() - nasc.getMonth();
  if (hoje.getDate() < nasc.getDate()) meses--;
  if (meses < 0) { anos--; meses += 12; }
  if (anos <= 0) return meses <= 0 ? "menos de 1 mês" : `${meses} ${meses === 1 ? "mês" : "meses"}`;
  let txt = `${anos} ${anos === 1 ? "ano" : "anos"}`;
  if (meses > 0) txt += ` e ${meses} ${meses === 1 ? "mês" : "meses"}`;
  return txt;
}

let toastTimer;
export function toast(msg, tipo = "") {
  const t = document.getElementById("toast");
  t.textContent = msg;
  t.className = "toast " + tipo;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.add("hidden"), 3200);
}

export function debounce(fn, wait = 600) {
  let timer;
  const wrapped = (...args) => { clearTimeout(timer); timer = setTimeout(() => fn(...args), wait); };
  wrapped.flush = () => { clearTimeout(timer); fn(); };
  wrapped.cancel = () => clearTimeout(timer);
  return wrapped;
}

// Modal generico. content = Node. actions = [{label, class, onClick(close)}]
export function modal({ title, content, actions = [] }) {
  const root = document.getElementById("modal-root");
  const close = () => clear(root);
  const box = h("div", { class: "modal" }, [
    title ? h("h3", {}, title) : null,
    content,
    h("div", { class: "modal-actions" }, actions.map((a) =>
      h("button", { class: a.class || "btn-ghost", onClick: () => a.onClick ? a.onClick(close) : close() }, a.label))),
  ]);
  const overlay = h("div", { class: "modal-overlay", onClick: (e) => { if (e.target === overlay) close(); } }, [box]);
  clear(root); root.appendChild(overlay);
  return close;
}

// Confirmacao (Promise<boolean>)
export function confirmar({ title = "Confirmar", message, okLabel = "Confirmar", danger = false }) {
  return new Promise((resolve) => {
    modal({
      title,
      content: h("p", { class: "muted" }, message),
      actions: [
        { label: "Cancelar", class: "btn-ghost", onClick: (c) => { c(); resolve(false); } },
        { label: okLabel, class: danger ? "btn-danger" : "btn", onClick: (c) => { c(); resolve(true); } },
      ],
    });
  });
}

// ---- Máscaras de digitação ----
// CPF: 000.000.000-00 (aceita colar com ou sem pontos/traço).
export function formatCpf(v) {
  const d = String(v || "").replace(/\D/g, "").slice(0, 11);
  if (d.length <= 3) return d;
  if (d.length <= 6) return `${d.slice(0, 3)}.${d.slice(3)}`;
  if (d.length <= 9) return `${d.slice(0, 3)}.${d.slice(3, 6)}.${d.slice(6)}`;
  return `${d.slice(0, 3)}.${d.slice(3, 6)}.${d.slice(6, 9)}-${d.slice(9)}`;
}
export function maskCpf(input) {
  input.setAttribute("inputmode", "numeric");
  input.setAttribute("maxlength", "14");
  input.placeholder = input.placeholder || "000.000.000-00";
  const aplicar = () => { input.value = formatCpf(input.value); };
  input.addEventListener("input", aplicar);
  aplicar();
  return input;
}

// Dinheiro: digita só números e a vírgula/pontos se ajustam (12000 -> 120,00;
// 123456 -> 1.234,56). moneyValue() devolve o número (ex.: 1234.56).
export function formatMoney(n) {
  const v = Number(n) || 0;
  return v.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}
export function moneyValue(input) {
  const d = String(input.value || "").replace(/\D/g, "");
  return d ? parseInt(d, 10) / 100 : 0;
}
export function maskMoney(input, valorInicial) {
  input.type = "text";
  input.setAttribute("inputmode", "numeric");
  input.placeholder = "0,00";
  const aplicar = () => {
    const d = input.value.replace(/\D/g, "").replace(/^0+/, "").slice(0, 11);
    input.value = d ? formatMoney(parseInt(d, 10) / 100) : "";
  };
  input.addEventListener("input", aplicar);
  if (valorInicial != null && valorInicial !== "") input.value = formatMoney(valorInicial);
  return input;
}
