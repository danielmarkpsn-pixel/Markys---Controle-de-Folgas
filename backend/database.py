from dotenv import load_dotenv
load_dotenv()
import os
import shutil
import sys
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

def _user_data_dir() -> Path:
    if os.name == "nt":
        base = Path(os.getenv("LOCALAPPDATA") or (Path.home() / "AppData" / "Local"))
    else:
        base = Path(os.getenv("XDG_DATA_HOME") or (Path.home() / ".local" / "share"))
    target = base / "MARKYS"
    target.mkdir(parents=True, exist_ok=True)
    return target

DATA_DIR = _user_data_dir()
LEGACY_DATABASE = Path.cwd() / "markys_folgas.db"
USER_DATABASE = DATA_DIR / "markys_folgas.db"
if not os.getenv("DATABASE_URL") and not USER_DATABASE.exists() and LEGACY_DATABASE.exists():
    try:
        shutil.copy2(LEGACY_DATABASE, USER_DATABASE)
    except OSError:
        pass

DATABASE_URL = os.getenv("DATABASE_URL") or ("sqlite:///" + USER_DATABASE.as_posix())
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
