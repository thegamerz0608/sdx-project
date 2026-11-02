"""
Unit tests for service duration calculations in utils.date_utils.
"""
from datetime import date
from utils.date_utils import calculate_service_duration, format_service_duration


def test_service_duration_same_day():
    join = date(2023, 5, 10)
    as_of = date(2023, 5, 10)
    y, m, d = calculate_service_duration(join, as_of)
    assert (y, m, d) == (0, 0, 0)
    assert format_service_duration(y, m, d) == "0 years, 0 months, 0 days"


def test_service_duration_future_joining_date():
    join = date(2027, 1, 1)
    as_of = date(2026, 10, 31)
    y, m, d = calculate_service_duration(join, as_of)
    assert (y, m, d) == (0, 0, 0)


def test_service_duration_exact_years():
    join = date(2020, 8, 15)
    as_of = date(2025, 8, 15)
    y, m, d = calculate_service_duration(join, as_of)
    assert (y, m, d) == (5, 0, 0)
    assert format_service_duration(y, m, d) == "5 years, 0 months, 0 days"


def test_service_duration_months_and_days():
    join = date(2021, 8, 10)
    as_of = date(2026, 10, 31)
    y, m, d = calculate_service_duration(join, as_of)
    assert (y, m, d) == (5, 2, 21)
    assert format_service_duration(y, m, d) == "5 years, 2 months, 21 days"


def test_service_duration_string_inputs():
    y, m, d = calculate_service_duration("2022-01-15", "2023-04-20")
    assert (y, m, d) == (1, 3, 5)


def test_service_duration_leap_year_feb29():
    # 2020 was a leap year
    join = date(2020, 2, 29)
    as_of = date(2021, 2, 28)
    y, m, d = calculate_service_duration(join, as_of)
    # Borrowing from Jan 2021 (31 days): 28 - 29 + 31 = 30 days, months = 1 - 1 = 0, years = 0
    # Or 11 months 30 days:
    # 2020-02-29 to 2021-02-28 is 365 days (0 years, 11 months, 30 days)
    assert y == 0
    assert m == 11
    assert d >= 28


def test_service_duration_month_end_boundary():
    join = date(2023, 1, 31)
    as_of = date(2023, 2, 28)
    y, m, d = calculate_service_duration(join, as_of)
    assert (y, m, d) == (0, 0, 28)


def test_service_duration_one_year_minus_one_day():
    join = date(2022, 5, 15)
    as_of = date(2023, 5, 14)
    y, m, d = calculate_service_duration(join, as_of)
    assert y == 0
    assert m == 11
    assert d == 29
