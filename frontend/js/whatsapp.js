// Lembrete de consulta por WhatsApp: abre o wa.me com uma mensagem pronta.
// Sem API nem custo — usa o WhatsApp Web/app do próprio computador.

import { openExternal } from "./store.js";
import { toast } from "./util.js";

// Normaliza telefone brasileiro para o formato do wa.me (só dígitos, com 55).
export function normalizarTelefone(raw) {
  let d = String(raw || "").replace(/\D/g, "");
  if (!d) return "";
  if (d.length >= 12 && d.startsWith("55")) return d;     // já tem DDI
  if (d.length === 10 || d.length === 11) return "55" + d; // DDD + número
  return d;
}

// Pega o primeiro telefone de um campo que pode ter vários.
export function primeiroTelefone(phones) {
  const parte = String(phones || "").split(/[,;/]|\se\s/)[0];
  return normalizarTelefone(parte);
}

// Monta e abre o lembrete. { phone, nome, data, hora, profissional }
export function lembreteWhatsApp({ phone, nome, data, hora, profissional }) {
  const num = normalizarTelefone(phone);
  if (!num) { toast("Sem telefone válido para enviar.", "err"); return; }
  const partes = [
    "Olá! 🙂 Passando para lembrar da consulta",
    nome ? ` de ${nome}` : "",
    data ? ` no dia ${data}` : "",
    hora ? ` às ${hora}` : "",
    profissional ? ` com ${profissional}` : "",
    ". Qualquer imprevisto, me avise por aqui.",
  ];
  const msg = partes.join("");
  openExternal(`https://wa.me/${num}?text=${encodeURIComponent(msg)}`);
}
