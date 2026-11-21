// Acoes de backup, restauracao e exportacao/importacao de dados.
// Funcionam no desktop (dialogos nativos) e no navegador (download / upload).

import { api } from "./api.js";
import { escolherPasta, escolherArquivo, escolherSalvar, hasBridge, baixar } from "./store.js";
import { toast, confirmar } from "./util.js";
import { loadSettings } from "./store.js";
import { refreshHeader } from "./app.js";

export async function fazerBackup() {
  const pasta = await escolherPasta();
  if (!pasta) return;
  try {
    const r = await api.backup(pasta);
    toast("Backup salvo em: " + r.path, "ok");
  } catch (e) { toast(e.message, "err"); }
}

export async function restaurarBackup() {
  if (!hasBridge()) {
    toast("Restauração disponível no aplicativo desktop.", "err");
    return;
  }
  const arquivo = await escolherArquivo("backup");
  if (!arquivo) return;
  const ok = await confirmar({
    title: "Restaurar backup",
    message: "Isso substituirá TODOS os dados atuais pelos do backup. Deseja continuar?",
    okLabel: "Restaurar", danger: true,
  });
  if (!ok) return;
  try {
    await api.restore(arquivo);
    toast("Backup restaurado. O aplicativo será reiniciado.", "ok");
    setTimeout(() => location.reload(), 1800);
  } catch (e) { toast(e.message, "err"); }
}

export async function exportarDados(format = "zip") {
  const nome = format === "json" ? "anamnese_dados.json" : "anamnese_dados.zip";
  const path = await escolherSalvar(nome, format.toUpperCase());
  if (path) {
    try {
      const r = await api.exportTo(path, format);
      toast("Dados exportados: " + r.path, "ok");
    } catch (e) { toast(e.message, "err"); }
  } else if (!hasBridge()) {
    try { await baixar(`/api/system/export?format=${format}`, nome); } catch (e) { toast(e.message, "err"); }
  }
}

export function importarDados(onDone) {
  const input = document.createElement("input");
  input.type = "file";
  input.accept = ".json,.zip";
  input.onchange = async () => {
    const file = input.files[0];
    if (!file) return;
    const ok = await confirmar({
      title: "Importar dados",
      message: "Os pacientes e fichas do arquivo serão adicionados/atualizados. Continuar?",
      okLabel: "Importar",
    });
    if (!ok) return;
    try {
      const r = await api.importData(file);
      const s = r.imported || {};
      await loadSettings(); refreshHeader();
      toast(`Importado: ${s.patients || 0} paciente(s), ${s.anamneses || 0} ficha(s).`, "ok");
      if (onDone) onDone();
    } catch (e) { toast(e.message, "err"); }
  };
  input.click();
}
