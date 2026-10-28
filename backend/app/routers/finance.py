"""Rotas do Financeiro (receitas, despesas, totais)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas import (
    CategoryTotal, FinanceEntryIn, FinanceEntryOut, FinanceEntryUpdate, FinanceTotals,
)
from ..services import finance_service

router = APIRouter(prefix="/api/finance", tags=["finance"])


@router.get("/entries", response_model=list[FinanceEntryOut])
def list_entries(kind: str | None = None, start: str | None = None, end: str | None = None,
                 paid: bool | None = None, category: str | None = None,
                 patient_id: str | None = None, recurring: bool | None = None,
                 db: Session = Depends(get_db)):
    return finance_service.list_entries(db, kind, start, end, paid, category, patient_id, recurring)


@router.get("/totals", response_model=FinanceTotals)
def totals(start: str | None = None, end: str | None = None, db: Session = Depends(get_db)):
    return finance_service.totals(db, start, end)


@router.get("/by-category", response_model=list[CategoryTotal])
def by_category(kind: str = "despesa", start: str | None = None, end: str | None = None,
                db: Session = Depends(get_db)):
    return finance_service.by_category(db, kind, start, end)


@router.get("/categories", response_model=list[str])
def categories(db: Session = Depends(get_db)):
    return finance_service.categories(db)


@router.post("/entries", response_model=FinanceEntryOut, status_code=201)
def create_entry(payload: FinanceEntryIn, db: Session = Depends(get_db)):
    return finance_service.create_entry(db, payload.model_dump())


@router.get("/entries/{entry_id}", response_model=FinanceEntryOut)
def get_entry(entry_id: str, db: Session = Depends(get_db)):
    e = finance_service.get_entry(db, entry_id)
    if not e:
        raise HTTPException(status_code=404, detail="Lançamento não encontrado.")
    return e


@router.patch("/entries/{entry_id}", response_model=FinanceEntryOut)
def update_entry(entry_id: str, payload: FinanceEntryUpdate, db: Session = Depends(get_db)):
    e = finance_service.update_entry(db, entry_id, payload.model_dump(exclude_unset=True))
    if not e:
        raise HTTPException(status_code=404, detail="Lançamento não encontrado.")
    return e


@router.delete("/entries/{entry_id}", status_code=204)
def delete_entry(entry_id: str, db: Session = Depends(get_db)):
    if not finance_service.delete_entry(db, entry_id):
        raise HTTPException(status_code=404, detail="Lançamento não encontrado.")
