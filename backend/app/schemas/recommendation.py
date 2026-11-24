from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class RecommendedBook(BaseModel):
    title: str
    authors: List[str]
    reason: str
    synopsis: Optional[str] = None
    cover_url: Optional[str] = None
    isbn: Optional[str] = None
    year: Optional[int] = None
    publisher: Optional[str] = None
    page_count: Optional[int] = None
    source: Optional[str] = None
    # Se recalcula en cada lectura: el usuario pudo agregarlo después.
    in_library: bool = False


class RecommendationsOut(BaseModel):
    recommendations: List[RecommendedBook]
    provider: Optional[str] = None
    model: Optional[str] = None
    generated_at: Optional[datetime] = None
    remaining_today: int
    daily_limit: int
    rated_books: int
    min_rated_books: int
