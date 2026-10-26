from datetime import datetime, date
from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, Text, Boolean, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base

# Tabelas de referência equivalentes às tabelas organizacionais do projeto Laravel.
class Cbo(Base):
    __tablename__ = "cbos"
    code: Mapped[str] = mapped_column("codigo", String(6), primary_key=True)
    description: Mapped[str] = mapped_column("descricao", String(255))
    category: Mapped[str | None] = mapped_column("categoria", String(100), nullable=True, index=True)

class Unit(Base):
    __tablename__ = "unidades"
    cnes: Mapped[str] = mapped_column(String(7), primary_key=True)
    name: Mapped[str] = mapped_column("nome", String(255))

class Council(Base):
    __tablename__ = "conselhos"
    acronym: Mapped[str] = mapped_column("sigla", String(10), primary_key=True)
    name: Mapped[str] = mapped_column("nome", String(255))

class State(Base):
    __tablename__ = "estados"
    uf: Mapped[str] = mapped_column(String(2), primary_key=True)
    code: Mapped[str] = mapped_column("codigo", String(2), unique=True)
    name: Mapped[str] = mapped_column("nome", String(20))

class Municipality(Base):
    __tablename__ = "municipios"
    code: Mapped[str] = mapped_column("codigo", String(6), primary_key=True)
    name: Mapped[str] = mapped_column("nome", String(255))
    uf: Mapped[str] = mapped_column(String(2), index=True)

class Agency(Base):
    __tablename__ = "orgaos"
    acronym: Mapped[str] = mapped_column("sigla", String(10), primary_key=True)
    name: Mapped[str] = mapped_column("nome", String(255))

class Contract(Base):
    __tablename__ = "contratos"
    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column("tipo", String(50))

class Sector(Base):
    __tablename__ = "setores"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column("nome", String(50))

class Team(Base):
    __tablename__ = "equipes"
    ine: Mapped[str] = mapped_column(String(10), primary_key=True)
    name: Mapped[str] = mapped_column("nome", String(50))

class Employee(Base):
    __tablename__ = "employees"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160), index=True)
    registration: Mapped[str | None] = mapped_column(String(60), unique=True, nullable=True)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Dados pessoais do esquema de origem. Campos opcionais para importação gradual.
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    sex: Mapped[str | None] = mapped_column(String(1), nullable=True)
    father: Mapped[str | None] = mapped_column(String(160), nullable=True)
    mother: Mapped[str | None] = mapped_column(String(160), nullable=True)
    ddd: Mapped[str | None] = mapped_column(String(2), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    marital_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    nationality: Mapped[str | None] = mapped_column(String(100), nullable=True)
    naturality_code: Mapped[str | None] = mapped_column(String(6), nullable=True)
    cns: Mapped[str | None] = mapped_column(String(15), nullable=True)

    # Dados funcionais e referências de organização do projeto de exemplo.
    cbo_code: Mapped[str | None] = mapped_column(String(6), nullable=True, index=True)
    council_sigla: Mapped[str | None] = mapped_column(String(10), nullable=True)
    class_registration: Mapped[str | None] = mapped_column(String(15), nullable=True)
    registration_uf: Mapped[str | None] = mapped_column(String(2), nullable=True)
    unit_cnes: Mapped[str | None] = mapped_column(String(7), nullable=True, index=True)
    team_ine: Mapped[str | None] = mapped_column(String(10), nullable=True, index=True)
    contract_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    appointment_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    possession_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    entry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    exit_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    exit_reason: Mapped[str | None] = mapped_column(String(200), nullable=True)
    sector_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    shift: Mapped[str | None] = mapped_column(String(10), nullable=True)
    weekly_hours: Mapped[str | None] = mapped_column(String(2), nullable=True)

    # Endereço e documentação. A aplicação não mostra estes dados em listagens.
    zip_code: Mapped[str | None] = mapped_column(String(9), nullable=True)
    street: Mapped[str | None] = mapped_column(String(200), nullable=True)
    street_number: Mapped[str | None] = mapped_column(String(7), nullable=True)
    complement: Mapped[str | None] = mapped_column(String(100), nullable=True)
    neighborhood: Mapped[str | None] = mapped_column(String(100), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    cpf: Mapped[str | None] = mapped_column(String(14), unique=True, nullable=True)
    nis: Mapped[str | None] = mapped_column(String(11), nullable=True)
    rg: Mapped[str | None] = mapped_column(String(10), nullable=True)
    rg_issuer: Mapped[str | None] = mapped_column(String(10), nullable=True)
    rg_uf: Mapped[str | None] = mapped_column(String(2), ForeignKey("estados.uf"), nullable=True)
    rg_issue_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    ctps: Mapped[str | None] = mapped_column(String(8), nullable=True)
    ctps_series: Mapped[str | None] = mapped_column(String(5), nullable=True)
    ctps_issue_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    voter_title: Mapped[str | None] = mapped_column(String(12), nullable=True)
    voter_zone: Mapped[str | None] = mapped_column(String(6), nullable=True)
    voter_section: Mapped[str | None] = mapped_column(String(6), nullable=True)
    image_path: Mapped[str | None] = mapped_column(String(255), nullable=True)

class LeaveType(Base):
    __tablename__ = "leave_types"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    days_validity: Mapped[int] = mapped_column(Integer, default=365, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

class LeaveGrant(Base):
    __tablename__ = "leave_grants"
    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), index=True)
    leave_type_id: Mapped[int] = mapped_column(ForeignKey("leave_types.id"), index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    event_date: Mapped[date] = mapped_column(Date, index=True)
    total_amount: Mapped[float] = mapped_column(Numeric(7, 2))
    available_amount: Mapped[float] = mapped_column(Numeric(7, 2))
    created_by: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    employee: Mapped["Employee"] = relationship()
    leave_type: Mapped["LeaveType"] = relationship()

class LeaveHistory(Base):
    __tablename__ = "leave_history"
    __table_args__ = (UniqueConstraint("employee_id", "leave_date", name="uq_employee_leave_date"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), index=True)
    grant_id: Mapped[int] = mapped_column(ForeignKey("leave_grants.id"), index=True)
    requested_at: Mapped[date] = mapped_column(Date, default=date.today)
    leave_date: Mapped[date] = mapped_column(Date, index=True)
    amount: Mapped[float] = mapped_column(Numeric(7, 2))
    shift: Mapped[str] = mapped_column(String(10))
    created_by: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    employee: Mapped["Employee"] = relationship()
    grant: Mapped["LeaveGrant"] = relationship()

class LeaveLimit(Base):
    __tablename__ = "leave_limits"
    id: Mapped[int] = mapped_column(primary_key=True)
    category: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    daily_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(256))
    role: Mapped[str] = mapped_column(String(20), default="consulta")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class LoginAttempt(Base):
    __tablename__ = "login_attempts"
    id: Mapped[int] = mapped_column(primary_key=True)
    remote_key: Mapped[str] = mapped_column(String(128), index=True)
    attempted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(80), index=True)
    action: Mapped[str] = mapped_column(String(80), index=True)
    entity: Mapped[str] = mapped_column(String(80))
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class BankHourEntry(Base):
    __tablename__ = "bank_hour_entries"
    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), index=True)
    entry_date: Mapped[date] = mapped_column(Date, index=True)
    hours: Mapped[float] = mapped_column(Numeric(8, 2))
    created_by: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    employee: Mapped["Employee"] = relationship()
