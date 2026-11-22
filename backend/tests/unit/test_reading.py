from datetime import date, datetime

import pytest

from app.core.reading import as_date, dates_for_status_change, goal_progress, validate_reading_dates

TODAY = date(2026, 7, 2)  # día 183 de 365
START = date(2026, 5, 1)
END = date(2026, 6, 15)


@pytest.mark.parametrize("status,started,finished,expected", [
    ("Quiero leer", START, END, (None, None)),
    ("Leyendo", None, None, (TODAY, None)),
    ("Leyendo", START, END, (START, None)),          # Leído → Leyendo: conserva inicio
    ("Leído", None, None, (None, TODAY)),             # no inventa la fecha de inicio
    ("Leído", START, None, (START, TODAY)),
    ("Leído", START, END, (START, END)),              # conserva el término existente
])
def test_dates_for_status_change(status, started, finished, expected):
    assert dates_for_status_change(status, started, finished, TODAY) == expected


@pytest.mark.parametrize("started,finished,error", [
    (None, None, None),
    (START, END, None),
    (START, START, None),
    (date(2026, 8, 1), None, "inicio no puede ser futura"),
    (None, date(2026, 8, 1), "término no puede ser futura"),
    (END, START, "anterior a la de inicio"),
])
def test_validate_reading_dates(started, finished, error):
    result = validate_reading_dates(started, finished, TODAY)
    if error is None:
        assert result is None
    else:
        assert error in result


def test_as_date_converts_oracle_datetime():
    assert as_date(datetime(2026, 5, 1, 0, 0)) == date(2026, 5, 1)
    assert as_date(START) == START
    assert as_date(None) is None


@pytest.mark.parametrize("target,read,year,status", [
    (24, 12, 2026, "on_track"),   # esperado ≈ 12.0
    (24, 14, 2026, "ahead"),
    (24, 9, 2026, "behind"),
    (24, 24, 2026, "completed"),
    (24, 30, 2025, "completed"),
    (24, 10, 2025, "not_met"),
    (24, 0, 2027, "upcoming"),
])
def test_goal_progress_status(target, read, year, status):
    assert goal_progress(target, read, year, TODAY)["status"] == status


def test_goal_progress_values():
    progress = goal_progress(24, 14, 2026, TODAY)
    assert progress["percent"] == 58
    assert progress["expected_to_date"] == 12.0
    assert progress["difference"] == 2.0
    assert progress["remaining"] == 10


def test_goal_progress_caps_percent_at_100():
    progress = goal_progress(10, 15, 2026, TODAY)
    assert progress["percent"] == 100
    assert progress["remaining"] == 0
