// Estado compartilhado (configuracoes) e ponte com os dialogos nativos do
// desktop (pywebview). No navegador, usa alternativas (download / prompt).

import { api } from "./api.js";

export const store = { settings: null };

export async function loadSettings() {
  store.settings = await api.getSettings();
  return store.settings;
}

// Os documentos usam sempre a logo oficial, que já traz nome, título e CRP —
// então o consultório está sempre "configurado" para a identidade visual.
export function isConfigured() {
  return !!store.settings;
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

function blobParaBase64(blob) {
  return new Promise((resolve, reject) => {
    const r = new FileReader();
    r.onload = () => resolve(String(r.result).split(",")[1] || "");
    r.onerror = () => reject(r.error);
    r.readAsDataURL(blob);
  });
}

// Salva um arquivo na pasta Downloads do computador.
// No app (pywebview) a janela não faz downloads: a ponte grava o arquivo em
// Downloads e devolve o caminho. No navegador, usa o download normal.
export async function salvarArquivo(blob, filename) {
  const nome = filename || "arquivo";
  if (hasBridge() && window.pywebview.api.save_download) {
    const r = await window.pywebview.api.save_download(nome, await blobParaBase64(blob));
    if (!r || !r.ok) throw new Error((r && r.error) || "Não foi possível salvar o arquivo.");
    return r.path;
  }
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = nome;
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 4000);
  return null;
}

// Nome do arquivo a partir do cabeçalho Content-Disposition da resposta.
export function nomeDoArquivo(res, fallback) {
  const cd = res.headers.get("content-disposition") || "";
  const m = cd.match(/filename\*?=(?:UTF-8'')?"?([^";]+)/i);
  if (!m) return fallback;
  try { return decodeURIComponent(m[1]); } catch { return m[1]; }
}

// Baixa uma URL do app para a pasta Downloads. Retorna o caminho salvo (app)
// ou null (navegador). Mostra o aviso de onde ficou.
export async function baixar(url, filename) {
  const res = await fetch(url);
  if (!res.ok) {
    let msg = "Falha ao baixar o arquivo.";
    try { const j = await res.json(); if (j && j.detail) msg = j.detail; } catch {}
    throw new Error(msg);
  }
  const nome = nomeDoArquivo(res, filename);
  return salvarArquivo(await res.blob(), nome);
}
