from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment or defaults."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
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
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    # JWT Authentication (Phase 5)
    JWT_SECRET_KEY: str = ""
    JWT_SECRET: str = ""
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    @property
    def effective_jwt_secret(self) -> str:
        """Return the effective JWT secret key from environment configuration."""
        secret = self.JWT_SECRET_KEY or self.JWT_SECRET
        return secret.strip() if secret else ""


settings = Settings()
