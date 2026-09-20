from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "AbhaySetu"
    app_env: str = "development"
    log_level: str = "INFO"
    secret_key: str = "change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 14
    api_v1_prefix: str = "/api/v1"
    backend_cors_origins: str = "http://localhost:5173,http://localhost:8080"
    public_base_url: str = "http://localhost:8000"

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "abhaysetu"
    postgres_password: str = "change-me"
    postgres_db: str = "abhaysetu"

    redis_url: str = "redis://localhost:6379/0"
    redis_required: bool = False

    bootstrap_admin_email: str = ""
    bootstrap_admin_password: str = ""
    bootstrap_admin_name: str = "AbhaySetu Admin"

    sos_rate_limit_per_device_per_hour: int = 20
    login_rate_limit_per_ip_per_minute: int = 10

    communication_order: str = "internet,local_network,peer_relay,radio,satellite,store_and_forward"
    radio_gateway_enabled: bool = False
    satellite_adapter_enabled: bool = False
    satellite_provider: str = ""
    allow_simulated_adapters: bool = False

    ai_provider: str = ""
    ai_api_key: str = ""
    ai_model: str = ""

    map_tile_url: str = "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
    map_attribution: str = "© OpenStreetMap contributors"
    map_data_updated_at: str = ""

    seed_sample_data: bool = False
    data_retention_days: int = 365

    @property
    def cors_origins(self) -> List[str]:
        return [item.strip() for item in self.backend_cors_origins.split(",") if item.strip()]

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def async_database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
