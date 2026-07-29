from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://arip:arip@localhost:5434/arip"
    redis_url: str = "redis://localhost:6380/0"

    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480

    anthropic_api_key: str | None = None
    openai_api_key: str | None = None
    openrouter_api_key: str | None = None
    openrouter_model: str = "openai/gpt-4o-mini"
    openrouter_site_url: str | None = None
    openrouter_site_name: str | None = None

    s3_endpoint_url: str = "http://localhost:9000"
    s3_access_key: str = "arip"
    s3_secret_key: str = "aripsecret"
    s3_bucket: str = "arip-documents"

    smtp_host: str = "127.0.0.1"
    smtp_port: int = 1026


@lru_cache
def get_settings() -> Settings:
    return Settings()
