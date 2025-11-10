"""
Budget Tracking Service - Manages monthly transcription budgets and usage

Tracks usage by provider and resets monthly.
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
from calendar import monthrange

logger = logging.getLogger(__name__)


class BudgetService:
    """Manages budget tracking and usage monitoring."""

    DATA_PATH = Path(__file__).parent.parent.parent / "data" / "budget_tracking.json"

    def __init__(self, monthly_budget: float = 250.0):
        """
        Initialize budget service.

        Args:
            monthly_budget: Monthly budget limit in USD (default: $250)
        """
        self.monthly_budget = monthly_budget
        self._ensure_data_directory()
        self.data = self._load_or_initialize()

    def _ensure_data_directory(self):
        """Create data directory if it doesn't exist."""
        self.DATA_PATH.parent.mkdir(parents=True, exist_ok=True)

    def _load_or_initialize(self) -> Dict[str, Any]:
        """Load existing budget data or initialize new."""
        if self.DATA_PATH.exists():
            try:
                with open(self.DATA_PATH, 'r') as f:
                    data = json.load(f)
                logger.info(f"Loaded budget data from {self.DATA_PATH}")
                return self._check_and_reset_if_new_month(data)
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Error loading budget data: {e}. Initializing fresh.")
                return self._initialize_new_month()
        else:
            logger.info("No existing budget data. Initializing fresh.")
            return self._initialize_new_month()

    def _initialize_new_month(self) -> Dict[str, Any]:
        """Initialize budget tracking for new month."""
        now = datetime.now()
        return {
            "month": now.strftime("%Y-%m"),
            "monthly_budget": self.monthly_budget,
            "providers": {
                "google": {
                    "total_cost": 0.0,
                    "free_tier_used": 0.0,
                    "free_tier_limit": 60.0,  # 60 minutes/month
                    "transcriptions": []
                },
                "whisper": {
                    "total_cost": 0.0,
                    "credit_used": 0.0,
                    "credit_limit": 5.0,  # $5 one-time credit
                    "transcriptions": []
                }
            },
            "last_updated": now.isoformat()
        }

    def _check_and_reset_if_new_month(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Check if we're in a new month and reset if needed."""
        current_month = datetime.now().strftime("%Y-%m")

        if data.get("month") != current_month:
            logger.info(f"New month detected: {current_month}. Resetting budget tracking.")
            # Archive old month's data (optional - for now just log)
            logger.info(f"Previous month {data.get('month')} total spent: ${self._calculate_total_spent(data):.2f}")
            # Initialize fresh for new month
            return self._initialize_new_month()

        return data

    def _calculate_total_spent(self, data: Dict[str, Any]) -> float:
        """Calculate total spent across all providers."""
        total = 0.0
        for provider_data in data.get("providers", {}).values():
            total += provider_data.get("total_cost", 0.0)
        return total

    def _save(self):
        """Save budget data to file."""
        self.data["last_updated"] = datetime.now().isoformat()
        with open(self.DATA_PATH, 'w') as f:
            json.dump(self.data, f, indent=2)
        logger.debug(f"Saved budget data to {self.DATA_PATH}")

    def get_budget_summary(self, provider: Optional[str] = None) -> Dict[str, Any]:
        """
        Get budget summary.

        Args:
            provider: Optional provider name to filter by

        Returns:
            Budget summary with usage, remaining budget, free tier info
        """
        # Ensure we're in current month
        self.data = self._check_and_reset_if_new_month(self.data)

        total_spent = self._calculate_total_spent(self.data)
        remaining = self.monthly_budget - total_spent

        summary = {
            "month": self.data["month"],
            "monthly_budget": self.monthly_budget,
            "total_spent": round(total_spent, 2),
            "remaining": round(remaining, 2),
            "percent_used": round((total_spent / self.monthly_budget * 100), 1) if self.monthly_budget > 0 else 0
        }

        # Add provider-specific info
        if provider:
            if provider not in self.data["providers"]:
                logger.warning(f"Unknown provider: {provider}")
                return summary

            provider_data = self.data["providers"][provider]
            summary["provider"] = {
                "name": provider,
                "total_cost": provider_data.get("total_cost", 0.0),
                "transcription_count": len(provider_data.get("transcriptions", []))
            }

            # Add free tier info
            if provider == "google":
                summary["provider"]["free_tier"] = {
                    "used": provider_data.get("free_tier_used", 0.0),
                    "limit": provider_data.get("free_tier_limit", 60.0),
                    "remaining": provider_data.get("free_tier_limit", 60.0) - provider_data.get("free_tier_used", 0.0)
                }
            elif provider == "whisper":
                summary["provider"]["credit"] = {
                    "used": provider_data.get("credit_used", 0.0),
                    "limit": provider_data.get("credit_limit", 5.0),
                    "remaining": provider_data.get("credit_limit", 5.0) - provider_data.get("credit_used", 0.0)
                }

        else:
            # Add all providers
            summary["providers"] = {}
            for prov_name, prov_data in self.data["providers"].items():
                summary["providers"][prov_name] = {
                    "total_cost": prov_data.get("total_cost", 0.0),
                    "transcription_count": len(prov_data.get("transcriptions", []))
                }

                if prov_name == "google":
                    summary["providers"][prov_name]["free_tier_remaining"] = (
                        prov_data.get("free_tier_limit", 60.0) - prov_data.get("free_tier_used", 0.0)
                    )

        return summary

    def record_transcription(
        self,
        provider: str,
        model: str,
        duration_minutes: float,
        cost: float,
        free_minutes_used: float = 0,
        filename: str = ""
    ) -> None:
        """
        Record a transcription in budget tracking.

        Args:
            provider: Provider name (e.g., 'google', 'whisper')
            model: Model used (e.g., 'chirp_batch')
            duration_minutes: Audio duration in minutes
            cost: Total cost for this transcription
            free_minutes_used: How many free tier minutes were used
            filename: Optional filename for tracking
        """
        # Ensure we're in current month
        self.data = self._check_and_reset_if_new_month(self.data)

        if provider not in self.data["providers"]:
            logger.warning(f"Unknown provider: {provider}. Initializing...")
            self.data["providers"][provider] = {
                "total_cost": 0.0,
                "transcriptions": []
            }

        provider_data = self.data["providers"][provider]

        # Record transcription
        transcription_record = {
            "timestamp": datetime.now().isoformat(),
            "model": model,
            "duration_minutes": round(duration_minutes, 2),
            "cost": round(cost, 2),
            "filename": filename
        }

        if free_minutes_used > 0:
            transcription_record["free_minutes_used"] = round(free_minutes_used, 2)

        provider_data["transcriptions"].append(transcription_record)
        provider_data["total_cost"] = round(provider_data.get("total_cost", 0.0) + cost, 2)

        # Update free tier tracking
        if provider == "google" and free_minutes_used > 0:
            provider_data["free_tier_used"] = round(
                provider_data.get("free_tier_used", 0.0) + free_minutes_used, 2
            )

        # Save to disk
        self._save()

        logger.info(
            f"Recorded transcription: {provider}/{model} - "
            f"{duration_minutes:.1f} min - ${cost:.2f}"
        )

    def get_free_tier_remaining(self, provider: str) -> float:
        """Get remaining free tier minutes/credit for provider."""
        # Ensure we're in current month
        self.data = self._check_and_reset_if_new_month(self.data)

        if provider not in self.data["providers"]:
            return 0.0

        provider_data = self.data["providers"][provider]

        if provider == "google":
            limit = provider_data.get("free_tier_limit", 60.0)
            used = provider_data.get("free_tier_used", 0.0)
            return max(0.0, limit - used)

        elif provider == "whisper":
            limit = provider_data.get("credit_limit", 5.0)
            used = provider_data.get("credit_used", 0.0)
            return max(0.0, limit - used)

        return 0.0


# Global instance
_budget_service = None


def get_budget_service(monthly_budget: float = 250.0) -> BudgetService:
    """Get singleton budget service instance."""
    global _budget_service
    if _budget_service is None:
        _budget_service = BudgetService(monthly_budget=monthly_budget)
    return _budget_service
