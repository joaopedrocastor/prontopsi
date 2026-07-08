"""Geracao do PDF da Ficha de Anamnese com ReportLab.

Reproduz o padrao visual da ficha em papel:
  - cabecalho em todas as paginas: logo + nome + titulo + CRP (esquerda) e o
    selo marrom "Ficha de Anamnese" (direita);
  - titulos de secao como pilulas arredondadas marrom com texto branco em caixa
    alta;
  - mesma ordem de campos do modelo; valores preenchidos aparecem como texto,
    campos vazios como linha pontilhada em branco (permite imprimir em branco).

Funciona igual no desktop e na nuvem (nao depende do sistema de janelas).
"""
from __future__ import annotations

import io

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Flowable,
    Frame,
    KeepTogether,
    PageTemplate,
    Spacer,
)

from ..config import FONTS_DIR
from ..form_schema import SECTIONS
from ..models import Anamnesis, Patient, Settings
from ..services.settings_service import resolve_logo_path
from ..utils import calcular_idade

# ---------------- Paleta e tipografia ----------------
TERRACOTA = HexColor("#8B3A1E")
TERRACOTA_ESCURO = HexColor("#7A3219")
TEXTO = HexColor("#3A3A3A")
CINZA_HINT = HexColor("#8A7F79")
PONTILHADO = HexColor("#C9B8AE")

PAGE_W, PAGE_H = A4
MARGIN = 42
TOP_MARGIN = 134
BOTTOM_MARGIN = 46
CONTENT_W = PAGE_W - 2 * MARGIN
LINE_H = 18.0
FIELD_SIZE = 11.0   # tamanho dos rotulos/valores dos campos
HINT_SIZE = 9.0

_FONTS_READY = False
F_REG = "Helvetica"
F_MED = "Helvetica"
F_SEMI = "Helvetica-Bold"
F_BOLD = "Helvetica-Bold"


def _ensure_fonts() -> None:
    """Registra a Poppins (tipografia arredondada da ficha) uma unica vez."""
    global _FONTS_READY, F_REG, F_MED, F_SEMI, F_BOLD
    if _FONTS_READY:
        return
    mapping = {
        "Poppins": "Poppins-Regular.ttf",
        "Poppins-Medium": "Poppins-Medium.ttf",
        "Poppins-SemiBold": "Poppins-SemiBold.ttf",
        "Poppins-Bold": "Poppins-Bold.ttf",
    }
    try:
        for name, filename in mapping.items():
            path = FONTS_DIR / filename
            if path.exists():
                pdfmetrics.registerFont(TTFont(name, str(path)))
        if (FONTS_DIR / "Poppins-Regular.ttf").exists():
            F_REG, F_MED, F_SEMI, F_BOLD = (
                "Poppins", "Poppins-Medium", "Poppins-SemiBold", "Poppins-Bold",
            )
    except Exception:
        # Mantem Helvetica como fallback: PDF continua sendo gerado.
        pass
    _FONTS_READY = True


def _fmt_date(iso: str) -> str:
    """ISO 'YYYY-MM-DD' -> 'DD/MM/AAAA' (formato da ficha)."""
    try:
        y, m, d = iso[:10].split("-")
        return f"{d}/{m}/{y}"
    except ValueError:
        return iso


def _wrap(text: str, font: str, size: float, first_w: float, full_w: float) -> list[str]:
    """Quebra o texto em linhas; a primeira linha usa `first_w`, as demais `full_w`."""
    words = str(text).split()
    if not words:
        return []
    lines: list[str] = []
    cur = ""
    idx = 0
    for w in words:
        avail = first_w if idx == 0 else full_w
        trial = w if not cur else f"{cur} {w}"
        if pdfmetrics.stringWidth(trial, font, size) <= avail or not cur:
            cur = trial
        else:
            lines.append(cur)
            idx += 1
            cur = w
    lines.append(cur)
    return lines


# ---------------- Flowables ----------------
class SectionPill(Flowable):
    """Titulo de secao: pilula arredondada marrom com texto branco em caixa alta."""

    def __init__(self, title: str):
        super().__init__()
        self.title = title.upper()
        self.size = 12.5
        self.pad_x = 16
        self.h = 26

    def wrap(self, avail_w, avail_h):
        self.width = avail_w
        self.height = self.h + 6
        return self.width, self.height

    def draw(self):
        c = self.canv
        text_w = pdfmetrics.stringWidth(self.title, F_SEMI, self.size)
        w = text_w + 2 * self.pad_x
        c.setFillColor(TERRACOTA)
        c.roundRect(0, 4, w, self.h, self.h / 2, stroke=0, fill=1)
        c.setFillColor(HexColor("#FFFFFF"))
        c.setFont(F_SEMI, self.size)
        c.drawString(self.pad_x, 4 + (self.h - self.size) / 2 + 1, self.title)


class FieldFlowable(Flowable):
    """Um campo da ficha: rotulo + valor (ou linhas pontilhadas se vazio)."""

    def __init__(self, field: dict, data: dict):
        super().__init__()
        self.field = field
        self.data = data
        self.label = field["label"]
        self.ftype = field["type"]
        self.hint = field.get("hint", "")
        self.rows = field.get("rows", 1)
        self._layout = None

    # -- helpers de valor --
    def _display_value(self) -> str:
        key = self.field["key"]
        raw = self.data.get(key)
        if self.ftype == "age":
            return calcular_idade(self.data.get(self.field.get("source", "")))
        if self.ftype == "checkboxes":
            selected = set(raw or [])
            return "   ".join(
                f"({'X' if opt in selected else ' '}) {opt}" for opt in self.field.get("options", [])
            )
        if self.ftype in ("radio", "select"):
            return "   ".join(
                f"({'X' if raw == opt else ' '}) {opt}" for opt in self.field.get("options", [])
            )
        if self.ftype == "date" and raw:
            return _fmt_date(str(raw))
        return "" if raw is None else str(raw)

    def _is_block(self) -> bool:
        # Rotulo em linha propria (texto longo/hint); demais ficam inline.
        return self.ftype == "textarea" or bool(self.hint)

    def _value_is_choice(self) -> bool:
        return self.ftype in ("radio", "select", "checkboxes")

    # -- medicao --
    def wrap(self, avail_w, avail_h):
        self.width = avail_w
        size = FIELD_SIZE
        label_txt = f"{self.label}:"
        label_w = pdfmetrics.stringWidth(label_txt + " ", F_SEMI, size)
        value = self._display_value()
        block = self._is_block()

        lines: list[dict] = []  # {type:'label'|'hint'|'value', text, x, dotted}

        if block:
            # Linha do rotulo (sem pontilhado)
            for ln in _wrap(label_txt, F_SEMI, size, CONTENT_W, CONTENT_W):
                lines.append({"kind": "label", "text": ln, "x": 0, "dotted": False})
            if self.hint:
                for ln in _wrap(f"({self.hint})", F_REG, HINT_SIZE, CONTENT_W, CONTENT_W):
                    lines.append({"kind": "hint", "text": ln, "x": 0, "dotted": False})
            # Linhas de valor (com pontilhado): preenchido = linhas do texto;
            # vazio = `rows` linhas em branco para escrever a mao / imprimir.
            if value:
                value_lines = _wrap(value, F_REG, size, CONTENT_W, CONTENT_W)
                n = max(len(value_lines), 1)
            else:
                value_lines = []
                n = self.rows
            for i in range(n):
                txt = value_lines[i] if i < len(value_lines) else ""
                lines.append({"kind": "value", "text": txt, "x": 0, "dotted": True})
        else:
            # Inline: rotulo + valor na mesma linha, pontilhado preenche o resto.
            first_w = CONTENT_W - label_w
            value_lines = _wrap(value, F_REG, size, first_w, CONTENT_W) if value else [""]
            for i, txt in enumerate(value_lines):
                x = label_w if i == 0 else 0
                lines.append({
                    "kind": "value", "text": txt, "x": x, "dotted": True,
                    "label": label_txt if i == 0 else None,
                })

        self._layout = lines
        self.height = len(lines) * LINE_H + 4
        return self.width, self.height

    def draw(self):
        c = self.canv
        size = FIELD_SIZE
        y = self.height - LINE_H + 3
        for ln in self._layout:
            kind = ln["kind"]
            if kind == "label":
                c.setFont(F_SEMI, size)
                c.setFillColor(TERRACOTA_ESCURO)
                c.drawString(0, y, ln["text"])
            elif kind == "hint":
                c.setFont(F_REG, HINT_SIZE)
                c.setFillColor(CINZA_HINT)
                c.drawString(0, y, ln["text"])
            else:  # value (com pontilhado)
                # rotulo inline (quando houver)
                if ln.get("label"):
                    c.setFont(F_SEMI, size)
                    c.setFillColor(TERRACOTA_ESCURO)
                    c.drawString(0, y, ln["label"])
                # linha pontilhada
                if ln.get("dotted"):
                    c.setStrokeColor(PONTILHADO)
                    c.setLineWidth(0.7)
                    c.setDash(1, 2)
                    c.line(ln["x"], y - 2.5, CONTENT_W, y - 2.5)
                    c.setDash()
                # valor por cima
                if ln["text"]:
                    c.setFont(F_REG, size)
                    c.setFillColor(TEXTO)
                    c.drawString(ln["x"] + 2, y, ln["text"])
            y -= LINE_H


# ---------------- Cabecalho / rodape ----------------
def _make_header(settings: Settings):
    name = settings.professional_name or ""
    title = settings.professional_title or ""
    crp = settings.crp or ""
    includes_info = bool(getattr(settings, "logo_includes_info", False))
    logo_path = resolve_logo_path(settings)
    logo_reader = None
    logo_dims = (0, 0)
    if logo_path:
        try:
            logo_reader = ImageReader(str(logo_path))
            logo_dims = logo_reader.getSize()
        except Exception:
            logo_reader = None

    have_logo = bool(logo_reader and logo_dims[1] > 0)
    # Se a logo ja traz nome/CRP, mostramos ela maior e sem repetir o texto.
    logo_only = have_logo and includes_info

    def draw(canvas, doc):
        canvas.saveState()
        top = PAGE_H - 26
        sep_y = PAGE_H - 118
        text_x = MARGIN

        # Selo "Ficha de Anamnese" (direita)
        seal_w, seal_h = 132, 54
        seal_x = PAGE_W - MARGIN - seal_w
        seal_y = top - seal_h
        canvas.setFillColor(TERRACOTA)
        canvas.roundRect(seal_x, seal_y, seal_w, seal_h, 11, stroke=0, fill=1)
        canvas.setFillColor(HexColor("#FFFFFF"))
        canvas.setFont(F_MED, 10)
        canvas.drawCentredString(seal_x + seal_w / 2, seal_y + seal_h - 19, "Ficha de")
        canvas.setFont(F_SEMI, 16)
        canvas.drawCentredString(seal_x + seal_w / 2, seal_y + 11, "Anamnese")

        # Logo (esquerda) — maior; maior ainda quando ja contem o texto.
        if have_logo:
            if logo_only:
                max_h, max_w = 88.0, seal_x - MARGIN - 16
            else:
                max_h, max_w = 74.0, 210.0
            scale = min(max_h / logo_dims[1], max_w / logo_dims[0])
            lw, lh = logo_dims[0] * scale, logo_dims[1] * scale
            band_mid = (top + sep_y) / 2
            try:
                canvas.drawImage(logo_reader, MARGIN, band_mid - lh / 2, width=lw, height=lh,
                                 mask="auto", preserveAspectRatio=True)
                text_x = MARGIN + lw + 14
            except Exception:
                pass

        # Nome / titulo / CRP (ocultos quando a logo ja os inclui)
        if not logo_only:
            canvas.setFillColor(TERRACOTA)
            canvas.setFont(F_SEMI, 15.5)
            if name:
                canvas.drawString(text_x, top - 22, name)
            canvas.setFillColor(TEXTO)
            canvas.setFont(F_REG, 11)
            if title:
                canvas.drawString(text_x, top - 40, title)
            canvas.setFont(F_REG, 10)
            canvas.setFillColor(CINZA_HINT)
            if crp:
                canvas.drawString(text_x, top - 55, crp if crp.upper().startswith("CRP") else f"CRP {crp}")

        # Separador
        canvas.setStrokeColor(TERRACOTA)
        canvas.setLineWidth(1.3)
        canvas.line(MARGIN, sep_y, PAGE_W - MARGIN, sep_y)

        # Rodape: numero da pagina
        canvas.setFont(F_REG, 8.5)
        canvas.setFillColor(CINZA_HINT)
        canvas.drawRightString(PAGE_W - MARGIN, 28, f"Página {doc.page}")

        canvas.restoreState()

    return draw


# ---------------- API do modulo ----------------
def build_pdf(anamnesis: Anamnesis, patient: Patient, settings: Settings) -> bytes:
    _ensure_fonts()
    data = dict(anamnesis.data or {})
    # Garante identificacao coerente com o cadastro do paciente.
    data.setdefault("nome", patient.name or "")
    if patient.birth_date:
        data.setdefault("data_nascimento", patient.birth_date)

    buffer = io.BytesIO()
    doc = BaseDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=TOP_MARGIN,
        bottomMargin=BOTTOM_MARGIN,
        title="Ficha de Anamnese",
        author=settings.professional_name or "",
    )
    frame = Frame(MARGIN, BOTTOM_MARGIN, CONTENT_W, PAGE_H - TOP_MARGIN - BOTTOM_MARGIN, id="body")
    doc.addPageTemplates([
        PageTemplate(id="ficha", frames=[frame], onPage=_make_header(settings))
    ])

    story: list = []
    for section in SECTIONS:
        pill = SectionPill(section["title"])
        first = section["fields"][0]
        # Mantem a pilula junto do primeiro campo (evita titulo orfao no rodape).
        story.append(KeepTogether([pill, Spacer(1, 3), FieldFlowable(first, data)]))
        for field in section["fields"][1:]:
            story.append(FieldFlowable(field, data))
        story.append(Spacer(1, 10))

    doc.build(story)
    return buffer.getvalue()
