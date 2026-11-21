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

function mb(n) { return (n / 1048576).toFixed(1).replace(".", ",") + " MB"; }

// Dispara o auto-update pela ponte: baixa o instalador (com barra de progresso),
// instala e reabre. Exportada para testar a tela com a ponte simulada.
export async function instalarAtualizacao(info) {
  const etapa = h("p", { style: "margin:0 0 10px;font-weight:600" }, `Baixando a versão ${info.latest}…`);
  const fill = h("div", { class: "upd-fill" });
  const bar = h("div", { class: "upd-bar" }, fill);
  const detalhe = h("div", { class: "upd-detail" }, "Iniciando…");
  const passos = h("ol", { class: "upd-steps" }, [
    h("li", { class: "on" }, "Baixar a atualização"),
    h("li", {}, "Instalar (o app fecha e aparece a janela do instalador)"),
    h("li", {}, "Reabrir o ProntoPsi sozinho"),
  ]);
  const close = modal({
    title: "Atualizando o ProntoPsi",
    content: h("div", {}, [
      etapa, bar, detalhe, passos,
      h("p", { class: "muted", style: "font-size:13px;margin-top:12px" }, "Não feche o computador. Seus dados são preservados."),
    ]),
    actions: [],
  });

  // Acompanha o andamento enquanto install_update roda (chamadas paralelas na ponte).
  const api = window.pywebview.api;
  const timer = setInterval(async () => {
    let s;
    try { s = await api.update_progress(); } catch { return; }
    if (!s) return;
    if (s.stage === "download") {
      const pct = s.total ? Math.min(100, Math.round((s.done / s.total) * 100)) : 0;
      fill.style.width = (s.total ? pct : 15) + "%";
      detalhe.textContent = s.total ? `${pct}% — ${mb(s.done)} de ${mb(s.total)}` : `${mb(s.done)} baixados`;
    } else if (s.stage === "instalando") {
      fill.style.width = "100%";
      bar.classList.add("upd-indet");
      etapa.textContent = "Download concluído. Instalando…";
      detalhe.textContent = "O app vai fechar agora e reabrir sozinho quando a instalação terminar.";
      passos.children[0].className = "ok";
      passos.children[1].className = "on";
    }
  }, 300);

  try {
    const r = await api.install_update(info.asset_url);
    if (!r || !r.ok) {
      clearInterval(timer);
      close();
      toast(((r && r.error) || "Não foi possível atualizar.") + " Abrindo o GitHub para baixar manualmente.", "err");
      openExternal(info.url);
    }
    else {
      // Deu certo: garante a tela de "Instalando…" (o app fecha em instantes).
      clearInterval(timer);
      fill.style.width = "100%";
      bar.classList.add("upd-indet");
      etapa.textContent = "Download concluído. Instalando…";
      detalhe.textContent = "O app vai fechar agora e reabrir sozinho quando a instalação terminar.";
      passos.children[0].className = "ok";
      passos.children[1].className = "on";
    }
  } catch (e) {
    clearInterval(timer);
    close();
    toast("Falha na atualização: " + (e.message || e) + " Abrindo o GitHub.", "err");
    openExternal(info.url);
  }
}
