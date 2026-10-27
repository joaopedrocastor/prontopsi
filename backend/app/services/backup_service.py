"""Backup e restauracao COMPLETOS (banco + logo + documentos).

O backup gera um ZIP com:
  - anamnese.db   (copia consistente via API de backup do SQLite)
  - assets/...    (logo e arquivos de identidade)
  - documents/... (documentos anexados aos clientes)

A restauracao aceita o ZIP novo e, por compatibilidade, um .db antigo.
"""
from __future__ import annotations

import shutil
import sqlite3
import zipfile
from datetime import datetime
from pathlib import Path

from ..config import get_data_dir, get_db_path
from ..database import engine

_INCLUDED_DIRS = ("assets", "documents")


def _consistent_db_copy(target_path: Path) -> None:
    """Copia o banco de forma consistente (mesmo com o app aberto)."""
    src = sqlite3.connect(str(get_db_path()))
    try:
        dst = sqlite3.connect(str(target_path))
        try:
            src.backup(dst)
        finally:
            dst.close()
    finally:
        src.close()


def create_backup(dest_dir: str) -> Path:
    """Gera um ZIP de backup (banco + logo + documentos) na pasta escolhida."""
    dest = Path(dest_dir).expanduser()
    dest.mkdir(parents=True, exist_ok=True)
    if not dest.is_dir():
        raise ValueError("Destino de backup inválido.")
    if not get_db_path().exists():
        raise FileNotFoundError("Banco de dados ainda não existe.")

    data_dir = get_data_dir()
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    target = dest / f"prontopsi_backup_{stamp}.zip"

    # Copia consistente do banco para um arquivo temporario antes de zipar.
    tmp_db = dest / f".anamnese_tmp_{stamp}.db"
    try:
        _consistent_db_copy(tmp_db)
        with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(tmp_db, "anamnese.db")
            for sub in _INCLUDED_DIRS:
                d = data_dir / sub
                if d.exists():
                    for f in d.rglob("*"):
                        if f.is_file():
                            zf.write(f, f"{sub}/{f.relative_to(d).as_posix()}")
    finally:
        tmp_db.unlink(missing_ok=True)
    return target


def restore_backup(src_file: str) -> None:
    """Restaura a partir de um ZIP (novo) ou de um .db (compatibilidade).

    O app deve ser reiniciado depois para reabrir a nova base.
    """
    src = Path(src_file).expanduser()
    if not src.exists() or not src.is_file():
        raise ValueError("Arquivo de backup não encontrado.")

    if zipfile.is_zipfile(src):
        _restore_from_zip(src)
    else:
        _restore_from_db(src)


def _restore_from_zip(src: Path) -> None:
    data_dir = get_data_dir()
    with zipfile.ZipFile(src) as zf:
        names = zf.namelist()
        if "anamnese.db" not in names:
            raise ValueError("O ZIP não contém um backup válido (sem anamnese.db).")
        # Valida o banco extraindo para um temporario.
        tmp_db = data_dir / ".restore_tmp.db"
        tmp_db.write_bytes(zf.read("anamnese.db"))
        _validate_sqlite(tmp_db)

        engine.dispose()
        shutil.copyfile(str(tmp_db), str(get_db_path()))
        tmp_db.unlink(missing_ok=True)

        # Restaura assets/ e documents/ (sem sair do diretorio de dados).
        for name in names:
            if name.endswith("/") or not name.startswith(_INCLUDED_DIRS):
                continue
            dest = (data_dir / name).resolve()
            if not str(dest).startswith(str(data_dir.resolve())):
                continue  # protege contra path traversal
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(zf.read(name))
    engine.dispose()


def _restore_from_db(src: Path) -> None:
    _validate_sqlite(src)
    engine.dispose()
    shutil.copyfile(str(src), str(get_db_path()))
    engine.dispose()


def _validate_sqlite(path: Path) -> None:
    try:
        con = sqlite3.connect(str(path))
        con.execute("SELECT name FROM sqlite_master LIMIT 1")
        con.close()
    except sqlite3.DatabaseError as exc:
        raise ValueError("O arquivo selecionado não é um backup válido.") from exc
