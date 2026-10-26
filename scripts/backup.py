#!/usr/bin/env python3
"""Backup consistente SQLite ou PostgreSQL com retenção de 30 dias."""
import os, shutil, sqlite3, subprocess, sys
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlsplit, unquote
from dotenv import dotenv_values

ROOT=Path(__file__).resolve().parents[1]
BACKUPS=ROOT/"backups"
BACKUPS.mkdir(exist_ok=True)
cfg=dotenv_values(ROOT/".env")
url=cfg.get("DATABASE_URL","sqlite:///./markys_folgas.db")
stamp=datetime.now().strftime("%Y%m%d-%H%M%S")
try:
    if url.startswith("sqlite:///"):
        raw=url[len("sqlite:///"):]
        source=Path(raw)
        if not source.is_absolute(): source=(ROOT/source).resolve()
        if not source.is_file(): raise RuntimeError(f"Banco SQLite não encontrado: {source}")
        dest=BACKUPS/f"markys-folgas-{stamp}.db"
        src=sqlite3.connect(str(source)); dst=sqlite3.connect(str(dest))
        try: src.backup(dst)
        finally: dst.close(); src.close()
        print(f"Backup SQLite criado: {dest}")
    elif url.startswith(("postgresql://","postgres://","postgresql+psycopg://")):
        if not shutil.which("pg_dump"): raise RuntimeError("pg_dump não encontrado. Instale as ferramentas de cliente PostgreSQL.")
        normalized=url.replace("postgresql+psycopg://","postgresql://",1)
        parts=urlsplit(normalized)
        env=os.environ.copy()
        if parts.password: env["PGPASSWORD"]=unquote(parts.password)
        safe_netloc=parts.hostname or "localhost"
        if parts.port: safe_netloc += f":{parts.port}"
        if parts.username: safe_netloc=unquote(parts.username)+"@"+safe_netloc
        safe_url=parts._replace(netloc=safe_netloc).geturl()
        dest=BACKUPS/f"markys-folgas-{stamp}.dump"
        cmd=["pg_dump","--format=custom","--no-owner","--no-acl","--file",str(dest),"--dbname",safe_url]
        result=subprocess.run(cmd,env=env,capture_output=True,text=True)
        if result.returncode: raise RuntimeError(result.stderr.strip() or "pg_dump falhou")
        print(f"Backup PostgreSQL criado: {dest}")
    else:
        raise RuntimeError("DATABASE_URL não suportada. Use SQLite ou PostgreSQL.")
    cutoff=datetime.now().timestamp()-30*24*60*60
    for p in BACKUPS.iterdir():
        if p.is_file() and p != dest and p.stat().st_mtime < cutoff and p.suffix in (".db",".dump"):
            p.unlink()
    print("Retenção aplicada: backups com mais de 30 dias foram removidos.")
except Exception as exc:
    print(f"ERRO no backup: {exc}",file=sys.stderr); sys.exit(1)
