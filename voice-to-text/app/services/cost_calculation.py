"""
Cost Calculation Service

Calculates actual transcription costs from billed duration, free tier, and model pricing.
Extracted from main.py for better separation of concerns.
"""

import logging
from typing import Dict, Any, Optional

from app.services.pricing import PricingService
from app.services.budget import BudgetService

logger = logging.getLogger(__name__)


class CostCalculationService:
    """Service for calculating transcription costs."""
    
    def __init__(
        self,
        pricing_service: PricingService,
        budget_service: BudgetService
    ):
        """Initialize cost calculation service.
        
        Args:
            pricing_service: Service for getting pricing rates
            budget_service: Service for getting free tier information
        """
        self.pricing_service = pricing_service
        self.budget_service = budget_service
    
    def calculate_actual_cost(
        self,
        provider: str,
        model: str,
        billed_duration_minutes: float,
        estimated_duration_minutes: Optional[float] = None,
        estimated_cost: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Calculate actual cost from billed duration.
        
        This is the authoritative cost calculation used when a job completes.
        It uses the actual billed duration from Google's API, not estimates.
        
        Args:
            provider: Provider name (e.g., 'google')
            model: Model name (e.g., 'chirp_batch')
            billed_duration_minutes: Actual billed duration from Google API
            estimated_duration_minutes: Fallback if billed_duration is None
            estimated_cost: Fallback if calculation fails
            
        Returns:
            Dict with:
                - actual_cost: Final cost in USD
                - actual_free_minutes_used: Free tier minutes consumed
                - actual_billable_minutes: Billable minutes (after free tier)
                - cost_per_minute: Rate used for calculation
                - billed_duration_minutes: Duration used (may be estimated if API didn't provide)
        """
        # Use billed duration if available, otherwise fall back to estimated
        if billed_duration_minutes is None:
            if estimated_duration_minutes is None:
                raise ValueError("billed_duration_minutes or estimated_duration_minutes must be provided")
            logger.warning(
                f"Missing billed_duration_minutes, using estimated duration: {estimated_duration_minutes:.2f} minutes"
            )
            billed_duration_minutes = estimated_duration_minutes
        else:
            logger.info(f"Using actual billed duration: {billed_duration_minutes:.2f} minutes")
        
        # Get current free tier remaining
        free_tier_remaining = self.budget_service.get_free_tier_remaining(provider)
        
        # Calculate actual free minutes used and billable minutes
        actual_free_minutes_used = min(billed_duration_minutes, free_tier_remaining)
        actual_billable_minutes = max(0, billed_duration_minutes - free_tier_remaining)
        
        # Get cost per minute for this model
        cost_per_minute = self.pricing_service.get_cost_per_minute(provider, model)
        
        if cost_per_minute is None:
            logger.warning(f"Could not get cost per minute for {provider}/{model}, using estimated cost")
            if estimated_cost is None:
                raise ValueError(f"Could not calculate cost: no pricing for {provider}/{model} and no estimated_cost provided")
            actual_cost = estimated_cost
        else:
            # Calculate actual cost
            actual_cost = actual_billable_minutes * cost_per_minute
            
            # Validate cost is reasonable
            if actual_cost < 0:
                logger.warning(f"Calculated negative cost: {actual_cost}, using estimated cost")
                if estimated_cost is not None:
                    actual_cost = estimated_cost
                else:
                    actual_cost = 0.0
        
        return {
            "actual_cost": actual_cost,
            "actual_free_minutes_used": actual_free_minutes_used,
            "actual_billable_minutes": actual_billable_minutes,
            "cost_per_minute": cost_per_minute,
            "billed_duration_minutes": billed_duration_minutes
        }


# Global service instance
_cost_calculation_service: Optional[CostCalculationService] = None


def get_cost_calculation_service() -> CostCalculationService:
    """Get global cost calculation service instance."""
    global _cost_calculation_service
    if _cost_calculation_service is None:
        from app.services.pricing import get_pricing_service
        from app.services.budget import get_budget_service
        import os
        
        pricing_service = get_pricing_service()
        monthly_budget = float(os.getenv("MONTHLY_BUDGET", "250.0"))
        budget_service = get_budget_service(monthly_budget=monthly_budget)
        
        _cost_calculation_service = CostCalculationService(
            pricing_service=pricing_service,
            budget_service=budget_service
        )
    
    return _cost_calculation_service

