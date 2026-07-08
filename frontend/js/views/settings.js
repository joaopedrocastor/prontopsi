// Tela de Configuracoes: identidade visual (logo, nome, CRP) e senha opcional.

import { api } from "../api.js";
import { store, loadSettings } from "../store.js";
import { refreshHeader } from "../app.js";
import { h, toast, confirmar } from "../util.js";

// Tela de Configuração: identidade (logo/nome/CRP), senha, recuperação e Google.
export async function renderSettings(container) {
  const s = store.settings || (await loadSettings());

  const head = h("div", { class: "page-head" }, [
    h("button", { class: "back-link", onClick: () => (location.hash = "#/painel") }, "← Painel"),
    h("div", { class: "spacer" }),
  ]);
  container.appendChild(head);
  container.appendChild(h("h1", { style: "color:var(--navy);margin:0 0 18px" }, "Configurações"));

  // ---- Identidade ----
  const logoImg = h("img", {
    class: "logo-preview" + (s.logo_path ? "" : " hidden"),
    src: s.logo_path ? "/api/settings/logo/image?t=" + Date.now() : "",
  });
  const logoHint = h("div", { class: "muted" }, s.logo_path ? "Logo atual" : "Nenhuma logo enviada");

  const fileInput = h("input", { type: "file", accept: ".png,.jpg,.jpeg,.webp", class: "hidden" });
  fileInput.addEventListener("change", async () => {
    const f = fileInput.files[0];
    if (!f) return;
    try {
      const upd = await api.uploadLogo(f);
      store.settings = upd; refreshHeader();
      logoImg.src = "/api/settings/logo/image?t=" + Date.now();
      logoImg.classList.remove("hidden");
      logoHint.textContent = "Logo atual";
      toast("Logo atualizada.", "ok");
    } catch (e) { toast(e.message, "err"); }
  });

  const drop = h("div", { class: "logo-drop", onClick: () => fileInput.click() }, [
    logoImg,
    h("div", {}, "📷 Clique para enviar sua logo (PNG ou JPG)"),
    logoHint,
  ]);

  const nameI = h("input", { type: "text", value: s.professional_name || "", placeholder: "Ex.: Thamires Benedito" });
  const titleI = h("input", { type: "text", value: s.professional_title || "Psicóloga", placeholder: "Psicóloga" });
  const crpI = h("input", { type: "text", value: s.crp || "", placeholder: "Ex.: CRP 04/83658" });
  const includesI = h("input", { type: "checkbox" });
  if (s.logo_includes_info) includesI.checked = true;

  const identCard = h("div", { class: "card" }, [
    h("div", { class: "field" }, [h("label", {}, "Logo"), drop, fileInput,
      s.logo_path ? h("button", {
        class: "btn-ghost btn-sm", style: "margin-top:8px",
        onClick: async () => {
          if (!(await confirmar({ title: "Remover logo", message: "Remover a logo atual?" }))) return;
          const upd = await api.removeLogo();
          store.settings = upd; refreshHeader();
          logoImg.classList.add("hidden"); logoHint.textContent = "Nenhuma logo enviada";
          toast("Logo removida.", "ok");
        },
      }, "Remover logo") : null,
    ]),
    h("div", { class: "form-row w-2" }, [
      h("div", { class: "field" }, [h("label", {}, "Nome profissional"), nameI]),
      h("div", { class: "field" }, [h("label", {}, "Título"), titleI]),
    ]),
    h("div", { class: "field" }, [h("label", {}, "CRP"), crpI]),
    h("div", { class: "field" }, [
      h("label", { class: "choice", style: "font-size:14px" }, [
        includesI, "Minha logo já inclui meu nome, título e CRP",
      ]),
      h("div", { class: "hint" }, "Marque se a imagem enviada já traz o texto (nome/CRP). O app mostra a logo maior e não repete o texto ao lado."),
    ]),
    h("div", { class: "form-actions" }, [
      h("button", {
        class: "btn",
        onClick: async () => {
          try {
            const upd = await api.saveSettings({
              professional_name: nameI.value.trim(),
              professional_title: titleI.value.trim() || "Psicóloga",
              crp: crpI.value.trim(),
              logo_includes_info: includesI.checked,
            });
            store.settings = { ...store.settings, ...upd };
            refreshHeader();
            toast("Configurações salvas.", "ok");
          } catch (e) { toast(e.message, "err"); }
        },
      }, "Salvar"),
    ]),
  ]);
  container.appendChild(identCard);

  // ---- Senha ----
  container.appendChild(h("h2", { style: "font-size:17px;color:var(--terracota);margin:26px 0 10px" }, "Senha de abertura (opcional)"));
  const passI = h("input", { type: "password", placeholder: s.has_password ? "•••••• (defina uma nova)" : "Deixe em branco para não usar senha" });
  const passCard = h("div", { class: "card" }, [
    h("div", { class: "field" }, [
      h("label", {}, s.has_password ? "Alterar senha" : "Definir senha"),
      h("div", { class: "hint" }, "Protege a abertura do aplicativo. Guarde-a bem — não há recuperação."),
      passI,
    ]),
    h("div", { class: "form-actions" }, [
      h("button", {
        class: "btn",
        onClick: async () => {
          try {
            const upd = await api.setPassword(passI.value || null);
            store.settings = upd;
            passI.value = "";
            toast(upd.has_password ? "Senha definida." : "Senha removida.", "ok");
          } catch (e) { toast(e.message, "err"); }
        },
      }, "Salvar senha"),
      s.has_password ? h("button", {
        class: "btn-danger",
        onClick: async () => {
          if (!(await confirmar({ title: "Remover senha", message: "O app abrirá sem pedir senha. Continuar?" }))) return;
          const upd = await api.setPassword(null);
          store.settings = upd;
          toast("Senha removida.", "ok");
          location.hash = "#/config"; renderSettingsReload();
        },
      }, "Remover senha") : null,
    ]),
  ]);
  container.appendChild(passCard);

  // ---- Recuperação de senha por e-mail ----
  container.appendChild(h("h2", { style: "font-size:17px;color:var(--navy);margin:26px 0 10px" }, "Recuperação de senha por e-mail"));
  const recEmailI = h("input", { type: "email", value: s.recovery_email || "", placeholder: "seu@email.com" });
  const smtpHostI = h("input", { type: "text", placeholder: "Ex.: smtp.gmail.com (opcional)" });
  const smtpPortI = h("input", { type: "number", placeholder: "465 ou 587" });
  const smtpUserI = h("input", { type: "text", placeholder: "usuário / e-mail de envio" });
  const smtpPassI = h("input", { type: "password", placeholder: s.has_smtp ? "•••••• (deixe em branco p/ manter)" : "senha do e-mail / app password" });
  const recCard = h("div", { class: "card" }, [
    h("div", { class: "field" }, [
      h("label", {}, "E-mail de recuperação"),
      h("div", { class: "hint" }, "Usado para redefinir a senha caso você esqueça. Sem servidor SMTP, a recuperação é feita localmente confirmando este e-mail."),
      recEmailI,
    ]),
    h("details", { style: "margin-top:6px" }, [
      h("summary", { style: "cursor:pointer;color:var(--primary);font-size:13.5px" }, "Servidor de e-mail (SMTP) — opcional, para enviar o código"),
      h("div", { style: "margin-top:12px" }, [
        h("div", { class: "form-row w-2" }, [
          h("div", { class: "field" }, [h("label", {}, "Servidor SMTP"), smtpHostI]),
          h("div", { class: "field" }, [h("label", {}, "Porta"), smtpPortI]),
        ]),
        h("div", { class: "field" }, [h("label", {}, "Usuário (e-mail de envio)"), smtpUserI]),
        h("div", { class: "field" }, [h("label", {}, "Senha do e-mail"), smtpPassI]),
        h("div", { class: "hint" }, "Gmail: use uma “senha de app”. Porta 465 (SSL) ou 587 (STARTTLS)."),
      ]),
    ]),
    h("div", { class: "form-actions" }, [
      h("button", {
        class: "btn",
        onClick: async () => {
          try {
            const upd = await api.saveRecovery({
              recovery_email: recEmailI.value.trim() || null,
              smtp_host: smtpHostI.value.trim() || null,
              smtp_port: smtpPortI.value ? Number(smtpPortI.value) : null,
              smtp_user: smtpUserI.value.trim() || null,
              smtp_password: smtpPassI.value || null,
            });
            store.settings = { ...store.settings, ...upd };
            smtpPassI.value = "";
            toast("Recuperação salva.", "ok");
          } catch (e) { toast(e.message, "err"); }
        },
      }, "Salvar recuperação"),
    ]),
  ]);
  container.appendChild(recCard);

  // ---- Integração com a Agenda Google ----
  container.appendChild(h("h2", { style: "font-size:17px;color:var(--navy);margin:26px 0 10px" }, "Integração com a Agenda Google"));
  const gWrap = h("div", { class: "card" }, [h("div", { class: "muted" }, "Carregando...")]);
  container.appendChild(gWrap);
  renderGoogleCard(gWrap);
}

// Renderiza o cartão da integração Google (status + configuração + conectar).
async function renderGoogleCard(wrap) {
  let st;
  try { st = await api.googleStatus(); } catch { st = { available: false, configured: false, connected: false }; }
  wrap.innerHTML = "";

  if (!st.available) {
    wrap.appendChild(h("div", { class: "muted" }, "Recurso de sincronização não disponível nesta versão."));
    return;
  }

  const statusEl = h("div", { style: "margin-bottom:12px" }, [
    st.connected
      ? h("span", { class: "badge badge-done" }, "✓ Conectado à Agenda Google")
      : h("span", { class: "badge badge-draft" }, "Não conectado"),
  ]);

  const cidI = h("input", { type: "text", placeholder: "Client ID do Google", value: "" });
  const csI = h("input", { type: "password", placeholder: st.configured ? "•••••• (deixe em branco p/ manter)" : "Client Secret" });
  const calI = h("input", { type: "text", value: st.calendar_id || "primary", placeholder: "primary" });
  const tzI = h("input", { type: "text", value: st.timezone || "America/Sao_Paulo" });

  const connectBtn = h("button", {
    class: "btn",
    onClick: async () => {
      connectBtn.disabled = true; connectBtn.textContent = "Abrindo navegador...";
      try { await api.googleConnect(); toast("Conectado! A agenda será sincronizada.", "ok"); renderGoogleCard(wrap); }
      catch (e) { toast(e.message, "err"); connectBtn.disabled = false; connectBtn.textContent = "Conectar"; }
    },
  }, "Conectar");

  wrap.appendChild(statusEl);
  wrap.appendChild(h("div", { class: "hint", style: "margin-bottom:12px" }, "Crie um projeto no Google Cloud, ative a API do Google Calendar e uma credencial OAuth do tipo “Aplicativo para computador”. Cole o Client ID e o Client Secret abaixo, salve e clique em Conectar."));
  wrap.appendChild(h("div", { class: "form-row w-2" }, [
    h("div", { class: "field" }, [h("label", {}, "Client ID"), cidI]),
    h("div", { class: "field" }, [h("label", {}, "Client Secret"), csI]),
  ]));
  wrap.appendChild(h("div", { class: "form-row w-2" }, [
    h("div", { class: "field" }, [h("label", {}, "ID do calendário"), calI]),
    h("div", { class: "field" }, [h("label", {}, "Fuso horário"), tzI]),
  ]));
  wrap.appendChild(h("div", { class: "form-actions" }, [
    h("button", {
      class: "btn-outline",
      onClick: async () => {
        try {
          await api.googleSaveConfig({
            client_id: cidI.value.trim() || null,
            client_secret: csI.value || null,
            calendar_id: calI.value.trim() || "primary",
            timezone: tzI.value.trim() || "America/Sao_Paulo",
          });
          csI.value = "";
          toast("Configuração do Google salva.", "ok");
          renderGoogleCard(wrap);
        } catch (e) { toast(e.message, "err"); }
      },
    }, "Salvar configuração"),
    st.configured ? connectBtn : null,
    st.connected ? h("button", {
      class: "btn-danger",
      onClick: async () => { try { await api.googleDisconnect(); toast("Desconectado.", "ok"); renderGoogleCard(wrap); } catch (e) { toast(e.message, "err"); } },
    }, "Desconectar") : null,
  ]));
}

function renderSettingsReload() {
  const v = document.getElementById("view");
  v.innerHTML = "";
  renderSettings(v);
}
