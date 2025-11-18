"""
Processing Time Service - Tracks and learns from actual transcription processing times

Uses linear regression to learn from historical data and improve progress estimates.
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
from collections import defaultdict

logger = logging.getLogger(__name__)


class ProcessingTimeService:
    """Tracks processing times and provides learned estimates."""

    DATA_PATH = Path(__file__).parent.parent.parent / "data" / "processing_times.json"

    def __init__(self):
        """Initialize processing time service."""
        self._ensure_data_directory()
        self.data = self._load_or_initialize()

    def _ensure_data_directory(self):
        """Create data directory if it doesn't exist."""
        self.DATA_PATH.parent.mkdir(parents=True, exist_ok=True)

    def _load_or_initialize(self) -> Dict[str, Any]:
        """Load existing data or initialize new."""
        if self.DATA_PATH.exists():
            try:
                with open(self.DATA_PATH, 'r') as f:
                    data = json.load(f)
                logger.info(f"Loaded processing time data: {len(data.get('records', []))} records")
                return data
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Error loading processing time data: {e}. Initializing fresh.")
                return self._initialize_empty()
        else:
            logger.info("No existing processing time data. Initializing fresh.")
            return self._initialize_empty()

    def _initialize_empty(self) -> Dict[str, Any]:
        """Initialize empty data structure."""
        return {
            "version": "1.0",
            "records": [],
            "models": {}
        }

    def _save(self):
        """Save data to file."""
        self.data["last_updated"] = datetime.now().isoformat()
        with open(self.DATA_PATH, 'w') as f:
            json.dump(self.data, f, indent=2)
        logger.debug(f"Saved processing time data to {self.DATA_PATH}")

    def record_processing_time(
        self,
        model: str,
        audio_duration_minutes: float,
        processing_time_seconds: float,
        job_id: Optional[str] = None
    ) -> None:
        """
        Record a processing time data point.

        Args:
            model: Model used (e.g., 'chirp_standard', 'long_standard')
            audio_duration_minutes: Audio duration in minutes
            processing_time_seconds: Processing time in seconds (processing_started_at to completed_at, excludes queueing)
            job_id: Optional job ID for tracking
        """
        record = {
            "model": model,
            "audio_duration_minutes": round(audio_duration_minutes, 2),
            "processing_time_seconds": round(processing_time_seconds, 2),
            "timestamp": datetime.now().isoformat(),
            "job_id": job_id
        }

        self.data["records"].append(record)

        # Recalculate model estimates
        self._update_model_estimates(model)

        # Save to disk
        self._save()

        logger.info(
            f"Recorded processing time: {model} - "
            f"{audio_duration_minutes:.1f} min → {processing_time_seconds:.1f}s"
        )

    def _update_model_estimates(self, model: str):
        """
        Update linear regression estimates for a model.

        Formula: processing_time = base_time + rate * audio_duration

        Args:
            model: Model name to update
        """
        # Get all records for this model
        model_records = [
            r for r in self.data["records"]
            if r["model"] == model
        ]

        if len(model_records) < 2:
            # Not enough data for regression - use fallback
            if len(model_records) == 1:
                # Single data point - use it as estimate
                record = model_records[0]
                # Estimate: assume 0 base time, rate = time / duration
                rate = record["processing_time_seconds"] / record["audio_duration_minutes"]
                self.data["models"][model] = {
                    "base_time_seconds": 0.0,
                    "rate_per_minute_seconds": round(rate, 2),
                    "sample_count": 1,
                    "confidence": "low",
                    "last_updated": datetime.now().isoformat()
                }
            else:
                # No data - use hardcoded fallback
                self.data["models"][model] = self._get_fallback_estimate(model)
            return

        # Linear regression: time = base + rate * duration
        # Formula: rate = (n*sum(dt) - sum(d)*sum(t)) / (n*sum(d^2) - sum(d)^2)
        #          base = (sum(t) - rate*sum(d)) / n
        n = len(model_records)
        sum_d = sum(r["audio_duration_minutes"] for r in model_records)
        sum_t = sum(r["processing_time_seconds"] for r in model_records)
        sum_dt = sum(r["audio_duration_minutes"] * r["processing_time_seconds"] for r in model_records)
        sum_d2 = sum(r["audio_duration_minutes"] ** 2 for r in model_records)

        denominator = (n * sum_d2 - sum_d ** 2)
        if denominator == 0:
            # All durations are the same - use average
            avg_time = sum_t / n
            avg_duration = sum_d / n
            rate = avg_time / avg_duration if avg_duration > 0 else 0
            base = 0.0
        else:
            rate = (n * sum_dt - sum_d * sum_t) / denominator
            base = (sum_t - rate * sum_d) / n

        # Calculate R² (coefficient of determination) for quality assessment
        predicted = [base + rate * r["audio_duration_minutes"] for r in model_records]
        actual = [r["processing_time_seconds"] for r in model_records]
        mean_actual = sum(actual) / len(actual)
        ss_res = sum((a - p) ** 2 for a, p in zip(actual, predicted))
        ss_tot = sum((a - mean_actual) ** 2 for a in actual)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0

        # Determine confidence based on sample count and R²
        if n >= 10 and r_squared >= 0.7:
            confidence = "high"
        elif n >= 5 and r_squared >= 0.5:
            confidence = "medium"
        else:
            confidence = "low"

        self.data["models"][model] = {
            "base_time_seconds": round(base, 2),
            "rate_per_minute_seconds": round(rate, 2),
            "sample_count": n,
            "r_squared": round(r_squared, 3),
            "confidence": confidence,
            "last_updated": datetime.now().isoformat()
        }

        logger.debug(
            f"Updated {model} estimate: {base:.1f}s + {rate:.2f}s/min * duration "
            f"(R²={r_squared:.3f}, n={n}, confidence={confidence})"
        )

    def _get_fallback_estimate(self, model: str) -> Dict[str, Any]:
        """
        Get hardcoded fallback estimate when no data available.

        Args:
            model: Model name

        Returns:
            Fallback estimate dict
        """
        # Hardcoded estimates (from original frontend code)
        if "batch" in model:
            base = 45.0
            rate = 5.0
        else:
            base = 22.0
            rate = 3.0

        return {
            "base_time_seconds": base,
            "rate_per_minute_seconds": rate,
            "sample_count": 0,
            "confidence": "fallback",
            "last_updated": datetime.now().isoformat()
        }

    def get_estimate(
        self,
        model: str,
        audio_duration_minutes: float
    ) -> Dict[str, Any]:
        """
        Get estimated processing time for a job.

        Args:
            model: Model name
            audio_duration_minutes: Audio duration in minutes

        Returns:
            Dict with estimated_seconds and confidence
        """
        # Get model estimate (or fallback)
        if model not in self.data["models"]:
            # No data for this model - use fallback
            model_estimate = self._get_fallback_estimate(model)
        else:
            model_estimate = self.data["models"][model]

        # Calculate estimate: base + rate * duration
        estimated_seconds = (
            model_estimate["base_time_seconds"] +
            model_estimate["rate_per_minute_seconds"] * audio_duration_minutes
        )

        # Ensure rate_per_minute_seconds is non-negative (validation requirement)
        rate_per_minute = max(0.0, model_estimate["rate_per_minute_seconds"])
        
        return {
            "estimated_seconds": round(estimated_seconds, 1),
            "confidence": model_estimate["confidence"],
            "sample_count": model_estimate["sample_count"],
            "base_time_seconds": model_estimate["base_time_seconds"],
            "rate_per_minute_seconds": rate_per_minute,
            "r_squared": model_estimate.get("r_squared", None)
        }

    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about processing time data.

        Returns:
            Dict with statistics per model
        """
        stats = {
            "total_records": len(self.data["records"]),
            "models": {}
        }

        for model, estimate in self.data["models"].items():
            stats["models"][model] = {
                "sample_count": estimate["sample_count"],
                "confidence": estimate["confidence"],
                "base_time_seconds": estimate["base_time_seconds"],
                "rate_per_minute_seconds": estimate["rate_per_minute_seconds"],
                "r_squared": estimate.get("r_squared", None),
                "last_updated": estimate["last_updated"]
            }

        return stats


# Global instance
_processing_time_service = None


def get_processing_time_service() -> ProcessingTimeService:
    """Get singleton processing time service instance."""
    global _processing_time_service
    if _processing_time_service is None:
        _processing_time_service = ProcessingTimeService()
    return _processing_time_service

