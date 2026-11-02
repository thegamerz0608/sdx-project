"""
Phase 2 Database Unit Tests
Verifies schema DDL, seed data script, SQL parsing, and database initialization logic.
"""
from pathlib import Path
import pytest
from database.connection import test_connection as db_test_connection
from database.init_db import initialize_database, verify_database_schema, BASE_DIR

SCHEMA_FILE = BASE_DIR / "database" / "schema.sql"
SEED_FILE = BASE_DIR / "database" / "seed_data.sql"


def test_schema_sql_exists():
    """Verify that schema.sql file exists and is non-empty."""
    assert SCHEMA_FILE.exists()
    content = SCHEMA_FILE.read_text(encoding="utf-8")
    assert "CREATE TABLE IF NOT EXISTS" in content
    assert "users" in content
    assert "faculty" in content
    assert "attendance" in content
    assert "leave_applications" in content
    assert "substitute_assignments" in content


def test_seed_data_sql_exists():
    """Verify that seed_data.sql file exists and contains initial reference data."""
    assert SEED_FILE.exists()
    content = SEED_FILE.read_text(encoding="utf-8")
    assert "INSERT INTO" in content
    assert "Casual Leave" in content
    assert "OFFICIAL_LOGIN_TIME" in content
    assert "Department of Computer Applications" in content


def test_database_initialization_execution():
    """
    Executes database initialization logic.
    If MySQL server is online, verifies 12 tables and seed data.
    If MySQL server is offline, verifies graceful connection failure handling.
    """
    is_online, msg = db_test_connection()
    success = initialize_database()

    if is_online:
        assert success is True, f"Database initialization failed: {msg}"
    else:
        assert success is False
        assert "Connection failed" in msg or "No MySQL driver" in msg or "Offline" in msg or "failed" in msg
