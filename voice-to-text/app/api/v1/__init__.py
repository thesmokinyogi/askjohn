"""
API v1 routes for Voice-to-Text service.

All API endpoints are versioned under /api/v1/ for future compatibility.
"""

from fastapi import APIRouter

# Create main API router
api_router = APIRouter(prefix="/api/v1", tags=["api"])

# Import all route modules (they will register with api_router)
from app.api.v1 import jobs, library, budget, transcription, errors

# Include all routers
api_router.include_router(jobs.router, tags=["jobs"])
api_router.include_router(library.router, tags=["library"])
api_router.include_router(budget.router, tags=["budget"])
api_router.include_router(transcription.router, tags=["transcription"])

__all__ = ["api_router"]

