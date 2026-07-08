"""Engine, sessao e utilidades de banco (camada de persistencia).

Usa SQLAlchemy ORM puro, sem SQL especifico do SQLite, para que a troca
SQLite -> PostgreSQL seja apenas mudanca da string de conexao.
"""
from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import get_database_url

_url = get_database_url()

# check_same_thread=False: o servidor roda em thread separada da janela desktop.
_connect_args = {"check_same_thread": False} if _url.startswith("sqlite") else {}

engine = create_engine(_url, connect_args=_connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)


class Base(DeclarativeBase):
    """Base declarativa compartilhada por todos os modelos e pelo Alembic."""


def get_db() -> Iterator["SessionLocal"]:
    """Dependencia FastAPI: abre uma sessao por requisicao e fecha ao final."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
