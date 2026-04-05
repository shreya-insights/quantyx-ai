from functools import lru_cache
from typing import Optional

from pydantic import Field, field_validator
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
    ALLOWED_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    # ─── Rate limiting & API metering (Redis + Subscription.api_calls_used) ─
    IP_RATE_LIMIT_PER_MINUTE: int = 100
    API_RATE_LIMIT_WINDOW_SECONDS: int = 60
    PLAN_RATE_LIMITS_PER_MINUTE: dict[str, int] = Field(
        default_factory=lambda: {
            "starter": 60,
            "growth": 300,
            "enterprise": 1000,
        }
    )
    QUOTA_SYNC_INTERVAL: int = 100
    PLAN_CACHE_TTL_SECONDS: int = 300
    DAILY_USAGE_KEY_TTL_SECONDS: int = 32 * 86_400
    # Comma-separated emails in .env (plain string). Do not use frozenset here:
    # pydantic-settings JSON-decodes complex env types before validators run.
    RATE_LIMIT_BYPASS_EMAILS: str = Field(default="")

    @property
    def bypass_emails_set(self) -> frozenset[str]:
        return frozenset(
            e.strip().lower()
            for e in self.RATE_LIMIT_BYPASS_EMAILS.split(",")
            if e.strip()
        )

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

    # Cap Celery fan-out after CSV bulk upload (each inserted row may enqueue one task).
    BULK_UPLOAD_MAX_FRAUD_TASKS: int = 2000

    # ─── ML Model ─────────────────────────────────────────────────────────────
    ML_MODEL_DIR: str = "backend/ml"

    # ─── Model monitoring / drift (env-tunable; global defaults) ──────────────
    MODEL_HEALTH_F1_THRESHOLD: float = 0.75
    MODEL_HEALTH_PRECISION_THRESHOLD: float = 0.70
    MODEL_HEALTH_PSI_MONITOR_THRESHOLD: float = 0.1
    MODEL_HEALTH_PSI_DRIFT_THRESHOLD: float = 0.2
    MODEL_HEALTH_PSI_DRIFT_MIN_FEATURES: int = 3
    MODEL_HEALTH_DRIFT_WINDOW_DAYS: int = 30

    # ─── Cache TTLs (seconds) ─────────────────────────────────────────────────
    CACHE_TTL_KPI: int = 300          # 5 min
    CACHE_TTL_REVENUE: int = 900      # 15 min
    CACHE_TTL_COHORT: int = 3600      # 1 hour
    CACHE_TTL_MERCHANT: int = 600     # 10 min
    CACHE_TTL_SEGMENTATION: int = 1800  # 30 min

    # ─── Analytics DB cache (pre-aggregated tables, Celery Beat) ─────────────
    ANALYTICS_CACHE_FRESHNESS_MINUTES: int = 60
    ANALYTICS_CACHE_STALE_TX_THRESHOLD: int = 100
    ANALYTICS_CACHE_IDEMPOTENCY_MINUTES: int = 5

    # ─── Email / SMTP ─────────────────────────────────────────────────────────
    MAIL_USERNAME: str = ""
    MAIL_PASSWORD: str = ""
    MAIL_FROM: str = ""
    MAIL_FROM_NAME: str = "Quantyx AI"
    MAIL_SERVER: str = "smtp.gmail.com"
    MAIL_PORT: int = 587
    MAIL_STARTTLS: bool = True
    MAIL_SSL_TLS: bool = False

    # ─── Invitation tokens ────────────────────────────────────────────────────
    INVITE_TOKEN_EXPIRE_HOURS: int = 72
    INVITE_SECRET_KEY: str = "change-this-to-random-64-char-string"
    FRONTEND_URL: str = "http://localhost:3000"

    # ─── AI Analyst / LLM (cloud-only, no local models) ──────────────────────
    LLM_PRIMARY_PROVIDER: str = "groq"
    LLM_FALLBACK_PROVIDER: str = "gemini"
    LLM_TERTIARY_PROVIDER: str = "openrouter"
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-1.5-flash"
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_MODEL: str = "meta-llama/llama-3.1-8b-instruct:free"
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    AI_ANALYST_MAX_TOKENS: int = 1500
    AI_ANALYST_RATE_LIMIT_PER_HOUR: int = 20
    AI_ANALYST_MAX_TOOL_ROUNDS: int = 5


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
