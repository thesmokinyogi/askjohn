"""
Pydantic models for API request/response validation.

This module provides type-safe models for all API endpoints,
ensuring consistent data structures and automatic validation.
"""

from app.models.requests import (
    TranscribeRequest,
    EstimateCostRequest,
    EstimateProcessingTimeRequest,
)
from app.models.responses import (
    TranscriptionResponse,
    JobStatusResponse,
    JobListResponse,
    JobStatsResponse,
    LibraryListResponse,
    LibraryEntryResponse,
    BudgetResponse,
    PricingResponse,
    ProcessingTimeEstimateResponse,
    CostEstimateResponse,
    AudioMetadataResponse,
    ErrorResponse,
    SuccessResponse,
)
from app.models.job import JobStatus, JobModel

__all__ = [
    # Requests
    "TranscribeRequest",
    "EstimateCostRequest",
    "EstimateProcessingTimeRequest",
    # Responses
    "TranscriptionResponse",
    "JobStatusResponse",
    "JobListResponse",
    "JobStatsResponse",
    "LibraryListResponse",
    "LibraryEntryResponse",
    "BudgetResponse",
    "PricingResponse",
    "ProcessingTimeEstimateResponse",
    "CostEstimateResponse",
    "AudioMetadataResponse",
    "ErrorResponse",
    "SuccessResponse",
    # Domain models
    "JobStatus",
    "JobModel",
]

