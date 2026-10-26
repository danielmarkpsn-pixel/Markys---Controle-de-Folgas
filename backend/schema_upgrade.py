"""Safe additive schema upgrade for databases created by early MARKYS prototypes."""
from sqlalchemy import inspect, text

# Existing tables are never dropped. Added employee columns are nullable so an older
# database can be upgraded without inventing personal data.
EMPLOYEE_COLUMNS = {
    "birth_date": "DATE",
    "sex": "VARCHAR(1)",
    "father": "VARCHAR(160)",
    "mother": "VARCHAR(160)",
    "ddd": "VARCHAR(2)",
    "phone": "VARCHAR(20)",
    "marital_status": "VARCHAR(20)",
    "nationality": "VARCHAR(100)",
    "naturality_code": "VARCHAR(6)",
    "cns": "VARCHAR(15)",
    "cbo_code": "VARCHAR(6)",
    "council_sigla": "VARCHAR(10)",
    "class_registration": "VARCHAR(15)",
    "registration_uf": "VARCHAR(2)",
    "unit_cnes": "VARCHAR(7)",
    "team_ine": "VARCHAR(10)",
    "contract_id": "INTEGER",
    "appointment_date": "DATE",
    "possession_date": "DATE",
    "entry_date": "DATE",
    "exit_date": "DATE",
    "exit_reason": "VARCHAR(200)",
    "sector_id": "INTEGER",
    "shift": "VARCHAR(10)",
    "weekly_hours": "VARCHAR(2)",
    "zip_code": "VARCHAR(9)",
    "street": "VARCHAR(200)",
    "street_number": "VARCHAR(7)",
    "complement": "VARCHAR(100)",
    "neighborhood": "VARCHAR(100)",
    "email": "VARCHAR(255)",
    "cpf": "VARCHAR(14)",
    "nis": "VARCHAR(11)",
    "rg": "VARCHAR(10)",
    "rg_issuer": "VARCHAR(10)",
    "rg_uf": "VARCHAR(2)",
    "rg_issue_date": "DATE",
    "ctps": "VARCHAR(8)",
    "ctps_series": "VARCHAR(5)",
    "ctps_issue_date": "DATE",
    "voter_title": "VARCHAR(12)",
    "voter_zone": "VARCHAR(6)",
    "voter_section": "VARCHAR(6)",
    "image_path": "VARCHAR(255)",
}

def upgrade_legacy_schema(engine):
    inspector = inspect(engine)
    if "employees" not in inspector.get_table_names():
        return
    existing = {column["name"] for column in inspector.get_columns("employees")}
    with engine.begin() as connection:
        for name, sql_type in EMPLOYEE_COLUMNS.items():
            if name not in existing:
                connection.execute(text(f'ALTER TABLE employees ADD COLUMN "{name}" {sql_type}'))
