from functools import lru_cache
import json
from typing import Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ─── Application ──────────────────────────────────────────────────────────
    APP_NAME: str = "Quantyx AI"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    SECRET_KEY: str = "change-me-in-production-must-be-at-least-32-characters-long"

    # ─── Database ─────────────────────────────────────────────────────────────
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_NAME: str = "quantyx_ai"
    DB_USER: str = "quantyx"
    DB_PASSWORD: str = "quantyx_password"

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"mysql+aiomysql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"
        )

    @property
    def SYNC_DATABASE_URL(self) -> str:
        return (
            f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"
        )

    # ─── Redis ────────────────────────────────────────────────────────────────
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None

    @property
    def REDIS_URL(self) -> str:
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # ─── JWT ──────────────────────────────────────────────────────────────────
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ─── CORS ─────────────────────────────────────────────────────────────────
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000"]

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_origins(cls, v):
        # pydantic-settings may provide:
        # - a Python `list[str]` (already parsed JSON from .env)
        # - or a raw string (from .env) that might be JSON (e.g. `["http://..."]`)
        #   or comma-separated (e.g. `http://a,http://b`)
        if v is None:
            return []

        if isinstance(v, list):
            return [str(origin).strip().strip('"').strip("'") for origin in v if str(origin).strip()]

        if isinstance(v, str):
            s = v.strip()
            # Prefer JSON-array parsing when the value looks like JSON.
            # This aligns with `.env.example` and avoids quoted/bracket artifacts.
            if s.startswith("["):
                try:
                    parsed = json.loads(s)
                    if isinstance(parsed, list):
                        return [
                            str(origin).strip().strip('"').strip("'")
                            for origin in parsed
                            if str(origin).strip()
                        ]
                except Exception:
                    # Fall back to comma parsing below.
                    pass

            # Fallback: treat as comma-separated list.
            return [origin.strip().strip('"').strip("'") for origin in s.split(",") if origin.strip()]

        return v

    # ─── Rate Limiting ────────────────────────────────────────────────────────
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 60  # seconds

    # ─── Seed ─────────────────────────────────────────────────────────────────
    FIRST_ADMIN_EMAIL: str = "admin@quantyx.ai"
    FIRST_ADMIN_PASSWORD: str = "Admin@Quantyx123!"
    FIRST_COMPANY_NAME: str = "Quantyx Demo Corp"
    FIRST_COMPANY_SLUG: str = "quantyx-demo"

    # ─── Fraud Detection Thresholds ───────────────────────────────────────────
    FRAUD_VELOCITY_THRESHOLD: int = 5       # transactions in window
    FRAUD_VELOCITY_WINDOW_MIN: int = 30     # minutes
    FRAUD_AMOUNT_SPIKE_MULTIPLIER: float = 3.0
    FRAUD_LOCATION_RADIUS_KM: float = 200.0
    FRAUD_DUPLICATE_WINDOW_MIN: int = 5

    # ─── Cache TTLs (seconds) ─────────────────────────────────────────────────
    CACHE_TTL_KPI: int = 300          # 5 min
    CACHE_TTL_REVENUE: int = 900      # 15 min
    CACHE_TTL_COHORT: int = 3600      # 1 hour
    CACHE_TTL_MERCHANT: int = 600     # 10 min
    CACHE_TTL_SEGMENTATION: int = 1800  # 30 min


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
