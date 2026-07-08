// Telas de Pacientes: lista, cadastro/edicao e detalhe (com fichas).

import { api } from "../api.js";
import { h, clear, toast, confirmar, iniciais, fmtData, calcIdade, fmtDataHora } from "../util.js";
import { exportarFicha } from "./export.js";

function queryParams() {
  const q = (location.hash.split("?")[1] || "");
  return Object.fromEntries(new URLSearchParams(q));
}

// ---------------- Lista ----------------
// Lista de pacientes com busca. Modo "nova ficha" inicia uma anamnese ao clicar.
export async function renderPatients(container) {
  const nova = queryParams().nova === "1";

  const head = h("div", { class: "page-head" }, [
    h("button", { class: "back-link", onClick: () => (location.hash = "#/") }, "← Início"),
    h("h1", {}, nova ? "Nova anamnese" : "Pacientes"),
    h("div", { class: "spacer" }),
    h("button", { class: "btn", onClick: () => (location.hash = "#/paciente/novo" + (nova ? "?nova=1" : "")) }, "＋ Novo paciente"),
  ]);
  container.appendChild(head);

  if (nova) {
    container.appendChild(h("div", { class: "notice", style: "margin-bottom:16px" }, [
      h("div", { class: "notice-text" }, "Selecione o paciente para iniciar a ficha — ou cadastre um novo."),
    ]));
  }

  const search = h("input", { class: "search", type: "text", placeholder: "🔎 Buscar por nome..." });
  container.appendChild(h("div", { class: "toolbar" }, [search]));

  const listEl = h("div", { class: "list" });
  container.appendChild(listEl);

  async function load() {
    clear(listEl);
    let patients = [];
    try { patients = await api.listPatients(search.value.trim()); }
    catch (e) { toast(e.message, "err"); return; }
    if (!patients.length) {
      listEl.appendChild(h("div", { class: "empty" }, [
        h("div", { class: "empty-icon" }, "👶"),
        h("div", {}, search.value ? "Nenhum paciente encontrado." : "Nenhum paciente cadastrado ainda."),
      ]));
      return;
    }
    for (const p of patients) listEl.appendChild(patientRow(p, nova));
  }

  let t;
  search.addEventListener("input", () => { clearTimeout(t); t = setTimeout(load, 250); });
  await load();
}

function patientRow(p, nova) {
  const sub = [
    p.age ? p.age : null,
    p.sex ? (p.sex === "F" ? "Feminino" : "Masculino") : null,
    `${p.anamneses_count} ficha(s)`,
  ].filter(Boolean).join("  ·  ");

  const onOpen = nova
    ? async () => { try { const a = await api.createAnamnesis(p.id); location.hash = "#/ficha/" + a.id; } catch (e) { toast(e.message, "err"); } }
    : () => (location.hash = "#/paciente/" + p.id);

  return h("div", { class: "list-item", onClick: onOpen }, [
    h("div", { class: "avatar" }, iniciais(p.name)),
    h("div", { class: "li-main" }, [
      h("div", { class: "li-title" }, p.name || "(sem nome)"),
      h("div", { class: "li-sub" }, sub),
    ]),
    nova
      ? h("button", { class: "btn-sm btn" }, "Iniciar ficha")
      : h("span", { class: "muted", style: "font-size:20px" }, "›"),
  ]);
}

// ---------------- Cadastro / edicao ----------------
// Formulário de cadastro/edição do paciente (idade calculada ao digitar a data).
export async function renderPatientForm(container, id) {
  const nova = queryParams().nova === "1";
  let p = { name: "", birth_date: "", sex: "", phones: "", notes: "" };
  if (id) { try { p = await api.getPatient(id); } catch (e) { toast(e.message, "err"); } }

  const back = () => (location.hash = id ? "#/paciente/" + id : "#/pacientes" + (nova ? "?nova=1" : ""));

  container.appendChild(h("div", { class: "page-head" }, [
    h("button", { class: "back-link", onClick: back }, "← Voltar"),
    h("h1", {}, id ? "Editar paciente" : "Novo paciente"),
  ]));

  const nameI = h("input", { type: "text", value: p.name || "", placeholder: "Nome completo" });
  const birthI = h("input", { type: "date", value: p.birth_date || "" });
  const ageEl = h("div", { class: "hint" }, p.birth_date ? "Idade: " + calcIdade(p.birth_date) : "");
  birthI.addEventListener("input", () => { ageEl.textContent = birthI.value ? "Idade: " + calcIdade(birthI.value) : ""; });
  const sexF = h("input", { type: "radio", name: "sex", value: "F" });
  const sexM = h("input", { type: "radio", name: "sex", value: "M" });
  if (p.sex === "F") sexF.checked = true;
  if (p.sex === "M") sexM.checked = true;
  const phonesI = h("input", { type: "text", value: p.phones || "", placeholder: "Telefones de contato" });
  const notesI = h("textarea", { rows: "3", placeholder: "Observações" }, p.notes || "");

  const card = h("div", { class: "card" }, [
    h("div", { class: "field" }, [h("label", {}, "Nome"), nameI]),
    h("div", { class: "form-row w-2" }, [
      h("div", { class: "field" }, [h("label", {}, "Data de nascimento"), birthI, ageEl]),
      h("div", { class: "field" }, [h("label", {}, "Sexo"),
        h("div", { class: "choices" }, [
          h("label", { class: "choice" }, [sexF, "Feminino"]),
          h("label", { class: "choice" }, [sexM, "Masculino"]),
        ]),
      ]),
    ]),
    h("div", { class: "field" }, [h("label", {}, "Telefones"), phonesI]),
    h("div", { class: "field" }, [h("label", {}, "Observações"), notesI]),
    h("div", { class: "form-actions" }, [
      h("button", {
        class: "btn",
        onClick: async () => {
          const data = {
            name: nameI.value.trim(),
            birth_date: birthI.value || null,
            sex: sexF.checked ? "F" : sexM.checked ? "M" : null,
            phones: phonesI.value.trim() || null,
            notes: notesI.value.trim() || null,
          };
          if (!data.name) { toast("Informe o nome do paciente.", "err"); return; }
          try {
            const saved = id ? await api.updatePatient(id, data) : await api.createPatient(data);
            toast("Paciente salvo.", "ok");
            if (nova && !id) { const a = await api.createAnamnesis(saved.id); location.hash = "#/ficha/" + a.id; }
            else location.hash = "#/paciente/" + saved.id;
          } catch (e) { toast(e.message, "err"); }
        },
      }, "Salvar"),
      h("button", { class: "btn-ghost", onClick: back }, "Cancelar"),
    ]),
  ]);
  container.appendChild(card);
}

// ---------------- Detalhe + fichas ----------------
// Detalhe do paciente: dados + lista de fichas (abrir, duplicar, exportar, excluir).
export async function renderPatientDetail(container, id) {
  let p;
  try { p = await api.getPatient(id); } catch (e) { toast(e.message, "err"); location.hash = "#/pacientes"; return; }

  container.appendChild(h("div", { class: "page-head" }, [
    h("button", { class: "back-link", onClick: () => (location.hash = "#/pacientes") }, "← Pacientes"),
    h("h1", {}, p.name || "(sem nome)"),
    h("div", { class: "spacer" }),
    h("button", { class: "btn-outline btn-sm", onClick: () => (location.hash = "#/paciente/" + id + "/editar") }, "✎ Editar"),
    h("button", {
      class: "btn-danger btn-sm",
      onClick: async () => {
        if (!(await confirmar({ title: "Excluir paciente", message: `Excluir "${p.name}" e todas as suas fichas? Esta ação não pode ser desfeita.`, okLabel: "Excluir", danger: true }))) return;
        try { await api.deletePatient(id); toast("Paciente excluído.", "ok"); location.hash = "#/pacientes"; }
        catch (e) { toast(e.message, "err"); }
      },
    }, "🗑 Excluir"),
  ]));

  const info = [
    p.age ? `Idade: ${p.age}` : null,
    p.birth_date ? `Nascimento: ${fmtData(p.birth_date)}` : null,
    p.sex ? `Sexo: ${p.sex === "F" ? "Feminino" : "Masculino"}` : null,
    p.phones ? `Telefones: ${p.phones}` : null,
  ].filter(Boolean);
  container.appendChild(h("div", { class: "card", style: "margin-bottom:22px" }, [
    h("div", {}, info.map((t) => h("div", { class: "li-sub", style: "font-size:14px;color:var(--text)" }, t))),
    p.notes ? h("div", { style: "margin-top:8px" }, [h("div", { class: "muted", style: "font-size:12px" }, "Observações"), h("div", {}, p.notes)]) : null,
  ]));

  const bar = h("div", { class: "section-progress" }, [
    h("h2", { style: "font-size:18px;color:var(--terracota);margin:0" }, "Fichas de anamnese"),
    h("button", {
      class: "btn",
      onClick: async () => { try { const a = await api.createAnamnesis(id); location.hash = "#/ficha/" + a.id; } catch (e) { toast(e.message, "err"); } },
    }, "＋ Nova anamnese"),
  ]);
  container.appendChild(bar);

  const listEl = h("div", { class: "list" });
  container.appendChild(listEl);

  async function loadFichas() {
    clear(listEl);
    const fichas = await api.listAnamneses(id);
    if (!fichas.length) {
      listEl.appendChild(h("div", { class: "empty" }, [h("div", { class: "empty-icon" }, "📄"), h("div", {}, "Nenhuma ficha ainda. Clique em “Nova anamnese”.")]));
      return;
    }
    for (const f of fichas) listEl.appendChild(fichaRow(f, loadFichas));
  }
  await loadFichas();
}

function fichaRow(f, reload) {
  const badge = f.status === "concluida"
    ? h("span", { class: "badge badge-done" }, "Concluída")
    : h("span", { class: "badge badge-draft" }, "Rascunho");
  const missing = f.missing_total > 0 ? h("span", { class: "badge badge-missing", title: "Campos vazios" }, f.missing_total + " vazios") : null;

  return h("div", { class: "list-item" }, [
    h("div", { class: "li-main", onClick: () => (location.hash = "#/ficha/" + f.id), style: "cursor:pointer" }, [
      h("div", { class: "li-title" }, [badge, " ", missing]),
      h("div", { class: "li-sub" }, "Atualizada em " + fmtDataHora(f.updated_at)),
    ]),
    h("div", { class: "li-actions" }, [
      h("button", { class: "btn-ghost btn-sm", title: "Abrir", onClick: () => (location.hash = "#/ficha/" + f.id) }, "Abrir"),
      h("button", { class: "btn-ghost btn-sm", title: "Exportar PDF", onClick: () => exportarFicha(f.id) }, "PDF"),
      h("button", {
        class: "btn-ghost btn-sm", title: "Duplicar",
        onClick: async () => { try { await api.duplicateAnamnesis(f.id); toast("Ficha duplicada.", "ok"); reload(); } catch (e) { toast(e.message, "err"); } },
      }, "Duplicar"),
      h("button", {
        class: "btn-ghost btn-sm", title: "Excluir",
        onClick: async () => {
          if (!(await confirmar({ title: "Excluir ficha", message: "Excluir esta ficha? Esta ação não pode ser desfeita.", okLabel: "Excluir", danger: true }))) return;
          try { await api.deleteAnamnesis(f.id); toast("Ficha excluída.", "ok"); reload(); } catch (e) { toast(e.message, "err"); }
        },
      }, "🗑"),
    ]),
  ]);
}
