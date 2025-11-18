"""
Storage Adapter Interface

Defines the interface for storage operations, allowing future migration from
JSON files to database (SQLite, Postgres, etc.) without changing business logic.

Current implementation: JSON file storage
Future implementation: Database storage
"""

from typing import Protocol, Dict, Any, Optional, List
from pathlib import Path


class JobStorageAdapter(Protocol):
    """Interface for job storage operations."""
    
    def create_job(
        self,
        job_id: str,
        filename: str,
        model: str,
        tier: Optional[str] = None,
        duration_minutes: float = 0,
        estimated_cost: float = 0,
        gcs_uri: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new job record."""
        ...
    
    def get_job(self, job_id: str, include_transcript: bool = False) -> Optional[Dict[str, Any]]:
        """Get a job record by ID."""
        ...
    
    def update_job(self, job_id: str, updates: Dict[str, Any]) -> None:
        """Update a job record."""
        ...
    
    def mark_complete(
        self,
        job_id: str,
        transcript: str,
        confidence: Optional[float],
        actual_cost: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Mark a job as complete with results."""
        ...
    
    def mark_failed(self, job_id: str, error: str) -> None:
        """Mark a job as failed."""
        ...
    
    def delete_job(self, job_id: str) -> None:
        """Delete a job and its transcript file."""
        ...
    
    def list_jobs(
        self,
        status: Optional[str] = None,
        limit: int = 100,
        include_transcripts: bool = False
    ) -> List[Dict[str, Any]]:
        """List jobs with optional filtering."""
        ...
    
    def get_stats(self) -> Dict[str, Any]:
        """Get job statistics."""
        ...


class LibraryStorageAdapter(Protocol):
    """Interface for library storage operations."""
    
    def add_entry(
        self,
        filename: str,
        transcript_file: str,
        duration_minutes: float,
        model: str,
        cost: float,
        file_size_bytes: int,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Add a new library entry. Returns library_id."""
        ...
    
    def get_entry(self, library_id: str) -> Optional[Dict[str, Any]]:
        """Get a library entry by ID."""
        ...
    
    def get_all_entries(self) -> List[Dict[str, Any]]:
        """Get all library entries."""
        ...
    
    def delete_entry(self, library_id: str) -> bool:
        """Delete a library entry. Returns True if deleted, False if not found."""
        ...
    
    def validate_library(self) -> Dict[str, Any]:
        """Validate library integrity."""
        ...


class TranscriptStorageAdapter(Protocol):
    """Interface for transcript file storage operations."""
    
    @property
    def transcripts_dir(self) -> Path:
        """Directory where transcript files are stored."""
        ...
    
    def save_transcript(
        self,
        job_id: str,
        transcript: str,
        words: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Save transcript to file. Returns filename."""
        ...
    
    def load_transcript(self, transcript_file: str) -> Dict[str, Any]:
        """Load transcript from file."""
        ...
    
    def delete_transcript(self, transcript_file: str) -> None:
        """Delete a transcript file."""
        ...

