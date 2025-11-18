"""
Job domain models and enums.
"""

from enum import Enum
from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    """Job status enumeration."""
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETE = "complete"
    FAILED = "failed"


class JobModel(BaseModel):
    """Job domain model."""
    
    job_id: str = Field(..., description="Unique job identifier (Google operation name)")
    filename: str = Field(..., description="Original audio filename")
    model: str = Field(..., description="Model used for transcription")
    tier: Optional[str] = Field(None, description="Recognition tier: 'batch' or 'standard'")
    status: JobStatus = Field(..., description="Current job status")
    submitted_at: datetime = Field(..., description="When job was submitted")
    
    # Optional fields
    duration_minutes: Optional[float] = Field(None, description="Audio duration in minutes")
    estimated_cost: Optional[float] = Field(None, ge=0, description="Estimated cost in USD")
    actual_cost: Optional[float] = Field(None, ge=0, description="Actual cost in USD")
    completed_at: Optional[datetime] = Field(None, description="When job completed")
    processing_started_at: Optional[datetime] = Field(None, description="When processing actually started (excludes queueing)")
    
    # Results (only present when complete)
    transcript: Optional[str] = Field(None, description="Transcription text")
    confidence: Optional[float] = Field(None, ge=0, le=1, description="Confidence score (0-1)")
    error: Optional[str] = Field(None, description="Error message if failed")
    
    # Library integration
    in_library: bool = Field(False, description="Whether job is in library")
    library_id: Optional[str] = Field(None, description="Library entry ID if in library")
    
    # Metadata
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata (words, timestamps, etc.)")
    gcs_uri: Optional[str] = Field(None, description="Google Cloud Storage URI")
    transcript_file: Optional[str] = Field(None, description="Transcript file path")
    
    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

