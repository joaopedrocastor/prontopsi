// Tela da Ficha de Anamnese: navegacao por secoes, salvamento automatico,
// status, indicador de campos vazios e geracao de PDF.

import { api } from "../api.js";
import { setLeaveHook } from "../app.js";
import { h, clear, toast, debounce, calcIdade } from "../util.js";
import { exportarFicha } from "./export.js";

// Gera o PDF da ficha e salva no Google Drive (na pasta "ProntoPsi - Fichas").
async function salvarNoDrive(id, saveNow, autosave, getSaveState) {
  autosave.cancel();
  if (getSaveState() !== "saved") { try { await saveNow(); } catch {} }
  toast("Enviando para o Google Drive...", "");
  try {
    await api.saveAnamnesisToDrive(id);
    toast("Ficha salva no Google Drive (pasta “ProntoPsi - Fichas”).", "ok");
  } catch (e) { toast(e.message, "err"); }
}

let SCHEMA = null;
async function getSchema() { if (!SCHEMA) SCHEMA = await api.formSchema(); return SCHEMA; }

function isEmpty(v) {
  if (v == null) return true;
  if (typeof v === "string") return v.trim() === "";
  if (Array.isArray(v)) return v.length === 0;
  return false;
}

// Tela da ficha: navegação por seções, salvamento automático e geração de PDF.
export async function renderAnamnesis(container, id) {
  const schema = await getSchema();
  let ficha, patient;
  try {
    ficha = await api.getAnamnesis(id);
    patient = await api.getPatient(ficha.patient_id);
  } catch (e) { toast(e.message, "err"); location.hash = "#/pacientes"; return; }

  const data = { ...(ficha.data || {}) };
  let current = 0;
  let saveState = "saved"; // saved | saving | dirty

  // ---- Salvamento automatico ----
  async function saveNow() {
    saveState = "saving"; renderSaveState();
    try {
      await api.updateAnamnesis(id, { data });
      saveState = "saved";
    } catch (e) { saveState = "dirty"; toast("Falha ao salvar: " + e.message, "err"); }
    renderSaveState();
  }
  const autosave = debounce(saveNow, 700);
  function touch() { saveState = "dirty"; renderSaveState(); autosave(); }

  // Rede de seguranca: se a usuaria FECHAR o app (ou a aba) com algo pendente,
  // envia o rascunho na hora (keepalive funciona durante o fechamento).
  function flushOnClose() {
    if (saveState === "saved") return;
    try {
      fetch("/api/anamneses/" + id, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ data }),
        keepalive: true,
      });
    } catch {}
  }
  window.addEventListener("beforeunload", flushOnClose);
  window.addEventListener("pagehide", flushOnClose);
  document.addEventListener("visibilitychange", () => { if (document.hidden) flushOnClose(); });

  // Ao sair da tela (navegacao interna), garante que nada fique pendente.
  setLeaveHook(() => {
    window.removeEventListener("beforeunload", flushOnClose);
    window.removeEventListener("pagehide", flushOnClose);
    autosave.cancel();
    return saveState !== "saved" ? saveNow() : null;
  });

  // ---- Contagem de campos vazios ----
  function sectionMissing(section) {
    let n = 0;
    for (const f of section.fields) {
      if (f.count_missing === false) continue;
      if (isEmpty(data[f.key])) n++;
    }
    return n;
  }
  function totalMissing() { return schema.sections.reduce((a, s) => a + sectionMissing(s), 0); }

  // ---- Estrutura da pagina ----
  const back = () => (location.hash = "#/paciente/" + ficha.patient_id);
  container.appendChild(h("div", { class: "page-head" }, [
    h("button", { class: "back-link", onClick: back }, "← " + (patient.name || "Paciente")),
    h("div", { class: "spacer" }),
  ]));

  const saveEl = h("span", { class: "save-state" });
  const statusSel = h("select", { style: "width:auto;padding:7px 12px" }, [
    h("option", { value: "rascunho" }, "Rascunho"),
    h("option", { value: "concluida" }, "Concluída"),
  ]);
  statusSel.value = ficha.status;
  statusSel.addEventListener("change", async () => {
    try { await api.updateAnamnesis(id, { status: statusSel.value }); toast("Status atualizado.", "ok"); }
    catch (e) { toast(e.message, "err"); }
  });

  const bar = h("div", { class: "ficha-bar" }, [
    h("strong", { style: "color:var(--terracota)" }, patient.name || "Ficha"),
    saveEl,
    h("div", { class: "spacer" }),
    h("label", { class: "muted", style: "font-size:12.5px" }, "Status:"),
    statusSel,
    h("button", { class: "btn-outline", title: "Salvar o PDF no seu Google Drive", onClick: () => salvarNoDrive(id, saveNow, autosave, () => saveState) }, "☁ Salvar no Drive"),
    h("button", { class: "btn", onClick: async () => { autosave.cancel(); if (saveState !== "saved") await saveNow(); exportarFicha(id); } }, "📄 Gerar PDF"),
  ]);
  container.appendChild(bar);

  function renderSaveState() {
    saveEl.className = "save-state " + (saveState === "saving" ? "saving" : saveState === "saved" ? "saved" : "");
    saveEl.textContent = saveState === "saving" ? "Salvando..." : saveState === "saved" ? "✓ Salvo automaticamente" : "Alterações não salvas";
  }
  renderSaveState();

  // Layout de duas colunas (nav + conteudo)
  const navEl = h("div", { class: "ficha-nav" });
  const mainEl = h("div", { class: "ficha-main" });
  container.appendChild(h("div", { class: "ficha-layout" }, [navEl, mainEl]));

  function renderNav() {
    clear(navEl);
    schema.sections.forEach((s, i) => {
      const miss = sectionMissing(s);
      navEl.appendChild(h("button", {
        class: "nav-item" + (i === current ? " active" : ""),
        onClick: () => { current = i; renderNav(); renderSection(); window.scrollTo(0, 0); },
      }, [
        h("span", {}, s.title.charAt(0) + s.title.slice(1).toLowerCase()),
        miss > 0 ? h("span", { class: "dot" }, String(miss)) : null,
      ]));
    });
  }

  function updateNavDots() {
    // Atualiza apenas os numeros (sem recriar a navegacao inteira).
    const items = navEl.querySelectorAll(".nav-item");
    schema.sections.forEach((s, i) => {
      const item = items[i]; if (!item) return;
      let dot = item.querySelector(".dot");
      const miss = sectionMissing(s);
      if (miss > 0) {
        if (!dot) { dot = h("span", { class: "dot" }); item.appendChild(dot); }
        dot.textContent = String(miss);
      } else if (dot) dot.remove();
    });
  }

  function renderSection() {
    const section = schema.sections[current];
    clear(mainEl);
    mainEl.appendChild(h("div", { class: "section-pill" }, section.title));

    const grid = h("div", {});
    section.fields.forEach((f) => grid.appendChild(renderField(f)));
    mainEl.appendChild(grid);

    // Navegacao inferior
    mainEl.appendChild(h("div", { class: "form-actions", style: "margin-top:22px" }, [
      current > 0 ? h("button", { class: "btn-outline", onClick: () => { current--; renderNav(); renderSection(); window.scrollTo(0, 0); } }, "← Anterior") : null,
      h("div", { class: "spacer" }),
      current < schema.sections.length - 1
        ? h("button", { class: "btn", onClick: () => { current++; renderNav(); renderSection(); window.scrollTo(0, 0); } }, "Próxima →")
        : h("button", { class: "btn", onClick: async () => { autosave.cancel(); if (saveState !== "saved") await saveNow(); exportarFicha(id); } }, "📄 Gerar PDF"),
    ]));
  }

  function renderField(f) {
    const wrap = h("div", { class: "field" });
    if (f.type !== "age") wrap.appendChild(h("label", {}, f.label));
    if (f.hint) wrap.appendChild(h("div", { class: "hint" }, f.hint));

    if (f.type === "textarea") {
      const ta = h("textarea", { rows: String(Math.min(f.rows || 3, 10)) }, data[f.key] || "");
      ta.addEventListener("input", () => { data[f.key] = ta.value; touch(); updateNavDots(); });
      wrap.appendChild(ta);
    } else if (f.type === "date") {
      const inp = h("input", { type: "date", value: data[f.key] || "" });
      inp.addEventListener("input", () => { data[f.key] = inp.value; touch(); updateNavDots(); updateAge(); });
      wrap.appendChild(inp);
    } else if (f.type === "age") {
      wrap.appendChild(h("label", {}, f.label));
      const val = h("div", { class: "age-value", style: "padding:9px 0;color:var(--text)" }, calcIdade(data[f.source]) || "—");
      val.dataset.ageField = "1";
      wrap.appendChild(val);
    } else if (f.type === "radio") {
      const choices = h("div", { class: "choices" });
      f.options.forEach((opt) => {
        const r = h("input", { type: "radio", name: "r_" + f.key, value: opt });
        if (data[f.key] === opt) r.checked = true;
        r.addEventListener("change", () => { data[f.key] = opt; touch(); updateNavDots(); });
        choices.appendChild(h("label", { class: "choice" }, [r, opt]));
      });
      // permite desmarcar clicando de novo? mantemos simples (escolha unica)
      wrap.appendChild(choices);
    } else if (f.type === "select") {
      const sel = h("select", {}, [h("option", { value: "" }, "—"), ...f.options.map((o) => h("option", { value: o }, o))]);
      sel.value = data[f.key] || "";
      sel.addEventListener("change", () => { data[f.key] = sel.value; touch(); updateNavDots(); });
      wrap.appendChild(sel);
    } else if (f.type === "checkboxes") {
      const choices = h("div", { class: "choices" });
      const selected = new Set(data[f.key] || []);
      f.options.forEach((opt) => {
        const cb = h("input", { type: "checkbox", value: opt });
        if (selected.has(opt)) cb.checked = true;
        cb.addEventListener("change", () => {
          if (cb.checked) selected.add(opt); else selected.delete(opt);
          data[f.key] = [...selected]; touch(); updateNavDots();
        });
        choices.appendChild(h("label", { class: "choice" }, [cb, opt]));
      });
      wrap.appendChild(choices);
    } else {
      const inp = h("input", { type: "text", value: data[f.key] || "" });
      inp.addEventListener("input", () => { data[f.key] = inp.value; touch(); updateNavDots(); });
      wrap.appendChild(inp);
    }
    return wrap;
  }

  function updateAge() {
    mainEl.querySelectorAll("[data-age-field]").forEach((el) => {
      el.textContent = calcIdade(data["data_nascimento"]) || "—";
    });
  }

  renderNav();
  renderSection();
}
