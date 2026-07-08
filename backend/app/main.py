"""Aplicacao FastAPI: monta a API e serve a interface estatica.

Mesma aplicacao roda no desktop (empacotada) e, no futuro, num servidor na
nuvem — basta trocar a string de conexao do banco e adicionar autenticacao.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .config import APP_VERSION, FRONTEND_DIR
from .db_init import ensure_schema
from .routers import anamnesis, appointments, google, meta, patients, settings, system


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_schema()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="ProntoPsi", version=APP_VERSION, lifespan=lifespan)

    # API
    app.include_router(meta.router)
    app.include_router(settings.router)
    app.include_router(patients.router)
    app.include_router(anamnesis.router)
    app.include_router(appointments.router)
    app.include_router(google.router)
    app.include_router(system.router)

    # Interface (HTML/CSS/JS). html=True faz "/" servir index.html.
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
    return app


app = create_app()
