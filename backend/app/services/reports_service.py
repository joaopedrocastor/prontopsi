"""Relatorios (camada de servico): agrega dados ja existentes.

So leitura — nenhuma tabela nova. Reaproveita finanças, agenda e clientes para
indicadores e series mensais mostradas na tela de Relatorios.
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import Appointment, FinanceEntry, Patient


def _months_back(n: int) -> list[str]:
    """Lista dos ultimos n meses em 'YYYY-MM', do mais antigo ao atual."""
    today = date.today()
    y, m = today.year, today.month
    out: list[str] = []
    for _ in range(n):
        out.append(f"{y:04d}-{m:02d}")
        m -= 1
        if m == 0:
            m = 12
            y -= 1
    return list(reversed(out))


def _reais(cents: int) -> float:
    return round((cents or 0) / 100, 2)


def finance_monthly(db: Session, months: int = 6) -> list[dict]:
    """Receita recebida x despesa paga (realizado) por mes."""
    labels = _months_back(months)
    rows = db.execute(
        select(
            func.substr(FinanceEntry.due_date, 1, 7),
            FinanceEntry.kind,
            func.coalesce(func.sum(FinanceEntry.amount_cents), 0),
        )
        .where(FinanceEntry.paid == True)  # noqa: E712
        .group_by(func.substr(FinanceEntry.due_date, 1, 7), FinanceEntry.kind)
    ).all()
    data = {mo: {"receita": 0.0, "despesa": 0.0} for mo in labels}
    for mo, kind, cents in rows:
        if mo in data and kind in ("receita", "despesa"):
            data[mo][kind] = _reais(cents)
    return [
        {"month": mo, "receita": data[mo]["receita"], "despesa": data[mo]["despesa"],
         "saldo": round(data[mo]["receita"] - data[mo]["despesa"], 2)}
        for mo in labels
    ]


def sessions_monthly(db: Session, months: int = 6) -> list[dict]:
    """Sessoes realizadas por mes."""
    labels = _months_back(months)
    rows = db.execute(
        select(func.substr(Appointment.start_at, 1, 7), func.count())
        .where(Appointment.status == "realizada")
        .group_by(func.substr(Appointment.start_at, 1, 7))
    ).all()
    done = {mo: n for mo, n in rows}
    return [{"month": mo, "realizadas": int(done.get(mo, 0))} for mo in labels]


def sessions_status(db: Session, months: int = 6) -> list[dict]:
    """Contagem por status no periodo (ultimos n meses)."""
    labels = _months_back(months)
    inicio = labels[0] + "-01"
    rows = db.execute(
        select(Appointment.status, func.count())
        .where(Appointment.start_at >= inicio)
        .group_by(Appointment.status)
    ).all()
    return [{"status": st, "count": int(n)} for st, n in rows]


def clients_status(db: Session) -> list[dict]:
    rows = db.execute(
        select(Patient.status, func.count()).group_by(Patient.status)
    ).all()
    return [{"status": st or "ativo", "count": int(n)} for st, n in rows]


def overview(db: Session, months: int = 6) -> dict:
    fin = finance_monthly(db, months)
    sess_m = sessions_monthly(db, months)
    sess_s = sessions_status(db, months)
    cli = clients_status(db)

    total_recebido = round(sum(f["receita"] for f in fin), 2)
    total_despesa = round(sum(f["despesa"] for f in fin), 2)
    total_realizadas = sum(s["realizadas"] for s in sess_m)
    total_clientes = sum(c["count"] for c in cli)
    ativos = sum(c["count"] for c in cli if c["status"] == "ativo")

    # Em aberto (receitas nao pagas, todo o periodo) para contexto.
    aberto = db.execute(
        select(func.coalesce(func.sum(FinanceEntry.amount_cents), 0))
        .where(FinanceEntry.kind == "receita").where(FinanceEntry.paid == False)  # noqa: E712
    ).scalar_one()

    return {
        "months": months,
        "finance_monthly": fin,
        "sessions_monthly": sess_m,
        "sessions_status": sess_s,
        "clients_status": cli,
        "totals": {
            "recebido": total_recebido,
            "despesa": total_despesa,
            "saldo": round(total_recebido - total_despesa, 2),
            "a_receber": _reais(aberto),
            "sessoes_realizadas": total_realizadas,
            "clientes": total_clientes,
            "clientes_ativos": ativos,
        },
    }
