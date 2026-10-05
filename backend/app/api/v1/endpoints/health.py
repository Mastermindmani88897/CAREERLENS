from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.core.config import settings
from app.core.logging import get_logger
from app.db.session import check_db_health

router = APIRouter()
logger = get_logger("health")


class HealthResponse(BaseModel):
    status: str
    app: str
    version: str


class DatabaseHealthResponse(BaseModel):
    status: str
    app: str
    version: str
    database: str
    pgvector_installed: bool
    pgvector_version: str | None
    pgvector_operational: bool


@router.get("/health", response_model=HealthResponse, summary="Service Health Check")
def health_check() -> HealthResponse:
    """Return basic health status of the API service."""
    return HealthResponse(
        status="ok",
        app=settings.PROJECT_NAME,
        version=settings.VERSION,
    )


@router.get(
    "/health/db",
    response_model=DatabaseHealthResponse,
    summary="Database & pgvector Health Check",
)
async def db_health_check() -> DatabaseHealthResponse:
    """Check database connectivity and pgvector extension status."""
    try:
        health_data = await check_db_health()
        return DatabaseHealthResponse(
            status="ok",
            app=settings.PROJECT_NAME,
            version=settings.VERSION,
            database=health_data["database"],
            pgvector_installed=health_data["pgvector_installed"],
            pgvector_version=health_data["pgvector_version"],
            pgvector_operational=health_data["pgvector_operational"],
        )
    except Exception as exc:
        logger.error("Database health check failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database health check failed: service unavailable",
        ) from None
