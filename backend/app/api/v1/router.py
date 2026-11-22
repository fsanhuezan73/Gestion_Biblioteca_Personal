from fastapi import APIRouter
from app.api.v1.endpoints import auth, books, goals, stats

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(books.router)
api_router.include_router(goals.router)
api_router.include_router(stats.router)
