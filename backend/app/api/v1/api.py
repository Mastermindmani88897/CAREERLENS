from fastapi import APIRouter

from app.api.v1.endpoints import auth, health, profiles, resumes

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(resumes.router, prefix="/resumes", tags=["resumes"])
api_router.include_router(profiles.router, prefix="/profiles", tags=["profiles"])
