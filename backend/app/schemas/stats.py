from datetime import date
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

MIN_YEAR = 1900
MAX_YEAR = 2100


class GoalIn(BaseModel):
    target_books: int = Field(strict=True, ge=1, le=365)

    model_config = {"extra": "forbid"}


class GoalOut(BaseModel):
    year: int
    target_books: int


class GoalProgress(BaseModel):
    target_books: int
    books_read: int
    percent: int
    expected_to_date: float
    difference: float
    remaining: int
    status: Literal["completed", "ahead", "on_track", "behind", "not_met", "upcoming"]


class MonthCount(BaseModel):
    month: int
    books: int
    pages: int


class LabelCount(BaseModel):
    label: str
    count: int


class RatingCount(BaseModel):
    rating: int
    count: int


class CurrentlyReading(BaseModel):
    id: int
    title: str
    cover_url: Optional[str] = None
    started_at: Optional[date] = None
    days_reading: Optional[int] = None


class YearStats(BaseModel):
    year: int
    books_read: int
    pages_read: int
    avg_days_to_finish: Optional[float] = None
    by_month: List[MonthCount]
    top_authors: List[LabelCount]
    goal: Optional[GoalProgress] = None


class LibraryStats(BaseModel):
    total_books: int
    want_to_read: int
    reading: int
    read: int
    read_without_date: int
    avg_rating: Optional[float] = None
    rated_books: int
    ratings: List[RatingCount]
    genres: List[LabelCount]
    currently_reading: List[CurrentlyReading]


class StatsOut(BaseModel):
    year_stats: YearStats
    library: LibraryStats
    available_years: List[int]
