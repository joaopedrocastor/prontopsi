"""PDFs de documentos simples (recibo, declaração de comparecimento).

Usa a identidade da clínica (logo + nome + título + CRP de Settings) e a mesma
tipografia/paleta da ficha. Uma página, desenhada direto no canvas.
"""
from __future__ import annotations

import io
from datetime import date

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfgen import canvas as canvas_mod

from ..models import Patient, Settings
from . import pdf_service
from .settings_service import resolve_logo_path

TERRACOTA = HexColor("#8B3A1E")
TEXTO = HexColor("#3A3A3A")
CINZA = HexColor("#8A7F79")

PAGE_W, PAGE_H = A4
MARGIN = 54
CONTENT_W = PAGE_W - 2 * MARGIN

MESES = ["", "janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
         "agosto", "setembro", "outubro", "novembro", "dezembro"]


def _fonts():
    pdf_service._ensure_fonts()
    return pdf_service.F_REG, pdf_service.F_SEMI


def _fmt_data_ext(iso: str) -> str:
    """ISO 'YYYY-MM-DD' -> '28 de outubro de 2026'."""
    try:
        y, m, d = iso[:10].split("-")
        return f"{int(d)} de {MESES[int(m)]} de {y}"
    except Exception:
        return iso


def _fmt_data(iso: str) -> str:
    try:
        y, m, d = iso[:10].split("-")
        return f"{d}/{m}/{y}"
    except Exception:
        return iso


def _moeda(v: float) -> str:
    s = f"{(v or 0):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return "R$ " + s


def _header(c, settings: Settings) -> float:
    """Desenha cabeçalho (logo + nome/título/CRP) e retorna o y abaixo dele."""
    F_REG, F_SEMI = _fonts()
    name = settings.professional_name or ""
    title = settings.professional_title or ""
    crp = settings.crp or ""
    top = PAGE_H - 56
    text_x = MARGIN

    logo_path = resolve_logo_path(settings)
    if logo_path:
        try:
            reader = ImageReader(str(logo_path))
            lw0, lh0 = reader.getSize()
            if lh0 > 0:
                max_h, max_w = 64.0, 150.0
                scale = min(max_h / lh0, max_w / lw0)
                lw, lh = lw0 * scale, lh0 * scale
                c.drawImage(reader, MARGIN, top - lh + 6, width=lw, height=lh,
                            mask="auto", preserveAspectRatio=True)
                text_x = MARGIN + lw + 14
        except Exception:
            pass

    c.setFillColor(TERRACOTA)
    c.setFont(F_SEMI, 15)
    if name:
        c.drawString(text_x, top - 12, name)
    c.setFillColor(TEXTO)
    c.setFont(F_REG, 10.5)
    if title:
        c.drawString(text_x, top - 28, title)
    c.setFillColor(CINZA)
    c.setFont(F_REG, 10)
    if crp:
        c.drawString(text_x, top - 42, crp if crp.upper().startswith("CRP") else f"CRP {crp}")

    sep_y = top - 58
    c.setStrokeColor(TERRACOTA)
    c.setLineWidth(1.2)
    c.line(MARGIN, sep_y, PAGE_W - MARGIN, sep_y)
    return sep_y - 40


def _wrap(c, text, font, size, max_w):
    words = str(text).split()
    lines, cur = [], ""
    for w in words:
        trial = w if not cur else f"{cur} {w}"
        if pdfmetrics.stringWidth(trial, font, size) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def _paragraph(c, text, y, font, size, leading=20, align="left"):
    for ln in _wrap(c, text, font, size, CONTENT_W):
        c.setFont(font, size)
        if align == "center":
            c.drawCentredString(PAGE_W / 2, y, ln)
        else:
            c.drawString(MARGIN, y, ln)
        y -= leading
    return y


def _title(c, text, y):
    _, F_SEMI = _fonts()
    c.setFillColor(TERRACOTA)
    c.setFont(F_SEMI, 17)
    c.drawCentredString(PAGE_W / 2, y, text)
    return y - 34


def _signature(c, settings: Settings, city: str, when_iso: str):
    F_REG, F_SEMI = _fonts()
    name = settings.professional_name or ""
    crp = settings.crp or ""
    cidade = (city or "").strip()
    local_data = (f"{cidade}, " if cidade else "") + _fmt_data_ext(when_iso)
    c.setFillColor(TEXTO)
    c.setFont(F_REG, 11)
    c.drawRightString(PAGE_W - MARGIN, 220, local_data)

    cx = PAGE_W / 2
    c.setStrokeColor(TEXTO)
    c.setLineWidth(0.8)
    c.line(cx - 130, 150, cx + 130, 150)
    c.setFillColor(TERRACOTA)
    c.setFont(F_SEMI, 12)
    if name:
        c.drawCentredString(cx, 134, name)
    c.setFillColor(CINZA)
    c.setFont(F_REG, 10)
    sub = " · ".join([s for s in [settings.professional_title or "", (crp if crp.upper().startswith("CRP") else (f"CRP {crp}" if crp else ""))] if s])
    if sub:
        c.drawCentredString(cx, 120, sub)


def build_recibo(settings: Settings, *, payer: str, amount: float, reference: str,
                 city: str = "", when_iso: str | None = None) -> bytes:
    F_REG, F_SEMI = _fonts()
    when_iso = when_iso or date.today().isoformat()
    buf = io.BytesIO()
    c = canvas_mod.Canvas(buf, pagesize=A4, initialFontName=F_REG)
    c.setTitle("Recibo")
    y = _header(c, settings)
    y = _title(c, "RECIBO", y - 6)

    # Valor em destaque
    c.setFillColor(TERRACOTA)
    c.setFont(F_SEMI, 22)
    c.drawString(MARGIN, y, _moeda(amount))
    y -= 40

    ref = (reference or "atendimento psicológico").strip()
    texto = (f"Recebi de {payer or '—'} a importância de {_moeda(amount)} "
             f"referente a {ref}.")
    c.setFillColor(TEXTO)
    y = _paragraph(c, texto, y, F_REG, 12, leading=22)

    _signature(c, settings, city, when_iso)
    c.showPage()
    c.save()
    return buf.getvalue()


def build_declaracao(settings: Settings, patient: Patient, *, when_iso: str,
                     start: str = "", end: str = "", city: str = "",
                     extra: str = "") -> bytes:
    F_REG, F_SEMI = _fonts()
    buf = io.BytesIO()
    c = canvas_mod.Canvas(buf, pagesize=A4, initialFontName=F_REG)
    c.setTitle("Declaração de Comparecimento")
    y = _header(c, settings)
    y = _title(c, "DECLARAÇÃO DE COMPARECIMENTO", y - 6)

    nome = patient.name if patient else "—"
    horario = ""
    if start and end:
        horario = f", no horário das {start} às {end}"
    elif start:
        horario = f", às {start}"
    texto = (f"Declaro para os devidos fins que {nome} compareceu a atendimento "
             f"psicológico neste consultório no dia {_fmt_data(when_iso)}{horario}.")
    c.setFillColor(TEXTO)
    y = _paragraph(c, texto, y, F_REG, 12, leading=24)
    if extra and extra.strip():
        y -= 6
        y = _paragraph(c, extra.strip(), y, F_REG, 12, leading=24)

    _signature(c, settings, city, when_iso)
    c.showPage()
    c.save()
    return buf.getvalue()
