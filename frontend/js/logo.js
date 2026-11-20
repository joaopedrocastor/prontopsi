// Logo oficial (Thamires Benedito — Psicóloga — CRP), embutida no app.
// Na barra lateral e na tela de senha usamos a versão empilhada (monograma em
// cima, nome embaixo), que fica legível em espaço estreito, sobre um cartão
// branco (a logo é terracota e precisa de fundo claro).
// Arquivos: assets/logo-oficial.png (horizontal, usada nos PDFs) e
//           assets/logo-oficial-vertical.png (empilhada, usada nas telas).

const LOGO_VERTICAL = "assets/logo-oficial-vertical.png";
const ALT = "Thamires Benedito — Psicóloga";

// Lockup para a barra lateral.
export function logoHorizontal(size = 160) {
  return `<div class="brand-card"><img class="pp-logo-img" src="${LOGO_VERTICAL}" alt="${ALT}" style="width:${size}px" /></div>`;
}

// Lockup grande para a tela de senha.
export function logoStacked(size = 200) {
  return `<img class="pp-logo-img" src="${LOGO_VERTICAL}" alt="${ALT}" style="width:${size}px" />`;
}
