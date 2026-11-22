"""Reglas de fechas de lectura y cálculo de metas anuales.

Funciones puras (sin base de datos) para poder probarlas de forma aislada.
"""

from calendar import isleap
from datetime import date, datetime
from zoneinfo import ZoneInfo

from app.core.config import get_settings

STATUS_WANT = "Quiero leer"
STATUS_READING = "Leyendo"
STATUS_READ = "Leído"


def today() -> date:
    """Fecha actual en la zona horaria de la aplicación (no la del servidor)."""
    return datetime.now(ZoneInfo(get_settings().app_timezone)).date()


def as_date(value) -> date | None:
    """Oracle devuelve DATE como datetime; la API trabaja solo con fechas."""
    if isinstance(value, datetime):
        return value.date()
    return value


def dates_for_status_change(
    new_status: str,
    started_at: date | None,
    finished_at: date | None,
    on: date,
) -> tuple[date | None, date | None]:
    """Fechas automáticas al cambiar de estado.

    - Quiero leer: el libro aún no se empieza, se borran ambas fechas.
    - Leyendo: se conserva el inicio (o se usa hoy) y se borra el término.
    - Leído: se conserva el inicio tal cual (no se inventa) y el término es hoy
      si no existía.
    """
    if new_status == STATUS_WANT:
        return None, None
    if new_status == STATUS_READING:
        return started_at or on, None
    if new_status == STATUS_READ:
        return started_at, finished_at or on
    return started_at, finished_at


def validate_reading_dates(started_at: date | None, finished_at: date | None, on: date) -> str | None:
    """Retorna un mensaje de error o None si las fechas son coherentes."""
    if started_at and started_at > on:
        return "La fecha de inicio no puede ser futura"
    if finished_at and finished_at > on:
        return "La fecha de término no puede ser futura"
    if started_at and finished_at and finished_at < started_at:
        return "La fecha de término no puede ser anterior a la de inicio"
    return None


def goal_progress(target: int, read: int, year: int, on: date) -> dict:
    """Avance de una meta anual y ritmo respecto de lo esperado a la fecha.

    status:
      completed  meta cumplida
      ahead      por sobre el ritmo esperado
      on_track   al día (diferencia menor a un libro)
      behind     bajo el ritmo esperado
      not_met    año terminado sin cumplir la meta
      upcoming   año futuro
    """
    percent = min(100, round(read * 100 / target)) if target else 0

    if year > on.year:
        expected = 0.0
    elif year < on.year:
        expected = float(target)
    else:
        days_in_year = 366 if isleap(year) else 365
        expected = target * on.timetuple().tm_yday / days_in_year

    difference = read - expected
    if read >= target:
        status = "completed"
    elif year < on.year:
        status = "not_met"
    elif year > on.year:
        status = "upcoming"
    elif difference >= 1:
        status = "ahead"
    elif difference <= -1:
        status = "behind"
    else:
        status = "on_track"

    return {
        "target_books": target,
        "books_read": read,
        "percent": percent,
        "expected_to_date": round(expected, 1),
        "difference": round(difference, 1),
        "remaining": max(0, target - read),
        "status": status,
    }
