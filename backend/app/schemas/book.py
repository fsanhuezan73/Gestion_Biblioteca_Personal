from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime


VALID_READING_STATUSES = ("Quiero leer", "Leyendo", "Leído")


class BookCreate(BaseModel):
    title: str
    authors: List[str]          # uno o más autores
    isbn: Optional[str] = None
    year: Optional[int] = None
    genre: Optional[str] = None
    publisher: Optional[str] = None
    cover_url: Optional[str] = None
    reading_status: Optional[str] = "Quiero leer"

    model_config = {"str_strip_whitespace": True}


class BookUpdate(BaseModel):
    title: Optional[str] = None
    authors: Optional[List[str]] = None
    isbn: Optional[str] = None
    year: Optional[int] = None
    genre: Optional[str] = None
    publisher: Optional[str] = None
    cover_url: Optional[str] = None
    reading_status: Optional[str] = None

    model_config = {"str_strip_whitespace": True}


class BookSummary(BaseModel):
    id: int
    title: str
    authors: List[str]
    isbn: Optional[str] = None
    year: Optional[int] = None
    genre: Optional[str] = None
    publisher: Optional[str] = None
    cover_url: Optional[str] = None
    reading_status: Optional[str] = None
    created_at: Optional[datetime] = None
    rating: Optional[int] = None


class BookOut(BookSummary):
    personal_notes: Optional[str] = None


class BookPersonalUpdate(BaseModel):
    rating: Optional[int] = Field(default=None, strict=True, ge=1, le=5)
    personal_notes: Optional[str] = Field(default=None, strict=True, max_length=5000)

    model_config = {"extra": "forbid"}

    @field_validator("personal_notes")
    @classmethod
    def empty_notes_as_null(cls, value: str | None) -> str | None:
        # Conservar saltos de línea y espacios de las notas no vacías.
        return value if value and value.strip() else None
