import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Automatically ensure venv site-packages is in sys.path if present
VENV_SITE = BASE_DIR / "venv" / "Lib" / "site-packages"
if VENV_SITE.exists() and str(VENV_SITE) not in sys.path:
    sys.path.insert(0, str(VENV_SITE))

from config.settings import settings
from utils.logger import logger
from database.connection import get_connection, test_connection, get_server_connection
from utils.exceptions import DatabaseConnectionError

SCHEMA_FILE = BASE_DIR / "database" / "postgres_schema.sql"
SEED_FILE = BASE_DIR / "database" / "postgres_seed_data.sql"

_LAST_INIT_ERROR: str = ""


def get_last_init_error() -> str:
    """Returns the most recent database initialization error message."""
    global _LAST_INIT_ERROR
    return _LAST_INIT_ERROR


def execute_sql_file(connection, file_path: Path):
    """Parses and executes a multi-statement SQL script file safely and idempotently in PostgreSQL."""
    if not file_path.exists():
        raise FileNotFoundError(f"SQL file not found at: {file_path}")

    logger.info(f"Executing PostgreSQL script: {file_path.name}...")
    sql_content = file_path.read_text(encoding="utf-8")

    cursor = connection.cursor()
    try:
        # PostgreSQL handles multi-statement scripts natively via cursor.execute()
        cursor.execute(sql_content)
        connection.commit()
        cursor.close()
        logger.info(f"Successfully processed {file_path.name}.")
    except Exception as exc:
        connection.rollback()
        cursor.close()
        logger.error(f"Error executing SQL in {file_path.name}: {exc}")
        raise exc


def verify_database_schema(connection) -> dict:
    """Verifies table creation and record counts across core PostgreSQL tables."""
    expected_tables = [
        "system_settings",
        "users",
        "departments",
        "faculty",
        "lab_instructors",
        "students",
        "student_marks",
        "leave_types",
        "leave_balance",
        "leave_applications",
        "attendance",
        "grace_minutes",
        "substitute_assignments",
        "holidays",
        "stationery_requests",
        "audit_logs",
        "faculty_subjects_handled",
        "profile_change_requests",
        "profile_change_audit",
    ]

    cursor = connection.cursor()
    cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';")
    existing_tables = [row[0].lower() for row in cursor.fetchall()]

    summary = {}
    for table in expected_tables:
        if table in existing_tables:
            cursor.execute(f'SELECT COUNT(*) FROM "{table}";')
            count = cursor.fetchone()[0]
            summary[table] = {"status": "EXISTS", "count": count}
        else:
            summary[table] = {"status": "MISSING", "count": 0}

    cursor.close()
    return summary


def initialize_database(return_details: bool = False):
    """
    Primary database migration runner function for PostgreSQL 16+.
    Connects to server, creates database if needed, applies schema,
    inserts seed data idempotently, and verifies table presence.
    Returns:
        bool: True on success, False on error (when return_details is False).
        tuple[bool, str]: (Success boolean, Status message) (when return_details is True).
    """
    global _LAST_INIT_ERROR
    _LAST_INIT_ERROR = ""
    logger.info("Starting PostgreSQL Database Initialization & Seeding...")

    try:
        # 1. Connect to PostgreSQL maintenance database ('postgres') to ensure target DB exists
        logger.info(f"Connecting to PostgreSQL server at {settings.DB_HOST}:{settings.DB_PORT}...")
        server_conn = get_server_connection(maintenance_db="postgres")
        cursor = server_conn.cursor()

        # Check if target database already exists
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s;", (settings.DB_NAME,))
        exists = cursor.fetchone()
        if not exists:
            logger.info(f"Database '{settings.DB_NAME}' does not exist. Creating...")
            cursor.execute(f'CREATE DATABASE "{settings.DB_NAME}" WITH ENCODING \'UTF8\';')
            logger.info(f"Database '{settings.DB_NAME}' created successfully.")
        else:
            logger.info(f"Database '{settings.DB_NAME}' already exists.")

        cursor.close()
        server_conn.close()

        # 2. Connect directly to target database
        logger.info(f"Connecting directly to target database '{settings.DB_NAME}'...")
        conn = get_connection()

        # 3. Apply schema definition
        execute_sql_file(conn, SCHEMA_FILE)

        # 4. Execute seed data DML
        execute_sql_file(conn, SEED_FILE)

        # 5. Verify Database Schema Integrity
        summary = verify_database_schema(conn)
        conn.close()

        logger.info("==================================================")
        logger.info("PostgreSQL Schema Verification Summary:")
        missing_found = False
        for tbl, data in summary.items():
            status_str = f"[OK] ({data['count']} rows)" if data["status"] == "EXISTS" else "[MISSING]"
            logger.info(f" - Table '{tbl}': {status_str}")
            if data["status"] != "EXISTS":
                missing_found = True
        logger.info("==================================================")

        if missing_found:
            missing_tables = [t for t, d in summary.items() if d["status"] != "EXISTS"]
            _LAST_INIT_ERROR = f"Initialization completed but required tables are missing: {', '.join(missing_tables)}"
            logger.error(_LAST_INIT_ERROR)
            return (False, _LAST_INIT_ERROR) if return_details else False

        success_msg = (
            f"Successfully connected to PostgreSQL '{settings.DB_NAME}' and verified all {len(summary)} "
            "tables with initial seed records!"
        )
        logger.info(success_msg)
        return (True, success_msg) if return_details else True

    except DatabaseConnectionError as exc:
        _LAST_INIT_ERROR = f"Could not connect to PostgreSQL server ({exc.message}). Detail: {exc.original_error or exc}"
        logger.error(f"Database initialization failed: {_LAST_INIT_ERROR}")
        return (False, _LAST_INIT_ERROR) if return_details else False
    except Exception as exc:
        _LAST_INIT_ERROR = str(exc)
        logger.error(f"Database initialization failed: {exc}")
        return (False, _LAST_INIT_ERROR) if return_details else False


if __name__ == "__main__":
    res = initialize_database(return_details=True)
    success, msg = res if isinstance(res, tuple) else (res, "")
    print(f"Result: {success} - {msg}")
    sys.exit(0 if success else 1)
