from dotenv import load_dotenv
load_dotenv()
import csv, hashlib, hmac, io, os, secrets
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware
from .database import Base, engine, get_db
from .models import Employee, LeaveType, LeaveGrant, LeaveHistory, LeaveLimit, User, AuditLog, LoginAttempt, Cbo, Unit, Council, State, Municipality, Agency, Contract, Sector, Team, BankHourEntry
from .schema_upgrade import upgrade_legacy_schema

APP_ENV = os.getenv("APP_ENV", "development").lower()
CONFIGURED_APP_SECRET_KEY = os.getenv("APP_SECRET_KEY")
APP_SECRET_KEY = CONFIGURED_APP_SECRET_KEY or secrets.token_urlsafe(32)
if APP_ENV == "production":
    if not CONFIGURED_APP_SECRET_KEY or len(CONFIGURED_APP_SECRET_KEY) < 32 or CONFIGURED_APP_SECRET_KEY.startswith("SUBSTITUA_"):
        raise RuntimeError("Defina APP_SECRET_KEY persistente com pelo menos 32 caracteres aleatórios.")
    if not os.getenv("DATABASE_URL", "").startswith(("postgresql://", "postgresql+psycopg://")):
        raise RuntimeError("Em produção, configure PostgreSQL em DATABASE_URL.")
    if os.getenv("COOKIE_HTTPS_ONLY", "false").lower() != "true":
        raise RuntimeError("Em produção, COOKIE_HTTPS_ONLY=true é obrigatório.")

Base.metadata.create_all(bind=engine)
upgrade_legacy_schema(engine)
app = FastAPI(title="MARKYS — Controle de Folgas", version="0.4.0",
              description="Aplicação independente baseada nas regras identificadas no projeto de exemplo.")
app.add_middleware(SessionMiddleware, secret_key=APP_SECRET_KEY,
                   same_site="lax", https_only=os.getenv("COOKIE_HTTPS_ONLY", "false").lower() == "true")
ROOT = Path(__file__).resolve().parent.parent
app.mount("/static", StaticFiles(directory=ROOT / "frontend"), name="static")


def uppercase_text_fields(values: dict, exclude: set[str] | None = None) -> dict:
    excluded = exclude or set()
    for key, value in list(values.items()):
        if key not in excluded and isinstance(value, str):
            values[key] = value.upper()
    return values

def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return "scrypt$" + salt.hex() + "$" + digest.hex()

def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, salt_hex, digest_hex = stored.split("$", 2)
        if scheme != "scrypt": return False
        actual = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt_hex), n=2**14, r=8, p=1)
        return hmac.compare_digest(actual.hex(), digest_hex)
    except (ValueError, TypeError):
        return False

def audit(db: Session, request: Request, action: str, entity: str, entity_id: int | None = None, detail: str | None = None):
    db.add(AuditLog(username=request.session.get("username", "sistema"), action=action,
                    entity=entity, entity_id=entity_id, detail=detail))

@app.on_event("startup")
def seed_default_leave_types():
    defaults = [
        ("Ação", "Folga por participação em ação", 45),
        ("TRE", "Folga relacionada ao TRE", 1825),
        ("Campanha", "Folga por campanha", 45),
        ("Natalícia", "Folga natalícia", 365),
        ("Banco de Horas", "Folga gerada pela conversão de horas trabalhadas", 45),
        ("Doação de Sangue", "Folga por doação de sangue", 45),
    ]
    from sqlalchemy.orm import Session as DbSession
    with DbSession(engine) as db:
        for name, description, validity in defaults:
            existing_type = db.scalar(select(LeaveType).where(LeaveType.name == name))
            if existing_type is None:
                db.add(LeaveType(name=name, description=description, days_validity=validity, active=True))
            else:
                # Mantém os prazos oficiais atualizados também em instalações existentes.
                existing_type.description = description
                existing_type.days_validity = validity
                existing_type.active = True
        db.commit()

@app.on_event("startup")
def reject_default_admin_password_in_production():
    if APP_ENV != "production":
        return
    db_generator = get_db()
    db = next(db_generator)
    try:
        existing = db.scalar(select(User).where(User.username == "admin"))
        if existing and verify_password("admin", existing.password_hash):
            raise RuntimeError("A conta admin ainda usa a senha padrao. Entre localmente, altere a senha do administrador e tente novamente.")
    finally:
        db.close()
        db_generator.close()


@app.on_event("startup")
def seed_admin():
    # Em instalação local limpa, sempre disponibiliza o acesso inicial admin/admin.
    # Em produção, nunca cria credenciais padrão: a configuração precisa ser explícita.
    username = (os.getenv("ADMIN_USERNAME") or ("admin" if APP_ENV != "production" else "")).strip()
    password = os.getenv("ADMIN_PASSWORD") or ("admin" if APP_ENV != "production" else "")
    if not username or not password or password.startswith("SUBSTITUA_") or len(password) < 5:
        return
    # Nunca cria a conta com credencial padrão em modo de rede/produção.
    if APP_ENV == "production" and username.lower() == "admin" and password.lower() == "admin":
        return
    db_generator = get_db()
    db = next(db_generator)
    try:
        existing = db.scalar(select(User).where(User.username == username))
        if existing is None:
            # Garante a conta administrativa padrão mesmo se já houver contas de consulta.
            db.add(User(username=username, password_hash=hash_password(password), role="admin", active=True))
            db.commit()
        elif username.lower() == "admin" and APP_ENV != "production" and not os.getenv("ADMIN_PASSWORD"):
            # No modo local padrão, garante ADMIN/ADMIN conforme solicitado.
            existing.password_hash = hash_password("admin")
            existing.role = "admin"
            existing.active = True
            db.commit()
    finally:
        db.close()
        db_generator.close()

def current_user(request: Request, db: Session = Depends(get_db)) -> User:
    username = request.session.get("username")
    if not username: raise HTTPException(401, "Entre no sistema para continuar.")
    user = db.scalar(select(User).where(User.username == username, User.active.is_(True)))
    if not user:
        request.session.clear()
        raise HTTPException(401, "Sessão inválida. Entre novamente.")
    return user

def admin_user(user: User = Depends(current_user)) -> User:
    if user.role != "admin": raise HTTPException(403, "Esta operação exige perfil administrador.")
    return user

class LoginIn(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=256)
class RegistrationIn(BaseModel):
    cpf: str = Field(min_length=11, max_length=14)
    password: str = Field(min_length=8, max_length=256)
    confirm_password: str = Field(min_length=8, max_length=256)
class ChangePasswordIn(BaseModel):
    current_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=8, max_length=256)
    confirm_password: str = Field(min_length=8, max_length=256)
class UserIn(BaseModel):
    username: str = Field(min_length=3, max_length=80)
    password: str = Field(min_length=12, max_length=256)
    role: str = Field(pattern="^(admin|consulta)$")
class EmployeeIn(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    registration: str | None = Field(default=None, max_length=60)
    category: str | None = Field(default=None, max_length=100)
    birth_date: date | None = None
    sex: str | None = Field(default=None, max_length=1)
    father: str | None = Field(default=None, max_length=160)
    mother: str | None = Field(default=None, max_length=160)
    ddd: str | None = Field(default=None, max_length=2)
    phone: str | None = Field(default=None, max_length=20)
    marital_status: str | None = Field(default=None, max_length=20)
    nationality: str | None = Field(default=None, max_length=100)
    naturality_code: str | None = Field(default=None, max_length=6)
    cns: str | None = Field(default=None, max_length=15)
    cbo_code: str | None = Field(default=None, max_length=6)
    council_sigla: str | None = Field(default=None, max_length=10)
    class_registration: str | None = Field(default=None, max_length=15)
    registration_uf: str | None = Field(default=None, max_length=2)
    unit_cnes: str | None = Field(default=None, max_length=7)
    team_ine: str | None = Field(default=None, max_length=10)
    contract_id: int | None = None
    appointment_date: date | None = None
    possession_date: date | None = None
    entry_date: date | None = None
    exit_date: date | None = None
    exit_reason: str | None = Field(default=None, max_length=200)
    sector_id: int | None = None
    shift: str | None = Field(default=None, max_length=10)
    weekly_hours: str | None = Field(default=None, max_length=2)
    zip_code: str | None = Field(default=None, max_length=9)
    street: str | None = Field(default=None, max_length=200)
    street_number: str | None = Field(default=None, max_length=7)
    complement: str | None = Field(default=None, max_length=100)
    neighborhood: str | None = Field(default=None, max_length=100)
    email: str | None = Field(default=None, max_length=255)
    cpf: str | None = Field(default=None, max_length=14)
    nis: str | None = Field(default=None, max_length=11)
    rg: str | None = Field(default=None, max_length=10)
    rg_issuer: str | None = Field(default=None, max_length=10)
    rg_uf: str | None = Field(default=None, max_length=2)
    rg_issue_date: date | None = None
    ctps: str | None = Field(default=None, max_length=8)
    ctps_series: str | None = Field(default=None, max_length=5)
    ctps_issue_date: date | None = None
    voter_title: str | None = Field(default=None, max_length=12)
    voter_zone: str | None = Field(default=None, max_length=6)
    voter_section: str | None = Field(default=None, max_length=6)
    image_path: str | None = Field(default=None, max_length=255)

class UserUpdateIn(BaseModel):
    role: str | None = Field(default=None, pattern="^(admin|consulta)$")
    active: bool | None = None
    password: str | None = Field(default=None, min_length=12, max_length=256)

class LeaveTypeIn(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    description: str | None = None
    days_validity: int = Field(ge=1, le=3650)
class GrantIn(BaseModel):
    employee_id: int
    leave_type_id: int
    description: str | None = None
    event_date: date
    quantity: Decimal = Field(gt=0, multiple_of=1, max_digits=7, decimal_places=2)
class UseIn(BaseModel):
    grant_id: int
    requested_at: date | None = None
    leave_date: date
    quantity: Decimal = Field(gt=0, max_digits=7, decimal_places=2)
    shift: str = Field(min_length=1, max_length=10)
class LimitIn(BaseModel):
    category: str = Field(min_length=1, max_length=100)
    daily_limit: int | None = Field(default=None, ge=0, le=10000)
class BankHourIn(BaseModel):
    employee_id: int
    entry_date: date
    hours: Decimal = Field(gt=0, multiple_of=1, max_digits=8, decimal_places=2)

@app.get("/")
def home():
    return FileResponse(ROOT / "frontend" / "index.html")

@app.get("/api/health")
def health():
    return {"status":"ok", "application":"MARKYS Controle de Folgas", "version":"0.4.0"}

@app.get("/api/auth/status")
def auth_status(request: Request, db: Session = Depends(get_db)):
    username = request.session.get("username")
    user = db.scalar(select(User).where(User.username == username, User.active.is_(True))) if username else None
    return {"authenticated": bool(user), "username": user.username if user else None,
            "role": user.role if user else None, "setup_required": db.scalar(select(func.count()).select_from(User)) == 0}

def normalize_cpf(value: str) -> str:
    digits = "".join(ch for ch in value if ch.isdigit())
    if len(digits) != 11 or len(set(digits)) == 1:
        raise HTTPException(422, "Informe um CPF válido com 11 dígitos.")
    for length in (9, 10):
        total = sum(int(digits[i]) * (length + 1 - i) for i in range(length))
        digit = (total * 10) % 11
        if digit == 10: digit = 0
        if digit != int(digits[length]):
            raise HTTPException(422, "Informe um CPF válido.")
    return digits

@app.post("/api/auth/register", status_code=201)
def register(payload: RegistrationIn, request: Request, db: Session = Depends(get_db)):
    cpf = normalize_cpf(payload.cpf)
    if payload.password != payload.confirm_password:
        raise HTTPException(422, "As senhas não conferem.")
    if db.scalar(select(User).where(User.username == cpf)):
        raise HTTPException(409, "Já existe uma conta cadastrada com este CPF.")
    item = User(username=cpf, password_hash=hash_password(payload.password), role="consulta", active=True)
    try:
        db.add(item); db.flush(); audit(db, request, "REGISTER", "user", item.id, "cadastro público com perfil consulta"); db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Já existe uma conta cadastrada com este CPF.")
    return {"ok": True, "username": item.username, "role": item.role}

@app.post("/api/auth/change-password")
def change_password(payload: ChangePasswordIn, request: Request, user: User = Depends(admin_user), db: Session = Depends(get_db)):
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(400, "A senha atual está incorreta.")
    if payload.new_password != payload.confirm_password:
        raise HTTPException(422, "A confirmação da nova senha não confere.")
    user.password_hash = hash_password(payload.new_password)
    audit(db, request, "CHANGE_PASSWORD", "user", user.id, "administrador alterou a própria senha")
    db.commit()
    return {"ok": True}

@app.post("/api/auth/login")
def login(payload: LoginIn, request: Request, db: Session = Depends(get_db)):
    remote = request.client.host if request.client else "unknown"
    remote_key = hmac.new(APP_SECRET_KEY.encode(), remote.encode(), hashlib.sha256).hexdigest()
    cutoff = datetime.utcnow() - timedelta(minutes=15)
    db.query(LoginAttempt).filter(LoginAttempt.attempted_at < cutoff).delete(synchronize_session=False)
    failures = db.scalar(select(func.count()).select_from(LoginAttempt).where(
        LoginAttempt.remote_key == remote_key, LoginAttempt.attempted_at >= cutoff)) or 0
    if failures >= 8:
        db.commit()
        raise HTTPException(429, "Muitas tentativas. Aguarde 15 minutos antes de tentar novamente.")
    login_name = payload.username.strip()
    if login_name.lower() == "admin":
        login_name = "admin"
    else:
        login_name = "".join(ch for ch in login_name if ch.isdigit()) if any(ch.isdigit() for ch in login_name) else login_name
    user = db.scalar(select(User).where(User.username == login_name, User.active.is_(True)))
    if not user or not verify_password(payload.password, user.password_hash):
        db.add(LoginAttempt(remote_key=remote_key))
        db.commit()
        raise HTTPException(401, "Usuário ou senha inválidos.")
    db.query(LoginAttempt).filter(LoginAttempt.remote_key == remote_key).delete(synchronize_session=False)
    request.session.clear()
    request.session["username"] = user.username
    audit(db, request, "LOGIN", "user", user.id)
    db.commit()
    return {"username": user.username, "role": user.role}

@app.post("/api/auth/logout")
def logout(request: Request):
    request.session.clear()
    return {"ok": True}

@app.get("/api/users")
def list_users(user: User = Depends(admin_user), db: Session = Depends(get_db)):
    return [{"id":x.id,"username":x.username,"role":x.role,"active":x.active,"created_at":x.created_at.isoformat()}
            for x in db.scalars(select(User).order_by(User.username)).all()]

@app.post("/api/users", status_code=201)
def create_user(payload: UserIn, request: Request, user: User = Depends(admin_user), db: Session = Depends(get_db)):
    username = payload.username.strip()
    if db.scalar(select(User).where(User.username == username)):
        raise HTTPException(409, "Este usuário já existe.")
    item = User(username=username, password_hash=hash_password(payload.password), role=payload.role, active=True)
    try:
        db.add(item); db.flush(); audit(db, request, "CREATE", "user", item.id, payload.role); db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Este usuário já existe.")
    return {"id":item.id,"username":item.username,"role":item.role,"active":item.active}

@app.patch("/api/users/{user_id}")
def update_user(user_id: int, payload: UserUpdateIn, request: Request,
                user: User = Depends(admin_user), db: Session = Depends(get_db)):
    item = db.get(User, user_id)
    if not item: raise HTTPException(404, "Usuário não encontrado.")
    if item.id == user.id and payload.active is False:
        raise HTTPException(422, "Não é permitido desativar a própria conta.")
    if item.id == user.id and payload.role is not None and payload.role != "admin":
        raise HTTPException(422, "Não é permitido rebaixar a própria conta administrativa.")
    removing_admin = item.role == "admin" and ((payload.active is False) or (payload.role == "consulta"))
    if removing_admin:
        active_admins = db.scalar(select(func.count()).select_from(User).where(User.active.is_(True), User.role == "admin")) or 0
        if active_admins <= 1:
            raise HTTPException(422, "Não é permitido remover ou rebaixar o último administrador ativo.")
    if payload.role is not None: item.role = payload.role
    if payload.active is not None: item.active = payload.active
    if payload.password: item.password_hash = hash_password(payload.password)
    audit(db, request, "UPDATE", "user", item.id, "perfil/estado/senha atualizados")
    db.commit()
    return {"id":item.id,"username":item.username,"role":item.role,"active":item.active}

@app.delete("/api/users/{user_id}")
def delete_user(user_id: int, request: Request, user: User = Depends(admin_user), db: Session = Depends(get_db)):
    item = db.get(User, user_id)
    if not item:
        raise HTTPException(404, "Usuário não encontrado.")
    if item.id == user.id:
        raise HTTPException(422, "Não é permitido excluir o próprio usuário conectado.")
    if item.role == "admin" and item.active:
        active_admins = db.scalar(select(func.count()).select_from(User).where(User.active.is_(True), User.role == "admin")) or 0
        if active_admins <= 1:
            raise HTTPException(422, "Não é permitido excluir o último administrador ativo.")
    audit(db, request, "DELETE", "user", item.id, "usuário excluído")
    db.delete(item)
    db.commit()
    return {"ok": True}

def employee_public(e: Employee):
    # Dados pessoais/documentos não são enviados na listagem geral.
    return {"id":e.id,"name":e.name,"registration":e.registration,"category":e.category,
            "birth_date":e.birth_date.isoformat() if e.birth_date else None,"weekly_hours":e.weekly_hours,
            "cbo_code":e.cbo_code,"unit_cnes":e.unit_cnes,"team_ine":e.team_ine,"shift":e.shift,
            "entry_date":e.entry_date.isoformat() if e.entry_date else None,
            "exit_date":e.exit_date.isoformat() if e.exit_date else None,
            "active":bool(e.active and e.exit_date is None)}

def employee_private(e: Employee):
    result = employee_public(e)
    for key in ("birth_date","sex","father","mother","ddd","phone","marital_status","nationality",
                "naturality_code","cns","council_sigla","class_registration","registration_uf","contract_id",
                "appointment_date","possession_date","exit_reason","sector_id","weekly_hours","zip_code",
                "street","street_number","complement","neighborhood","email","cpf","nis","rg","rg_issuer",
                "rg_uf","rg_issue_date","ctps","ctps_series","ctps_issue_date","voter_title","voter_zone",
                "voter_section","image_path"):
        value = getattr(e, key)
        result[key] = value.isoformat() if isinstance(value, date) else value
    return result

@app.get("/api/employees")
def list_employees(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return [employee_public(e) for e in db.scalars(select(Employee).order_by(Employee.name)).all()]

@app.get("/api/employees/{employee_id}")
def get_employee(employee_id: int, user: User = Depends(admin_user), db: Session = Depends(get_db)):
    item = db.get(Employee, employee_id)
    if not item: raise HTTPException(404, "Funcionário não encontrado.")
    return employee_private(item)

@app.post("/api/employees", status_code=201)
def create_employee(payload: EmployeeIn, request: Request, user: User = Depends(admin_user), db: Session = Depends(get_db)):
    name = payload.name.strip()
    registration = payload.registration.strip() if payload.registration and payload.registration.strip() else None
    if not name: raise HTTPException(422, "Informe o nome do funcionário.")
    if registration and db.scalar(select(Employee).where(Employee.registration == registration)):
        raise HTTPException(409, "Já existe funcionário com esta matrícula.")
    values = uppercase_text_fields(payload.model_dump(), {"email"})
    name = name.upper()
    registration = registration.upper() if registration else None
    values["name"] = name
    values["registration"] = registration
    values["category"] = (payload.category or "").strip() or None
    if payload.cbo_code and not values["category"]:
        cbo = db.get(Cbo, payload.cbo_code)
        if cbo: values["category"] = cbo.category
    values["active"] = payload.exit_date is None
    values["email"] = (payload.email or "").strip().lower() or None
    values["cpf"] = (payload.cpf or "").strip() or None
    for key in ("email","cpf"):
        value = values[key]
        if value and db.scalar(select(Employee).where(getattr(Employee,key)==value)):
            raise HTTPException(409, f"Já existe funcionário com este {key.upper()}.")
    item = Employee(**values)
    try:
        db.add(item); db.flush(); audit(db, request, "CREATE", "employee", item.id, name); db.commit(); db.refresh(item)
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Há matrícula, CPF, e-mail ou referência já cadastrada.")
    return employee_public(item)

@app.put("/api/employees/{employee_id}")
def update_employee(employee_id: int, payload: EmployeeIn, request: Request,
                    user: User = Depends(admin_user), db: Session = Depends(get_db)):
    item = db.get(Employee, employee_id)
    if not item: raise HTTPException(404, "Funcionário não encontrado.")
    values = uppercase_text_fields(payload.model_dump(), {"email"})
    values["name"] = payload.name.strip().upper()
    values["registration"] = (payload.registration or "").strip().upper() or None
    values["category"] = (payload.category or "").strip().upper() or None
    values["email"] = (payload.email or "").strip().lower() or None
    values["cpf"] = (payload.cpf or "").strip() or None
    if payload.cbo_code and not values["category"]:
        cbo = db.get(Cbo, payload.cbo_code)
        if cbo: values["category"] = cbo.category
    for key in ("registration","email","cpf"):
        value = values.get(key)
        if value and db.scalar(select(Employee).where(getattr(Employee,key)==value, Employee.id != employee_id)):
            raise HTTPException(409, f"Já existe funcionário com este {key}.")
    values["active"] = payload.exit_date is None
    for key,value in values.items():
        setattr(item,key,value)
    try:
        audit(db, request, "UPDATE", "employee", item.id, item.name); db.commit(); db.refresh(item)
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Há matrícula, CPF, e-mail ou referência já cadastrada.")
    return employee_public(item)

@app.get("/api/lookups")
def list_lookups(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return {
        "cbos":[{"code":x.code,"description":x.description,"category":x.category} for x in db.scalars(select(Cbo).order_by(Cbo.description)).all()],
        "units":[{"cnes":x.cnes,"name":x.name} for x in db.scalars(select(Unit).order_by(Unit.name)).all()],
        "teams":[{"ine":x.ine,"name":x.name} for x in db.scalars(select(Team).order_by(Team.name)).all()],
        "councils":[{"sigla":x.acronym,"name":x.name} for x in db.scalars(select(Council).order_by(Council.name)).all()],
        "states":[{"uf":x.uf,"name":x.name} for x in db.scalars(select(State).order_by(State.uf)).all()],
        "contracts":[{"id":x.id,"kind":x.kind} for x in db.scalars(select(Contract).order_by(Contract.kind)).all()],
        "sectors":[{"id":x.id,"name":x.name} for x in db.scalars(select(Sector).order_by(Sector.name)).all()],
        "agencies":[{"sigla":x.acronym,"name":x.name} for x in db.scalars(select(Agency).order_by(Agency.name)).all()],
        "municipalities":[{"code":x.code,"name":x.name,"uf":x.uf} for x in db.scalars(select(Municipality).order_by(Municipality.name)).all()]
    }

@app.get("/api/reports/employees.csv")
def export_employees(user: User = Depends(admin_user), db: Session = Depends(get_db)):
    out = io.StringIO(); writer = csv.writer(out, delimiter=";")
    writer.writerow(["ID","Nome","Matrícula","Categoria","CBO","Unidade CNES","Equipe INE","Turno","Data de entrada","Data de saída","Ativo"])
    for e in db.scalars(select(Employee).order_by(Employee.name)).all():
        writer.writerow([e.id,e.name,e.registration or "",e.category or "",e.cbo_code or "",e.unit_cnes or "",
                         e.team_ine or "",e.shift or "",e.entry_date or "",e.exit_date or "", "Sim" if e.active and not e.exit_date else "Não"])
    out.seek(0)
    return StreamingResponse(iter([out.getvalue()]), media_type="text/csv; charset=utf-8",
                             headers={"Content-Disposition":"attachment; filename=funcionarios-markys.csv"})

@app.get("/api/leave-types")
def list_leave_types(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return [{"id":t.id,"name":t.name,"description":t.description,"days_validity":t.days_validity,"active":t.active}
            for t in db.scalars(select(LeaveType).order_by(LeaveType.name)).all()]

@app.post("/api/leave-types", status_code=201)
def create_leave_type(payload: LeaveTypeIn, request: Request, user: User = Depends(admin_user), db: Session = Depends(get_db)):
    name = payload.name.strip()
    if db.scalar(select(LeaveType).where(LeaveType.name == name)):
        raise HTTPException(409, "Este tipo de folga já existe.")
    item = LeaveType(name=name, description=payload.description, days_validity=payload.days_validity)
    try:
        db.add(item); db.flush(); audit(db, request, "CREATE", "leave_type", item.id, name); db.commit(); db.refresh(item)
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Este tipo de folga já existe.")
    return {"id":item.id,"name":item.name,"description":item.description,"days_validity":item.days_validity,"active":item.active}

@app.get("/api/grants")
def list_grants(user: User = Depends(current_user), db: Session = Depends(get_db)):
    items = db.scalars(select(LeaveGrant).order_by(LeaveGrant.event_date.desc(), LeaveGrant.id.desc())).all()
    today = date.today()
    return [{"id":g.id,"employee_id":g.employee_id,"employee":g.employee.name,"category":g.employee.category,
             "leave_type_id":g.leave_type_id,"leave_type":g.leave_type.name,"description":g.description,
             "event_date":g.event_date.isoformat(),"valid_until":(g.event_date + timedelta(days=g.leave_type.days_validity)).isoformat(),
             "total_amount":float(g.total_amount),"available_amount":float(g.available_amount),"created_by":g.created_by,
             "expired":today > g.event_date + timedelta(days=g.leave_type.days_validity)} for g in items]

@app.post("/api/grants", status_code=201)
def create_grant(payload: GrantIn, request: Request, user: User = Depends(admin_user), db: Session = Depends(get_db)):
    employee = db.get(Employee, payload.employee_id); leave_type = db.get(LeaveType, payload.leave_type_id)
    if not employee or not employee.active or employee.exit_date is not None: raise HTTPException(404, "Funcionário ativo não encontrado.")
    if not leave_type or not leave_type.active: raise HTTPException(404, "Tipo de folga ativo não encontrado.")
    item = LeaveGrant(employee_id=employee.id, leave_type_id=leave_type.id, description=payload.description,
                      event_date=payload.event_date, total_amount=payload.quantity, available_amount=payload.quantity,
                      created_by=user.username)
    db.add(item); db.flush(); audit(db, request, "CREDIT", "leave_grant", item.id, str(payload.quantity)); db.commit(); db.refresh(item)
    return {"id":item.id,"available_amount":float(item.available_amount)}

@app.get("/api/grants/{grant_id}")
def get_grant(grant_id: int, user: User = Depends(admin_user), db: Session = Depends(get_db)):
    grant = db.get(LeaveGrant, grant_id)
    if not grant: raise HTTPException(404, "Crédito de folga não encontrado.")
    return {"id":grant.id,"employee_id":grant.employee_id,"leave_type_id":grant.leave_type_id,
            "description":grant.description,"event_date":grant.event_date.isoformat(),
            "quantity":float(grant.total_amount),"total_amount":float(grant.total_amount),
            "available_amount":float(grant.available_amount)}

@app.put("/api/grants/{grant_id}")
def update_grant(grant_id: int, payload: GrantIn, request: Request,
                 user: User = Depends(admin_user), db: Session = Depends(get_db)):
    grant = db.scalar(select(LeaveGrant).where(LeaveGrant.id == grant_id).with_for_update())
    if not grant: raise HTTPException(404, "Crédito de folga não encontrado.")
    employee = db.get(Employee, payload.employee_id)
    leave_type = db.get(LeaveType, payload.leave_type_id)
    if not employee or not employee.active or employee.exit_date is not None:
        raise HTTPException(404, "Funcionário ativo não encontrado.")
    if not leave_type or not leave_type.active:
        raise HTTPException(404, "Tipo de folga ativo não encontrado.")
    used = Decimal(str(grant.total_amount)) - Decimal(str(grant.available_amount))
    has_history = (db.scalar(select(func.count()).select_from(LeaveHistory).where(LeaveHistory.grant_id == grant.id)) or 0) > 0
    if has_history and (payload.employee_id != grant.employee_id or payload.leave_type_id != grant.leave_type_id or payload.event_date != grant.event_date):
        raise HTTPException(409, "Este crédito já tem gozos no histórico. Funcionário, tipo e data do evento não podem ser alterados.")
    if payload.quantity < used:
        raise HTTPException(422, f"A quantidade total não pode ficar abaixo do já utilizado ({used}).")
    grant.employee_id = payload.employee_id
    grant.leave_type_id = payload.leave_type_id
    grant.description = payload.description
    grant.event_date = payload.event_date
    grant.total_amount = payload.quantity
    grant.available_amount = payload.quantity - used
    audit(db, request, "UPDATE_CREDIT", "leave_grant", grant.id, f"total={payload.quantity}; utilizado={used}")
    db.commit()
    return {"id":grant.id,"available_amount":float(grant.available_amount)}

@app.delete("/api/grants/{grant_id}")
def delete_grant(grant_id: int, request: Request, user: User = Depends(admin_user), db: Session = Depends(get_db)):
    grant = db.scalar(select(LeaveGrant).where(LeaveGrant.id == grant_id).with_for_update())
    if not grant: raise HTTPException(404, "Crédito de folga não encontrado.")
    if (db.scalar(select(func.count()).select_from(LeaveHistory).where(LeaveHistory.grant_id == grant.id)) or 0) > 0:
        raise HTTPException(409, "Este crédito possui histórico de gozo e não pode ser excluído.")
    audit(db, request, "DELETE_CREDIT", "leave_grant", grant.id, "crédito sem histórico excluído")
    db.delete(grant); db.commit()
    return {"ok":True}

@app.get("/api/history")
def list_history(month: int | None = None, year: int | None = None, category: str | None = None,
                 user: User = Depends(current_user), db: Session = Depends(get_db)):
    stmt = select(LeaveHistory).join(Employee, LeaveHistory.employee_id == Employee.id).order_by(LeaveHistory.leave_date.desc(), LeaveHistory.id.desc())
    if month is not None:
        if month < 1 or month > 12: raise HTTPException(422, "Mês inválido.")
        stmt = stmt.where(func.extract("month", LeaveHistory.leave_date) == month)
    if year is not None: stmt = stmt.where(func.extract("year", LeaveHistory.leave_date) == year)
    if category: stmt = stmt.where(Employee.category == category)
    items = db.scalars(stmt).all()
    return [{"id":h.id,"employee_id":h.employee_id,"employee":h.employee.name,"category":h.employee.category,"grant_id":h.grant_id,
             "leave_type":h.grant.leave_type.name,"event_date":h.grant.event_date.isoformat(),"valid_until":(h.grant.event_date + timedelta(days=h.grant.leave_type.days_validity)).isoformat(),"leave_date":h.leave_date.isoformat(),"requested_at":h.requested_at.isoformat(),
             "quantity":float(h.amount),"shift":h.shift,"created_by":h.created_by} for h in items]

@app.post("/api/history", status_code=201)
def use_leave(payload: UseIn, request: Request, user: User = Depends(admin_user), db: Session = Depends(get_db)):
    grant = db.scalar(select(LeaveGrant).where(LeaveGrant.id == payload.grant_id).with_for_update())
    if not grant: raise HTTPException(404, "Crédito de folga não encontrado.")
    leave_type = db.get(LeaveType, grant.leave_type_id)
    employee = db.get(Employee, grant.employee_id)
    last_day = grant.event_date + timedelta(days=leave_type.days_validity)
    if payload.leave_date > last_day: raise HTTPException(422, "A data de gozo ultrapassa a validade deste crédito.")
    if payload.leave_date < grant.event_date: raise HTTPException(422, "A data de gozo não pode anteceder o evento que gerou a folga.")
    if db.scalar(select(LeaveHistory).where(LeaveHistory.employee_id == employee.id, LeaveHistory.leave_date == payload.leave_date)):
        raise HTTPException(409, "Já existe uma solicitação para este funcionário nesta data.")
    if payload.quantity > Decimal(str(grant.available_amount)): raise HTTPException(422, "Quantidade maior que o saldo disponível.")
    if employee.category:
        limit = db.scalar(select(LeaveLimit).where(LeaveLimit.category == employee.category))
        if limit:
            scheduled = db.scalar(select(func.count()).select_from(LeaveHistory).join(Employee).where(
                Employee.category == employee.category, LeaveHistory.leave_date == payload.leave_date)) or 0
            if scheduled >= limit.daily_limit:
                raise HTTPException(409, f"Limite diário da categoria atingido ({limit.daily_limit}).")
    item = LeaveHistory(employee_id=employee.id, grant_id=grant.id, requested_at=payload.requested_at or date.today(),
                        leave_date=payload.leave_date, amount=payload.quantity, shift=payload.shift.strip(),
                        created_by=user.username)
    grant.available_amount = Decimal(str(grant.available_amount)) - payload.quantity
    try:
        db.add(item); db.flush(); audit(db, request, "USE", "leave_history", item.id, f"{payload.quantity} em {payload.leave_date}"); db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Já existe uma solicitação para este funcionário nesta data.")
    return {"id":item.id,"available_amount":float(grant.available_amount)}

@app.delete("/api/history/{history_id}")
def delete_history(history_id: int, request: Request, user: User = Depends(admin_user), db: Session = Depends(get_db)):
    item = db.scalar(select(LeaveHistory).where(LeaveHistory.id == history_id).with_for_update())
    if not item: raise HTTPException(404, "Registro de histórico não encontrado.")
    grant = db.scalar(select(LeaveGrant).where(LeaveGrant.id == item.grant_id).with_for_update())
    if not grant: raise HTTPException(409, "Crédito vinculado não encontrado; revise o banco antes de cancelar.")
    grant.available_amount = Decimal(str(grant.available_amount)) + Decimal(str(item.amount))
    audit(db, request, "CANCEL_USE", "leave_history", item.id, "Cancelamento e devolução do saldo")
    db.delete(item); db.commit()
    return {"ok":True,"available_amount":float(grant.available_amount)}

@app.get("/api/limits")
def list_limits(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return [{"id":x.id,"category":x.category,"daily_limit":x.daily_limit} for x in db.scalars(select(LeaveLimit).order_by(LeaveLimit.category)).all()]

@app.post("/api/limits")
def save_limit(payload: LimitIn, request: Request, user: User = Depends(admin_user), db: Session = Depends(get_db)):
    item = db.scalar(select(LeaveLimit).where(LeaveLimit.category == payload.category.strip()))
    if payload.daily_limit is None:
        if item:
            audit(db, request, "DELETE_LIMIT", "leave_limit", item.id, "limite removido")
            db.delete(item); db.commit()
        return {"category":payload.category.strip(),"daily_limit":None}
    if item: item.daily_limit = payload.daily_limit
    else:
        item = LeaveLimit(category=payload.category.strip(), daily_limit=payload.daily_limit); db.add(item)
    db.flush(); audit(db, request, "SET_LIMIT", "leave_limit", item.id, str(payload.daily_limit)); db.commit()
    return {"category":item.category,"daily_limit":item.daily_limit}


@app.get("/api/bank-hours")
def list_bank_hours(employee_id: int | None = None, user: User = Depends(current_user), db: Session = Depends(get_db)):
    stmt = select(BankHourEntry).join(Employee).order_by(BankHourEntry.entry_date.desc(), BankHourEntry.id.desc())
    if employee_id is not None: stmt = stmt.where(BankHourEntry.employee_id == employee_id)
    entries = db.scalars(stmt).all()
    return [{"id":x.id,"employee_id":x.employee_id,"employee":x.employee.name,"entry_date":x.entry_date.isoformat(),
             "hours":float(x.hours),"created_by":x.created_by} for x in entries]

@app.post("/api/bank-hours", status_code=201)
def create_bank_hours(payload: BankHourIn, request: Request, user: User = Depends(admin_user), db: Session = Depends(get_db)):
    employee = db.get(Employee, payload.employee_id)
    if not employee or not employee.active: raise HTTPException(404, "Funcionário ativo não encontrado.")
    if not employee.weekly_hours or not str(employee.weekly_hours).isdigit() or int(employee.weekly_hours) <= 0:
        raise HTTPException(422, "Cadastre a carga horária semanal do funcionário antes de lançar horas.")
    db.add(BankHourEntry(employee_id=employee.id, entry_date=payload.entry_date, hours=payload.hours, created_by=user.username))
    db.flush()
    entries = db.scalars(select(BankHourEntry).where(BankHourEntry.employee_id == employee.id).order_by(BankHourEntry.entry_date, BankHourEntry.id)).all()
    # Uma folga corresponde a um dia de trabalho: carga semanal dividida por cinco dias úteis.
    workload = Decimal(str(int(employee.weekly_hours))) / Decimal("5")
    total = sum((Decimal(str(x.hours)) for x in entries), Decimal("0"))
    generated = int(total // workload)
    # Converte cada carga horária completa em uma folga e mantém apenas o saldo de horas.
    prior_generated = sum(1 for x in entries if x.id != entries[-1].id and getattr(x, "_converted", False))
    # Recalcula folgas geradas a partir do total de horas já lançado, sem apagar o histórico de horas.
    existing_bank_type = db.scalar(select(LeaveType).where(LeaveType.name == "Banco de Horas"))
    if existing_bank_type is None:
        existing_bank_type = LeaveType(name="Banco de Horas", description="Folga gerada pela conversão de horas trabalhadas", days_validity=365)
        db.add(existing_bank_type); db.flush()
    existing_generated = db.scalar(select(func.count()).select_from(LeaveGrant).where(
        LeaveGrant.employee_id == employee.id, LeaveGrant.leave_type_id == existing_bank_type.id,
        LeaveGrant.description.like("Conversão automática de banco de horas%"))) or 0
    to_create = max(0, generated - existing_generated)
    for n in range(to_create):
        db.add(LeaveGrant(employee_id=employee.id, leave_type_id=existing_bank_type.id,
            description=f"Conversão automática de banco de horas ({n + existing_generated + 1})",
            event_date=payload.entry_date, total_amount=Decimal("1"), available_amount=Decimal("1"), created_by=user.username))
    audit(db, request, "CREATE", "bank_hours", entries[-1].id, f"{payload.hours} horas; total acumulado={total}; folgas geradas={generated}")
    db.commit()
    return {"ok":True,"total_hours":float(total),"workload_hours":float(workload),
            "generated_leaves":generated,"remaining_hours":float(total % workload)}

@app.get("/api/balances")
def balances(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows=[]; today=date.today()
    for e in db.scalars(select(Employee).where(Employee.active.is_(True)).order_by(Employee.name)).all():
        grants=db.scalars(select(LeaveGrant).where(LeaveGrant.employee_id==e.id)).all()
        for g in grants:
            end=g.event_date+timedelta(days=g.leave_type.days_validity)
            if Decimal(str(g.available_amount)) > 0 and today <= end:
                rows.append({"employee_id":e.id,"employee":e.name,"category":e.category,"leave_type":g.leave_type.name,
                             "event_date":g.event_date.isoformat(),"valid_until":end.isoformat(),"balance":float(g.available_amount)})
    return rows

@app.get("/api/reports/history.csv")
def export_history(user: User = Depends(current_user), db: Session = Depends(get_db)):
    out=io.StringIO(); writer=csv.writer(out, delimiter=";")
    writer.writerow(["Funcionário","Categoria","Tipo de folga","Data de gozo","Data da solicitação","Quantidade","Turno","Registrado por"])
    for h in db.scalars(select(LeaveHistory).order_by(LeaveHistory.leave_date.desc())).all():
        writer.writerow([h.employee.name,h.employee.category or "",h.grant.leave_type.name,h.leave_date.isoformat(),
                         h.requested_at.isoformat(),str(h.amount),h.shift,h.created_by])
    out.seek(0)
    return StreamingResponse(iter([out.getvalue()]), media_type="text/csv; charset=utf-8",
                             headers={"Content-Disposition":"attachment; filename=historico-folgas.csv"})

@app.get("/api/audit")
def audit_log(user: User = Depends(admin_user), db: Session = Depends(get_db)):
    return [{"id":a.id,"username":a.username,"action":a.action,"entity":a.entity,"entity_id":a.entity_id,
             "detail":a.detail,"created_at":a.created_at.isoformat()}
            for a in db.scalars(select(AuditLog).order_by(AuditLog.id.desc()).limit(500)).all()]
