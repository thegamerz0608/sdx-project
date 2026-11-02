"""
PostgreSQL Database Connection Manager
Provides connection testing, safe connection creation, RealDictCursor wrapping,
and Circuit Breaker resilience for PostgreSQL 16+.
"""
import time
from typing import Tuple, Any, Optional
from config.settings import settings
from utils.logger import get_logger
from utils.exceptions import DatabaseConnectionError

logger = get_logger("database.connection")

_DRIVER = None
_LAST_CONNECT_FAIL_TIME = 0.0
_FAIL_COOLDOWN_SECONDS = 3.0

try:
    import psycopg2
    import psycopg2.extras
    import psycopg2.pool
    from psycopg2 import Error as PostgresError
    _DRIVER = "psycopg2"
except ImportError:
    try:
        import psycopg
        from psycopg import Error as PostgresError
        _DRIVER = "psycopg"
    except ImportError:
        _DRIVER = None
        PostgresError = Exception


def get_driver_name() -> str:
    """Returns the detected active PostgreSQL driver name."""
    return _DRIVER if _DRIVER else "None (No PostgreSQL driver installed)"


class PostgresConnectionWrapper:
    """
    Transparent proxy wrapping psycopg2 connection.
    Intercepts cursor(dictionary=True) calls from legacy repository code and
    maps them to psycopg2.extras.RealDictCursor.
    """
    def __init__(self, raw_conn):
        self._conn = raw_conn

    def cursor(self, *args, **kwargs):
        if kwargs.pop("dictionary", False) and _DRIVER == "psycopg2":
            kwargs["cursor_factory"] = psycopg2.extras.RealDictCursor
        return self._conn.cursor(*args, **kwargs)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._conn:
            self._conn.close()

    def __getattr__(self, name):
        return getattr(self._conn, name)


def get_server_connection(maintenance_db: str = "postgres"):
    """
    Creates and returns a raw connection to the PostgreSQL host server connected to
    the default maintenance database ('postgres') with autocommit=True.
    Used for database creation / bootstrap outside transaction blocks.
    """
    if _DRIVER is None:
        raise DatabaseConnectionError(
            "No PostgreSQL driver found. Please install psycopg2-binary in your Python environment."
        )

    db_config = settings.get_db_config()
    try:
        if _DRIVER == "psycopg2":
            conn = psycopg2.connect(
                host=db_config["host"],
                port=db_config["port"],
                user=db_config["user"],
                password=db_config["password"],
                dbname=maintenance_db,
                connect_timeout=db_config.get("connect_timeout", 5),
            )
            conn.autocommit = True
            return conn
        else:
            conn = psycopg.connect(
                host=db_config["host"],
                port=db_config["port"],
                user=db_config["user"],
                password=db_config["password"],
                dbname=maintenance_db,
                connect_timeout=db_config.get("connect_timeout", 5),
                autocommit=True,
            )
            return conn
    except Exception as exc:
        msg = f"Failed to connect to PostgreSQL maintenance server at {db_config['host']}:{db_config['port']}"
        logger.error(f"{msg}: {exc}")
        raise DatabaseConnectionError(msg, original_error=exc) from exc


def get_connection():
    """
    Creates and returns a PostgreSQL database connection wrapped for dictionary cursor compatibility.
    Applies a Circuit Breaker pattern with a 3-second cooldown to prevent freezing the UI.
    """
    global _LAST_CONNECT_FAIL_TIME

    if _DRIVER is None:
        raise DatabaseConnectionError(
            "No PostgreSQL driver found. Please install psycopg2-binary."
        )

    if time.time() - _LAST_CONNECT_FAIL_TIME < _FAIL_COOLDOWN_SECONDS:
        raise DatabaseConnectionError(
            "PostgreSQL server is currently unreachable (offline fallback active)."
        )

    db_config = settings.get_db_config()
    try:
        if _DRIVER == "psycopg2":
            raw_conn = psycopg2.connect(
                host=db_config["host"],
                port=db_config["port"],
                user=db_config["user"],
                password=db_config["password"],
                dbname=db_config["database"],
                connect_timeout=db_config.get("connect_timeout", 5),
            )
            _LAST_CONNECT_FAIL_TIME = 0.0
            return PostgresConnectionWrapper(raw_conn)
        else:
            raw_conn = psycopg.connect(
                host=db_config["host"],
                port=db_config["port"],
                user=db_config["user"],
                password=db_config["password"],
                dbname=db_config["database"],
                connect_timeout=db_config.get("connect_timeout", 5),
            )
            _LAST_CONNECT_FAIL_TIME = 0.0
            return PostgresConnectionWrapper(raw_conn)

    except PostgresError as exc:
        _LAST_CONNECT_FAIL_TIME = time.time()
        msg = f"Failed to connect to PostgreSQL database '{db_config['database']}' at {db_config['host']}:{db_config['port']}"
        logger.debug(f"{msg}: {exc}")
        raise DatabaseConnectionError(msg, original_error=exc) from exc
    except Exception as exc:
        _LAST_CONNECT_FAIL_TIME = time.time()
        msg = f"Unexpected error connecting to PostgreSQL database: {exc}"
        logger.debug(msg)
        raise DatabaseConnectionError(msg, original_error=exc) from exc


def test_connection() -> Tuple[bool, str]:
    """
    Tests connectivity to the configured PostgreSQL database.
    Returns:
        Tuple[bool, str]: (Success boolean, Status message)
    """
    global _LAST_CONNECT_FAIL_TIME
    _LAST_CONNECT_FAIL_TIME = 0.0  # Force live probe on explicit test

    if _DRIVER is None:
        msg = "No PostgreSQL driver installed (psycopg2-binary missing)."
        logger.warning(f"Database Connection Test Failed: {msg}")
        return False, msg

    db_config = settings.get_db_config()
    logger.info(
        f"Testing PostgreSQL connection to {db_config['host']}:{db_config['port']} (Database: '{db_config['database']}', Driver: {_DRIVER})..."
    )

    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version_row = cursor.fetchone()
        cursor.close()
        conn.close()

        server_ver = version_row[0] if version_row else "Unknown"
        msg = f"Successfully connected to PostgreSQL server (Version: {server_ver[:40]}..., Driver: {_DRIVER})."
        logger.info(msg)
        return True, msg

    except DatabaseConnectionError as exc:
        msg = f"Connection failed: {exc.message}"
        if exc.original_error:
            msg += f" Details: {exc.original_error}"
        logger.warning(msg)
        return False, msg
    except Exception as exc:
        msg = f"Database test error: {str(exc)}"
        logger.error(msg)
        return False, msg
