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
