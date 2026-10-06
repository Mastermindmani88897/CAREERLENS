from fastapi import APIRouter

from app.api.v1.endpoints import auth, health, resumes

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(resumes.router, prefix="/resumes", tags=["resumes"])
