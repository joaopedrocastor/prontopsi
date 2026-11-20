"""Números por extenso em português (Brasil), para recibos.

    extenso(120)               -> 'cento e vinte'
    extenso(2, feminino=True)  -> 'duas'
    moeda_extenso(120.5)       -> 'cento e vinte reais e cinquenta centavos'
"""
from __future__ import annotations

_UNI = ["", "um", "dois", "três", "quatro", "cinco", "seis", "sete", "oito", "nove"]
_UNI_F = ["", "uma", "duas", "três", "quatro", "cinco", "seis", "sete", "oito", "nove"]
_DEZ_19 = ["dez", "onze", "doze", "treze", "catorze", "quinze", "dezesseis",
           "dezessete", "dezoito", "dezenove"]
_DEZENAS = ["", "", "vinte", "trinta", "quarenta", "cinquenta", "sessenta",
            "setenta", "oitenta", "noventa"]
_CENTENAS = ["", "cento", "duzentos", "trezentos", "quatrocentos", "quinhentos",
             "seiscentos", "setecentos", "oitocentos", "novecentos"]


def _ate_999(n: int, feminino: bool) -> str:
    if n == 0:
        return ""
    if n == 100:
        return "cem"
    c, resto = divmod(n, 100)
    d, u = divmod(resto, 10)
    partes = []
    if c:
        cent = _CENTENAS[c]
        if feminino and c >= 2:
            cent = cent[:-2] + "as"  # duzentos -> duzentas
        partes.append(cent)
    if resto:
        if resto < 10:
            partes.append((_UNI_F if feminino else _UNI)[u])
        elif resto < 20:
            partes.append(_DEZ_19[resto - 10])
        else:
            dez = _DEZENAS[d]
            partes.append(dez if not u else f"{dez} e {(_UNI_F if feminino else _UNI)[u]}")
    return " e ".join(partes)


def extenso(n: int, feminino: bool = False) -> str:
    """Inteiro (0 a 999.999.999) por extenso."""
    n = int(n)
    if n == 0:
        return "zero"
    if n < 0:
        return "menos " + extenso(-n, feminino)
    milhoes, resto = divmod(n, 1_000_000)
    milhares, unidades = divmod(resto, 1000)
    grupos = []
    if milhoes:
        grupos.append("um milhão" if milhoes == 1 else f"{_ate_999(milhoes, False)} milhões")
    if milhares:
        grupos.append("mil" if milhares == 1 else f"{_ate_999(milhares, feminino)} mil")
    if unidades:
        grupos.append(_ate_999(unidades, feminino))
    if len(grupos) == 1:
        return grupos[0]
    # "mil e duzentos", "mil e trinta", mas "mil duzentos e trinta".
    ultimo = unidades if unidades else milhares
    sep = " e " if (ultimo < 100 or ultimo % 100 == 0) else " "
    return " ".join(grupos[:-1]) + sep + grupos[-1]


def moeda_extenso(valor: float) -> str:
    """Valor em reais por extenso: 'cento e vinte reais e cinquenta centavos'."""
    cents_total = int(round((valor or 0) * 100))
    reais, centavos = divmod(cents_total, 100)
    partes = []
    if reais:
        txt = extenso(reais)
        if reais % 1_000_000 == 0:
            txt += " de"  # "um milhão de reais"
        partes.append(f"{txt} {'real' if reais == 1 else 'reais'}")
    if centavos:
        partes.append(f"{extenso(centavos)} {'centavo' if centavos == 1 else 'centavos'}")
    return " e ".join(partes) if partes else "zero real"
