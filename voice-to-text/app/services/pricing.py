"""
Pricing Service - Manages transcription pricing across providers

Loads pricing from config/pricing.json and provides cost estimation.
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class PricingService:
    """Manages pricing configuration and cost estimation."""

    CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "pricing.json"

    def __init__(self):
        """Initialize pricing service."""
        self.config = self._load_config()
        self._check_freshness()

    def _load_config(self) -> Dict[str, Any]:
        """Load pricing configuration from JSON file."""
        try:
            with open(self.CONFIG_PATH, 'r') as f:
                config = json.load(f)
            logger.info(f"Loaded pricing config version {config.get('version', 'unknown')}")
            return config
        except FileNotFoundError:
            logger.error(f"Pricing config not found: {self.CONFIG_PATH}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Invalid pricing config JSON: {e}")
            raise

    def _check_freshness(self):
        """Warn if pricing data is stale (>90 days)."""
        for provider_name, provider_config in self.config['providers'].items():
            if provider_config['fetch_method'] == 'manual':
                models = provider_config['models']
                for model_name, model_config in models.items():
                    last_verified = datetime.fromisoformat(model_config['last_verified'])
                    age_days = (datetime.now() - last_verified).days

                    if age_days > 90:
                        logger.warning(
                            f"⚠️  {provider_name}/{model_name} pricing not verified in "
                            f"{age_days} days. Please review pricing."
                        )

    def get_all_pricing(self) -> Dict[str, Any]:
        """Get complete pricing configuration."""
        return self.config

    def get_provider_pricing(self, provider: str) -> Dict[str, Any]:
        """Get pricing for specific provider."""
        if provider not in self.config['providers']:
            raise ValueError(f"Unknown provider: {provider}")
        return self.config['providers'][provider]

    def get_model_pricing(self, provider: str, model: str) -> Dict[str, Any]:
        """Get pricing for specific provider/model."""
        provider_config = self.get_provider_pricing(provider)

        if model not in provider_config['models']:
            raise ValueError(f"Unknown model {model} for provider {provider}")

        return provider_config['models'][model]

    def get_cost_per_minute(self, provider: str, model: str) -> float:
        """Get cost per minute for provider/model."""
        model_config = self.get_model_pricing(provider, model)
        return model_config['cost_per_min']

    def get_free_tier_info(self, provider: str) -> Dict[str, Any]:
        """Get free tier information for provider."""
        provider_config = self.get_provider_pricing(provider)
        return provider_config.get('free_tier', {})

    def estimate_cost(
        self,
        provider: str,
        model: str,
        duration_minutes: float,
        free_tier_remaining: float = 0
    ) -> Dict[str, Any]:
        """
        Estimate cost for transcription.

        Args:
            provider: Provider name (e.g., 'google', 'whisper')
            model: Model name (e.g., 'chirp_batch', 'long_standard')
            duration_minutes: Audio duration in minutes
            free_tier_remaining: Remaining free tier minutes for this month

        Returns:
            Dict with cost breakdown:
            {
                'total_minutes': float,
                'free_minutes_used': float,
                'billable_minutes': float,
                'cost_per_minute': float,
                'total_cost': float,
                'currency': str,
                'model_info': dict
            }
        """
        cost_per_min = self.get_cost_per_minute(provider, model)
        model_info = self.get_model_pricing(provider, model)

        # Calculate billable minutes (after free tier)
        free_minutes_used = min(duration_minutes, free_tier_remaining)
        billable_minutes = max(0, duration_minutes - free_tier_remaining)

        # Calculate total cost
        total_cost = billable_minutes * cost_per_min

        return {
            'total_minutes': duration_minutes,
            'free_minutes_used': free_minutes_used,
            'billable_minutes': billable_minutes,
            'cost_per_minute': cost_per_min,
            'total_cost': round(total_cost, 2),
            'currency': 'USD',
            'model_info': {
                'display_name': model_info['display_name'],
                'processing_time': model_info['processing_time'],
                'features': model_info['features']
            }
        }

    def update_model_pricing(self, provider: str, model: str, cost_per_min: float) -> None:
        """
        Update pricing for a specific model (admin function).

        Args:
            provider: Provider name
            model: Model name
            cost_per_min: New cost per minute
        """
        if provider not in self.config['providers']:
            raise ValueError(f"Unknown provider: {provider}")

        if model not in self.config['providers'][provider]['models']:
            raise ValueError(f"Unknown model {model} for provider {provider}")

        # Update pricing
        self.config['providers'][provider]['models'][model]['cost_per_min'] = cost_per_min
        self.config['providers'][provider]['models'][model]['last_verified'] = datetime.now().isoformat()
        self.config['last_updated'] = datetime.now().isoformat()

        # Save to file
        with open(self.CONFIG_PATH, 'w') as f:
            json.dump(self.config, f, indent=2)

        logger.info(f"Updated {provider}/{model} pricing to ${cost_per_min}/min")


# Global instance
_pricing_service = None


def get_pricing_service() -> PricingService:
    """Get singleton pricing service instance."""
    global _pricing_service
    if _pricing_service is None:
        _pricing_service = PricingService()
    return _pricing_service
