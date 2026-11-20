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
from reportlab.pdfgen.canvas import FILL_EVEN_ODD

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


# ---------------------------------------------------------------------------
# Recibo de prestação de serviços psicológicos (layout do modelo em papel:
# logo no topo, arcos decorativos, título espaçado, texto justificado e
# rodapé terracota com o endereço do consultório da cidade escolhida).
# ---------------------------------------------------------------------------
R_FONT = "Helvetica"
R_BOLD = "Helvetica-Bold"
R_TEXTO = HexColor("#1F1F1F")
R_ARCO = HexColor("#C4A094")      # arcos decorativos (rosé/taupe)
R_RODAPE = HexColor("#8A4529")    # faixa do rodapé
R_X0, R_X1 = 90.0, PAGE_W - 61.0  # margens do texto do recibo
R_W = R_X1 - R_X0


def _logo_recortada(path) -> ImageReader | None:
    """Abre a logo, torna o fundo liso transparente e recorta as sobras.

    Logos exportadas de editores costumam vir num quadrado com fundo bege e
    muito espaço vazio; no papel branco isso apareceria como uma caixa."""
    try:
        from PIL import Image, ImageChops

        img = Image.open(str(path)).convert("RGBA")
        r, g, b, a = img.getpixel((0, 0))
        if a > 250:  # fundo opaco: remove a cor do canto
            rgb = img.convert("RGB")
            diff = ImageChops.difference(rgb, Image.new("RGB", rgb.size, (r, g, b))).convert("L")
            mask = diff.point(lambda v: 0 if v < 12 else min(255, (v - 12) * 6))
            img.putalpha(ImageChops.multiply(mask, img.getchannel("A")))
        bbox = img.getchannel("A").point(lambda v: 255 if v > 20 else 0).getbbox()
        if bbox:
            img = img.crop(bbox)
        out = io.BytesIO()
        img.save(out, format="PNG")
        out.seek(0)
        return ImageReader(out)
    except Exception:
        try:
            return ImageReader(str(path))
        except Exception:
            return None


def _recibo_cabecalho(c, settings: Settings) -> None:
    F_REG, F_SEMI = _fonts()
    top = PAGE_H - 26
    x = 20.0
    reader = None
    logo_path = resolve_logo_path(settings)
    if logo_path:
        reader = _logo_recortada(logo_path)
    if reader is not None:
        lw0, lh0 = reader.getSize()
        if settings.logo_includes_info:
            max_w, max_h = 290.0, 78.0
        else:
            max_w, max_h = 80.0, 70.0
        s = min(max_w / lw0, max_h / lh0)
        lw, lh = lw0 * s, lh0 * s
        c.drawImage(reader, x, top - lh, width=lw, height=lh, mask="auto")
        if settings.logo_includes_info:
            return
        x += lw + 10
    # Sem logo "completa": escreve nome / título / CRP ao lado.
    crp = settings.crp or ""
    c.setFillColor(TERRACOTA)
    c.setFont(F_REG, 20)
    c.drawString(x, top - 24, settings.professional_name or "")
    c.setFont(F_REG, 10)
    c.drawString(x, top - 40, settings.professional_title or "")
    if crp:
        c.drawString(x, top - 53, crp if crp.upper().startswith("CRP") else f"CRP {crp}")


def _anel(c, x: float, y: float, raio: float, espessura: float) -> None:
    """Anel preenchido (sem a 'emenda' que o traço de um círculo deixa)."""
    p = c.beginPath()
    p.circle(x, y, raio + espessura / 2)
    p.circle(x, y, raio - espessura / 2)
    c.drawPath(p, stroke=0, fill=1, fillMode=FILL_EVEN_ODD)


def _recibo_arcos(c) -> None:
    c.saveState()
    c.setFillColor(R_ARCO)
    _anel(c, 620, 697, 78, 22)        # topo direito
    _anel(c, 10, 175, 80, 22)         # inferior esquerdo
    _anel(c, -14, 60, 30, 15)         # volta menor embaixo
    c.circle(6, 283, 9, stroke=0, fill=1)  # pingo
    c.restoreState()


def _titulo_espacado(c, linhas: list[str], y: float, size: float = 12.5,
                     largura_1a: float = 451.0, leading: float = 29.0) -> None:
    """Título em caixa alta com letras espaçadas, centralizado."""
    n = len(linhas[0])
    w0 = pdfmetrics.stringWidth(linhas[0], R_BOLD, size)
    espaco = max(0.0, (largura_1a - w0) / max(1, n - 1))
    for ln in linhas:
        w = pdfmetrics.stringWidth(ln, R_BOLD, size) + espaco * (len(ln) - 1)
        _texto_espacado(c, ln, PAGE_W / 2 - w / 2, y, R_BOLD, size, espaco)
        y -= leading


def _texto_espacado(c, txt: str, x: float, y: float, font: str, size: float,
                    espaco: float) -> None:
    # O espaçamento entre letras fica no estado gráfico do PDF: salva/restaura
    # para não "vazar" para os textos seguintes.
    c.saveState()
    t = c.beginText(x, y)
    t.setFont(font, size)
    t.setCharSpace(espaco)
    t.textLine(txt)
    c.drawText(t)
    c.restoreState()


def _linhas_justificadas(texto: str, font: str, size: float, max_w: float) -> list[list[str]]:
    # Divide só no espaço comum: o espaço não separável (ex.: "R$ 120,00")
    # mantém as duas partes juntas na mesma linha.
    palavras, linhas, atual = [p for p in texto.split(" ") if p], [], []
    largura = lambda ws: pdfmetrics.stringWidth(" ".join(ws), font, size)  # noqa: E731
    for p in palavras:
        if atual and largura(atual + [p]) > max_w:
            # Palavra com hífen (ex.: "Cognitivo-Comportamental)") pode quebrar
            # no hífen, evitando um buraco grande na linha justificada.
            partes = p.split("-")
            cabe = None
            for i in range(len(partes) - 1, 0, -1):
                inicio = "-".join(partes[:i]) + "-"
                if largura(atual + [inicio]) <= max_w:
                    cabe = (inicio, "-".join(partes[i:]))
                    break
            if cabe:
                linhas.append(atual + [cabe[0]])
                atual = [cabe[1]]
            else:
                linhas.append(atual)
                atual = [p]
        else:
            atual.append(p)
    if atual:
        linhas.append(atual)
    return linhas


def _desenha_justificado(c, linhas: list[list[str]], y: float, font: str, size: float,
                         leading: float) -> float:
    c.setFont(font, size)
    for i, palavras in enumerate(linhas):
        ultima = i == len(linhas) - 1
        if ultima or len(palavras) == 1:
            c.drawString(R_X0, y, " ".join(palavras))
        else:
            larguras = [pdfmetrics.stringWidth(p, font, size) for p in palavras]
            gap = (R_W - sum(larguras)) / (len(palavras) - 1)
            x = R_X0
            for p, w in zip(palavras, larguras):
                c.drawString(x, y, p)
                x += w + gap
        y -= leading
    return y


def _data_ext2(iso: str) -> str:
    """'2026-11-09' -> '09 de novembro de 2026' (dia com 2 dígitos, como no modelo)."""
    try:
        y, m, d = iso[:10].split("-")
        return f"{d} de {MESES[int(m)]} de {y}"
    except Exception:
        return iso


def _juntar(itens: list[str]) -> str:
    if len(itens) <= 1:
        return "".join(itens)
    return ", ".join(itens[:-1]) + " e " + itens[-1]


def datas_por_extenso(datas: list[str]) -> str:
    """['2026-11-04','2026-11-11'] -> '04 e 11 de novembro de 2026'.
    Meses diferentes: '28 de outubro, 04 e 11 de novembro de 2026'."""
    ds = sorted({d[:10] for d in datas if d and len(d) >= 10})
    if not ds:
        return ""
    grupos: list[tuple[str, str, list[str]]] = []  # (ano, mes, dias)
    for d in ds:
        y, m, dia = d.split("-")
        if grupos and grupos[-1][0] == y and grupos[-1][1] == m:
            grupos[-1][2].append(dia)
        else:
            grupos.append((y, m, [dia]))
    partes = []
    for i, (y, m, dias) in enumerate(grupos):
        txt = f"{_juntar(dias)} de {MESES[int(m)]}"
        prox_ano = grupos[i + 1][0] if i + 1 < len(grupos) else None
        if prox_ano != y:
            txt += f" de {y}"
        partes.append(txt)
    return ", ".join(partes)


def texto_recibo(settings: Settings, *, payer: str, payer_cpf: str = "",
                 payer_title: str = "", patient_name: str = "", patient_sex: str = "",
                 amount: float, sessions: int | None = None,
                 session_dates: list[str] | None = None, service: str = "",
                 when_iso: str) -> str:
    """Monta o parágrafo do recibo no padrão do modelo em papel."""
    from .extenso import extenso, moeda_extenso

    titulo_prof = (settings.professional_title or "Psicóloga").strip().lower()
    prof_fem = not titulo_prof.endswith("o")
    nome_prof = (settings.legal_name or settings.professional_name or "").strip()
    crp = (settings.crp or "").strip()
    if crp.upper().startswith("CRP"):
        crp = crp[3:].strip()
    partes = [f"{nome_prof}, inscrit{'a' if prof_fem else 'o'} no CRP sob o número {crp}"]
    if settings.cpf:
        partes[0] += f" e no CPF sob o número {settings.cpf.strip()}"
    tratamento = (payer_title or "").strip()
    if tratamento == "Sr.":
        quem, insc = f"do Sr. {payer}", "inscrito"
    elif tratamento == "Sra.":
        quem, insc = f"da Sra. {payer}", "inscrita"
    else:
        quem, insc = f"de {payer}", "inscrito(a)"
    frase = f"recebi {quem}"
    if payer_cpf and payer_cpf.strip():
        frase += f", {insc} no CPF sob o nº {payer_cpf.strip()}"
    valor = _moeda(amount).replace("R$ ", "R$ ")
    frase += f", a quantia de {valor} ({moeda_extenso(amount)})"

    datas = sorted({d[:10] for d in (session_dates or []) if d})
    n = sessions or len(datas) or 1
    plural = n > 1
    servico = (service or "Psicoterapia").strip()
    frase += (f", referente a {n} ({extenso(n, feminino=True)}) "
              f"{'sessões' if plural else 'sessão'} de prestação de serviços de {servico}")
    if datas:
        futuras = all(d > when_iso[:10] for d in datas)
        if futuras:
            verbo = "a serem realizadas" if plural else "a ser realizada"
        else:
            verbo = "realizadas" if plural else "realizada"
        dia = "nos dias" if len(datas) > 1 else "no dia"
        frase += f" {verbo} {dia} {datas_por_extenso(datas)}"
    if patient_name:
        artigo = {"F": "a", "M": "o"}.get((patient_sex or "").upper(), "o(a)")
        frase += f" para {artigo} paciente {patient_name}"
    return partes[0] + ", " + frase + "."


def build_recibo(settings: Settings, *, payer: str, amount: float, reference: str = "",
                 city: str = "", when_iso: str | None = None, number: int | None = None,
                 payer_cpf: str = "", payer_title: str = "", patient_name: str = "",
                 patient_sex: str = "", sessions: int | None = None,
                 session_dates: list[str] | None = None, service: str = "",
                 office: dict | None = None) -> bytes:
    when_iso = when_iso or date.today().isoformat()
    buf = io.BytesIO()
    c = canvas_mod.Canvas(buf, pagesize=A4, initialFontName=R_FONT)
    c.setTitle(f"Recibo {number:03d}" if number else "Recibo")

    _recibo_arcos(c)
    _recibo_cabecalho(c, settings)

    c.setFillColor(R_TEXTO)
    _titulo_espacado(c, ["RECIBO DE PRESTAÇÃO DE SERVIÇOS", "PSICOLÓGICOS"], 700)

    c.setFont(R_FONT, 14)
    if number:
        c.drawString(R_X0, 602, f"Nº do Recibo: {number:03d}")
    c.drawRightString(R_X1, 602, f"Valor: {_moeda(amount)}")

    texto = texto_recibo(
        settings, payer=payer, payer_cpf=payer_cpf, payer_title=payer_title,
        patient_name=patient_name, patient_sex=patient_sex, amount=amount,
        sessions=sessions, session_dates=session_dates,
        service=service or reference, when_iso=when_iso,
    )
    size = 13.5
    linhas = _linhas_justificadas(texto, R_FONT, size, R_W)
    # Cabe tudo antes da cidade/data? Se não, aperta o espaçamento.
    disponivel = 536 - 250
    leading = min(32.0, disponivel / (len(linhas) + 1))
    y = _desenha_justificado(c, linhas, 536, R_FONT, size, leading)
    c.drawString(R_X0, y, "Para maior clareza e validade legal, firmo o presente recibo.")

    cidade = (office or {}).get("city") or (city or "").strip()
    local = (f"{cidade}, " if cidade else "") + _data_ext2(when_iso) + "."
    c.setFont(R_FONT, 14)
    c.drawRightString(R_X1, min(206, y - 46), local)

    # Assinatura
    cx = (172 + 435) / 2
    c.setStrokeColor(HexColor("#8C7B72"))
    c.setLineWidth(0.7)
    c.line(172, 116, 435, 116)
    c.setFont(R_BOLD, 10.5)
    crp = (settings.crp or "").strip()
    crp_txt = crp if crp.upper().startswith("CRP") else (f"CRP {crp}" if crp else "")
    for i, ln in enumerate([(settings.professional_name or "").upper(),
                            (settings.professional_title or "").upper(), crp_txt]):
        if ln:
            c.drawCentredString(cx, 98 - i * 19, ln)

    # Rodapé com o endereço do consultório
    c.setFillColor(R_RODAPE)
    c.rect(0, 0, PAGE_W, 45, stroke=0, fill=1)
    if office and (office.get("address") or office.get("phone")):
        c.setFillColor(HexColor("#FFFFFF"))
        for txt, yy in ((office.get("address") and f"Endereço: {office['address']}", 26),
                        (office.get("phone") and f"Telefone: {office['phone']}", 11)):
            if not txt:
                continue
            w = pdfmetrics.stringWidth(txt, R_BOLD, 10) + 0.6 * (len(txt) - 1)
            _texto_espacado(c, txt, PAGE_W / 2 - w / 2, yy, R_BOLD, 10, 0.6)

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
