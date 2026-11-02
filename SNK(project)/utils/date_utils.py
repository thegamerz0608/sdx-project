"""
Date Utilities for Faculty Attendance & Leave Management ERP.
Provides robust date arithmetic, service duration calculation,
and display formatting.
"""
from datetime import date, datetime
import calendar
from typing import Tuple, Union, Optional


def calculate_service_duration(
    join_date: Union[date, datetime, str],
    as_of: Optional[Union[date, datetime, str]] = None,
) -> Tuple[int, int, int]:
    """
    Calculates exact service duration (years, months, days) from join_date to as_of.
    
    Handles:
      - String dates in ISO format ('YYYY-MM-DD')
      - datetime or date objects
      - Month-end dates and varying month lengths
      - Leap years (Feb 29)
      - Future joining dates (returns (0, 0, 0))
    
    Returns:
        Tuple[int, int, int]: (years, months, days)
    """
    # 1. Parse join_date
    if isinstance(join_date, str):
        join_date = datetime.strptime(join_date.strip()[:10], "%Y-%m-%d").date()
    elif isinstance(join_date, datetime):
        join_date = join_date.date()

    # 2. Parse as_of (defaulting to system/simulated time)
    if as_of is None:
        try:
            from services.time_service import TimeService
            as_of = TimeService.get_current_time().date()
        except Exception:
            as_of = date.today()
    elif isinstance(as_of, str):
        as_of = datetime.strptime(as_of.strip()[:10], "%Y-%m-%d").date()
    elif isinstance(as_of, datetime):
        as_of = as_of.date()

    # 3. Handle Future Joining Date
    if join_date > as_of:
        return (0, 0, 0)

    # 4. Standard Calendar Arithmetic with Month/Day Borrowing
    years = as_of.year - join_date.year
    months = as_of.month - join_date.month
    days = as_of.day - join_date.day

    if days < 0:
        # Borrow from the month immediately preceding as_of
        if as_of.month == 1:
            prev_month = 12
            prev_year = as_of.year - 1
        else:
            prev_month = as_of.month - 1
            prev_year = as_of.year
        days_in_prev_month = calendar.monthrange(prev_year, prev_month)[1]
        days += days_in_prev_month
        months -= 1

    if months < 0:
        months += 12
        years -= 1

    return (max(0, years), max(0, months), max(0, days))


def format_service_duration(years: int, months: int, days: int) -> str:
    """
    Formats the duration tuple into the ERP display format:
    'X years, Y months, Z days'
    """
    return f"{years} years, {months} months, {days} days"
