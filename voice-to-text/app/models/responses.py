"""
Response models for API endpoints.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

from app.models.job import JobStatus, JobModel


# ============================================================================
# Transcription Responses
# ============================================================================

class TranscriptionResponse(BaseModel):
    """Response model for transcription submission."""
    
    job_id: str = Field(..., description="Unique job identifier")
    status: JobStatus = Field(..., description="Job status")
    filename: str = Field(..., description="Original audio filename")
    model: str = Field(..., description="Model used for transcription")
    duration_minutes: float = Field(..., ge=0, description="Audio duration in minutes")
    estimated_cost: float = Field(..., ge=0, description="Estimated cost in USD")
    submitted_at: datetime = Field(..., description="When job was submitted")
    check_status_url: str = Field(..., description="URL to check job status")
    
    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class JobStatusResponse(BaseModel):
    """Response model for job status check."""
    
    job_id: str = Field(..., description="Unique job identifier")
    status: JobStatus = Field(..., description="Current job status")
    filename: str = Field(..., description="Original audio filename")
    model: str = Field(..., description="Model used for transcription")
    submitted_at: datetime = Field(..., description="When job was submitted")
    
    # Optional fields based on status
    completed_at: Optional[datetime] = Field(None, description="When job completed")
    transcript: Optional[str] = Field(None, description="Transcription text (if complete)")
    confidence: Optional[float] = Field(None, ge=0, le=1, description="Confidence score (if complete)")
    actual_cost: Optional[float] = Field(None, ge=0, description="Actual cost in USD (if complete)")
    error: Optional[str] = Field(None, description="Error message (if failed)")
    message: Optional[str] = Field(None, description="Status message (if processing)")
    
    # Library integration
    in_library: bool = Field(False, description="Whether job is in library")
    library_id: Optional[str] = Field(None, description="Library entry ID if in library")
    
    # Metadata
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    
    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# ============================================================================
# Job List Responses
# ============================================================================

class JobStatsResponse(BaseModel):
    """Statistics for job list."""
    
    total_jobs: int = Field(..., ge=0, description="Total number of jobs")
    by_status: Dict[str, int] = Field(..., description="Job count by status")
    total_cost: float = Field(..., ge=0, description="Total cost across all jobs")


class JobListResponse(BaseModel):
    """Response model for job list."""
    
    jobs: List[Dict[str, Any]] = Field(..., description="List of job records")
    stats: JobStatsResponse = Field(..., description="Job statistics")
    count: int = Field(..., ge=0, description="Number of jobs returned")


# ============================================================================
# Library Responses
# ============================================================================

class LibraryEntryResponse(BaseModel):
    """Response model for a single library entry."""
    
    library_id: str = Field(..., description="Unique library entry identifier")
    filename: str = Field(..., description="Original audio filename")
    transcript_file: str = Field(..., description="Transcript file path")
    duration_minutes: float = Field(..., ge=0, description="Audio duration in minutes")
    model: str = Field(..., description="Model used for transcription")
    cost: float = Field(..., ge=0, description="Cost in USD")
    file_size_bytes: int = Field(..., ge=0, description="Transcript file size in bytes")
    created_at: datetime = Field(..., description="When entry was created")
    
    # Optional fields
    transcript: Optional[str] = Field(None, description="Transcription text (if loaded)")
    words: Optional[List[Dict[str, Any]]] = Field(None, description="Word-level timestamps (if loaded)")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class LibraryListResponse(BaseModel):
    """Response model for library list."""
    
    entries: List[Dict[str, Any]] = Field(..., description="List of library entries")
    total: int = Field(..., ge=0, description="Total number of entries")


# ============================================================================
# Budget & Pricing Responses
# ============================================================================

class BudgetResponse(BaseModel):
    """Response model for budget summary."""
    
    total_spent: float = Field(..., ge=0, description="Total spent this month")
    monthly_budget: float = Field(..., ge=0, description="Monthly budget limit")
    providers: Optional[Dict[str, Any]] = Field(None, description="Per-provider budget details")
    provider: Optional[Dict[str, Any]] = Field(None, description="Single provider budget details (if provider specified)")


class PricingResponse(BaseModel):
    """Response model for pricing information."""
    
    # This is a flexible structure that varies by provider
    # Using Dict to accommodate different provider structures
    pricing: Dict[str, Any] = Field(..., description="Pricing configuration")


# ============================================================================
# Processing Time & Cost Estimation Responses
# ============================================================================

class ProcessingTimeEstimateResponse(BaseModel):
    """Response model for processing time estimate."""
    
    estimated_seconds: float = Field(..., gt=0, description="Estimated processing time in seconds")
    confidence: str = Field(..., description="Confidence level (high/medium/low/fallback)")
    base_time_seconds: float = Field(..., ge=0, description="Base processing time (y-intercept)")
    rate_per_minute_seconds: float = Field(..., ge=0, description="Time per minute of audio (slope)")
    sample_count: int = Field(..., ge=0, description="Number of samples used for estimate")
    r_squared: Optional[float] = Field(None, ge=0, le=1, description="R² value for regression quality")


class CostEstimateResponse(BaseModel):
    """Response model for cost estimate."""
    
    total_cost: float = Field(..., ge=0, description="Total estimated cost in USD")
    cost_per_minute: float = Field(..., ge=0, description="Cost per minute for this model")
    billable_minutes: float = Field(..., ge=0, description="Billable minutes (after free tier)")
    free_minutes_used: float = Field(..., ge=0, description="Free tier minutes used")
    free_tier_remaining: float = Field(..., ge=0, description="Free tier minutes remaining")


# ============================================================================
# Audio Metadata Response
# ============================================================================

class AudioMetadataResponse(BaseModel):
    """Response model for audio metadata extraction."""
    
    duration: float = Field(..., gt=0, description="Duration in seconds")
    duration_minutes: float = Field(..., gt=0, description="Duration in minutes")
    format: str = Field(..., description="Audio format (e.g., 'mp3', 'm4a')")
    codec: str = Field(..., description="Audio codec")
    sample_rate: int = Field(..., gt=0, description="Sample rate in Hz")
    channels: int = Field(..., gt=0, description="Number of audio channels")
    bit_rate: Optional[str] = Field(None, description="Bit rate")
    file_size: int = Field(..., ge=0, description="File size in bytes")
    filename: str = Field(..., description="Original filename")


# ============================================================================
# Common Response Models
# ============================================================================

class ErrorResponse(BaseModel):
    """Standardized error response model."""
    
    error: Dict[str, Any] = Field(..., description="Error details")
    
    class Config:
        json_schema_extra = {
            "example": {
                "error": {
                    "code": "INVALID_REQUEST",
                    "message": "Invalid file type. Allowed: mp3, wav, m4a",
                    "details": {
                        "field": "file",
                        "received": "pdf"
                    },
                    "request_id": "req_123456"
                }
            }
        }


class SuccessResponse(BaseModel):
    """Standardized success response model."""
    
    success: bool = Field(True, description="Operation success flag")
    message: str = Field(..., description="Success message")
    
    # Optional fields for specific operations
    job_id: Optional[str] = Field(None, description="Job ID (for job operations)")
    library_id: Optional[str] = Field(None, description="Library ID (for library operations)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Job deleted successfully",
                "job_id": "projects/.../operations/123"
            }
        }

