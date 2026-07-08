// Placeholder para módulos futuros (Financeiro, Relatórios).
import { h } from "../util.js";

export function renderSoon(container, nome, icon) {
  container.appendChild(h("div", { class: "empty" }, [
    h("div", { class: "empty-icon" }, icon || "🚧"),
    h("h2", { style: "color:var(--navy);margin:8px 0 4px" }, nome),
    h("p", { class: "muted" }, "Este módulo chega em breve. Estamos priorizando a Agenda agora."),
    h("span", { class: "badge badge-soon" }, "Em breve"),
  ]));
}
