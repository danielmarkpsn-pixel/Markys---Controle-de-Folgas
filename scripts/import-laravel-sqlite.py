#!/usr/bin/env python3
"""Importa tabelas de folgas de uma cópia SQLite Laravel para o banco MARKYS.
Não importa contas/senhas Laravel. Faça backup antes e revise o relatório.
"""
import argparse
import sqlite3
import sys
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.database import Base, engine, SessionLocal
from backend.schema_upgrade import upgrade_legacy_schema
from backend.models import (
    Employee, LeaveType, LeaveGrant, LeaveHistory, LeaveLimit,
    Cbo, Unit, Council, State, Municipality, Agency, Contract, Sector, Team,
)

def val(row, *names, default=None):
    for name in names:
        if name in row.keys() and row[name] is not None and row[name] != "":
            return row[name]
    return default

def as_date(value):
    if not value: return None
    if isinstance(value, date): return value
    raw = str(value).strip()
    try: return datetime.fromisoformat(raw.replace("Z", "+00:00")).date()
    except ValueError:
        try: return date.fromisoformat(raw[:10])
        except ValueError: return None

def rows(conn, table):
    return conn.execute('SELECT * FROM "' + table.replace('"','""') + '"').fetchall()

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, help="Caminho para cópia do banco SQLite Laravel")
    parser.add_argument("--dry-run", action="store_true", help="Validar tabelas sem gravar no MARKYS")
    args = parser.parse_args()
    source = Path(args.source).expanduser().resolve()
    if not source.is_file():
        raise SystemExit(f"Arquivo não encontrado: {source}")
    src = sqlite3.connect(source.as_uri() + "?mode=ro", uri=True)
    src.row_factory = sqlite3.Row
    tables = {r[0] for r in src.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    required = {"funcionarios", "tipos_folgas", "folgas", "historico_folgas"}
    missing = sorted(required - tables)
    if missing:
        print("IMPORTAÇÃO CANCELADA: o banco de origem não contém as tabelas de dados: " + ", ".join(missing))
        print("O SQLite incluído no ZIP de exemplo contém apenas tabelas de autenticação/infraestrutura.")
        print("Use uma cópia de backup do banco Laravel já migrado e com os dados reais. Nenhum dado foi alterado.")
        return 2
    print("Tabelas de origem encontradas:", ", ".join(sorted(required | ({"limite_folgas"} & tables))))
    if args.dry_run:
        for t in sorted(required | ({"cbos","unidades","conselhos","estados","municipios","orgaos","contratos","setores","equipes","limite_folgas"} & tables)):
            print(f"  {t}: {src.execute('SELECT COUNT(*) FROM "'+t+'"').fetchone()[0]} registros")
        print("Pré-validação concluída; nenhuma alteração foi gravada.")
        return 0

    Base.metadata.create_all(bind=engine)
    upgrade_legacy_schema(engine)
    db = SessionLocal()
    report = {}
    try:
        # Reference tables: keep source keys when available, do not overwrite existing rows.
        lookup_specs = [
            ("cbos", Cbo, "codigo", lambda r: {"code":str(val(r,"codigo")),"description":str(val(r,"descricao",default="")),"category":val(r,"categoria")}),
            ("unidades", Unit, "cnes", lambda r: {"cnes":str(val(r,"cnes")),"name":str(val(r,"nome",default=""))}),
            ("conselhos", Council, "sigla", lambda r: {"acronym":str(val(r,"sigla")),"name":str(val(r,"nome",default=""))}),
            ("estados", State, "uf", lambda r: {"uf":str(val(r,"uf")),"code":str(val(r,"codigo",default="")),"name":str(val(r,"nome",default=""))}),
            ("municipios", Municipality, "codigo", lambda r: {"code":str(val(r,"codigo")),"name":str(val(r,"nome",default="")),"uf":str(val(r,"uf",default=""))}),
            ("orgaos", Agency, "sigla", lambda r: {"acronym":str(val(r,"sigla")),"name":str(val(r,"nome",default=""))}),
            ("contratos", Contract, "id", lambda r: {"id":int(val(r,"id")),"kind":str(val(r,"tipo",default=""))}),
            ("setores", Sector, "id", lambda r: {"id":int(val(r,"id")),"name":str(val(r,"nome",default=""))}),
            ("equipes", Team, "ine", lambda r: {"ine":str(val(r,"ine")),"name":str(val(r,"nome",default=""))}),
        ]
        for table, model, key, mapper in lookup_specs:
            if table not in tables: continue
            count = 0
            for row in rows(src, table):
                data = mapper(row); keyval = data.get({"codigo":"code","cnes":"cnes","sigla":"acronym","uf":"uf","id":"id","ine":"ine"}.get(key,key))
                existing = db.get(model, keyval)
                if not existing:
                    db.add(model(**data)); count += 1
            db.commit(); report[table] = count

        employee_map = {}
        count = 0
        for r in rows(src, "funcionarios"):
            old_id = int(val(r,"id"))
            old_cbo = str(val(r,"cbo_codigo", default="") or "")
            cbo = db.get(Cbo, old_cbo) if old_cbo else None
            registration = val(r,"matricula")
            existing = db.get(Employee, old_id)
            if not existing and registration:
                existing = db.query(Employee).filter(Employee.registration == str(registration)).first()
            if existing:
                employee_map[old_id] = existing.id
                continue
            data = {
                "name":str(val(r,"nome",default=f"Funcionário {old_id}")),
                "registration":str(registration) if registration else None,
                "category":(cbo.category if cbo else val(r,"categoria")),
                "active":val(r,"data_saida") in (None,""),
                "birth_date":as_date(val(r,"data_nascimento")),"sex":val(r,"sexo"),
                "father":val(r,"pai"),"mother":val(r,"mae"),"ddd":val(r,"ddd"),"phone":val(r,"telefone"),
                "marital_status":val(r,"estado_civil"),"nationality":val(r,"nacionalidade"),
                "naturality_code":val(r,"naturalidade_codigo"),"cns":val(r,"cns"),"cbo_code":old_cbo or None,
                "council_sigla":val(r,"conselho_sigla"),"class_registration":val(r,"registro_classe"),
                "registration_uf":val(r,"registro_uf"),"unit_cnes":val(r,"unidade_cnes"),"team_ine":val(r,"equipe_ine"),
                "contract_id":val(r,"contrato_id"),"appointment_date":as_date(val(r,"data_nomeacao")),
                "possession_date":as_date(val(r,"data_posse")),"entry_date":as_date(val(r,"data_entrada")),
                "exit_date":as_date(val(r,"data_saida")),"exit_reason":val(r,"motivo_saida"),
                "sector_id":val(r,"setor_id"),"shift":val(r,"turno"),"weekly_hours":val(r,"carga_horaria"),
                "zip_code":val(r,"cep"),"street":val(r,"logradouro"),"street_number":val(r,"numero"),
                "complement":val(r,"complemento"),"neighborhood":val(r,"bairro"),"email":val(r,"email"),
                "cpf":val(r,"cpf"),"nis":val(r,"nis"),"rg":val(r,"rg"),"rg_issuer":val(r,"rg_emissor"),
                "rg_uf":val(r,"rg_uf"),"rg_issue_date":as_date(val(r,"rg_emissao")),
                "ctps":val(r,"ctps"),"ctps_series":val(r,"ctps_serie"),"ctps_issue_date":as_date(val(r,"ctps_emissao")),
                "voter_title":val(r,"titulo"),"voter_zone":val(r,"zona"),"voter_section":val(r,"secao"),
                "image_path":val(r,"imagem"),
            }
            if not data["email"]: data["email"] = None
            if not data["cpf"]: data["cpf"] = None
            if old_id > 0 and not db.get(Employee, old_id): data["id"] = old_id
            else: data["id"] = None
            item = Employee(**data); db.add(item); db.flush()
            employee_map[old_id] = item.id; count += 1
        db.commit(); report["funcionarios"] = count

        type_map = {}; count = 0
        for r in rows(src, "tipos_folgas"):
            old_id = int(val(r,"id")); name = str(val(r,"descricao",default=f"Tipo {old_id}"))
            item = db.get(LeaveType, old_id) or db.query(LeaveType).filter(LeaveType.name == name).first()
            if not item:
                item = LeaveType(name=name, days_validity=int(val(r,"dias_validade",default=365)))
                if old_id > 0: item.id = old_id
                db.add(item); db.flush(); count += 1
            type_map[old_id] = item.id
        db.commit(); report["tipos_folgas"] = count

        grant_map = {}; count = 0
        for r in rows(src, "folgas"):
            old_id = int(val(r,"id")); old_employee = int(val(r,"funcionario_id")); old_type = int(val(r,"tipo_id"))
            employee_id = employee_map.get(old_employee); type_id = type_map.get(old_type)
            if not employee_id or not type_id: continue
            item = db.get(LeaveGrant, old_id)
            if not item:
                item = LeaveGrant(employee_id=employee_id, leave_type_id=type_id,
                    description=val(r,"descricao"), event_date=as_date(val(r,"data_evento")) or date.today(),
                    total_amount=val(r,"qtd_total",default=0), available_amount=val(r,"qtd_disponivel",default=0),
                    created_by="importacao")
                if old_id > 0: item.id = old_id
                db.add(item); db.flush(); count += 1
            grant_map[old_id] = item.id
        db.commit(); report["folgas"] = count

        count = 0
        for r in rows(src, "historico_folgas"):
            old_id = int(val(r,"id"))
            if db.get(LeaveHistory, old_id): continue
            employee_id = employee_map.get(int(val(r,"funcionario_id")))
            grant_id = grant_map.get(int(val(r,"folga_id")))
            if not employee_id or not grant_id: continue
            item = LeaveHistory(employee_id=employee_id, grant_id=grant_id,
                requested_at=as_date(val(r,"data_solicitacao")) or date.today(),
                leave_date=as_date(val(r,"data_gozo")) or date.today(),
                amount=val(r,"quantidade",default=0), shift=str(val(r,"turno",default="")),
                created_by="importacao")
            if old_id > 0: item.id = old_id
            try:
                with db.begin_nested():
                    db.add(item)
                    db.flush()
                count += 1
            except Exception:
                print(f"Aviso: histórico de origem ID {old_id} ignorado por conflito de dados.")
        db.commit(); report["historico_folgas"] = count

        if "limite_folgas" in tables:
            count = 0
            for r in rows(src,"limite_folgas"):
                category = str(val(r,"cbo_categoria",default="")).strip()
                if not category: continue
                item = db.query(LeaveLimit).filter(LeaveLimit.category == category).first()
                if not item:
                    db.add(LeaveLimit(category=category,daily_limit=val(r,"limite"))); count += 1
            db.commit(); report["limite_folgas"] = count

        if engine.dialect.name == "postgresql":
            with engine.begin() as conn:
                for table in ("employees","leave_types","leave_grants","leave_history","leave_limits"):
                    conn.exec_driver_sql(f"SELECT setval(pg_get_serial_sequence('{table}','id'), COALESCE((SELECT MAX(id) FROM {table}), 1), EXISTS(SELECT 1 FROM {table}))")
        print("Importação concluída. Registros novos por tabela:")
        for table, number in report.items(): print(f"  {table}: {number}")
        print("Usuários e senhas Laravel NÃO foram importados; crie usuários no MARKYS.")
        print("Confira saldos, datas e relatórios antes de liberar o uso.")
        return 0
    finally:
        db.close(); src.close()

if __name__ == "__main__":
    raise SystemExit(main())
