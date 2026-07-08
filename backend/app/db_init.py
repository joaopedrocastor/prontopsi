"""Inicializacao do schema do banco.

Usa Alembic (migracoes controladas e reproduziveis em qualquer ambiente). Se o
Alembic falhar por algum motivo no ambiente empacotado, cai para create_all
como rede de seguranca, garantindo que o app sempre abra.
"""
from __future__ import annotations

import logging

from .config import BASE_DIR, get_database_url

logger = logging.getLogger("anamnese")


def ensure_schema() -> None:
    try:
        from alembic import command
        from alembic.config import Config

        ini = BASE_DIR / "alembic.ini"
        cfg = Config(str(ini)) if ini.exists() else Config()
        cfg.set_main_option("script_location", str(BASE_DIR / "backend" / "alembic"))
        cfg.set_main_option("sqlalchemy.url", get_database_url())
        command.upgrade(cfg, "head")
        logger.info("Migrações Alembic aplicadas (head).")
    except Exception as exc:  # rede de seguranca
        logger.warning("Alembic indisponível (%s); usando create_all.", exc)
        from .database import Base, engine
        from . import models  # noqa: F401  (registra os modelos no metadata)

        Base.metadata.create_all(bind=engine)
