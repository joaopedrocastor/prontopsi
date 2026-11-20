// Aviso de nova versão: faixa fixa no topo de todas as telas, com link para a
// release no GitHub (prontopsi-releases). Checa ao abrir o app e a cada 3 horas.

import { api } from "./api.js";
import { openExternal, hasBridge } from "./store.js";
import { h, modal, toast } from "./util.js";

const INTERVALO_MS = 3 * 60 * 60 * 1000;

// Inicia a checagem (ao abrir e periodicamente, pois o app costuma ficar aberto).
export function iniciarChecagemAtualizacao() {
  verificar();
  setInterval(verificar, INTERVALO_MS);
}

async function verificar() {
  let info;
  try { info = await api.checkUpdate(); } catch { return; }
  if (info && info.update_available) mostrarAviso(info);
}

// Desenha a faixa de atualização (exportada para testar com dados simulados).
export function mostrarAviso(info) {
  const el = document.getElementById("update-banner");
  if (!el) return;
  // No app instalado (ponte pywebview + instalador na release): atualização em 1 clique.
  const auto = hasBridge() && window.pywebview.api.install_update && info.asset_url;
  el.innerHTML = "";
  el.appendChild(h("div", { class: "update-text" }, [
    h("strong", {}, `🔔 Nova atualização disponível: ${info.latest}`),
    h("span", {}, ` — você está na v${String(info.current).replace(/^v/, "")}. `
      + (auto ? "Clique em Atualizar agora: o app baixa, instala e reabre sozinho."
              : "Baixe o instalador no GitHub e instale por cima — seus dados são mantidos.")),
  ]));
  el.appendChild(h("div", { class: "update-actions" }, [
    auto ? h("button", { class: "btn-accent", onClick: () => instalarAtualizacao(info) }, "⬇ Atualizar agora") : null,
    h("button", { class: auto ? "btn" : "btn-accent", onClick: () => openExternal(info.url) },
      auto ? "Ver no GitHub" : "⬇ Baixar no GitHub"),
  ]));
  el.classList.remove("hidden");
}

// Dispara o auto-update pela ponte: baixa o instalador, roda silencioso e reabre.
async function instalarAtualizacao(info) {
  const close = modal({
    title: "Atualizando o ProntoPsi",
    content: h("div", {}, [
      h("p", {}, `Baixando a versão ${info.latest}…`),
      h("p", { class: "muted", style: "font-size:13px" }, "O app vai fechar e reabrir sozinho em instantes. Seus dados são preservados."),
    ]),
    actions: [],
  });
  try {
    const r = await window.pywebview.api.install_update(info.asset_url);
    if (!r || !r.ok) {
      close();
      toast(((r && r.error) || "Não foi possível atualizar.") + " Abrindo o GitHub para baixar manualmente.", "err");
      openExternal(info.url);
    }
    // Se deu certo, o app fecha sozinho — nada mais a fazer aqui.
  } catch (e) {
    close();
    toast("Falha na atualização: " + (e.message || e) + " Abrindo o GitHub.", "err");
    openExternal(info.url);
  }
}
