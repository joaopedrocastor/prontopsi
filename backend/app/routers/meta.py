"""Rotas de metadados: saude e esquema do formulario."""
from __future__ import annotations

from fastapi import APIRouter

from ..form_schema import get_schema

router = APIRouter(prefix="/api", tags=["meta"])


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.get("/form-schema")
def form_schema() -> dict:
    """Esquema canonico da ficha (secoes e campos) para a interface renderizar."""
    return get_schema()
