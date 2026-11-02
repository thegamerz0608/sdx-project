"""
Global System Time Service (Normal vs. Test Mode)
Manages ERP temporal context across desktop application and FastAPI web portals.
Allows Administrators to toggle between live system clock and simulated/mocked test time.
"""
from datetime import datetime, date, time
from typing import Optional, Union
import threading

from repositories.settings_repository import settings_repository
from utils.logger import get_logger

logger = get_logger("services.time_service")

# Global lock for thread safety
_time_lock = threading.Lock()


class TimeService:
    """
    Central time provider for the Faculty Attendance ERP.
    In 'NORMAL' mode, provides the real-time system clock (datetime.now()).
    In 'TEST' mode, provides an administrator-configured simulated date and time.
    """

    _in_memory_override: Optional[datetime] = None

    @classmethod
    def is_test_mode(cls) -> bool:
        """Returns True if ERP is running under TEST_MODE, False for NORMAL mode."""
        mode = settings_repository.get_setting("SYSTEM_TIME_MODE", "NORMAL")
        return bool(mode and mode.strip().upper() == "TEST")

    @classmethod
    def get_current_time(cls) -> datetime:
        """
        Returns the effective current datetime.
        If TEST mode is enabled, returns the mocked test time; otherwise real datetime.now().
        """
        if cls._in_memory_override is not None:
            return cls._in_memory_override

        if cls.is_test_mode():
            raw_test_time = settings_repository.get_setting("SYSTEM_TEST_TIME", "")
            if raw_test_time and raw_test_time.strip():
                try:
                    # Support standard formats: 'YYYY-MM-DD HH:MM:SS' or ISO 'YYYY-MM-DDTHH:MM:SS'
                    clean = raw_test_time.strip().replace("T", " ")
                    if len(clean) == 10:  # YYYY-MM-DD
                        return datetime.strptime(clean, "%Y-%m-%d")
                    return datetime.strptime(clean[:19], "%Y-%m-%d %H:%M:%S")
                except Exception as e:
                    logger.warning(f"Could not parse SYSTEM_TEST_TIME '{raw_test_time}': {e}. Falling back to now.")

        return datetime.now()

    @classmethod
    def get_current_date(cls) -> date:
        """Returns the effective current date."""
        return cls.get_current_time().date()

    @classmethod
    def get_current_time_str(cls, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
        """Returns the formatted string of effective current time."""
        return cls.get_current_time().strftime(fmt)

    @classmethod
    def get_test_time(cls) -> Optional[datetime]:
        """Returns the currently configured test datetime, if any."""
        if cls._in_memory_override is not None:
            return cls._in_memory_override

        raw = settings_repository.get_setting("SYSTEM_TEST_TIME", "")
        if raw and raw.strip():
            try:
                clean = raw.strip().replace("T", " ")
                if len(clean) == 10:
                    return datetime.strptime(clean, "%Y-%m-%d")
                return datetime.strptime(clean[:19], "%Y-%m-%d %H:%M:%S")
            except Exception:
                pass
        return None

    @classmethod
    def set_time_mode(
        cls,
        mode: str,
        test_datetime: Optional[Union[datetime, str]] = None,
    ) -> bool:
        """
        Switches between 'NORMAL' and 'TEST' modes.
        If test_datetime is provided, sets the mocked date/time.
        """
        with _time_lock:
            clean_mode = "TEST" if mode.strip().upper() == "TEST" else "NORMAL"
            settings_repository.set_setting(
                "SYSTEM_TIME_MODE",
                clean_mode,
                description="Global System Time Mode (NORMAL or TEST)"
            )

            if test_datetime is not None:
                if isinstance(test_datetime, datetime):
                    val_str = test_datetime.strftime("%Y-%m-%d %H:%M:%S")
                    cls._in_memory_override = test_datetime
                else:
                    val_str = str(test_datetime).strip()
                    try:
                        clean = val_str.replace("T", " ")
                        if len(clean) == 10:
                            cls._in_memory_override = datetime.strptime(clean, "%Y-%m-%d")
                        else:
                            cls._in_memory_override = datetime.strptime(clean[:19], "%Y-%m-%d %H:%M:%S")
                    except Exception:
                        cls._in_memory_override = None

                settings_repository.set_setting(
                    "SYSTEM_TEST_TIME",
                    val_str,
                    description="Simulated mock date/time for TEST mode"
                )
            elif clean_mode == "NORMAL":
                cls._in_memory_override = None

            logger.info(f"System time mode updated: {clean_mode} (Mocked: {cls._in_memory_override})")
            return True

    @classmethod
    def reset_to_normal(cls) -> bool:
        """Convenience method to revert to real-time system clock."""
        return cls.set_time_mode("NORMAL")

    @classmethod
    def set_in_memory_override(cls, dt: Optional[datetime]):
        """Direct in-memory override for fast unit tests without DB writes."""
        cls._in_memory_override = dt


# Global singleton instance
time_service = TimeService()
