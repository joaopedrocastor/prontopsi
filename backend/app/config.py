"""Configuracao central de caminhos e ambiente.

Toda a resolucao de diretorios (dados, assets, banco) vive aqui, isolada do
resto do codigo. Na migracao para a nuvem basta trocar `database_url` e o
diretorio de storage.
"""
from __future__ import annotations

import os
import sys
from functools import lru_cache
from pathlib import Path

APP_NAME = "AnamneseInfantil"

# Versão atual do aplicativo (usada na checagem de atualizações).
APP_VERSION = "1.1.4"
# Repositório público onde ficam os instaladores/releases do ProntoPsi.
RELEASES_REPO = "joaopedrocastor/prontopsi-releases"

# Raiz do repositorio (…/anamnese)
BASE_DIR = Path(__file__).resolve().parents[2]
FRONTEND_DIR = BASE_DIR / "frontend"
FONTS_DIR = FRONTEND_DIR / "assets" / "fonts"


def _is_frozen() -> bool:
    """True quando rodando como executavel PyInstaller."""
    return getattr(sys, "frozen", False)


@lru_cache(maxsize=1)
def get_data_dir() -> Path:
    """Diretorio onde ficam banco, logo e arquivos gerados.

    Ordem de resolucao:
      1. Variavel de ambiente ANAMNESE_DATA_DIR (util em testes/nuvem).
      2. Executavel empacotado  -> %LOCALAPPDATA%/AnamneseInfantil (persiste
         entre atualizacoes do app).
      3. Desenvolvimento         -> <repo>/data
    """
    env = os.environ.get("ANAMNESE_DATA_DIR")
    if env:
        data_dir = Path(env).expanduser().resolve()
    elif _is_frozen():
        root = os.environ.get("LOCALAPPDATA") or str(Path.home())
        data_dir = Path(root) / APP_NAME
    else:
        data_dir = BASE_DIR / "data"

    (data_dir / "assets").mkdir(parents=True, exist_ok=True)
    return data_dir


def get_assets_dir() -> Path:
    """Pasta de arquivos enviados pela usuaria (logo, etc.)."""
    d = get_data_dir() / "assets"
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_db_path() -> Path:
    return get_data_dir() / "anamnese.db"


def get_database_url() -> str:
    """String de conexao do SQLAlchemy.

    Local: SQLite. Nuvem futura: definir ANAMNESE_DATABASE_URL apontando para o
    PostgreSQL e nada mais muda no codigo.
    """
    override = os.environ.get("ANAMNESE_DATABASE_URL")
    if override:
        return override
    return f"sqlite:///{get_db_path().as_posix()}"
