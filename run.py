"""Launcher do aplicativo desktop.

Sobe o backend FastAPI (uvicorn) numa thread em localhost e abre a interface
numa janela nativa (pywebview). Para a psicologa e um programa comum: clica no
icone e a janela abre. O mesmo backend/mesma interface vao para a nuvem depois.
"""
from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import webbrowser
from pathlib import Path
from urllib.request import Request, urlopen

# Nome do mutex que o instalador (Inno Setup, AppMutex) usa para detectar e
# fechar o app antes de substituir o .exe durante o auto-update.
APP_MUTEX = "ProntoPsi_SingleInstance_Mutex"

# Garante que a raiz do projeto esteja no path (dev e empacotado).
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import uvicorn  # noqa: E402
import webview  # noqa: E402

from backend.app.main import app  # noqa: E402

HOST = "127.0.0.1"


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, 0))
        return s.getsockname()[1]


def _run_server(port: int) -> None:
    config = uvicorn.Config(app, host=HOST, port=port, log_level="warning")
    server = uvicorn.Server(config)
    server.run()


def _wait_ready(port: int, timeout: float = 20.0) -> bool:
    url = f"http://{HOST}:{port}/api/health"
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urlopen(url, timeout=1) as r:
                if r.status == 200:
                    return True
        except Exception:
            time.sleep(0.15)
    return False


def _first(result):
    if result is None:
        return None
    if isinstance(result, (list, tuple)):
        return result[0] if result else None
    return result


def _file_types(filtro: str):
    f = (filtro or "").upper()
    todos = "Todos os arquivos (*.*)"
    if "BACKUP" in f:
        return ("Backup do ProntoPsi (*.zip;*.db)", "Arquivo ZIP (*.zip)",
                "Banco de dados (*.db)", todos)
    if "PDF" in f:
        return ("Documento PDF (*.pdf)", todos)
    if "ZIP" in f:
        return ("Arquivo ZIP (*.zip)", todos)
    if "JSON" in f:
        return ("Arquivo JSON (*.json)", todos)
    if "DB" in f or "BANCO" in f:
        return ("Banco de dados (*.db)", todos)
    return (todos,)


class Bridge:
    """API exposta ao JavaScript para abrir dialogos nativos de arquivo."""

    def choose_folder(self):
        win = webview.windows[0]
        return _first(win.create_file_dialog(webview.FOLDER_DIALOG))

    def choose_open_file(self, filtro=""):
        win = webview.windows[0]
        return _first(win.create_file_dialog(webview.OPEN_DIALOG, file_types=_file_types(filtro)))

    def choose_save_file(self, suggestion="", filtro=""):
        win = webview.windows[0]
        r = win.create_file_dialog(webview.SAVE_DIALOG, save_filename=suggestion or "",
                                   file_types=_file_types(filtro))
        return _first(r)

    def open_external(self, url):
        """Abre um link no navegador padrão do sistema (ex.: página de download)."""
        try:
            webbrowser.open(url)
            return True
        except Exception:
            return False

    def install_update(self, url):
        """Baixa o instalador da nova versão e o executa em modo silencioso,
        reabrindo o app no fim. Só funciona no aplicativo instalado (empacotado).

        O instalador (Inno Setup, per-user) roda sem pedir permissão de admin e,
        via AppMutex, aguarda este app fechar antes de substituir o .exe. Os
        dados ficam em %LOCALAPPDATA% e não são tocados.
        """
        if not getattr(sys, "frozen", False):
            return {"ok": False, "error": "Disponível apenas no aplicativo instalado."}
        if not url:
            return {"ok": False, "error": "Link da atualização indisponível."}
        try:
            tmp = Path(tempfile.gettempdir()) / "ProntoPsi-Update"
            tmp.mkdir(parents=True, exist_ok=True)
            dest = tmp / "ProntoPsi-Setup.exe"
            req = Request(url, headers={"User-Agent": "ProntoPsi"})
            with urlopen(req, timeout=180) as resp, open(dest, "wb") as fh:
                shutil.copyfileobj(resp, fh)
        except Exception as exc:
            return {"ok": False, "error": f"Falha ao baixar a atualização: {exc}"}

        exe = sys.executable
        app_dir = str(Path(exe).parent)
        # Instala silencioso na MESMA pasta e reabre o app no fim.
        cmd = (f'"{dest}" /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /NOCANCEL '
               f'/DIR="{app_dir}" & start "" "{exe}"')
        try:
            DETACHED = 0x00000008 | 0x00000200  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
            subprocess.Popen(["cmd", "/c", cmd], creationflags=DETACHED, close_fds=True)
        except Exception as exc:
            return {"ok": False, "error": f"Falha ao iniciar a instalação: {exc}"}

        # Fecha o app para liberar o .exe (o instalador espera via AppMutex).
        def _close():
            time.sleep(1.2)
            try:
                webview.windows[0].destroy()
            except Exception:
                pass
            os._exit(0)

        threading.Thread(target=_close, daemon=True).start()
        return {"ok": True}


def _create_mutex() -> None:
    """Cria o mutex nomeado que o instalador usa para fechar o app no update."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        # Mantém o handle vivo pela duração do processo (não fechar).
        global _MUTEX_HANDLE
        _MUTEX_HANDLE = ctypes.windll.kernel32.CreateMutexW(None, False, APP_MUTEX)
    except Exception:
        pass


def main() -> None:
    _create_mutex()
    port = _free_port()
    threading.Thread(target=_run_server, args=(port,), daemon=True).start()
    if not _wait_ready(port):
        # Ainda assim abre a janela; a interface mostrara erro de conexao.
        pass

    webview.create_window(
        "ProntoPsi",
        f"http://{HOST}:{port}/",
        js_api=Bridge(),
        width=1200,
        height=820,
        min_size=(940, 620),
    )
    webview.start()


if __name__ == "__main__":
    main()
