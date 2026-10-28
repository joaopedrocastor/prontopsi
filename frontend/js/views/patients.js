// Módulo Clientes: listagem em tabela e "Ficha de Cliente" completa
// (Principal + timeline, Cadastro, Anamnese, Sessões, Documentos, Financeiro).

import { api } from "../api.js";
import { openExternal, baixar } from "../store.js";
import { h, clear, toast, confirmar, modal, iniciais, fmtData, calcIdade, fmtDataHora } from "../util.js";
import { exportarFicha } from "./export.js";

// Situações possíveis do cliente (rótulo + cores do badge).
const STATUS = {
  ativo: { label: "Ativo", bg: "#E1F1E9", fg: "#2E8B63" },
  espera: { label: "Lista de espera", bg: "#FBECD9", fg: "#C8791E" },
  alta: { label: "Alta", bg: "#E4F1F3", fg: "#0E7C8A" },
  desativado: { label: "Desativado", bg: "#ECEFF1", fg: "#7E8B93" },
  desistente: { label: "Desistente", bg: "#FBE3DF", fg: "#C4432F" },
};
function statusBadge(st) {
  const s = STATUS[st] || STATUS.ativo;
  return h("span", { class: "badge", style: `background:${s.bg};color:${s.fg}` }, s.label);
}
function queryParams() {
  return Object.fromEntries(new URLSearchParams(location.hash.split("?")[1] || ""));
}

// ==================== Listagem (tabela) ====================
export async function renderPatients(container) {
  const nova = queryParams().nova === "1";

  container.appendChild(h("div", { class: "page-head" }, [
    h("h1", {}, nova ? "Nova anamnese — escolha o cliente" : "Clientes"),
    h("div", { class: "spacer" }),
    h("button", { class: "btn", onClick: () => (location.hash = "#/paciente/novo" + (nova ? "?nova=1" : "")) }, "＋ Adicionar cliente"),
  ]));

  const statusSel = h("select", { style: "width:auto;min-width:180px" }, [
    h("option", { value: "todos" }, "Todos os status"),
    ...Object.entries(STATUS).map(([k, v]) => h("option", { value: k }, v.label)),
  ]);
  const search = h("input", { class: "search", type: "text", placeholder: "🔎 Pesquisar por nome ou e-mail..." });
  container.appendChild(h("div", { class: "toolbar" }, [
    h("label", { class: "muted", style: "font-size:13px" }, "Status:"), statusSel, search,
  ]));

  const tableWrap = h("div", {});
  container.appendChild(tableWrap);

  async function load() {
    clear(tableWrap);
    let patients = [];
    try { patients = await api.listPatients(search.value.trim(), statusSel.value === "todos" ? "" : statusSel.value); }
    catch (e) { toast(e.message, "err"); return; }
    if (!patients.length) {
      tableWrap.appendChild(h("div", { class: "empty" }, [
        h("div", { class: "empty-icon" }, "👥"),
        h("div", {}, search.value || statusSel.value !== "todos" ? "Nenhum cliente encontrado." : "Nenhum cliente cadastrado ainda."),
      ]));
      return;
    }
    tableWrap.appendChild(clientTable(patients, nova));
  }

  let t;
  search.addEventListener("input", () => { clearTimeout(t); t = setTimeout(load, 250); });
  statusSel.addEventListener("change", load);
  await load();
}

function clientTable(patients, nova) {
  const rows = patients.map((p) => {
    const open = nova
      ? async () => { try { const a = await api.createAnamnesis(p.id); location.hash = "#/ficha/" + a.id; } catch (e) { toast(e.message, "err"); } }
      : () => (location.hash = "#/paciente/" + p.id);
    return h("tr", {}, [
      h("td", {}, [
        h("div", { class: "cell-name", onClick: open }, [
          h("span", { class: "avatar sm" }, iniciais(p.name)),
          h("span", { class: "link-name" }, p.name || "(sem nome)"),
        ]),
      ]),
      h("td", {}, statusBadge(p.status)),
      h("td", { class: "muted" }, p.email || "—"),
      h("td", { class: "muted" }, p.phones || "—"),
      h("td", { class: "muted" }, fmtDataHora(p.created_at)),
      h("td", {}, h("div", { class: "row-actions" }, [
        nova
          ? h("button", { class: "btn btn-sm", onClick: open }, "Iniciar ficha")
          : h("button", { class: "btn-outline btn-sm", onClick: open }, "Abrir"),
      ])),
    ]);
  });
  const table = h("table", { class: "ctable" }, [
    h("thead", {}, h("tr", {}, ["Nome do cliente", "Status", "E-mail", "Telefone", "Data de cadastro", "Ações"].map((t) => h("th", {}, t)))),
    h("tbody", {}, rows),
  ]);
  return h("div", { class: "table-wrap" }, [table]);
}

// ==================== Cadastro (criar) ====================
export async function renderPatientForm(container, id) {
  const nova = queryParams().nova === "1";
  let p = { name: "", birth_date: "", sex: "", phones: "", email: "", status: "ativo", notes: "" };
  if (id) { try { p = await api.getPatient(id); } catch (e) { toast(e.message, "err"); } }
  const back = () => (location.hash = id ? "#/paciente/" + id : "#/pacientes" + (nova ? "?nova=1" : ""));

  container.appendChild(h("div", { class: "page-head" }, [
    h("button", { class: "back-link", onClick: back }, "← Voltar"),
    h("h1", {}, id ? "Editar cliente" : "Novo cliente"),
  ]));

  const form = buildPatientForm(p);
  container.appendChild(h("div", { class: "card" }, [
    form.node,
    h("div", { class: "form-actions" }, [
      h("button", {
        class: "btn",
        onClick: async () => {
          const data = form.getData();
          if (!data.name) { toast("Informe o nome do cliente.", "err"); return; }
          try {
            const saved = id ? await api.updatePatient(id, data) : await api.createPatient(data);
            toast("Cliente salvo.", "ok");
            if (nova && !id) { const a = await api.createAnamnesis(saved.id); location.hash = "#/ficha/" + a.id; }
            else location.hash = "#/paciente/" + saved.id;
          } catch (e) { toast(e.message, "err"); }
        },
      }, "Salvar"),
      h("button", { class: "btn-ghost", onClick: back }, "Cancelar"),
    ]),
  ]));
}

// Monta os campos do cadastro e devolve node + getData() (reusado em 2 lugares).
function buildPatientForm(p) {
  const nameI = h("input", { type: "text", value: p.name || "", placeholder: "Nome completo" });
  const birthI = h("input", { type: "date", value: p.birth_date || "" });
  const ageEl = h("div", { class: "hint" }, p.birth_date ? "Idade: " + calcIdade(p.birth_date) : "");
  birthI.addEventListener("input", () => { ageEl.textContent = birthI.value ? "Idade: " + calcIdade(birthI.value) : ""; });
  const sexF = h("input", { type: "radio", name: "sex", value: "F" });
  const sexM = h("input", { type: "radio", name: "sex", value: "M" });
  if (p.sex === "F") sexF.checked = true;
  if (p.sex === "M") sexM.checked = true;
  const statusSel = h("select", {}, Object.entries(STATUS).map(([k, v]) => h("option", { value: k }, v.label)));
  statusSel.value = p.status || "ativo";
  const phonesI = h("input", { type: "text", value: p.phones || "", placeholder: "Telefones de contato" });
  const emailI = h("input", { type: "email", value: p.email || "", placeholder: "email@exemplo.com" });
  const notesI = h("textarea", { rows: "3", placeholder: "Observações" }, p.notes || "");

  const node = h("div", {}, [
    h("div", { class: "field" }, [h("label", {}, "Nome"), nameI]),
    h("div", { class: "form-row w-2" }, [
      h("div", { class: "field" }, [h("label", {}, "Data de nascimento"), birthI, ageEl]),
      h("div", { class: "field" }, [h("label", {}, "Situação"), statusSel]),
    ]),
    h("div", { class: "field" }, [h("label", {}, "Sexo"),
      h("div", { class: "choices" }, [
        h("label", { class: "choice" }, [sexF, "Feminino"]),
        h("label", { class: "choice" }, [sexM, "Masculino"]),
      ]),
    ]),
    h("div", { class: "form-row w-2" }, [
      h("div", { class: "field" }, [h("label", {}, "Telefones"), phonesI]),
      h("div", { class: "field" }, [h("label", {}, "E-mail"), emailI]),
    ]),
    h("div", { class: "field" }, [h("label", {}, "Observações"), notesI]),
  ]);
  const getData = () => ({
    name: nameI.value.trim(),
    birth_date: birthI.value || null,
    sex: sexF.checked ? "F" : sexM.checked ? "M" : null,
    status: statusSel.value,
    phones: phonesI.value.trim() || null,
    email: emailI.value.trim() || null,
    notes: notesI.value.trim() || null,
  });
  return { node, getData };
}

// ==================== Ficha de Cliente (detalhe) ====================
const SECOES = [
  { id: "principal", label: "Principal", icon: "👤" },
  { id: "cadastro", label: "Cadastro", icon: "📝" },
  { id: "anamnese", label: "Anamnese", icon: "📋" },
  { id: "sessoes", label: "Sessões realizadas", icon: "🗓️" },
  { id: "prontuario", label: "Prontuário", icon: "📖" },
  { id: "documentos", label: "Documentos", icon: "📎" },
  { id: "financeiro", label: "Financeiro", icon: "💰" },
];

// Formata valor em reais (R$ 1.234,56).
function fmtMoeda(v) { return (v || 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" }); }
function hojeISOd() { const d = new Date(); const p = (n) => String(n).padStart(2, "0"); return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`; }

export async function renderPatientDetail(container, id) {
  let p;
  try { p = await api.getPatient(id); } catch (e) { toast(e.message, "err"); location.hash = "#/pacientes"; return; }
  let current = queryParams().sec || "principal";

  container.appendChild(h("div", { class: "page-head" }, [
    h("button", { class: "back-link", onClick: () => (location.hash = "#/pacientes") }, "← Clientes"),
    h("div", { class: "spacer" }),
    h("button", {
      class: "btn-danger btn-sm",
      onClick: async () => {
        if (!(await confirmar({ title: "Excluir cliente", message: `Excluir "${p.name}" e todas as suas fichas, sessões e documentos? Não pode ser desfeito.`, okLabel: "Excluir", danger: true }))) return;
        try { await api.deletePatient(id); toast("Cliente excluído.", "ok"); location.hash = "#/pacientes"; }
        catch (e) { toast(e.message, "err"); }
      },
    }, "🗑 Excluir"),
  ]));

  // Cabeçalho do cliente
  container.appendChild(h("div", { class: "cli-head" }, [
    h("span", { class: "avatar lg" }, iniciais(p.name)),
    h("div", {}, [
      h("div", { class: "cli-name" }, [p.name || "(sem nome)", " ", statusBadge(p.status)]),
      h("div", { class: "cli-meta" }, [
        p.age ? p.age : null, p.sex ? (p.sex === "F" ? "Feminino" : "Masculino") : null,
        p.phones || null, p.email || null,
      ].filter(Boolean).join("  ·  ")),
    ]),
  ]));

  // Sub-menu + conteúdo
  const nav = h("div", { class: "cli-nav" });
  const content = h("div", { class: "cli-content" });
  container.appendChild(h("div", { class: "cli-layout" }, [nav, content]));

  function renderNav() {
    clear(nav);
    SECOES.forEach((s) => {
      nav.appendChild(h("button", {
        class: "cli-item" + (s.id === current ? " active" : ""),
        onClick: () => { current = s.id; renderNav(); renderSection(); },
      }, [h("span", { class: "ic" }, s.icon), s.label, s.soon ? h("span", { class: "tag-soon" }, "em breve") : null]));
    });
  }

  async function renderSection() {
    clear(content);
    if (current === "principal") await secPrincipal(content, p);
    else if (current === "cadastro") await secCadastro(content, id, () => renderPatientDetail(container, id));
    else if (current === "anamnese") await secAnamnese(content, id, p);
    else if (current === "sessoes") await secSessoes(content, id);
    else if (current === "prontuario") await secProntuario(content, id, p);
    else if (current === "documentos") await secDocumentos(content, id);
    else if (current === "financeiro") await secFinanceiro(content, id, p);
  }

  renderNav();
  await renderSection();
}

// ----- Principal: resumo + timeline de anotações -----
async function secPrincipal(content, p) {
  content.appendChild(h("div", { class: "panel", style: "margin-bottom:18px" }, [
    h("div", { class: "panel-head" }, [h("h2", {}, "🧾 Dados principais")]),
    h("div", { class: "panel-body", style: "padding:16px" }, [
      infoLine("Nascimento", p.birth_date ? fmtData(p.birth_date) + (p.age ? `  (${p.age})` : "") : "—"),
      infoLine("Sexo", p.sex === "F" ? "Feminino" : p.sex === "M" ? "Masculino" : "—"),
      infoLine("Telefones", p.phones || "—"),
      infoLine("E-mail", p.email || "—"),
      infoLine("Cadastro", fmtDataHora(p.created_at)),
      p.notes ? infoLine("Observações", p.notes) : null,
    ]),
  ]));

  // Timeline
  const tl = h("div", { class: "panel" }, [
    h("div", { class: "panel-head" }, [h("h2", {}, "🕒 Timeline de anotações"), h("button", { class: "btn btn-sm", id: "add-note" }, "＋ Nova anotação")]),
    h("div", { class: "panel-body", id: "tl-body" }, [h("div", { class: "muted", style: "padding:16px" }, "Carregando...")]),
  ]);
  content.appendChild(tl);
  const body = tl.querySelector("#tl-body");
  tl.querySelector("#add-note").addEventListener("click", () => openNoteEditor(p.id, null, () => loadTimeline(body, p.id)));
  await loadTimeline(body, p.id);
}

async function loadTimeline(body, patientId) {
  clear(body);
  let notes = [];
  try { notes = await api.listNotes(patientId); } catch (e) { toast(e.message, "err"); return; }
  if (!notes.length) { body.appendChild(h("div", { class: "empty", style: "padding:30px" }, [h("div", { class: "empty-icon" }, "📝"), h("div", { class: "muted" }, "Nenhuma anotação ainda.")])); return; }
  const tl = h("div", { class: "timeline" });
  for (const n of notes) {
    tl.appendChild(h("div", { class: "tl-item" }, [
      h("div", { class: "tl-dot" }),
      h("div", { class: "tl-card" }, [
        h("div", { class: "tl-top" }, [
          h("span", { class: "tl-date" }, fmtData(n.date)),
          n.title ? h("strong", { class: "tl-title" }, n.title) : null,
          h("span", { class: "spacer", style: "flex:1" }),
          h("button", { class: "icon-btn", title: "Editar", onClick: () => openNoteEditor(patientId, n, () => loadTimeline(body, patientId)) }, "✎"),
          h("button", { class: "icon-btn", title: "Excluir", onClick: async () => { if (await confirmar({ title: "Excluir anotação", message: "Excluir esta anotação?", okLabel: "Excluir", danger: true })) { await api.deleteNote(n.id); loadTimeline(body, patientId); } } }, "🗑"),
        ]),
        n.text ? h("div", { class: "tl-text" }, n.text) : null,
      ]),
    ]));
  }
  body.appendChild(tl);
}

// Modal para criar/editar uma anotação da timeline.
function openNoteEditor(patientId, note, reload) {
  const dateI = h("input", { type: "date", value: note ? note.date : new Date().toISOString().slice(0, 10) });
  const titleI = h("input", { type: "text", value: note ? (note.title || "") : "", placeholder: "Título (opcional)" });
  const textI = h("textarea", { rows: "5", placeholder: "Anotação..." }, note ? note.text : "");
  const content = h("div", {}, [
    h("div", { class: "form-row w-2" }, [
      h("div", { class: "field" }, [h("label", {}, "Data"), dateI]),
      h("div", { class: "field" }, [h("label", {}, "Título"), titleI]),
    ]),
    h("div", { class: "field" }, [h("label", {}, "Anotação"), textI]),
  ]);
  modal({
    title: note ? "Editar anotação" : "Nova anotação",
    content,
    actions: [
      { label: "Cancelar", class: "btn-ghost" },
      { label: "Salvar", class: "btn", onClick: async (close) => {
        const data = { date: dateI.value, title: titleI.value.trim() || null, text: textI.value.trim() };
        try { if (note) await api.updateNote(note.id, data); else await api.createNote(patientId, data); close(); toast("Anotação salva.", "ok"); reload(); }
        catch (e) { toast(e.message, "err"); } },
      },
    ],
  });
}

// ----- Cadastro (editar inline) -----
async function secCadastro(content, id, reload) {
  let p;
  try { p = await api.getPatient(id); } catch (e) { toast(e.message, "err"); return; }
  const form = buildPatientForm(p);
  content.appendChild(h("div", { class: "card" }, [
    form.node,
    h("div", { class: "form-actions" }, [
      h("button", { class: "btn", onClick: async () => {
        const data = form.getData();
        if (!data.name) { toast("Informe o nome.", "err"); return; }
        try { await api.updatePatient(id, data); toast("Cadastro atualizado.", "ok"); reload(); }
        catch (e) { toast(e.message, "err"); }
      } }, "Salvar alterações"),
    ]),
  ]));
}

// ----- Anamnese (fichas do cliente) -----
async function secAnamnese(content, id, p) {
  content.appendChild(h("div", { class: "section-progress" }, [
    h("h2", { style: "font-size:17px;color:var(--navy);margin:0" }, "Fichas de anamnese"),
    h("button", { class: "btn", onClick: async () => { try { const a = await api.createAnamnesis(id); location.hash = "#/ficha/" + a.id; } catch (e) { toast(e.message, "err"); } } }, "＋ Nova anamnese"),
  ]));
  const list = h("div", { class: "list" });
  content.appendChild(list);
  const fichas = await api.listAnamneses(id);
  if (!fichas.length) { list.appendChild(h("div", { class: "empty" }, [h("div", { class: "empty-icon" }, "📋"), h("div", { class: "muted" }, "Nenhuma ficha ainda.")])); return; }
  for (const f of fichas) {
    const badge = f.status === "concluida" ? h("span", { class: "badge badge-done" }, "Concluída") : h("span", { class: "badge badge-draft" }, "Rascunho");
    const miss = f.missing_total > 0 ? h("span", { class: "badge badge-missing" }, f.missing_total + " vazios") : null;
    list.appendChild(h("div", { class: "list-item" }, [
      h("div", { class: "li-main", style: "cursor:pointer", onClick: () => (location.hash = "#/ficha/" + f.id) }, [
        h("div", { class: "li-title" }, [badge, " ", miss]),
        h("div", { class: "li-sub" }, "Atualizada em " + fmtDataHora(f.updated_at)),
      ]),
      h("div", { class: "li-actions" }, [
        h("button", { class: "btn-ghost btn-sm", onClick: () => (location.hash = "#/ficha/" + f.id) }, "Abrir"),
        h("button", { class: "btn-ghost btn-sm", onClick: () => exportarFicha(f.id) }, "PDF"),
        h("button", { class: "btn-ghost btn-sm", onClick: async () => { await api.duplicateAnamnesis(f.id); toast("Duplicada.", "ok"); secAnamnese(clearReturn(content), id, p); } }, "Duplicar"),
        h("button", { class: "btn-ghost btn-sm", onClick: async () => { if (await confirmar({ title: "Excluir ficha", message: "Excluir esta ficha?", okLabel: "Excluir", danger: true })) { await api.deleteAnamnesis(f.id); secAnamnese(clearReturn(content), id, p); } } }, "🗑"),
      ]),
    ]));
  }
}
function clearReturn(el) { clear(el); return el; }

// ----- Sessões realizadas -----
async function secSessoes(content, id) {
  content.appendChild(h("h2", { style: "font-size:17px;color:var(--navy);margin:0 0 14px" }, "Sessões"));
  const list = h("div", { class: "list" });
  content.appendChild(list);
  let sess = [];
  try { sess = await api.listAppointmentsByPatient(id); } catch (e) { toast(e.message, "err"); return; }
  sess = sess.slice().reverse(); // mais recentes primeiro
  if (!sess.length) { list.appendChild(h("div", { class: "empty" }, [h("div", { class: "empty-icon" }, "🗓️"), h("div", { class: "muted" }, "Nenhuma sessão registrada. Agende na Agenda.")])); return; }
  const stLabel = { agendada: "Agendada", confirmada: "Confirmada", realizada: "Realizada", cancelada: "Cancelada", faltou: "Faltou" };
  const reload = () => secSessoes(clearReturn(content), id);
  for (const a of sess) {
    const temEvo = !!(a.evolution && a.evolution.trim());
    list.appendChild(h("div", { class: "list-item" }, [
      h("div", { class: "up-when", style: "min-width:96px" }, [h("div", { class: "d" }, fmtDataHora(a.start_at)), h("div", { class: "t", style: "font-size:15px" }, a.start_at.slice(11, 16))]),
      h("div", { class: "li-main" }, [
        h("div", { class: "li-title" }, [h("span", { class: "badge badge-soon" }, stLabel[a.status] || a.status), a.modality ? "  " + a.modality : "", temEvo ? h("span", { class: "badge badge-done", style: "margin-left:6px" }, "📖 Evolução") : null]),
        a.notes ? h("div", { class: "li-sub" }, a.notes) : h("div", { class: "li-sub muted" }, "Sem anotações"),
      ]),
      h("div", { class: "li-actions" }, [
        h("button", { class: "btn-outline btn-sm", onClick: () => openEvolutionEditor(a, reload) }, temEvo ? "Ver evolução" : "＋ Evolução"),
        h("button", { class: "btn-ghost btn-sm", onClick: () => (location.hash = "#/agenda") }, "Agenda"),
      ]),
    ]));
  }
}

// ----- Prontuário: evoluções clínicas das sessões (mais recente primeiro) -----
async function secProntuario(content, id, p) {
  const reload = () => secProntuario(clearReturn(content), id, p);
  content.appendChild(h("h2", { style: "font-size:17px;color:var(--navy);margin:0 0 6px" }, "Prontuário"));
  content.appendChild(h("p", { class: "muted", style: "font-size:13px;margin:0 0 14px" }, "Evoluções registradas nas sessões, da mais recente para a mais antiga. Clique para editar."));

  let sess = [];
  try { sess = await api.listAppointmentsByPatient(id); } catch (e) { toast(e.message, "err"); return; }
  const comEvo = sess.filter((a) => a.evolution && a.evolution.trim()).sort((a, b) => b.start_at.localeCompare(a.start_at));

  if (!comEvo.length) {
    content.appendChild(h("div", { class: "empty" }, [
      h("div", { class: "empty-icon" }, "📖"),
      h("div", { class: "muted" }, "Nenhuma evolução registrada ainda."),
      h("div", { class: "muted", style: "font-size:13px;margin-top:4px" }, "Abra uma sessão em “Sessões realizadas” e registre a evolução."),
    ]));
    return;
  }
  const list = h("div", { class: "list" });
  content.appendChild(list);
  for (const a of comEvo) {
    list.appendChild(h("div", { class: "pront-card", onClick: () => openEvolutionEditor(a, reload) }, [
      h("div", { class: "pront-head" }, [
        h("span", { class: "tl-date" }, fmtDataHora(a.start_at) + " · " + a.start_at.slice(11, 16)),
        h("span", { class: "icon-btn", title: "Editar" }, "✎"),
      ]),
      h("div", { class: "pront-text" }, a.evolution),
    ]));
  }
}

// Modal para escrever/editar a evolução clínica de uma sessão.
function openEvolutionEditor(appt, reload) {
  const quando = fmtDataHora(appt.start_at) + " às " + appt.start_at.slice(11, 16);
  const textI = h("textarea", { rows: "9", placeholder: "Evolução da sessão (relato clínico, observações, encaminhamentos)..." }, appt.evolution || "");
  modal({
    title: "Evolução — " + quando,
    content: h("div", {}, [
      h("div", { class: "field" }, [h("label", {}, "Registro clínico"), textI]),
      h("p", { class: "muted", style: "font-size:12px;margin:0" }, "Fica no prontuário do cliente e junto da sessão na agenda."),
    ]),
    actions: [
      { label: "Cancelar", class: "btn-ghost" },
      { label: "Salvar", class: "btn", onClick: async (close) => {
        try { await api.updateAppointment(appt.id, { evolution: textI.value }); appt.evolution = textI.value; close(); toast("Evolução salva.", "ok"); reload(); }
        catch (e) { toast(e.message, "err"); }
      } },
    ],
  });
}

// ----- Documentos -----
async function secDocumentos(content, id) {
  const fileInput = h("input", { type: "file", class: "hidden" });
  fileInput.addEventListener("change", async () => {
    const f = fileInput.files[0]; if (!f) return;
    try { await api.uploadDocument(id, f); toast("Documento enviado.", "ok"); secDocumentos(clearReturn(content), id); }
    catch (e) { toast(e.message, "err"); }
  });
  content.appendChild(h("div", { class: "section-progress" }, [
    h("h2", { style: "font-size:17px;color:var(--navy);margin:0" }, "Documentos"),
    h("button", { class: "btn", onClick: () => fileInput.click() }, "⬆ Enviar documento"),
  ]));
  content.appendChild(fileInput);
  const list = h("div", { class: "list" });
  content.appendChild(list);
  let docs = [];
  try { docs = await api.listDocuments(id); } catch (e) { toast(e.message, "err"); return; }
  if (!docs.length) { list.appendChild(h("div", { class: "empty" }, [h("div", { class: "empty-icon" }, "📎"), h("div", { class: "muted" }, "Nenhum documento anexado.")])); return; }
  for (const d of docs) {
    list.appendChild(h("div", { class: "list-item" }, [
      h("span", { class: "avatar sm" }, "📄"),
      h("div", { class: "li-main" }, [h("div", { class: "li-title" }, d.filename), h("div", { class: "li-sub" }, `${fmtDataHora(d.created_at)}  ·  ${(d.size / 1024).toFixed(0)} KB`)]),
      h("div", { class: "li-actions" }, [
        h("button", { class: "btn-outline btn-sm", onClick: () => baixar(api.docUrl(d.id), d.filename) }, "Baixar"),
        h("button", { class: "btn-ghost btn-sm", onClick: async () => { if (await confirmar({ title: "Excluir documento", message: "Excluir este arquivo?", okLabel: "Excluir", danger: true })) { await api.deleteDocument(d.id); secDocumentos(clearReturn(content), id); } } }, "🗑"),
      ]),
    ]));
  }
}

// ----- Financeiro do cliente (lançamentos ligados a este paciente) -----
async function secFinanceiro(content, id, p) {
  const refresh = () => secFinanceiro(clearReturn(content), id, p);

  content.appendChild(h("div", { class: "section-progress" }, [
    h("h2", { style: "font-size:17px;color:var(--navy);margin:0" }, "Financeiro do cliente"),
    h("div", { style: "display:flex;gap:8px" }, [
      h("button", { class: "btn", onClick: () => cobrancaModal(id, p, null, refresh) }, "＋ Cobrança"),
      h("button", { class: "btn-ghost btn-sm", onClick: () => (location.hash = "#/financeiro") }, "Abrir Financeiro"),
    ]),
  ]));

  let items = [];
  try { items = await api.listFinance({ patient_id: id }); } catch (e) { toast(e.message, "err"); return; }

  // Totais (só receitas: cobranças do cliente).
  const rec = items.filter((e) => e.kind === "receita");
  const recebido = rec.filter((e) => e.paid).reduce((s, e) => s + e.amount, 0);
  const aberto = rec.filter((e) => !e.paid).reduce((s, e) => s + e.amount, 0);
  content.appendChild(h("div", { class: "grid grid-3", style: "margin-bottom:16px" }, [
    miniStat("Recebido", fmtMoeda(recebido), "var(--ok)"),
    miniStat("Em aberto", fmtMoeda(aberto), "var(--accent)"),
    miniStat("Total", fmtMoeda(recebido + aberto), "var(--navy)"),
  ]));

  if (!items.length) {
    content.appendChild(h("div", { class: "empty" }, [h("div", { class: "empty-icon" }, "💰"), h("div", { class: "muted" }, "Nenhuma cobrança lançada para este cliente.")]));
    return;
  }

  const list = h("div", { class: "list" });
  content.appendChild(list);
  for (const e of items) {
    const venc = e.due_date < hojeISOd() && !e.paid;
    const badge = e.paid
      ? h("span", { class: "badge badge-done" }, "Pago")
      : venc ? h("span", { class: "badge badge-missing" }, "Vencida") : h("span", { class: "badge badge-draft" }, "Em aberto");
    list.appendChild(h("div", { class: "list-item" }, [
      h("div", { class: "up-when", style: "min-width:90px" }, [h("div", { class: "d" }, fmtData(e.due_date))]),
      h("div", { class: "li-main" }, [
        h("div", { class: "li-title" }, [e.description || "(cobrança)", "  ", badge]),
        h("div", { class: "li-sub muted" }, e.category || (e.kind === "receita" ? "Receita" : "Despesa")),
      ]),
      h("span", { style: `font-weight:700;color:${e.kind === "receita" ? "var(--ok)" : "var(--accent)"}` }, (e.kind === "receita" ? "+ " : "− ") + fmtMoeda(e.amount)),
      h("div", { class: "li-actions" }, [
        h("button", { class: "btn-ghost btn-sm", title: e.paid ? "Marcar não pago" : "Marcar pago", onClick: async () => { try { await api.updateFinance(e.id, { paid: !e.paid }); refresh(); } catch (err) { toast(err.message, "err"); } } }, e.paid ? "↩" : "✓"),
        h("button", { class: "btn-ghost btn-sm", onClick: () => cobrancaModal(id, p, e, refresh) }, "✎"),
        h("button", { class: "btn-ghost btn-sm", onClick: async () => { if (await confirmar({ title: "Excluir lançamento", message: "Excluir esta cobrança?", okLabel: "Excluir", danger: true })) { await api.deleteFinance(e.id); refresh(); } } }, "🗑"),
      ]),
    ]));
  }
}

function miniStat(label, value, color) {
  return h("div", { class: "stat" }, [
    h("div", { class: "st-label" }, label),
    h("div", { class: "st-value", style: `font-size:19px;color:${color}` }, value),
  ]);
}

// Modal de cobrança/lançamento já vinculado ao paciente.
function cobrancaModal(patientId, p, entry, reload) {
  const edit = !!entry;
  const descI = h("input", { type: "text", value: entry ? entry.description : "Sessão", placeholder: "Descrição" });
  const amountI = h("input", { type: "number", step: "0.01", min: "0", value: entry ? entry.amount : "", placeholder: "0,00" });
  const catI = h("input", { type: "text", value: entry ? entry.category : "Consultas", placeholder: "Categoria" });
  const dateI = h("input", { type: "date", value: entry ? entry.due_date : hojeISOd() });
  const paidChk = h("input", { type: "checkbox" }); if (entry && entry.paid) paidChk.checked = true;
  const kindSel = h("select", {}, [h("option", { value: "receita" }, "Receita (cobrança)"), h("option", { value: "despesa" }, "Despesa")]);
  if (entry) kindSel.value = entry.kind;

  modal({
    title: edit ? "Editar lançamento" : `Nova cobrança — ${p.name}`,
    content: h("div", {}, [
      h("div", { class: "field" }, [h("label", {}, "Descrição"), descI]),
      h("div", { class: "form-row w-2" }, [
        h("div", { class: "field" }, [h("label", {}, "Valor (R$)"), amountI]),
        h("div", { class: "field" }, [h("label", {}, "Vencimento"), dateI]),
      ]),
      h("div", { class: "form-row w-2" }, [
        h("div", { class: "field" }, [h("label", {}, "Tipo"), kindSel]),
        h("div", { class: "field" }, [h("label", {}, "Categoria"), catI]),
      ]),
      h("label", { class: "choice" }, [paidChk, h("span", {}, "Já pago / recebido")]),
    ]),
    actions: [
      { label: "Cancelar", class: "btn-ghost" },
      { label: edit ? "Salvar" : "Lançar", class: "btn", onClick: async (close) => {
        const data = {
          kind: kindSel.value, description: descI.value.trim(),
          amount: parseFloat(amountI.value) || 0, category: catI.value.trim(),
          due_date: dateI.value, paid: paidChk.checked, patient_id: patientId,
        };
        if (!data.amount) { toast("Informe o valor.", "err"); return; }
        if (!data.due_date) { toast("Informe o vencimento.", "err"); return; }
        try { if (edit) await api.updateFinance(entry.id, data); else await api.createFinance(data); close(); toast(edit ? "Lançamento salvo." : "Cobrança lançada.", "ok"); reload(); }
        catch (e) { toast(e.message, "err"); }
      } },
    ],
  });
}

function infoLine(label, value) {
  return h("div", { class: "info-line" }, [h("span", { class: "info-k" }, label), h("span", { class: "info-v" }, value)]);
}
