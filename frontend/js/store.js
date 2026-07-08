// Estado compartilhado (configuracoes) e ponte com os dialogos nativos do
// desktop (pywebview). No navegador, usa alternativas (download / prompt).

import { api } from "./api.js";

export const store = { settings: null };

export async function loadSettings() {
  store.settings = await api.getSettings();
  return store.settings;
}

export function isConfigured() {
  const s = store.settings;
  return !!(s && s.professional_name && s.crp);
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

// Baixa uma URL como arquivo (fallback do navegador).
export function baixar(url, filename) {
  const a = document.createElement("a");
  a.href = url; a.download = filename || "";
  document.body.appendChild(a); a.click(); a.remove();
}
