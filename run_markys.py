"""Inicializador desktop do MARKYS — Controle de Folgas para Windows."""
import ctypes
import os
import secrets
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

APP_TITLE = "MARKYS - Controle de Folgas"
APP_USER_MODEL_ID = "MARKYS.ControleDeFolgas"
HOST = os.getenv("MARKYS_HOST", "127.0.0.1")
PORT = int(os.getenv("MARKYS_PORT", "8000"))
BASE_URL = f"http://{HOST}:{PORT}"
NO_DESKTOP = os.getenv("MARKYS_NO_BROWSER") == "1"

# Todos os dados mutáveis ficam fora da pasta de instalação para sobreviver
# a atualizações e desinstalações.
DATA_DIR = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "MARKYS"
DATA_DIR.mkdir(parents=True, exist_ok=True)
ENV_FILE = DATA_DIR / ".env"
os.environ.setdefault("MARKYS_ENV_FILE", str(ENV_FILE))

initial_password = None
if not ENV_FILE.exists():
    initial_password = "admin"
    secret = secrets.token_urlsafe(48)
    ENV_FILE.write_text(
        f"DATABASE_URL=sqlite:///{(DATA_DIR / 'markys_folgas.db').as_posix()}\n"
        "APP_ENV=development\n"
        f"APP_SECRET_KEY={secret}\n"
        "ADMIN_USERNAME=admin\n"
        f"ADMIN_PASSWORD={initial_password}\n"
        "COOKIE_HTTPS_ONLY=false\n",
        encoding="utf-8",
    )

from dotenv import load_dotenv
load_dotenv(ENV_FILE)
# Fixa instalações antigas que ainda apontam para um banco relativo à pasta de execução.
_database_url = os.getenv("DATABASE_URL", "")
if _database_url == "sqlite:///./markys_folgas.db":
    _database_url = f"sqlite:///{(DATA_DIR / 'markys_folgas.db').as_posix()}"
    _env_text = ENV_FILE.read_text(encoding="utf-8")
    _env_text = _env_text.replace("DATABASE_URL=sqlite:///./markys_folgas.db", f"DATABASE_URL={_database_url}")
    ENV_FILE.write_text(_env_text, encoding="utf-8")
    os.environ["DATABASE_URL"] = _database_url

if initial_password:
    (DATA_DIR / "ACESSO-INICIAL.txt").write_text(
        "MARKYS — acesso inicial\n\n"
        f"Endereço local: {BASE_URL}\n"
        "Usuário: admin\n"
        f"Senha: {initial_password}\n\n"
        "Guarde a senha em local seguro e apague este arquivo depois de entrar.\n",
        encoding="utf-8",
    )

import uvicorn
from backend.main import app, hash_password
from backend.database import SessionLocal
from backend.models import User, LoginAttempt
from sqlalchemy import select


def reset_local_admin() -> None:
    """Recupera o acesso local sem apagar funcionários, folgas ou histórico."""
    username = "admin"
    new_password = "admin"
    if not new_password or new_password.startswith("SUBSTITUA_"):
        show_error("Configure ADMIN_PASSWORD no arquivo %LOCALAPPDATA%\\MARKYS\\.env antes de recuperar o acesso.")
        return
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.username == username))
        if user is None:
            user = db.scalar(select(User).where(User.role == "admin").order_by(User.id))
        if user is None:
            user = db.scalar(select(User).order_by(User.id))
        if user is None:
            user = User(username=username, password_hash=hash_password(new_password),
                        role="admin", active=True)
            db.add(user)
        else:
            user.username = username
            user.password_hash = hash_password(new_password)
            user.role = "admin"
            user.active = True
        db.query(LoginAttempt).delete(synchronize_session=False)
        db.commit()
        username = user.username
    (DATA_DIR / "ACESSO-INICIAL.txt").write_text(
        "MARKYS — recuperação de acesso\n\n"
        f"Usuário: {username}\nSenha temporária: {new_password}\n\n"
        "Este arquivo contém dados de recuperação local. Apague-o depois de confirmar o acesso.\n",
        encoding="utf-8",
    )
    try:
        ctypes.windll.user32.MessageBoxW(
            0,
            "A senha de administrador foi redefinida.\n\n"
            "Consulte o arquivo ACESSO-INICIAL.txt na pasta %LOCALAPPDATA%\\MARKYS.\n"
            "Nenhum funcionário, saldo ou histórico foi apagado.",
            APP_TITLE, 0x40,
        )
    except Exception:
        pass


def show_error(message: str) -> None:
    """Exibe erros mesmo no executável Windows sem console."""
    try:
        ctypes.windll.user32.MessageBoxW(0, message, APP_TITLE, 0x10)
    except Exception:
        pass


def wait_until_ready(server: uvicorn.Server, worker: threading.Thread, timeout: int = 40) -> bool:
    deadline = time.monotonic() + timeout
    health_url = f"{BASE_URL}/api/health"
    while time.monotonic() < deadline:
        if not worker.is_alive() or server.started:
            try:
                with urllib.request.urlopen(health_url, timeout=1.5) as response:
                    if response.status == 200:
                        return True
            except (urllib.error.URLError, TimeoutError, OSError):
                if not worker.is_alive():
                    return False
        time.sleep(0.25)
    return False


def run_server_only() -> None:
    """Modo usado pelo teste automatizado do executável."""
    uvicorn.run(app, host=HOST, port=PORT, log_level="critical",
                access_log=False, log_config=None)


def run_desktop() -> None:
    if sys.platform == "win32":
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)
        except Exception:
            pass
    config = uvicorn.Config(app, host=HOST, port=PORT, log_level="critical",
                            access_log=False, log_config=None)
    server = uvicorn.Server(config)
    worker = threading.Thread(target=server.run, name="MARKYS-local-server", daemon=True)
    worker.start()

    if not wait_until_ready(server, worker):
        server.should_exit = True
        show_error(
            "O MARKYS não conseguiu iniciar o serviço local.\n\n"
            "Verifique se outra aplicação está usando a porta "
            f"{PORT} e tente abrir o MARKYS novamente."
        )
        return

    try:
        import webview

        window = webview.create_window(
            APP_TITLE,
            BASE_URL,
            width=1280,
            height=850,
            min_size=(960, 640),
            text_select=True,
        )
        # A janela desktop é a interface principal; não abre uma aba do navegador.
        webview.start(debug=False)
    except Exception as exc:
        show_error(
            "Não foi possível abrir a janela desktop do MARKYS.\n\n"
            "Instale ou atualize o Microsoft Edge WebView2 Runtime e tente novamente.\n\n"
            f"Detalhe: {exc}"
        )
        server.should_exit = True
        worker.join(timeout=5)
        return
    finally:
        server.should_exit = True
        worker.join(timeout=5)


if __name__ == "__main__":
    if "--reset-admin" in sys.argv:
        reset_local_admin()
        raise SystemExit(0)
    if NO_DESKTOP:
        run_server_only()
    else:
        run_desktop()
