// Geração de documentos em PDF (recibo, declaração de comparecimento).
// Abre um modal para confirmar/completar os dados e baixa o PDF gerado.

import { api } from "./api.js";
import { h, modal, toast } from "./util.js";

function hojeISO() { const d = new Date(); const p = (n) => String(n).padStart(2, "0"); return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`; }
function getCidade() { try { return localStorage.getItem("docCidade") || ""; } catch { return ""; } }
function setCidade(v) { try { localStorage.setItem("docCidade", v || ""); } catch {} }

// Baixa o PDF a partir da Response (blob) com o nome do cabeçalho.
async function baixarPdf(res, fallbackName) {
  const blob = await res.blob();
  let name = fallbackName;
  const cd = res.headers.get("content-disposition") || "";
  const m = cd.match(/filename\*?=(?:UTF-8''|")?([^";]+)/i);
  if (m) { try { name = decodeURIComponent(m[1]); } catch { name = m[1]; } }
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = name;
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 4000);
}

const field = (label, control) => h("div", { class: "field" }, [h("label", {}, label), control]);

// Recibo de pagamento. opts: { patient_id?, payer?, amount?, reference?, when? }
export function gerarRecibo(opts = {}) {
  const payerI = h("input", { type: "text", value: opts.payer || "", placeholder: "Nome de quem pagou (responsável)" });
  const amountI = h("input", { type: "number", step: "0.01", min: "0", value: opts.amount != null ? opts.amount : "", placeholder: "0,00" });
  const refI = h("input", { type: "text", value: opts.reference || "atendimento psicológico", placeholder: "Referente a..." });
  const cityI = h("input", { type: "text", value: getCidade(), placeholder: "Cidade (opcional)" });
  const dateI = h("input", { type: "date", value: opts.when || hojeISO() });

  modal({
    title: "Gerar recibo",
    content: h("div", {}, [
      field("Pagador (responsável)", payerI),
      h("div", { class: "form-row w-2" }, [field("Valor (R$)", amountI), field("Data", dateI)]),
      field("Referente a", refI),
      field("Cidade", cityI),
    ]),
    actions: [
      { label: "Cancelar", class: "btn-ghost" },
      { label: "Gerar PDF", class: "btn", onClick: async (close) => {
        const amount = parseFloat(amountI.value) || 0;
        if (!amount) { toast("Informe o valor.", "err"); return; }
        setCidade(cityI.value.trim());
        try {
          const res = await api.reciboPdf({
            patient_id: opts.patient_id || null, payer: payerI.value.trim(),
            amount, reference: refI.value.trim(), city: cityI.value.trim(), when: dateI.value,
          });
          await baixarPdf(res, "Recibo.pdf"); close(); toast("Recibo gerado.", "ok");
        } catch (e) { toast(e.message || "Falha ao gerar.", "err"); }
      } },
    ],
  });
}

// Declaração de comparecimento. opts: { patient_id, name?, when?, start?, end? }
export function gerarDeclaracao(opts = {}) {
  const dateI = h("input", { type: "date", value: opts.when || hojeISO() });
  const startI = h("input", { type: "time", value: opts.start || "" });
  const endI = h("input", { type: "time", value: opts.end || "" });
  const cityI = h("input", { type: "text", value: getCidade(), placeholder: "Cidade (opcional)" });
  const extraI = h("textarea", { rows: "2", placeholder: "Texto adicional (opcional)" }, "");

  modal({
    title: "Declaração de comparecimento" + (opts.name ? " — " + opts.name : ""),
    content: h("div", {}, [
      h("div", { class: "form-row w-3" }, [field("Data", dateI), field("Início", startI), field("Fim", endI)]),
      field("Cidade", cityI),
      field("Texto adicional", extraI),
    ]),
    actions: [
      { label: "Cancelar", class: "btn-ghost" },
      { label: "Gerar PDF", class: "btn", onClick: async (close) => {
        if (!dateI.value) { toast("Informe a data.", "err"); return; }
        setCidade(cityI.value.trim());
        try {
          const res = await api.declaracaoPdf({
            patient_id: opts.patient_id, when: dateI.value, start: startI.value,
            end: endI.value, city: cityI.value.trim(), extra: extraI.value.trim(),
          });
          await baixarPdf(res, "Declaracao.pdf"); close(); toast("Declaração gerada.", "ok");
        } catch (e) { toast(e.message || "Falha ao gerar.", "err"); }
      } },
    ],
  });
}
