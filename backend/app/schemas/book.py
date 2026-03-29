from pydantic import BaseModel
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


class BookOut(BaseModel):
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
