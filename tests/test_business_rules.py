import os
import sqlite3
import subprocess
import sys
import tempfile
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

_test_db = Path(tempfile.gettempdir()) / ("markys-test-" + str(os.getpid()) + ".db")
_test_db.unlink(missing_ok=True)
os.environ["DATABASE_URL"] = "sqlite:///" + str(_test_db).replace("\\", "/")
os.environ["ADMIN_USERNAME"] = "testadmin"
os.environ["ADMIN_PASSWORD"] = "SenhaForteDeTeste123!"
os.environ["APP_SECRET_KEY"] = "test-secret-not-for-production"

from fastapi.testclient import TestClient
from backend.main import app, hash_password, verify_password

def valid_until(event_date: date, days_validity: int) -> date:
    return event_date + timedelta(days=days_validity)

def can_use(event_date: date, days_validity: int, leave_date: date) -> bool:
    return event_date <= leave_date <= valid_until(event_date, days_validity)

def remaining_balance(current: Decimal, requested: Decimal) -> Decimal:
    if requested <= 0:
        raise ValueError("quantidade deve ser positiva")
    if requested > current:
        raise ValueError("saldo insuficiente")
    return current - requested

def login(client):
    return client.post("/api/auth/login", json={"username":"testadmin","password":"SenhaForteDeTeste123!"})

def test_validity_includes_last_day():
    event = date(2026, 1, 1)
    assert valid_until(event, 30) == date(2026, 1, 31)
    assert can_use(event, 30, date(2026, 1, 31))
    assert not can_use(event, 30, date(2026, 2, 1))

def test_balance_cannot_go_negative():
    assert remaining_balance(Decimal("2.00"), Decimal("1.25")) == Decimal("0.75")
    try:
        remaining_balance(Decimal("1.00"), Decimal("1.01"))
        assert False, "deveria rejeitar saldo insuficiente"
    except ValueError:
        pass

def test_password_hashing():
    hashed = hash_password("SenhaForteDeTeste123!")
    assert hashed != "SenhaForteDeTeste123!"
    assert verify_password("SenhaForteDeTeste123!", hashed)
    assert not verify_password("senha-errada", hashed)

def test_api_login_grant_use_duplicate_cancel_and_expiry():
    with TestClient(app) as client:
        assert client.get("/api/employees").status_code == 401
        assert login(client).status_code == 200
        employee = client.post("/api/employees", json={"name":"Funcionário Teste","registration":"TST-001","category":"Equipe A"})
        assert employee.status_code == 201, employee.text
        leave_type = client.post("/api/leave-types", json={"name":"Compensação teste","description":"teste automatizado","days_validity":2})
        assert leave_type.status_code == 201, leave_type.text
        today = date.today()
        grant = client.post("/api/grants", json={"employee_id":employee.json()["id"],"leave_type_id":leave_type.json()["id"],
            "description":"Teste de validade","event_date":today.isoformat(),"quantity":2})
        assert grant.status_code == 201, grant.text
        grant_id = grant.json()["id"]
        use = client.post("/api/history", json={"grant_id":grant_id,"leave_date":today.isoformat(),
            "quantity":1,"shift":"MANHÃ"})
        assert use.status_code == 201, use.text
        filtered = client.get("/api/history", params={"month":today.month,"year":today.year,"category":"Equipe A"})
        assert filtered.status_code == 200, filtered.text
        assert len(filtered.json()) == 1
        assert client.delete("/api/grants/"+str(grant_id)).status_code == 409
        duplicate = client.post("/api/history", json={"grant_id":grant_id,"leave_date":today.isoformat(),
            "quantity":1,"shift":"TARDE"})
        assert duplicate.status_code == 409
        overdraw = client.post("/api/history", json={"grant_id":grant_id,"leave_date":(today+timedelta(days=2)).isoformat(),
            "quantity":2,"shift":"INTEGRAL"})
        assert overdraw.status_code == 422
        cancel = client.delete("/api/history/"+str(use.json()["id"]))
        assert cancel.status_code == 200
        grant_row = next(g for g in client.get("/api/grants").json() if g["id"] == grant_id)
        assert grant_row["available_amount"] == 2.0
        expired = client.post("/api/history", json={"grant_id":grant_id,"leave_date":(today+timedelta(days=3)).isoformat(),
            "quantity":1,"shift":"INTEGRAL"})
        assert expired.status_code == 422

def test_full_employee_fields_are_admin_only():
    with TestClient(app) as client:
        assert login(client).status_code == 200
        result = client.post("/api/employees", json={"name":"Funcionária Perfil Completo","registration":"TST-002",
            "birth_date":"1990-03-12","cpf":"111.222.333-44","phone":"999999999","cbo_code":"123456",
            "category":"Saúde","unit_cnes":"0000001","team_ine":"0000000001"})
        assert result.status_code == 201, result.text
        employee_id = result.json()["id"]
        listing = client.get("/api/employees").json()
        record = next(x for x in listing if x["id"] == employee_id)
        assert record["cbo_code"] == "123456"
        assert "cpf" not in record
        details = client.get(f"/api/employees/{employee_id}")
        assert details.status_code == 200
        assert details.json()["cpf"] == "111.222.333-44"
        assert details.json()["birth_date"] == "1990-03-12"

def test_user_management_and_role_restrictions():
    with TestClient(app) as client:
        assert login(client).status_code == 200
        created = client.post("/api/users", json={"username":"consulta_teste","password":"SenhaConsulta123!","role":"consulta"})
        assert created.status_code == 201, created.text
        client.post("/api/auth/logout")
        assert client.post("/api/auth/login", json={"username":"consulta_teste","password":"SenhaConsulta123!"}).status_code == 200
        assert client.get("/api/users").status_code == 403
        denied = client.post("/api/employees", json={"name":"Não autorizado"})
        assert denied.status_code == 403

def test_limit_can_be_removed():
    with TestClient(app) as client:
        assert login(client).status_code == 200
        added = client.post("/api/limits", json={"category":"Categoria Teste Limite","daily_limit":2})
        assert added.status_code == 200
        removed = client.post("/api/limits", json={"category":"Categoria Teste Limite","daily_limit":None})
        assert removed.status_code == 200
        assert all(x["category"] != "Categoria Teste Limite" for x in client.get("/api/limits").json())

def test_login_rate_limit():
    with TestClient(app, client=("192.0.2.44", 12345)) as client:
        for _ in range(8):
            response = client.post("/api/auth/login", json={"username":"testadmin","password":"senha-errada"})
            assert response.status_code == 401
        blocked = client.post("/api/auth/login", json={"username":"testadmin","password":"senha-errada"})
        assert blocked.status_code == 429

def test_importer_refuses_sqlite_without_laravel_tables(tmp_path):
    source = tmp_path / "empty-laravel.sqlite"
    connection = sqlite3.connect(source)
    connection.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)")
    connection.commit()
    connection.close()
    script = Path(__file__).resolve().parents[1] / "scripts" / "import-laravel-sqlite.py"
    result = subprocess.run([sys.executable, str(script), "--source", str(source), "--dry-run"],
        capture_output=True, text=True, cwd=Path(__file__).resolve().parents[1])
    assert result.returncode == 2
    assert "IMPORTAÇÃO CANCELADA" in result.stdout
    assert "Nenhum dado foi alterado" in result.stdout

def test_credit_edit_preserves_used_balance_and_delete_without_history():
    with TestClient(app) as client:
        assert login(client).status_code == 200
        employee = client.post("/api/employees", json={"name":"Funcionário Crédito Editável","registration":"TST-003","category":"Equipe B"})
        leave_type = client.post("/api/leave-types", json={"name":"Crédito editável teste","days_validity":10})
        assert employee.status_code == 201 and leave_type.status_code == 201
        today = date.today()
        grant = client.post("/api/grants", json={"employee_id":employee.json()["id"],"leave_type_id":leave_type.json()["id"],
            "event_date":today.isoformat(),"quantity":2})
        assert grant.status_code == 201
        grant_id = grant.json()["id"]
        update = client.put("/api/grants/"+str(grant_id), json={"employee_id":employee.json()["id"],"leave_type_id":leave_type.json()["id"],
            "event_date":today.isoformat(),"quantity":3,"description":"Atualizado"})
        assert update.status_code == 200, update.text
        assert update.json()["available_amount"] == 3.0
        deleted = client.delete("/api/grants/"+str(grant_id))
        assert deleted.status_code == 200, deleted.text

def test_last_admin_cannot_be_disabled():
    with TestClient(app) as client:
        assert login(client).status_code == 200
        admins = [u for u in client.get("/api/users").json() if u["role"] == "admin" and u["active"]]
        assert admins
        response = client.patch("/api/users/"+str(admins[0]["id"]), json={"active":False})
        assert response.status_code == 422

def test_production_refuses_missing_secret_and_postgres():
    root = Path(__file__).resolve().parents[1]
    script = "import backend.main"
    env = os.environ.copy()
    env["APP_ENV"] = "production"
    env["COOKIE_HTTPS_ONLY"] = "true"
    env.pop("APP_SECRET_KEY", None)
    env.pop("DATABASE_URL", None)
    missing_secret = subprocess.run([sys.executable, "-c", script], cwd=root, env=env,
        capture_output=True, text=True)
    assert missing_secret.returncode != 0
    assert "APP_SECRET_KEY persistente" in missing_secret.stderr

    env["APP_SECRET_KEY"] = "x" * 48
    missing_database = subprocess.run([sys.executable, "-c", script], cwd=root, env=env,
        capture_output=True, text=True)
    assert missing_database.returncode != 0
    assert "configure PostgreSQL" in missing_database.stderr
