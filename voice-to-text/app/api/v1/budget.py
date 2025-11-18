"""
Budget and pricing API endpoints.

Handles budget tracking, pricing information, and cost estimation.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Path, Body
from fastapi.responses import JSONResponse
from typing import Dict, Any, Optional

from app.models.requests import EstimateCostRequest
from app.models.responses import BudgetResponse, PricingResponse, CostEstimateResponse, ProcessingTimeEstimateResponse
from app.services.budget import BudgetService
from app.services.pricing import PricingService
from app.services.processing_time import ProcessingTimeService

logger = logging.getLogger(__name__)

# Create router for this module
router = APIRouter()


def get_budget_service() -> BudgetService:
    """Dependency: Get budget service."""
    from app.services.budget import get_budget_service
    import os
    monthly_budget = float(os.getenv("MONTHLY_BUDGET", "250.0"))
    return get_budget_service(monthly_budget=monthly_budget)


def get_pricing_service() -> PricingService:
    """Dependency: Get pricing service."""
    from app.services.pricing import get_pricing_service
    return get_pricing_service()


def get_processing_time_service() -> ProcessingTimeService:
    """Dependency: Get processing time service."""
    from app.services.processing_time import get_processing_time_service
    return get_processing_time_service()


@router.get("/budget", response_model=BudgetResponse)
async def get_budget(
    budget_service: BudgetService = Depends(get_budget_service)
):
    """
    Get current budget summary for all providers.
    
    Returns:
        BudgetResponse with usage, remaining budget, free tier info for all providers
    """
    try:
        # Get summary for all providers (no provider filter)
        summary = budget_service.get_budget_summary(provider=None)
        return BudgetResponse(**summary)
    except Exception as e:
        logger.error(f"Error getting budget summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pricing", response_model=PricingResponse)
async def get_pricing(
    pricing_service: PricingService = Depends(get_pricing_service)
):
    """
    Get pricing information for all providers and models.
    
    Returns:
        PricingResponse with complete pricing configuration
    """
    try:
        pricing = pricing_service.get_all_pricing()
        return PricingResponse(pricing=pricing)
    except Exception as e:
        logger.error(f"Error getting pricing: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pricing/{provider}", response_model=PricingResponse)
async def get_provider_pricing(
    provider: str = Path(..., description="Provider name (e.g., 'google', 'whisper')"),
    pricing_service: PricingService = Depends(get_pricing_service)
):
    """
    Get pricing for specific provider.
    
    Args:
        provider: Provider name (e.g., 'google', 'whisper')
        
    Returns:
        PricingResponse with provider pricing configuration
    """
    try:
        pricing = pricing_service.get_provider_pricing(provider)
        return PricingResponse(pricing=pricing)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting provider pricing: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/estimate-cost", response_model=CostEstimateResponse)
async def estimate_cost(
    request: EstimateCostRequest = Body(...),
    pricing_service: PricingService = Depends(get_pricing_service),
    budget_service: BudgetService = Depends(get_budget_service)
):
    """
    Estimate cost for a transcription.
    
    Request body:
        {
            "provider": "google",
            "model": "chirp_batch",
            "duration_minutes": 75.0
        }
        
    Returns:
        CostEstimateResponse with cost breakdown
    """
    try:
        import os
        provider = request.provider or os.getenv("STT_PROVIDER", "google")
        model = request.model or os.getenv("GOOGLE_MODEL", "long")
        duration_minutes = request.duration_minutes
        
        logger.info(f"Cost estimate request: provider={provider}, model={model}, duration={duration_minutes}")
        
        # Get free tier remaining
        free_tier_remaining = budget_service.get_free_tier_remaining(provider)
        
        # Calculate estimate
        estimate = pricing_service.estimate_cost(
            provider=provider,
            model=model,
            duration_minutes=duration_minutes,
            free_tier_remaining=free_tier_remaining
        )
        
        logger.info(f"Cost estimate result: ${estimate['total_cost']:.2f} for {duration_minutes} minutes")
        
        return CostEstimateResponse(**estimate)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error estimating cost: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/estimate-processing-time", response_model=ProcessingTimeEstimateResponse)
async def estimate_processing_time(
    model: str,
    duration_minutes: float,
    processing_time_service: ProcessingTimeService = Depends(get_processing_time_service)
):
    """
    Get estimated processing time for a transcription job.
    
    Uses learned estimates from historical data, with fallback to hardcoded values.
    
    Args:
        model: Model name (e.g., 'chirp_standard', 'long_standard')
        duration_minutes: Audio duration in minutes
        
    Returns:
        ProcessingTimeEstimateResponse with estimated_seconds, confidence, and model details
    """
    try:
        if duration_minutes <= 0:
            raise HTTPException(status_code=400, detail="duration_minutes must be > 0")
        
        estimate = processing_time_service.get_estimate(
            model=model,
            audio_duration_minutes=duration_minutes
        )
        
        return ProcessingTimeEstimateResponse(**estimate)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error estimating processing time: {e}")
        raise HTTPException(status_code=500, detail=str(e))

