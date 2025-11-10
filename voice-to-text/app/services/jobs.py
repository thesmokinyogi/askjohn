"""
Job Storage Service - Manages transcription job records

This service handles storing and retrieving transcription job metadata.
Jobs are stored in a simple JSON file for Phase 1 (single user, low volume).

Design decisions:
- JSON file storage (not database) for simplicity
- Atomic writes (write to temp file, then rename) to prevent corruption
- Job ID is Google's operation name (unique, can reconnect to operation)
- Stores minimal metadata (filename, model, timestamps, status)

Future: Migrate to SQLite/Postgres when integrating with Content Cockpit
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List
import tempfile
import shutil

logger = logging.getLogger(__name__)


class JobStorageService:
    """
    Manages transcription job records in JSON file storage.

    Thread safety: Uses atomic file operations (write to temp, then rename)
    Corruption resistance: Validates JSON before writing, keeps backup on write
    """

    # Where we store the jobs data
    DATA_PATH = Path(__file__).parent.parent.parent / "data" / "jobs.json"

    def __init__(self):
        """Initialize job storage, creating data directory if needed."""
        # Ensure the data directory exists
        # parents=True creates intermediate dirs if needed
        # exist_ok=True doesn't error if already exists
        self.DATA_PATH.parent.mkdir(parents=True, exist_ok=True)

        # Load existing jobs into memory (if file exists)
        self.jobs = self._load_jobs()

        logger.info(f"Job storage initialized: {len(self.jobs)} existing jobs")

    def _load_jobs(self) -> Dict[str, Any]:
        """
        Load jobs from JSON file.

        Returns:
            Dictionary of jobs, keyed by job_id (Google operation name)
            Empty dict if file doesn't exist or is corrupted
        """
        # If file doesn't exist yet, start with empty dict
        if not self.DATA_PATH.exists():
            logger.info(f"No existing jobs file at {self.DATA_PATH}")
            return {}

        try:
            # Read and parse JSON file
            with open(self.DATA_PATH, 'r') as f:
                jobs = json.load(f)

            logger.info(f"Loaded {len(jobs)} jobs from {self.DATA_PATH}")
            return jobs

        except json.JSONDecodeError as e:
            # File is corrupted - log error but don't crash
            logger.error(f"Corrupted jobs file: {e}")
            logger.error("Starting with empty jobs database")

            # Rename corrupted file so we don't lose it
            backup_path = self.DATA_PATH.with_suffix('.json.corrupted')
            shutil.copy(self.DATA_PATH, backup_path)
            logger.info(f"Saved corrupted file to {backup_path}")

            return {}

        except Exception as e:
            # Unexpected error - log and start fresh
            logger.error(f"Error loading jobs: {e}")
            return {}

    def _save_jobs(self):
        """
        Save jobs to JSON file using atomic write.

        Atomic write process:
        1. Write to temporary file
        2. Verify it's valid JSON
        3. Rename temp file to actual file (atomic operation)

        This prevents corruption if process crashes during write.
        """
        try:
            # Create temp file in same directory as target file
            # This ensures rename is atomic (same filesystem)
            temp_fd, temp_path = tempfile.mkstemp(
                dir=self.DATA_PATH.parent,
                suffix='.tmp',
                prefix='jobs_'
            )

            # Write jobs to temp file
            # indent=2 makes it human-readable (good for debugging)
            with open(temp_fd, 'w') as f:
                json.dump(self.jobs, f, indent=2, default=str)

            # Verify the temp file is valid JSON before committing
            with open(temp_path, 'r') as f:
                json.load(f)  # Will raise exception if invalid

            # Atomic rename - if this succeeds, write is durable
            # If process crashes after this, data is safe
            shutil.move(temp_path, self.DATA_PATH)

            logger.debug(f"Saved {len(self.jobs)} jobs to {self.DATA_PATH}")

        except Exception as e:
            logger.error(f"Error saving jobs: {e}")
            # Clean up temp file if it exists
            if 'temp_path' in locals() and Path(temp_path).exists():
                Path(temp_path).unlink()
            raise

    def create_job(
        self,
        job_id: str,
        filename: str,
        model: str,
        duration_minutes: float = 0,
        estimated_cost: float = 0
    ) -> Dict[str, Any]:
        """
        Create a new job record.

        Args:
            job_id: Google operation name (unique identifier)
            filename: Original audio filename
            model: Model used (e.g., 'chirp_batch', 'long_standard')
            duration_minutes: Audio duration in minutes
            estimated_cost: Estimated transcription cost

        Returns:
            The created job record
        """
        # Create job record with metadata
        job = {
            "job_id": job_id,
            "filename": filename,
            "model": model,
            "duration_minutes": duration_minutes,
            "estimated_cost": estimated_cost,
            "status": "queued",  # Initial state
            "submitted_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            # Results populated later when job completes
            "transcript": None,
            "confidence": None,
            "actual_cost": None,
            "completed_at": None,
            "error": None
        }

        # Store in memory
        self.jobs[job_id] = job

        # Persist to disk
        self._save_jobs()

        logger.info(f"Created job: {job_id} ({filename}, {model})")
        return job

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a job by ID.

        Args:
            job_id: Google operation name

        Returns:
            Job record or None if not found
        """
        return self.jobs.get(job_id)

    def update_job(self, job_id: str, updates: Dict[str, Any]):
        """
        Update a job's fields.

        Args:
            job_id: Google operation name
            updates: Dictionary of fields to update

        Raises:
            KeyError if job doesn't exist
        """
        if job_id not in self.jobs:
            raise KeyError(f"Job not found: {job_id}")

        # Update fields
        self.jobs[job_id].update(updates)

        # Always update the timestamp
        self.jobs[job_id]["updated_at"] = datetime.now().isoformat()

        # Persist to disk
        self._save_jobs()

        logger.info(f"Updated job {job_id}: {list(updates.keys())}")

    def mark_complete(
        self,
        job_id: str,
        transcript: str,
        confidence: float,
        actual_cost: float,
        metadata: Dict[str, Any] = None
    ):
        """
        Mark a job as complete with results.

        Args:
            job_id: Google operation name
            transcript: The transcribed text
            confidence: Confidence score (0.0 to 1.0)
            actual_cost: Actual cost charged
            metadata: Optional additional metadata
        """
        updates = {
            "status": "complete",
            "transcript": transcript,
            "confidence": confidence,
            "actual_cost": actual_cost,
            "completed_at": datetime.now().isoformat()
        }

        # Add any additional metadata
        if metadata:
            updates["metadata"] = metadata

        self.update_job(job_id, updates)

    def mark_failed(self, job_id: str, error: str):
        """
        Mark a job as failed with error message.

        Args:
            job_id: Google operation name
            error: Error message describing what went wrong
        """
        self.update_job(job_id, {
            "status": "failed",
            "error": error,
            "completed_at": datetime.now().isoformat()
        })

    def list_jobs(
        self,
        status: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        List jobs, optionally filtered by status.

        Args:
            status: Filter by status ('queued', 'processing', 'complete', 'failed')
            limit: Maximum number of jobs to return

        Returns:
            List of job records, sorted by submission time (newest first)
        """
        # Start with all jobs
        jobs_list = list(self.jobs.values())

        # Filter by status if specified
        if status:
            jobs_list = [j for j in jobs_list if j.get("status") == status]

        # Sort by submission time (newest first)
        jobs_list.sort(
            key=lambda j: j.get("submitted_at", ""),
            reverse=True
        )

        # Limit results if specified
        if limit:
            jobs_list = jobs_list[:limit]

        return jobs_list

    def get_stats(self) -> Dict[str, Any]:
        """
        Get overall statistics about jobs.

        Returns:
            Dictionary with counts and totals
        """
        total = len(self.jobs)

        # Count by status
        status_counts = {}
        for job in self.jobs.values():
            status = job.get("status", "unknown")
            status_counts[status] = status_counts.get(status, 0) + 1

        # Calculate total cost (completed jobs only)
        total_cost = sum(
            job.get("actual_cost", 0) or 0
            for job in self.jobs.values()
            if job.get("status") == "complete"
        )

        return {
            "total_jobs": total,
            "by_status": status_counts,
            "total_cost": round(total_cost, 2),
            "complete_count": status_counts.get("complete", 0),
            "pending_count": status_counts.get("queued", 0) + status_counts.get("processing", 0)
        }


# ===== GLOBAL SINGLETON =====
# Single instance shared across the application
# This ensures all parts of the app see the same jobs data
_job_storage = None


def get_job_storage() -> JobStorageService:
    """
    Get the singleton job storage instance.

    Returns:
        JobStorageService instance
    """
    global _job_storage
    if _job_storage is None:
        _job_storage = JobStorageService()
    return _job_storage
