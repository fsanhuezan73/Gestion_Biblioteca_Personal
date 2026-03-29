from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.db.session import init_db_pool, close_db_pool


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: inicializar pool Oracle
    init_db_pool()
    yield
    # Shutdown: cerrar pool Oracle
    close_db_pool()


app = FastAPI(
    title="Gestión Biblioteca Personal",
    description="API REST para gestionar tu colección de libros personal",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — permitir peticiones desde el frontend Vue.js en desarrollo
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",   # Vite dev server
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok"}
