"""Regras de negocio do Financeiro (camada de servico).

Valores trafegam na API em reais (float) e sao guardados no banco em centavos
(inteiro), evitando erro de ponto flutuante ao somar. A conversao acontece so
aqui, nas bordas (`_to_dict` / `create` / `update`).
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import FinanceEntry, Patient

_FIELDS = (
    "kind", "description", "category", "currency", "due_date",
    "paid", "paid_date", "recurrence", "notes", "appointment_id",
)


def _reais(cents: int) -> float:
    return round((cents or 0) / 100, 2)


def _cents(reais: float | None) -> int:
    return int(round((reais or 0) * 100))


def _to_dict(e: FinanceEntry, patient_name: str | None = None) -> dict:
    return {
        "id": e.id,
        "kind": e.kind,
        "description": e.description or "",
        "category": e.category or "",
        "amount": _reais(e.amount_cents),
        "currency": e.currency or "BRL",
        "due_date": e.due_date,
        "paid": bool(e.paid),
        "paid_date": e.paid_date,
        "recurrence": e.recurrence or "nenhuma",
        "patient_id": e.patient_id,
        "patient_name": patient_name if patient_name is not None else (e.patient.name if e.patient else ""),
        "appointment_id": e.appointment_id,
        "notes": e.notes,
        "created_at": e.created_at,
        "updated_at": e.updated_at,
    }


def list_entries(db: Session, kind: str | None = None, start: str | None = None,
                 end: str | None = None, paid: bool | None = None,
                 category: str | None = None, patient_id: str | None = None,
                 recurring: bool | None = None) -> list[dict]:
    """Lista lancamentos filtrados por periodo (due_date em [start, end]) e demais campos."""
    stmt = select(FinanceEntry, Patient.name).join(
        Patient, FinanceEntry.patient_id == Patient.id, isouter=True
    )
    if kind:
        stmt = stmt.where(FinanceEntry.kind == kind)
    if start:
        stmt = stmt.where(FinanceEntry.due_date >= start)
    if end:
        stmt = stmt.where(FinanceEntry.due_date <= end)
    if paid is not None:
        stmt = stmt.where(FinanceEntry.paid == paid)
    if category:
        stmt = stmt.where(FinanceEntry.category == category)
    if patient_id:
        stmt = stmt.where(FinanceEntry.patient_id == patient_id)
    if recurring:
        stmt = stmt.where(FinanceEntry.recurrence != "nenhuma")
    stmt = stmt.order_by(FinanceEntry.due_date.desc())
    return [_to_dict(e, name or "") for e, name in db.execute(stmt).all()]


def get_entry(db: Session, entry_id: str) -> dict | None:
    e = db.get(FinanceEntry, entry_id)
    return _to_dict(e) if e else None


def create_entry(db: Session, data: dict) -> dict:
    e = FinanceEntry(
        kind=data.get("kind") or "receita",
        description=(data.get("description") or "").strip(),
        category=(data.get("category") or "").strip(),
        amount_cents=_cents(data.get("amount")),
        currency=data.get("currency") or "BRL",
        due_date=data["due_date"],
        paid=bool(data.get("paid")),
        paid_date=data.get("paid_date") or (date.today().isoformat() if data.get("paid") else None),
        recurrence=data.get("recurrence") or "nenhuma",
        patient_id=data.get("patient_id") or None,
        appointment_id=data.get("appointment_id") or None,
        notes=data.get("notes"),
    )
    db.add(e)
    db.commit()
    db.refresh(e)
    return _to_dict(e)


def charge_exists_for_appointment(db: Session, appointment_id: str) -> bool:
    """Já existe cobrança vinculada a esta sessão?"""
    n = db.execute(
        select(func.count(FinanceEntry.id)).where(FinanceEntry.appointment_id == appointment_id)
    ).scalar_one()
    return n > 0


def create_session_charge(db: Session, patient, appointment) -> dict | None:
    """Gera a cobrança (receita) de uma sessão realizada, se o cliente tem valor
    padrão e ainda não houver cobrança para a sessão. Retorna o lançamento ou None."""
    if not patient or (patient.session_price_cents or 0) <= 0:
        return None
    if charge_exists_for_appointment(db, appointment.id):
        return None
    e = FinanceEntry(
        kind="receita",
        description="Sessão de " + (patient.name or "atendimento"),
        category="Consultas",
        amount_cents=patient.session_price_cents,
        due_date=(appointment.start_at or "")[:10],
        paid=False,
        patient_id=patient.id,
        appointment_id=appointment.id,
    )
    db.add(e)
    db.commit()
    db.refresh(e)
    return _to_dict(e)


def update_entry(db: Session, entry_id: str, data: dict) -> dict | None:
    e = db.get(FinanceEntry, entry_id)
    if not e:
        return None
    for field in _FIELDS:
        if field in data and data[field] is not None:
            setattr(e, field, data[field])
    if "amount" in data and data["amount"] is not None:
        e.amount_cents = _cents(data["amount"])
    if "patient_id" in data:
        e.patient_id = data["patient_id"] or None
    # Ao marcar como pago sem data, assume hoje; ao desmarcar, limpa a data.
    if data.get("paid") and not e.paid_date:
        e.paid_date = date.today().isoformat()
    if "paid" in data and data["paid"] is False:
        e.paid_date = None
    db.commit()
    db.refresh(e)
    return _to_dict(e)


def set_paid(db: Session, entry_id: str, paid: bool) -> dict | None:
    return update_entry(db, entry_id, {"paid": paid})


def delete_entry(db: Session, entry_id: str) -> bool:
    e = db.get(FinanceEntry, entry_id)
    if not e:
        return False
    db.delete(e)
    db.commit()
    return True


def totals(db: Session, start: str | None = None, end: str | None = None) -> dict:
    """Totais do periodo (reais). Vencidas usam a data de hoje, nao o periodo."""
    def soma(kind: str, paid: bool | None) -> int:
        stmt = select(func.coalesce(func.sum(FinanceEntry.amount_cents), 0)).where(
            FinanceEntry.kind == kind
        )
        if start:
            stmt = stmt.where(FinanceEntry.due_date >= start)
        if end:
            stmt = stmt.where(FinanceEntry.due_date <= end)
        if paid is not None:
            stmt = stmt.where(FinanceEntry.paid == paid)
        return int(db.execute(stmt).scalar_one())

    income_received = soma("receita", True)
    income_pending = soma("receita", False)
    expense_paid = soma("despesa", True)
    expense_open = soma("despesa", False)

    hoje = date.today().isoformat()
    overdue = int(db.execute(
        select(func.coalesce(func.sum(FinanceEntry.amount_cents), 0))
        .where(FinanceEntry.paid == False)  # noqa: E712
        .where(FinanceEntry.due_date < hoje)
    ).scalar_one())

    forecast = (income_received + income_pending) - (expense_paid + expense_open)
    balance = income_received - expense_paid
    return {
        "income_received": _reais(income_received),
        "income_pending": _reais(income_pending),
        "expense_paid": _reais(expense_paid),
        "expense_open": _reais(expense_open),
        "overdue": _reais(overdue),
        "forecast": _reais(forecast),
        "balance": _reais(balance),
    }


def by_category(db: Session, kind: str = "despesa", start: str | None = None,
                end: str | None = None) -> list[dict]:
    """Soma por categoria (para o grafico da aba Analise)."""
    stmt = (
        select(FinanceEntry.category, func.coalesce(func.sum(FinanceEntry.amount_cents), 0))
        .where(FinanceEntry.kind == kind)
    )
    if start:
        stmt = stmt.where(FinanceEntry.due_date >= start)
    if end:
        stmt = stmt.where(FinanceEntry.due_date <= end)
    stmt = stmt.group_by(FinanceEntry.category).order_by(func.sum(FinanceEntry.amount_cents).desc())
    return [
        {"category": (cat or "Sem categoria"), "total": _reais(total)}
        for cat, total in db.execute(stmt).all()
    ]


def categories(db: Session) -> list[str]:
    stmt = select(FinanceEntry.category).where(FinanceEntry.category != "").distinct()
    return sorted({c for (c,) in db.execute(stmt).all() if c})
