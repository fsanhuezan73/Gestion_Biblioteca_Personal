from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    oracle_user: str
    oracle_password: str
    oracle_dsn: str
    oracle_wallet_dir: str = ""
    oracle_wallet_password: str = ""

    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30

    app_env: str = "development"

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
