// Geração de documentos em PDF (recibo, declaração de comparecimento).
// Abre um modal para confirmar/completar os dados e baixa o PDF gerado.

import { api } from "./api.js";
import { h, clear, modal, toast, fmtData } from "./util.js";

function hojeISO() { const d = new Date(); const p = (n) => String(n).padStart(2, "0"); return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`; }
function getCidade() { try { return localStorage.getItem("docCidade") || ""; } catch { return ""; } }
function setCidade(v) { try { localStorage.setItem("docCidade", v || ""); } catch {} }

// Baixa o PDF a partir da Response (blob) com o nome do cabeçalho.
export async function baixarPdf(res, fallbackName) {
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

function getServico() { try { return localStorage.getItem("docServico") || ""; } catch { return ""; } }
function setServico(v) { try { localStorage.setItem("docServico", v || ""); } catch {} }
const SERVICO_PADRAO = "Psicoterapia (Terapia Cognitivo-Comportamental)";

// Tratamento a partir do parentesco do responsável (Mãe -> Sra., Pai -> Sr.).
function tratamentoDe(kinship) {
  const k = (kinship || "").trim().toLowerCase();
  if (/^(m[ãa]e|av[óo]$|avó|tia|madrasta|irm[ãa]$|prima|madrinha)/.test(k)) return "Sra.";
  if (/^(pai|av[ôo]|tio|padrasto|irm[ãa]o|primo|padrinho)/.test(k)) return "Sr.";
  return "";
}

// Baixa o PDF de um recibo já salvo.
export async function baixarRecibo(receipt) {
  try {
    const res = await api.receiptPdf(receipt.id);
    await baixarPdf(res, `Recibo_${String(receipt.number).padStart(3, "0")}.pdf`);
  } catch (e) { toast(e.message || "Falha ao gerar o PDF.", "err"); }
}

// Recibo de prestação de serviços.
//   Novo:   gerarRecibo({ patient_id?, amount?, dates?: ['YYYY-MM-DD'], onSaved? })
//   Editar: gerarRecibo({ receipt, onSaved? })  (mantém o mesmo número)
// O número é automático e contínuo; o recibo fica salvo para reabrir depois.
export async function gerarRecibo(opts = {}) {
  const rec = opts.receipt || null;
  const [settings, patients, prox] = await Promise.all([
    api.getSettings().catch(() => ({})),
    api.listPatients().catch(() => []),
    rec ? null : api.nextReceiptNumber().catch(() => null),
  ]);
  const offices = settings.offices || [];
  const numero = rec ? rec.number : (prox ? prox.next : null);

  const whenI = h("input", { type: "date", value: rec ? rec.issued_on : hojeISO() });

  // Paciente: lista com todos os cadastrados.
  const patSel = h("select", {}, [
    h("option", { value: "" }, "— Selecione o paciente —"),
    ...patients.map((p) => h("option", { value: p.id }, p.name)),
  ]);
  patSel.value = (rec ? rec.patient_id : opts.patient_id) || "";

  // Pagador: responsáveis do paciente escolhido, o próprio paciente ou outra pessoa.
  const titleSel = h("select", {}, [
    h("option", { value: "Sr." }, "Sr."), h("option", { value: "Sra." }, "Sra."), h("option", { value: "" }, "—"),
  ]);
  const payerI = h("input", { type: "text", placeholder: "Nome de quem pagou" });
  const cpfI = h("input", { type: "text", placeholder: "000.000.000-00" });
  const quemSel = h("select", {});
  let guardians = [];
  let patient = null;

  function aplicarPagador() {
    const v = quemSel.value;
    if (v.startsWith("g")) {
      const g = guardians[+v.slice(1)];
      payerI.value = g.name || ""; cpfI.value = g.cpf || ""; titleSel.value = tratamentoDe(g.kinship);
    } else if (v === "p" && patient) {
      payerI.value = patient.name || ""; cpfI.value = "";
      titleSel.value = patient.sex === "F" ? "Sra." : patient.sex === "M" ? "Sr." : "";
    } else {
      payerI.value = ""; cpfI.value = ""; titleSel.value = "Sr.";
    }
  }
  quemSel.addEventListener("change", aplicarPagador);

  // Carrega os responsáveis do paciente; preencher=false mantém o pagador já salvo.
  async function carregarPaciente(preencher) {
    const id = patSel.value;
    patient = patients.find((p) => p.id === id) || null;
    guardians = id ? await api.listGuardians(id).catch(() => []) : [];
    clear(quemSel);
    guardians.forEach((g, i) => quemSel.appendChild(h("option", { value: "g" + i },
      `${g.name}${g.kinship ? " (" + g.kinship + ")" : ""}${g.is_primary ? " ★" : ""}`)));
    if (patient) quemSel.appendChild(h("option", { value: "p" }, `${patient.name} (o próprio paciente)`));
    quemSel.appendChild(h("option", { value: "o" }, "Outra pessoa"));
    if (!preencher) {
      const idx = guardians.findIndex((g) => g.name === rec.payer);
      quemSel.value = idx >= 0 ? "g" + idx : (patient && patient.name === rec.payer ? "p" : "o");
      return;
    }
    const principal = guardians.findIndex((g) => g.is_primary);
    quemSel.value = guardians.length ? "g" + Math.max(0, principal) : (patient ? "p" : "o");
    aplicarPagador();
  }
  patSel.addEventListener("change", () => carregarPaciente(true));

  const amountI = h("input", { type: "number", step: "0.01", min: "0", placeholder: "0,00" });
  const servI = h("input", { type: "text", value: (rec && rec.service) || getServico() || SERVICO_PADRAO });

  // Dias das sessões (uma pessoa pode pagar várias sessões de uma vez).
  const origem = rec ? rec.session_dates : (opts.dates || []);
  const datas = [...new Set(origem.filter(Boolean).map((d) => d.slice(0, 10)))].sort();
  const qtdI = h("input", { type: "number", min: "1", step: "1", value: (rec && rec.sessions) || datas.length || 1 });
  const chips = h("div", { style: "display:flex;flex-wrap:wrap;gap:6px;margin-bottom:6px" });
  const novaI = h("input", { type: "date", style: "width:auto" });
  function desenharDatas() {
    clear(chips);
    if (!datas.length) chips.appendChild(h("span", { class: "muted", style: "font-size:13px" }, "Nenhum dia informado."));
    datas.forEach((d, i) => chips.appendChild(h("span", { class: "badge badge-cat", style: "display:inline-flex;gap:6px;align-items:center" }, [
      fmtData(d),
      h("button", { class: "icon-btn", title: "Remover", style: "padding:0 2px", onClick: () => { datas.splice(i, 1); qtdI.value = datas.length || 1; desenharDatas(); } }, "×"),
    ])));
  }
  desenharDatas();
  const addBtn = h("button", { class: "btn-ghost btn-sm", onClick: () => {
    if (!novaI.value || datas.includes(novaI.value)) return;
    datas.push(novaI.value); datas.sort(); qtdI.value = datas.length; novaI.value = ""; desenharDatas();
  } }, "＋ Adicionar dia");

  // Cidade -> endereço do rodapé.
  const cidade = rec ? rec.city : getCidade();
  const cityCtl = offices.length
    ? h("select", {}, offices.map((o) => h("option", { value: o.city, ...(o.city === cidade ? { selected: "selected" } : {}) }, o.city)))
    : h("input", { type: "text", value: cidade, placeholder: "Cidade" });

  // Valores iniciais.
  if (rec) {
    amountI.value = rec.amount; payerI.value = rec.payer; cpfI.value = rec.payer_cpf;
    titleSel.value = rec.payer_title || "";
    await carregarPaciente(false);
  } else {
    if (opts.amount != null) amountI.value = opts.amount;
    await carregarPaciente(true);
  }

  const numTxt = numero != null ? String(numero).padStart(3, "0") : "—";
  modal({
    title: rec ? `Editar recibo nº ${numTxt}` : "Gerar recibo",
    content: h("div", {}, [
      h("div", { class: "form-row w-2" }, [
        field("Nº do recibo", h("div", { style: "padding:9px 0;font-weight:600" }, [
          numTxt, h("span", { class: "muted", style: "font-weight:400;font-size:12.5px;margin-left:6px" }, rec ? "(mantido)" : "(automático)"),
        ])),
        field("Data do recibo", whenI),
      ]),
      field("Paciente", patSel),
      field("Quem pagou", quemSel),
      h("div", { style: "display:grid;grid-template-columns:90px 1fr 170px;gap:10px" }, [
        field("Tratamento", titleSel), field("Nome", payerI), field("CPF", cpfI),
      ]),
      h("div", { class: "form-row w-2" }, [field("Valor total (R$)", amountI), field("Qtd. de sessões", qtdI)]),
      field("Dias das sessões", h("div", {}, [chips, h("div", { style: "display:flex;gap:8px;align-items:center" }, [novaI, addBtn])])),
      field("Serviço", servI),
      field("Cidade", cityCtl),
      offices.length ? null : h("div", { class: "hint" }, "Dica: cadastre os consultórios em Configuração → Dados do recibo para o endereço sair no rodapé."),
    ]),
    actions: [
      { label: "Cancelar", class: "btn-ghost" },
      { label: rec ? "Salvar e gerar PDF" : "Gerar PDF", class: "btn", onClick: async (close) => {
        const amount = parseFloat(amountI.value) || 0;
        if (!amount) { toast("Informe o valor.", "err"); return; }
        if (!payerI.value.trim()) { toast("Informe quem pagou.", "err"); return; }
        const city = (cityCtl.value || "").trim();
        setCidade(city); setServico(servI.value.trim());
        const p = patients.find((x) => x.id === patSel.value);
        const dados = {
          patient_id: patSel.value || null, patient_name: p ? p.name : "",
          issued_on: whenI.value || hojeISO(),
          payer: payerI.value.trim(), payer_cpf: cpfI.value.trim(), payer_title: titleSel.value,
          amount, sessions: parseInt(qtdI.value, 10) || null, session_dates: datas,
          service: servI.value.trim(), city,
        };
        try {
          const salvo = rec ? await api.updateReceipt(rec.id, dados) : await api.createReceipt(dados);
          await baixarRecibo(salvo);
          close();
          toast(`Recibo nº ${String(salvo.number).padStart(3, "0")} ${rec ? "atualizado" : "gerado e salvo"}.`, "ok");
          if (opts.onSaved) opts.onSaved(salvo);
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
