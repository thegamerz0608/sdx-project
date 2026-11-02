"""
Attendance Import & Validation Engine
Provides AttendanceDataProvider interface, CSV/Excel parsing, validation rules,
late minute calculation, working hour calculation, and conflict flagging.
"""
from abc import ABC, abstractmethod
import csv
import re
from pathlib import Path
from datetime import datetime, date, time, timedelta
from typing import List, Dict, Any, Tuple, Optional

from repositories.faculty_repository import FacultyRepository
from utils.logger import get_logger

logger = get_logger("imports.attendance_importer")


class AttendanceDataProvider(ABC):
    """Abstract Base Class for Attendance Data Import Providers."""

    @abstractmethod
    def parse_and_validate(self, file_path: str) -> Dict[str, Any]:
        """
        Parses and validates the input attendance source file.
        Returns:
            Dict containing records_found, valid_records, invalid_records, duplicate_records, summary.
        """
        pass


class CSVAttendanceProvider(AttendanceDataProvider):
    """Concrete Attendance Data Provider for CSV and Excel files."""

    def __init__(self):
        self.faculty_repo = FacultyRepository()

    def _parse_date(self, date_str: str) -> Optional[date]:
        """Parses various date format strings safely."""
        clean_str = date_str.strip()
        formats = [
            "%Y-%m-%d",
            "%d-%m-%Y",
            "%m/%d/%Y",
            "%d/%m/%Y",
            "%Y/%m/%d",
            "%d.%m.%Y",
        ]
        for fmt in formats:
            try:
                return datetime.strptime(clean_str, fmt).date()
            except ValueError:
                continue
        return None

    def _parse_time(self, time_str: str) -> Optional[time]:
        """Parses various time format strings safely."""
        clean_str = time_str.strip().upper()
        formats = [
            "%H:%M:%S",
            "%H:%M",
            "%I:%M:%S %p",
            "%I:%M %p",
            "%I:%M%p",
        ]
        for fmt in formats:
            try:
                return datetime.strptime(clean_str, fmt).time()
            except ValueError:
                continue
        return None

    def _calculate_late_minutes(self, login_t: time, official_login_t: time = time(9, 0, 0)) -> int:
        """Calculates late arrival minutes past official deadline (default 09:00 AM)."""
        login_dt = datetime.combine(date.today(), login_t)
        official_dt = datetime.combine(date.today(), official_login_t)
        if login_dt > official_dt:
            diff = login_dt - official_dt
            return int(diff.total_seconds() // 60)
        return 0

    def _calculate_working_hours(self, login_t: time, logout_t: time) -> float:
        """Calculates total working hours between login and logout."""
        login_dt = datetime.combine(date.today(), login_t)
        logout_dt = datetime.combine(date.today(), logout_t)
        if logout_dt > login_dt:
            diff = logout_dt - login_dt
            hours = diff.total_seconds() / 3600.0
            return round(hours, 2)
        return 0.0

    def parse_and_validate(self, file_path: str) -> Dict[str, Any]:
        """
        Parses and validates CSV / Excel attendance file.
        Returns detailed report dictionary.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Fetch existing registered faculty mapping (employee_code -> faculty_dict)
        all_faculty = self.faculty_repo.get_all()
        faculty_map = {f["employee_code"].strip().upper(): f for f in all_faculty}

        valid_records = []
        invalid_records = []
        duplicate_records = []
        seen_keys = set()
        row_counter = 0

        # Read file
        lines = []
        if path.suffix.lower() in [".csv", ".txt"]:
            with open(path, "r", encoding="utf-8-sig") as f:
                reader = csv.reader(f)
                lines = list(reader)
        else:
            # Fallback text parsing if not standard CSV
            content = path.read_text(encoding="utf-8-sig")
            for line in content.splitlines():
                if line.strip():
                    lines.append([c.strip() for c in line.split(",")])

        if not lines:
            return {
                "records_found": 0,
                "valid_records": [],
                "invalid_records": [{"row": 0, "raw": "", "error": "File is empty"}],
                "duplicate_records": [],
                "summary": "Import failed: File is empty.",
            }

        # Header identification
        header = [c.strip().lower().replace(" ", "_") for c in lines[0]]
        
        # Map column indices
        emp_idx, date_idx, login_idx, logout_idx = -1, -1, -1, -1
        for idx, col in enumerate(header):
            if col in ["employee_id", "employee_code", "emp_id", "emp_code"]:
                emp_idx = idx
            elif col in ["date", "attendance_date"]:
                date_idx = idx
            elif col in ["login", "login_time", "time_in", "in_time"]:
                login_idx = idx
            elif col in ["logout", "logout_time", "time_out", "out_time"]:
                logout_idx = idx

        # Default column mapping fallback if header not found
        if emp_idx == -1 or date_idx == -1 or login_idx == -1 or logout_idx == -1:
            emp_idx, date_idx, login_idx, logout_idx = 0, 1, 2, 3

        data_rows = lines[1:] if (lines and any("date" in str(c).lower() for c in lines[0])) else lines

        for row in data_rows:
            row_counter += 1
            if len(row) < 4:
                invalid_records.append({
                    "row": row_counter,
                    "raw": ",".join(row),
                    "error": "Insufficient columns (Requires: Employee_ID, Date, Login, Logout)",
                })
                continue

            raw_emp = row[emp_idx].strip().upper()
            raw_date = row[date_idx].strip()
            raw_login = row[login_idx].strip()
            raw_logout = row[logout_idx].strip()

            # 1. Validate Employee ID
            if not raw_emp:
                invalid_records.append({
                    "row": row_counter,
                    "raw": ",".join(row),
                    "error": "Missing Employee ID",
                })
                continue

            if raw_emp not in faculty_map:
                invalid_records.append({
                    "row": row_counter,
                    "raw": ",".join(row),
                    "error": f"Unregistered Employee ID '{raw_emp}'",
                })
                continue

            faculty_info = faculty_map[raw_emp]

            # 2. Validate Date Format
            parsed_date = self._parse_date(raw_date)
            if not parsed_date:
                invalid_records.append({
                    "row": row_counter,
                    "raw": ",".join(row),
                    "error": f"Invalid Date format '{raw_date}' (Supported: YYYY-MM-DD, DD-MM-YYYY, MM/DD/YYYY)",
                })
                continue

            # 3. Validate Login & Logout Times
            parsed_login = self._parse_time(raw_login)
            parsed_logout = self._parse_time(raw_logout)

            if not parsed_login:
                invalid_records.append({
                    "row": row_counter,
                    "raw": ",".join(row),
                    "error": f"Invalid Login time '{raw_login}' (Supported: HH:MM, HH:MM:SS, 12-hr AM/PM)",
                })
                continue

            if not parsed_logout:
                invalid_records.append({
                    "row": row_counter,
                    "raw": ",".join(row),
                    "error": f"Invalid Logout time '{raw_logout}' (Supported: HH:MM, HH:MM:SS, 12-hr AM/PM)",
                })
                continue

            # 4. In-File Duplicate Check
            dup_key = (faculty_info["id"], str(parsed_date))
            if dup_key in seen_keys:
                duplicate_records.append({
                    "row": row_counter,
                    "raw": ",".join(row),
                    "error": f"Duplicate record for {raw_emp} on {parsed_date}",
                })
                continue
            seen_keys.add(dup_key)

            # 5. Calculations
            late_mins = self._calculate_late_minutes(parsed_login)
            working_hrs = self._calculate_working_hours(parsed_login, parsed_logout)
            status = "PRESENT"
            if working_hrs < 4.0:
                status = "HALF_DAY"

            record = {
                "row": row_counter,
                "faculty_id": faculty_info["id"],
                "employee_code": raw_emp,
                "faculty_name": faculty_info["full_name"],
                "department_id": faculty_info["department_id"],
                "department_code": faculty_info["department_code"],
                "attendance_date": str(parsed_date),
                "login_time": str(parsed_login),
                "logout_time": str(parsed_logout),
                "status": status,
                "late_minutes": late_mins,
                "working_hours": working_hrs,
                "early_departure_minutes": 0,
                "is_flagged": 0,
                "flag_reason": None,
            }

            valid_records.append(record)

        summary_msg = (
            f"Parsed {row_counter} records. "
            f"Valid: {len(valid_records)}, Invalid: {len(invalid_records)}, Duplicates: {len(duplicate_records)}."
        )
        logger.info(f"CSV Attendance Import Preview: {summary_msg}")

        return {
            "records_found": row_counter,
            "valid_records": valid_records,
            "invalid_records": invalid_records,
            "duplicate_records": duplicate_records,
            "summary": summary_msg,
        }


def generate_sample_csv(target_path: str = "sample_attendance.csv") -> str:
    """Generates a valid sample CSV attendance dataset for testing."""
    sample_rows = [
        ["Employee_ID", "Date", "Login", "Logout"],
        ["F001", "2026-09-10", "08:55:00", "17:05:00"],
        ["F002", "2026-09-10", "09:15:00", "17:00:00"],  # 15 mins late
        ["F003", "2026-09-10", "09:00:00", "17:00:00"],
        ["F004", "2026-09-10", "09:20:00", "16:45:00"],  # 20 mins late
        ["F002", "2026-09-11", "09:08:00", "17:10:00"],  # 8 mins late
        ["INVALID_ID", "2026-09-10", "09:00:00", "17:00:00"],  # Invalid employee ID test
        ["F001", "INVALID_DATE", "09:00:00", "17:00:00"],  # Invalid date format test
    ]

    p = Path(target_path)
    with open(p, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(sample_rows)

    logger.info(f"Generated sample attendance CSV at: {p.resolve()}")
    return str(p.resolve())
