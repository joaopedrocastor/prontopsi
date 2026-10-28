"""Rotas de Relatorios (somente leitura; agrega dados existentes)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..services import reports_service

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/overview")
def overview(months: int = 6, db: Session = Depends(get_db)):
    months = max(1, min(24, months))
    return reports_service.overview(db, months)
