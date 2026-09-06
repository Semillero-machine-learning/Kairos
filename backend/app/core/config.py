"""Application settings loaded from environment variables via pydantic-settings."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    database_url: str

    # JWT
    jwt_secret: str
    jwt_access_ttl_minutes: int = 15
    jwt_refresh_ttl_days: int = 7

    # Email (Resend). Empty api key -> emails are logged, not sent.
    resend_api_key: str = ""
    email_from: str = "Semillero ML <notificaciones@send.kairospartners.uk>"

    # Links embedded in emails
    frontend_url: str = "https://app.kairospartners.uk"

    # Scheduled reminders job shared secret
    job_token: str = ""

    # Comma-separated list of allowed CORS origins
    cors_origins: str = "http://localhost:4200"

    environment: str = "development"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
