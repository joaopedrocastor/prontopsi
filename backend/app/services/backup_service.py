"""Backup e restauracao do banco local (copia simples do arquivo SQLite)."""
from __future__ import annotations

import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

from ..config import get_db_path
from ..database import engine


def create_backup(dest_dir: str) -> Path:
    """Copia o banco para a pasta/pen drive escolhido, com nome datado.

    Usa a API de backup do SQLite (copia consistente mesmo com o app aberto).
    """
    dest = Path(dest_dir).expanduser()
    if not dest.exists():
        dest.mkdir(parents=True, exist_ok=True)
    if not dest.is_dir():
        raise ValueError("Destino de backup inválido.")

    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    target = dest / f"anamnese_backup_{stamp}.db"

    src_path = get_db_path()
    if not src_path.exists():
        raise FileNotFoundError("Banco de dados ainda não existe.")

    src = sqlite3.connect(str(src_path))
    try:
        dst = sqlite3.connect(str(target))
        try:
            src.backup(dst)
        finally:
            dst.close()
    finally:
        src.close()
    return target


def restore_backup(src_file: str) -> None:
    """Substitui o banco atual por um arquivo de backup.

    O app deve ser reiniciado depois para reabrir a nova base.
    """
    src = Path(src_file).expanduser()
    if not src.exists() or not src.is_file():
        raise ValueError("Arquivo de backup não encontrado.")

    # Valida que e realmente um banco SQLite.
    try:
        con = sqlite3.connect(str(src))
        con.execute("SELECT name FROM sqlite_master LIMIT 1")
        con.close()
    except sqlite3.DatabaseError as exc:
        raise ValueError("O arquivo selecionado não é um backup válido.") from exc

    # Fecha conexoes abertas antes de trocar o arquivo.
    engine.dispose()
    shutil.copyfile(str(src), str(get_db_path()))
    engine.dispose()
