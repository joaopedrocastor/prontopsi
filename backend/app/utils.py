"""Utilidades puras (sem dependencia de banco ou web)."""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone


def new_uuid() -> str:
    """UUID4 em texto. Usado como chave de pacientes, fichas e anexos.

    Evita conflitos ao importar dados no banco da nuvem (nunca autoincremento).
    """
    return str(uuid.uuid4())


def now_iso() -> str:
    """Momento atual em ISO 8601 UTC (ex.: 2026-07-07T13:45:00Z)."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def calcular_idade(data_nascimento: str | None, referencia: date | None = None) -> str:
    """Idade a partir da data de nascimento (ISO 'YYYY-MM-DD').

    Retorna texto amigavel em pt-BR ('7 anos', '11 meses', '1 ano e 2 meses').
    String vazia quando a data e invalida/ausente.
    """
    if not data_nascimento:
        return ""
    try:
        nasc = date.fromisoformat(data_nascimento[:10])
    except (ValueError, TypeError):
        return ""
    hoje = referencia or date.today()
    if nasc > hoje:
        return ""

    anos = hoje.year - nasc.year
    meses = hoje.month - nasc.month
    if hoje.day < nasc.day:
        meses -= 1
    if meses < 0:
        anos -= 1
        meses += 12

    if anos <= 0:
        if meses <= 0:
            return "menos de 1 mês"
        return f"{meses} {'mês' if meses == 1 else 'meses'}"
    partes = [f"{anos} {'ano' if anos == 1 else 'anos'}"]
    if meses > 0:
        partes.append(f"{meses} {'mês' if meses == 1 else 'meses'}")
    return " e ".join(partes)
