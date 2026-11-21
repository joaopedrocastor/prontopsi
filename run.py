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

# Andamento do auto-update (lido pela tela via Bridge.update_progress).
_UPDATE_STATE = {"stage": "", "done": 0, "total": 0}


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


def _downloads_dir() -> Path:
    """Pasta Downloads do usuário (respeita se ela foi movida no Windows)."""
    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes
            import uuid

            class GUID(ctypes.Structure):
                _fields_ = [("Data1", wintypes.DWORD), ("Data2", wintypes.WORD),
                            ("Data3", wintypes.WORD), ("Data4", ctypes.c_ubyte * 8)]

            u = uuid.UUID("{374DE290-123F-4565-9164-39C4925E467B}")  # FOLDERID_Downloads
            guid = GUID(u.fields[0], u.fields[1], u.fields[2],
                        (ctypes.c_ubyte * 8).from_buffer_copy(u.bytes[8:]))
            ptr = ctypes.c_wchar_p()
            if ctypes.windll.shell32.SHGetKnownFolderPath(ctypes.byref(guid), 0, None,
                                                          ctypes.byref(ptr)) == 0:
                path = Path(ptr.value)
                ctypes.windll.ole32.CoTaskMemFree(ptr)
                if path.is_dir():
                    return path
        except Exception:
            pass
    path = Path.home() / "Downloads"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _safe_filename(name: str) -> str:
    name = "".join("_" if c in '<>:"/\\|?*' or ord(c) < 32 else c for c in (name or "")).strip(" .")
    return name or "arquivo.pdf"


def _unique_path(folder: Path, name: str) -> Path:
    dest = folder / name
    stem, suffix, n = dest.stem, dest.suffix, 1
    while dest.exists():
        dest = folder / f"{stem} ({n}){suffix}"
        n += 1
    return dest


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

    def save_download(self, filename, b64):
        """Grava um arquivo (base64) na pasta Downloads e devolve o caminho.

        A janela do pywebview não faz downloads (<a download> é ignorado), então
        os PDFs gerados na tela chegam aqui. Não sobrescreve: "nome (1).pdf".
        """
        import base64
        try:
            data = base64.b64decode(b64 or "")
            dest = _unique_path(_downloads_dir(), _safe_filename(filename))
            dest.write_bytes(data)
            return {"ok": True, "path": str(dest)}
        except Exception as exc:
            return {"ok": False, "error": f"Não foi possível salvar em Downloads: {exc}"}

    def update_progress(self):
        """Andamento do auto-update para a barra de progresso da tela."""
        return dict(_UPDATE_STATE)

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
            _UPDATE_STATE.update(stage="download", done=0, total=0)
            with urlopen(req, timeout=180) as resp, open(dest, "wb") as fh:
                esperado = int(resp.headers.get("Content-Length") or 0)
                _UPDATE_STATE["total"] = esperado
                while True:
                    bloco = resp.read(256 * 1024)
                    if not bloco:
                        break
                    fh.write(bloco)
                    _UPDATE_STATE["done"] += len(bloco)
            if esperado and dest.stat().st_size != esperado:
                _UPDATE_STATE["stage"] = "erro"
                return {"ok": False, "error": "Download da atualização incompleto. Tente de novo."}
        except Exception as exc:
            _UPDATE_STATE["stage"] = "erro"
            return {"ok": False, "error": f"Falha ao baixar a atualização: {exc}"}
        _UPDATE_STATE["stage"] = "instalando"

        try:
            script = _write_update_script(tmp, dest, Path(sys.executable))
            # Script do PowerShell (sem 'cmd /c', cujas aspas quebravam o comando):
            # espera este app fechar, instala silencioso e reabre o app — mesmo
            # se a instalação falhar, para o app nunca ficar fechado.
            CREATE_NO_WINDOW = 0x08000000
            BREAKAWAY = 0x01000000       # CREATE_BREAKAWAY_FROM_JOB
            NEW_GROUP = 0x00000200       # CREATE_NEW_PROCESS_GROUP
            args = ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
                    "-WindowStyle", "Hidden", "-File", str(script)]
            try:
                subprocess.Popen(args, creationflags=CREATE_NO_WINDOW | NEW_GROUP | BREAKAWAY,
                                 close_fds=True, cwd=str(tmp))
            except OSError:  # job sem permissão de breakaway
                subprocess.Popen(args, creationflags=CREATE_NO_WINDOW | NEW_GROUP,
                                 close_fds=True, cwd=str(tmp))
        except Exception as exc:
            _UPDATE_STATE["stage"] = "erro"
            return {"ok": False, "error": f"Falha ao iniciar a instalação: {exc}"}

        # Fecha o app para liberar o .exe (o script espera ele terminar). Dá
        # tempo da tela mostrar "Instalando…" antes de fechar.
        def _close():
            time.sleep(2.5)
            try:
                webview.windows[0].destroy()
            except Exception:
                pass
            os._exit(0)

        threading.Thread(target=_close, daemon=True).start()
        return {"ok": True}


def _ps_quote(value) -> str:
    """Literal de string do PowerShell (aspas simples, '' escapa ')."""
    return "'" + str(value).replace("'", "''") + "'"


def _write_update_script(tmp: Path, setup: Path, exe: Path) -> Path:
    """Gera o script que conclui o auto-update fora do processo do app.

    Espera os processos deste app terminarem (no PyInstaller onefile há o
    processo do bootloader + o filho), roda o instalador em modo silencioso
    na mesma pasta (com log) e reabre o app.
    """
    pids = [os.getpid()]
    try:
        ppid = os.getppid()
        out = subprocess.run(
            ["tasklist", "/FI", f"PID eq {ppid}", "/FO", "CSV", "/NH"],
            capture_output=True, text=True, timeout=5,
            creationflags=0x08000000).stdout
        if exe.name.lower() in out.lower():
            pids.append(ppid)
    except Exception:
        pass
    log = tmp / "update-install.log"
    script = tmp / "aplicar-atualizacao.ps1"
    texto = f"""$ErrorActionPreference = 'Continue'
$setup = {_ps_quote(setup)}
$exe = {_ps_quote(exe)}
$dir = {_ps_quote(exe.parent)}
$log = {_ps_quote(log)}
$trace = {_ps_quote(tmp / "update-trace.txt")}
"inicio $(Get-Date -Format s)" | Out-File $trace -Encoding utf8
# 1) Espera o app fechar (até 60 s) para o instalador poder trocar o .exe.
foreach ($p in @({", ".join(str(p) for p in pids)})) {{
  try {{ Wait-Process -Id $p -Timeout 60 -ErrorAction Stop }} catch {{}}
}}
Start-Sleep -Seconds 1
# 2) Instala na mesma pasta.
# /SILENT (não /VERYSILENT): sem perguntas, mas mostra a janela com a barra
# de progresso da instalação enquanto o app está fechado.
$argsSetup = @('/SILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/NOCANCEL',
               ('/DIR="' + $dir + '"'), ('/LOG="' + $log + '"'))
try {{
  $proc = Start-Process -FilePath $setup -ArgumentList $argsSetup -Wait -PassThru
  "instalador saiu com codigo $($proc.ExitCode)" | Out-File $trace -Append -Encoding utf8
}} catch {{
  "falha ao rodar instalador: $_" | Out-File $trace -Append -Encoding utf8
}}
# 3) Reabre o app (versão nova, ou a antiga se a instalação falhou).
Start-Process -FilePath $exe -WorkingDirectory $dir
"reaberto $(Get-Date -Format s)" | Out-File $trace -Append -Encoding utf8
"""
    # UTF-8 com BOM: o Windows PowerShell 5.1 lê caminhos acentuados (ex.: "MARCÃO").
    script.write_text(texto, encoding="utf-8-sig")
    return script


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
