"""Normalización y validación de ISBN (mismas reglas que frontend/src/utils/isbn.js)."""

import re


def normalize_isbn(raw: str | None) -> str:
    return re.sub(r"[^0-9X]", "", (raw or "").upper())


def is_valid_isbn13(value: str) -> bool:
    if not re.fullmatch(r"\d{13}", value):
        return False
    return sum(int(d) * (1 if i % 2 == 0 else 3) for i, d in enumerate(value)) % 10 == 0


def is_valid_isbn10(value: str) -> bool:
    if not re.fullmatch(r"\d{9}[\dX]", value):
        return False
    return sum((10 if c == "X" else int(c)) * (10 - i) for i, c in enumerate(value)) % 11 == 0


def isbn10_to_13(isbn10: str) -> str:
    core = "978" + isbn10[:9]
    check = (10 - sum(int(d) * (1 if i % 2 == 0 else 3) for i, d in enumerate(core)) % 10) % 10
    return core + str(check)


def isbn13_to_10(isbn13: str) -> str | None:
    """Solo los ISBN-13 con prefijo 978 tienen equivalente ISBN-10."""
    if not isbn13.startswith("978"):
        return None
    core = isbn13[3:12]
    check = (11 - sum(int(d) * (10 - i) for i, d in enumerate(core)) % 11) % 11
    return core + ("X" if check == 10 else str(check))


def to_isbn13(raw: str | None) -> str | None:
    value = normalize_isbn(raw)
    if len(value) == 13:
        return value if is_valid_isbn13(value) and value[:3] in ("978", "979") else None
    if len(value) == 10:
        return isbn10_to_13(value) if is_valid_isbn10(value) else None
    return None
