// Logo do ProntoPsi (SVG inline, reutilizavel). Cores: teal + laranja + navy.
// Marca de exemplo — a psicóloga usa a própria logo nas fichas/PDF.

function markSvg(size = 96) {
  return `
  <svg class="pp-mark" width="${size}" height="${size}" viewBox="0 0 120 120" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
    <!-- bowl do Psi (U aberto para cima) -->
    <path d="M30 26 L30 56 C30 78 44 88 60 88 C76 88 90 78 90 56 L90 26"
          stroke="#0E7C8A" stroke-width="11" stroke-linecap="round" fill="none"/>
    <!-- haste central + pé -->
    <path d="M60 20 L60 104 M44 104 L76 104"
          stroke="#0E7C8A" stroke-width="11" stroke-linecap="round"/>
    <!-- flecha laranja (crescimento) -->
    <path d="M34 84 C64 86 74 46 98 30" stroke="#F0801A" stroke-width="11"
          stroke-linecap="round" fill="none"/>
    <path d="M84 26 L102 26 L100 46 Z" fill="#F0801A"/>
  </svg>`;
}

// Lockup horizontal (marca + wordmark) — para a barra lateral.
export function logoHorizontal(markSize = 40) {
  return `
  <span class="pp-logo pp-logo-h">
    ${markSvg(markSize)}
    <span class="pp-word"><b>Pronto</b><span class="pp-teal">Psi</span></span>
  </span>`;
}

// Lockup vertical grande (marca + wordmark + tagline) — login / topo.
export function logoStacked(markSize = 96, tagline = true) {
  return `
  <span class="pp-logo pp-logo-v">
    ${markSvg(markSize)}
    <span class="pp-word pp-word-lg"><b>Pronto</b><span class="pp-teal">Psi</span></span>
    ${tagline ? '<span class="pp-tag">PLATAFORMA INTELIGENTE PARA PSICÓLOGAS INFANTIS</span>' : ""}
  </span>`;
}
