// Estado compartilhado (configuracoes) e ponte com os dialogos nativos do
// desktop (pywebview). No navegador, usa alternativas (download / prompt).

import { api } from "./api.js";

export const store = { settings: null };

export async function loadSettings() {
  store.settings = await api.getSettings();
  return store.settings;
}

// Consultório está configurado se tiver nome+CRP OU uma logo que já inclui esses dados.
export function isConfigured() {
  const s = store.settings;
  if (!s) return false;
  if (s.logo_path && s.logo_includes_info) return true;
  return !!(s.professional_name && s.crp);
}

// ---- Ponte pywebview ----
export function hasBridge() {
  return typeof window.pywebview !== "undefined" && window.pywebview.api;
}

// Escolher pasta (backup). Retorna caminho ou null.
export async function escolherPasta() {
  if (hasBridge() && window.pywebview.api.choose_folder) {
    const r = await window.pywebview.api.choose_folder();
    return r || null;
  }
  const p = window.prompt("Cole o caminho da pasta de destino (ex.: E:\\Backups):");
  return p ? p.trim() : null;
}

// Escolher arquivo para abrir (restaurar/importar). Retorna caminho ou null.
export async function escolherArquivo(filtro) {
  if (hasBridge() && window.pywebview.api.choose_open_file) {
    const r = await window.pywebview.api.choose_open_file(filtro || "");
    return r || null;
  }
  return null; // no navegador usa-se <input type=file>
}

// Escolher onde salvar (PDF/export). Retorna caminho ou null.
export async function escolherSalvar(sugestao, filtro) {
  if (hasBridge() && window.pywebview.api.choose_save_file) {
    const r = await window.pywebview.api.choose_save_file(sugestao || "", filtro || "");
    return r || null;
  }
  return null;
}

// Abre uma URL no navegador do sistema (no desktop usa a ponte pywebview).
export function openExternal(url) {
  if (hasBridge() && window.pywebview.api.open_external) {
    window.pywebview.api.open_external(url);
  } else {
    window.open(url, "_blank", "noopener");
  }
}

// Baixa uma URL como arquivo (fallback do navegador).
export function baixar(url, filename) {
  const a = document.createElement("a");
  a.href = url; a.download = filename || "";
  document.body.appendChild(a); a.click(); a.remove();
}
