import oracledb
from contextlib import contextmanager
from typing import Generator

from app.core.config import get_settings

settings = get_settings()

# Configurar pool de conexiones al iniciar la aplicación
_pool: oracledb.ConnectionPool | None = None


def init_db_pool() -> None:
    """Inicializa el pool de conexiones Oracle. Llamar al arrancar la app."""
    global _pool

    connect_params: dict = {
        "user": settings.oracle_user,
        "password": settings.oracle_password,
        "dsn": settings.oracle_dsn,
    }

    # Si se configuró wallet (Oracle Autonomous Database en OCI)
    if settings.oracle_wallet_dir:
        connect_params.update(
            {
                "config_dir": settings.oracle_wallet_dir,
                "wallet_location": settings.oracle_wallet_dir,
                "wallet_password": settings.oracle_wallet_password,
            }
        )

    _pool = oracledb.create_pool(
        **connect_params,
        min=1,
        max=5,
        increment=1,
    )


def close_db_pool() -> None:
    """Cierra el pool de conexiones. Llamar al detener la app."""
    global _pool
    if _pool:
        _pool.close()
        _pool = None


@contextmanager
def get_db_connection() -> Generator[oracledb.Connection, None, None]:
    """Context manager que entrega y devuelve una conexión del pool."""
    if _pool is None:
        raise RuntimeError("El pool de base de datos no está inicializado")
    conn = _pool.acquire()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _pool.release(conn)
