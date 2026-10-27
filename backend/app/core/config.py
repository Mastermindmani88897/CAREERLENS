from typing import Any

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment or defaults."""

    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    PROJECT_NAME: str = "CareerLens"
    VERSION: str = "0.5.0"
    API_V1_STR: str = "/api/v1"

    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    DATABASE_URL: str = "postgresql+asyncpg://careerlens_user:PASSWORD@localhost:5432/careerlens_db"
    TEST_DATABASE_URL: str = (
        "postgresql+asyncpg://careerlens_user:PASSWORD@localhost:5432/careerlens_test"
    )
    ALLOWED_ORIGINS: str | list[str] | None = None
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    # Security & Tooling Hardening (Phase 8)
    SECURE_HEADERS: bool = True
    LOG_LEVEL: str = "INFO"

    # JWT Authentication (Phase 5)
    JWT_SECRET_KEY: str = ""
    JWT_SECRET: str = ""
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Resume Upload & Processing (Phase 11)
    RESUME_UPLOAD_DIR: str = "./data/uploads/resumes"
    MAX_RESUME_SIZE_MB: int = 10

    # Embeddings Foundation (Phase 16)
    EMBEDDING_PROVIDER: str = "local"
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    EMBEDDING_DIMENSION: int = 384

    # External Opportunity Connectors (Phase 26)
    GREENHOUSE_BOARD_TOKENS: str = ""
    LEVER_SITE_TOKENS: str = ""
    ADZUNA_APP_ID: str = ""
    ADZUNA_APP_KEY: str = ""
    USAJOBS_API_KEY: str = ""
    USAJOBS_EMAIL: str = ""

    # Connector Synchronization & Scheduler (Phase 26.5)
    SCHEDULER_ENABLED: bool = False
    SCHEDULER_INTERVAL_SECONDS: int = 60
    SCHEDULER_MAX_CONCURRENCY: int = 2
    CONNECTOR_TIMEOUT_SECONDS: int = 300
    CONNECTOR_STALE_LOCK_MINUTES: int = 30
    CONNECTOR_DEFAULT_REFRESH_MINUTES: int = 60

    # External Application Autofill (Phase 27)
    AUTOFILL_ENABLED: bool = False
    AUTOFILL_SESSION_TIMEOUT_MINUTES: int = 30
    AUTOFILL_ALLOWED_ATS_DOMAINS: list[str] = [
        "boards.greenhouse.io",
        "job-boards.greenhouse.io",
        "jobs.lever.co",
    ]

    @model_validator(mode="before")
    @classmethod
    def assemble_settings_aliases(cls, data: Any) -> Any:
        """Allow environment variable aliases and parse comma-separated origin strings."""
        if isinstance(data, dict):
            raw_origins = (
                data.get("CORS_ORIGINS") if "CORS_ORIGINS" in data else data.get("ALLOWED_ORIGINS")
            )
            if raw_origins is not None:
                if isinstance(raw_origins, str):
                    parsed = [o.strip().rstrip("/") for o in raw_origins.split(",") if o.strip()]
                    data["CORS_ORIGINS"] = parsed
                elif isinstance(raw_origins, list):
                    data["CORS_ORIGINS"] = [
                        str(o).strip().rstrip("/") for o in raw_origins if str(o).strip()
                    ]
            if "MAX_RESUME_FILE_SIZE_MB" in data and "MAX_RESUME_SIZE_MB" not in data:
                data["MAX_RESUME_SIZE_MB"] = data["MAX_RESUME_FILE_SIZE_MB"]
            raw_ats_domains = data.get("AUTOFILL_ALLOWED_ATS_DOMAINS")
            if raw_ats_domains is not None and isinstance(raw_ats_domains, str):
                data["AUTOFILL_ALLOWED_ATS_DOMAINS"] = [
                    d.strip().lower() for d in raw_ats_domains.split(",") if d.strip()
                ]
        return data

    @field_validator("CORS_ORIGINS", mode="after")
    @classmethod
    def validate_cors_origins(cls, v: list[str]) -> list[str]:
        """Normalize CORS origins and ensure trailing slashes are removed."""
        sanitized = [origin.rstrip("/") for origin in v if origin]
        return sanitized

    @model_validator(mode="after")
    def validate_production_security(self) -> "Settings":
        """Enforce strict security constraints when running in production."""
        is_prod = self.ENVIRONMENT.lower() in ("production", "prod")
        if is_prod:
            if self.DEBUG:
                raise ValueError("DEBUG must be set to False in production environment.")
            if not self.effective_jwt_secret or len(self.effective_jwt_secret) < 32:
                raise ValueError(
                    "JWT secret key must be at least 32 characters in production environment."
                )
            if "PASSWORD@" in self.DATABASE_URL or "PASSWORD@" in self.TEST_DATABASE_URL:
                raise ValueError(
                    "Production DATABASE_URL must not contain default placeholder credentials."
                )
            if "*" in self.CORS_ORIGINS:
                raise ValueError("Wildcard CORS origin is forbidden in production.")
        return self

    @property
    def effective_jwt_secret(self) -> str:
        """Return the effective JWT secret key from environment configuration."""
        secret = self.JWT_SECRET_KEY or self.JWT_SECRET
        return secret.strip() if secret else ""

    @property
    def effective_database_url(self) -> str:
        """Return the database URL appropriate for the active environment."""
        if self.ENVIRONMENT.lower() == "test":
            return self.TEST_DATABASE_URL
        return self.DATABASE_URL


settings = Settings()
