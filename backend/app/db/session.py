import base64
import binascii
from pathlib import Path
from tempfile import TemporaryDirectory
from contextlib import contextmanager
from typing import Generator
from zipfile import BadZipFile, ZipFile

import oracledb

from app.core.config import get_settings

settings = get_settings()

# Configurar pool de conexiones al iniciar la aplicación
_pool: oracledb.ConnectionPool | None = None
_wallet_directory: TemporaryDirectory[str] | None = None


def get_wallet_directory() -> str:
    """Obtiene el wallet local o extrae el configurado como secreto de entorno."""
    global _wallet_directory

    if settings.oracle_wallet_dir:
        return settings.oracle_wallet_dir

    if not settings.oracle_wallet_base64:
        return ""

    try:
        wallet_bytes = base64.b64decode(settings.oracle_wallet_base64, validate=True)
        _wallet_directory = TemporaryDirectory(prefix="oracle-wallet-")
        wallet_zip_path = Path(_wallet_directory.name) / "wallet.zip"
        wallet_zip_path.write_bytes(wallet_bytes)
        with ZipFile(wallet_zip_path) as wallet_file:
            wallet_file.extractall(_wallet_directory.name)
    except (BadZipFile, binascii.Error) as error:
        raise RuntimeError("ORACLE_WALLET_BASE64 debe contener un ZIP valido en Base64") from error

    wallet_config_file = next(Path(_wallet_directory.name).rglob("tnsnames.ora"), None)
    if wallet_config_file is None:
        raise RuntimeError("El wallet debe incluir el archivo tnsnames.ora")

    return str(wallet_config_file.parent)


def init_db_pool() -> None:
    """Inicializa el pool de conexiones Oracle. Llamar al arrancar la app."""
    global _pool

    connect_params: dict = {
        "user": settings.oracle_user,
        "password": settings.oracle_password,
        "dsn": settings.oracle_dsn,
    }

    wallet_directory = get_wallet_directory()
    # Si se configuró wallet (Oracle Autonomous Database en OCI)
    if wallet_directory:
        connect_params.update(
            {
                "config_dir": wallet_directory,
                "wallet_location": wallet_directory,
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
    global _pool, _wallet_directory
    if _pool:
        _pool.close()
        _pool = None
    if _wallet_directory:
        _wallet_directory.cleanup()
        _wallet_directory = None


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
