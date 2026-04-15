"""
TeenSync – Application Configuration
Uses pydantic-settings to load from .env file with type validation.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ──────────────────────────────────────────────────────────────────────
    app_name: str = "TeenSync API"
    app_version: str = "1.0.0"
    debug: bool = True
    allowed_origins: str = "http://localhost:3456,http://127.0.0.1:3456"

    # ── Database ─────────────────────────────────────────────────────────────────
    database_url: str = "sqlite+aiosqlite:///./teensync.db"

    @property
    def async_database_url(self) -> str:
        """Convert postgres:// to postgresql+asyncpg:// for SQLAlchemy async support."""
        url = self.database_url
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url

    # ── JWT ──────────────────────────────────────────────────────────────────────
    secret_key: str = "dev-secret-key-change-in-production-please"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # ── LLM Integration ──────────────────────────────────────────────────────────
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-1.5-flash"
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "llama3"

    # ── NLP ──────────────────────────────────────────────────────────────────────
    sentiment_threshold: float = 0.05

    # ── Burnout ──────────────────────────────────────────────────────────────────
    burnout_high_threshold: int = 65
    burnout_medium_threshold: int = 35

    # ── Moderation ───────────────────────────────────────────────────────────────
    moderation_enabled: bool = True

    @property
    def origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]

    @property
    def has_openai(self) -> bool:
        return bool(self.openai_api_key)

    @property
    def has_gemini(self) -> bool:
        return bool(self.gemini_api_key)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
