from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.api import api_router
from app.api.v1.endpoints.health import (
    DatabaseHealthResponse,
    HealthResponse,
    db_health_check,
    health_check,
)
from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
if settings.CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Include API v1 router: provides /api/v1/health and /api/v1/health/db
app.include_router(api_router, prefix=settings.API_V1_STR)

# Expose health checks directly at root level as well
app.add_api_route(
    "/health",
    health_check,
    methods=["GET"],
    response_model=HealthResponse,
    tags=["health"],
)
app.add_api_route(
    "/health/db",
    db_health_check,
    methods=["GET"],
    response_model=DatabaseHealthResponse,
    tags=["health"],
)


@app.get("/", summary="Root Endpoint")
def root():
    """Root entry point providing basic API metadata."""
    return {
        "app": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "docs": "/docs",
        "health": f"{settings.API_V1_STR}/health",
    }
