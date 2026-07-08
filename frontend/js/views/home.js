// Tela inicial (Home): ponto central de navegacao.

import { store, isConfigured } from "../store.js";
import { h } from "../util.js";
import { fazerBackup, restaurarBackup, exportarDados, importarDados } from "../systemActions.js";

export function renderHome(container) {
  const s = store.settings || {};

  const hero = h("div", { class: "home-hero" + (s.logo_path && s.logo_includes_info ? " logo-only" : "") }, [
    s.logo_path
      ? h("img", { class: "hero-logo", src: "/api/settings/logo/image?t=" + Date.now(), alt: "Logo" })
      : h("div", { class: "hero-fallback" }, iniciaisHero(s.professional_name)),
    h("h1", {}, s.professional_name || "Ficha de Anamnese"),
    h("div", { class: "hero-sub" }, [
      (s.professional_title || "Psicóloga"),
      s.crp ? "  ·  " + (s.crp.toUpperCase().startsWith("CRP") ? s.crp : "CRP " + s.crp) : "",
    ].join("")),
  ]);

  const parts = [hero];

  if (!isConfigured()) {
    parts.push(h("div", { class: "notice" }, [
      h("div", { class: "notice-text" }, [
        h("strong", {}, "Configure seu consultório. "),
        "Adicione sua logo, nome e CRP para que apareçam nas fichas e nos PDFs.",
      ]),
      h("button", { class: "btn", onClick: () => (location.hash = "#/config") }, "Configurar agora"),
    ]));
  }

  const tiles = h("div", { class: "home-actions" }, [
    tile("👥", "Acessar sistema", "Pacientes e fichas salvas", "#/pacientes"),
    tile("📝", "Nova anamnese", "Iniciar uma ficha", "#/pacientes?nova=1"),
    tile("📄", "Exportar PDF", "Escolher ficha e gerar PDF", "#/exportar"),
  ]);
  parts.push(tiles);

  const secondary = h("div", { class: "secondary-actions" }, [
    h("button", { class: "btn-outline btn-sm", onClick: () => (location.hash = "#/config") }, "⚙ Configurações"),
    h("button", { class: "btn-ghost btn-sm", onClick: fazerBackup }, "💾 Fazer backup"),
    h("button", { class: "btn-ghost btn-sm", onClick: restaurarBackup }, "♻ Restaurar backup"),
    h("button", { class: "btn-ghost btn-sm", onClick: () => exportarDados("zip") }, "⬇ Exportar dados"),
    h("button", { class: "btn-ghost btn-sm", onClick: () => importarDados() }, "⬆ Importar dados"),
  ]);
  parts.push(secondary);

  container.appendChild(h("div", {}, parts));
}

function tile(icon, title, desc, hash) {
  return h("div", { class: "home-tile", onClick: () => (location.hash = hash) }, [
    h("div", { class: "tile-icon" }, icon),
    h("div", { class: "tile-title" }, title),
    h("div", { class: "tile-desc" }, desc),
  ]);
}

function iniciaisHero(nome) {
  const p = (nome || "").trim().split(/\s+/).filter(Boolean);
  if (!p.length) return "FA";
  return ((p[0][0] || "") + (p[1]?.[0] || "")).toUpperCase();
}
