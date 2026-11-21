// Exportacao em PDF: aviso de campos vazios (nao bloqueante) + geracao.
// Tambem a tela "Exportar PDF" da home (escolher ficha da lista).

import { api } from "../api.js";
import { baixar } from "../store.js";
import { h, clear, toast, modal, fmtDataHora } from "../util.js";

function slug(s) {
  return (s || "").trim().replace(/[^a-zA-Z0-9À-ÿ]+/g, "_").replace(/^_+|_+$/g, "").slice(0, 40);
}

// Exporta uma ficha em PDF: primeiro avisa (sem bloquear) sobre campos vazios.
export async function exportarFicha(id) {
  let ficha, patient, missing;
  try {
    ficha = await api.getAnamnesis(id);
    patient = await api.getPatient(ficha.patient_id);
    missing = await api.missing(id);
  } catch (e) { toast(e.message, "err"); return; }

  const nome = patient.name || "ficha";

  if (missing.total > 0) {
    const resumo = missing.sections.map((s) => `${s.title} (${s.missing.length})`).join(", ");
    modal({
      title: "Preenchimento incompleto",
      content: h("div", {}, [
        h("p", {}, `Atenção: ${missing.total} campo(s) não preenchido(s) em ${missing.sections.length} seção(ões).`),
        h("ul", { class: "missing-list" }, missing.sections.map((s) =>
          h("li", {}, [h("b", {}, s.title), ": " + s.missing.join(", ")]))),
        h("p", { class: "muted", style: "margin-top:10px" }, "Você pode continuar mesmo assim — os campos vazios sairão com linhas pontilhadas."),
      ]),
      actions: [
        { label: "Voltar e preencher", class: "btn-ghost" },
        { label: "Continuar mesmo assim", class: "btn", onClick: (close) => { close(); doExport(id, nome); } },
      ],
    });
    return;
  }
  doExport(id, nome);
}

// Gera o PDF da ficha e salva direto na pasta Downloads (sempre PDF).
async function doExport(id, nome) {
  const sug = `anamnese_${slug(nome) || "ficha"}.pdf`;
  toast("Gerando PDF...", "");
  try {
    const path = await baixar(api.pdfUrl(id), sug);
    const arquivo = path ? path.split(/[\\/]/).pop() : sug;
    toast(`PDF salvo na pasta Downloads: ${arquivo}`, "ok");
  } catch (e) { toast(e.message || "Falha ao gerar o PDF.", "err"); }
}

// ---- Tela "Exportar PDF" (lista todas as fichas) ----
export async function renderExport(container) {
  container.appendChild(h("div", { class: "page-head" }, [
    h("button", { class: "back-link", onClick: () => (location.hash = "#/") }, "← Início"),
    h("h1", {}, "Exportar PDF"),
  ]));
  container.appendChild(h("p", { class: "muted", style: "margin-top:-8px" }, "Escolha a ficha que deseja exportar."));

  const listEl = h("div", { class: "list" });
  container.appendChild(listEl);

  let fichas = [];
  try { fichas = await api.listAnamneses(); } catch (e) { toast(e.message, "err"); return; }
  if (!fichas.length) {
    listEl.appendChild(h("div", { class: "empty" }, [h("div", { class: "empty-icon" }, "📄"), h("div", {}, "Nenhuma ficha salva ainda.")]));
    return;
  }
  for (const f of fichas) {
    const badge = f.status === "concluida"
      ? h("span", { class: "badge badge-done" }, "Concluída")
      : h("span", { class: "badge badge-draft" }, "Rascunho");
    listEl.appendChild(h("div", { class: "list-item" }, [
      h("div", { class: "li-main" }, [
        h("div", { class: "li-title" }, f.patient_name || "(sem nome)"),
        h("div", { class: "li-sub" }, ["Atualizada em " + fmtDataHora(f.updated_at) + "  ", badge]),
      ]),
      h("button", { class: "btn btn-sm", onClick: () => exportarFicha(f.id) }, "📄 Exportar"),
    ]));
  }
}
