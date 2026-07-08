# -*- mode: python ; coding: utf-8 -*-
# Empacota o aplicativo num executavel unico (instalacao = copiar o .exe).
#   Gerar:  .venv\Scripts\pyinstaller anamnese.spec
# O .exe fica em dist\FichaDeAnamnese.exe
from PyInstaller.utils.hooks import collect_submodules, collect_data_files, collect_all

hiddenimports = []
# Imports dinamicos do uvicorn que o PyInstaller nao descobre sozinho.
hiddenimports += [
    "uvicorn.logging",
    "uvicorn.loops.auto",
    "uvicorn.loops.asyncio",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.http.h11_impl",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.protocols.websockets.websockets_impl",
    "uvicorn.lifespan.on",
    "uvicorn.lifespan.off",
]
hiddenimports += collect_submodules("backend")

datas = [
    ("frontend", "frontend"),            # HTML/CSS/JS + fontes Poppins + icone
    ("backend/alembic", "backend/alembic"),
    ("alembic.ini", "."),
]
datas += collect_data_files("reportlab")

# Integracao Google (opcional): inclui libs + arquivos de descoberta da API.
for _pkg in ("googleapiclient", "google_auth_oauthlib", "google.auth"):
    try:
        _d, _b, _h = collect_all(_pkg)
        datas += _d
        hiddenimports += _h
    except Exception:
        pass

ICON = "frontend/assets/prontopsi.ico"

block_cipher = None

a = Analysis(
    ["run.py"],
    pathex=["."],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter", "pytest"],
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="ProntoPsi",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    runtime_tmpdir=None,
    console=False,   # sem janela de terminal
    icon=ICON,
)
