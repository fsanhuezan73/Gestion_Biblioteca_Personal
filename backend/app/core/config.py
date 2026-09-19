from functools import lru_cache
from pathlib import Path
from typing import Literal
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    oracle_user: str
    oracle_password: str
    oracle_dsn: str
    oracle_wallet_dir: str = ""
    oracle_wallet_password: str = ""
    oracle_wallet_base64: str = ""

    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    password_reset_enabled: bool = False
    frontend_base_url: str = "http://localhost:5173"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_security: Literal["starttls", "ssl"] = "starttls"
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_email: str = ""

    allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174"
    app_env: str = "development"

    class Config:
        env_file = (str(BASE_DIR / ".env"), ".env", "backend/.env")
        case_sensitive = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
