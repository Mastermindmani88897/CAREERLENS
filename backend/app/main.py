from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.api import api_router
from app.api.v1.endpoints.health import (
    DatabaseHealthResponse,
    HealthResponse,
    db_health_check,
    health_check,
)
from app.core.config import settings
from app.core.logging import get_logger, setup_logging

# Initialize centralized logging security foundation
setup_logging(level=settings.LOG_LEVEL)
logger = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan context for startup and shutdown event handling."""
    logger.info(
        "Starting %s v%s in %s mode", settings.PROJECT_NAME, settings.VERSION, settings.ENVIRONMENT
    )
    yield
    logger.info("Shutting down %s", settings.PROJECT_NAME)


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)


# Security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Inject standard protective HTTP headers on all outgoing responses."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), payment=()"
    if settings.ENVIRONMENT.lower() in ("production", "prod"):
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


# Global exception handler to prevent stack trace and credential leakage
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Sanitize internal errors to prevent server path and credential leakage."""
    logger.error(
        "Unhandled exception during %s %s: %s",
        request.method,
        request.url.path,
        exc,
        exc_info=True,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )


# CORS middleware with explicit methods and headers
if settings.CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
        allow_headers=[
            "Content-Type",
            "Authorization",
            "Accept",
            "Origin",
            "X-Requested-With",
        ],
    )

# Include API v1 router: provides /api/v1/health, /api/v1/health/db, /api/v1/auth
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
