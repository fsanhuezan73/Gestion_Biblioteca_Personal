import logging
import secrets
from contextlib import asynccontextmanager

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.db.session import close_db_pool, get_db_connection, init_db_pool

settings = get_settings()
logger = logging.getLogger(__name__)
allowed_origins = [
    origin.strip()
    for origin in settings.allowed_origins.split(",")
    if origin.strip()
]


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
    allow_origins=allowed_origins,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok"}


@app.get("/health/db", tags=["Health"], include_in_schema=False)
def database_health_check(x_health_token: str | None = Header(default=None)):
    """Ejecuta SQL real en Oracle para evitar la detención por inactividad.

    Oracle Always Free detiene la base tras 7 días sin conexiones que ejecuten
    SQL. Este endpoint lo llama a diario el workflow `oracle-keepalive`.
    Requiere el header `X-Health-Token`; si no hay token configurado, no existe.
    """
    expected = get_settings().healthcheck_token
    if not expected:
        raise HTTPException(status_code=404, detail="Not Found")
    if not x_health_token or not secrets.compare_digest(x_health_token, expected):
        raise HTTPException(status_code=401, detail="No autorizado")

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM DUAL")
            row = cursor.fetchone()
        if not row or row[0] != 1:
            raise RuntimeError("Respuesta inesperada de Oracle")
    except Exception:
        # Sin detalles al cliente: el error completo queda solo en los logs.
        logger.exception("Health check de base de datos falló")
        return JSONResponse(status_code=503, content={"status": "unavailable", "database": "down"})

    return {"status": "ok", "database": "up"}
