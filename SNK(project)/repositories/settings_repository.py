"""
System Settings Repository
Handles database persistence and cached fallback for global ERP configuration keys
in the `system_settings` table.
"""
import json
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

from database.connection import get_connection
from utils.logger import get_logger

logger = get_logger("repositories.settings_repository")

BASE_DIR = Path(__file__).resolve().parent.parent
CACHE_FILE = BASE_DIR / "config" / "settings_cache.json"

# In-memory default settings
DEFAULT_SETTINGS: Dict[str, str] = {
    "BIOMETRIC_SERVER_URL": "http://127.0.0.1:8000/punch-interface",
    "BIOMETRIC_DAEMON_STATUS": "OFFLINE",
    "BIOMETRIC_SHIFT_START": "09:00:00",
    "SYSTEM_TIME_MODE": "NORMAL",
    "SYSTEM_TEST_TIME": "",
    "APP_VERSION": "1.0.0",
}


class SettingsRepository:
    """Repository managing global key-value configuration in system_settings table."""

    def __init__(self):
        self._cache = dict(DEFAULT_SETTINGS)
        self._load_disk_cache()

    def _load_disk_cache(self):
        if CACHE_FILE.exists():
            try:
                with open(CACHE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        self._cache.update(data)
            except Exception as e:
                logger.debug(f"Could not load settings cache file: {e}")

    def _save_disk_cache(self):
        try:
            CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(self._cache, f, indent=2)
        except Exception as e:
            logger.debug(f"Could not save settings cache file: {e}")

    def get_setting(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """
        Retrieves setting value from MySQL system_settings table.
        Falls back to local cache if database is offline.
        """
        clean_key = key.strip()
        try:
            conn = get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                "SELECT setting_value FROM system_settings WHERE setting_key = %s LIMIT 1;",
                (clean_key,),
            )
            row = cursor.fetchone()
            cursor.close()
            conn.close()
            if row and row.get("setting_value") is not None:
                val = str(row["setting_value"])
                self._cache[clean_key] = val
                self._save_disk_cache()
                return val
        except Exception as exc:
            logger.debug(f"Database lookup failed for setting '{clean_key}': {exc}. Using cache.")

        # Fallback to local memory/disk cache
        return self._cache.get(clean_key, default)

    def set_setting(self, key: str, value: str, description: Optional[str] = None) -> bool:
        """
        Persists a setting key-value pair to system_settings table (INSERT ... ON CONFLICT DO UPDATE)
        and synchronizes memory/disk cache.
        """
        clean_key = key.strip()
        str_val = str(value)
        self._cache[clean_key] = str_val
        self._save_disk_cache()

        try:
            conn = get_connection()
            cursor = conn.cursor()
            sql = """
                INSERT INTO system_settings (setting_key, setting_value, description, updated_at)
                VALUES (%s, %s, %s, NOW())
                ON CONFLICT (setting_key) DO UPDATE SET 
                    setting_value = EXCLUDED.setting_value,
                    description = COALESCE(EXCLUDED.description, system_settings.description),
                    updated_at = NOW();
            """
            cursor.execute(sql, (clean_key, str_val, description))
            conn.commit()
            cursor.close()
            conn.close()
            logger.info(f"Setting '{clean_key}' updated in database.")
            return True
        except Exception as exc:
            logger.debug(f"Database write failed for setting '{clean_key}': {exc}. Saved to cache only.")
            return True


settings_repository = SettingsRepository()
