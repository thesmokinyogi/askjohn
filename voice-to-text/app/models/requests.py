"""
Request models for API endpoints.
"""

from typing import Optional
from pydantic import BaseModel, Field, validator


class TranscribeRequest(BaseModel):
    """Request model for transcription submission.
    
    Note: File upload is handled separately via UploadFile,
    this model is for the model parameter only.
    """
    
    model: Optional[str] = Field(
        None,
        description="Model to use for transcription (e.g., 'chirp_batch', 'long_standard')"
    )
    
    @validator('model')
    def validate_model(cls, v):
        """Validate model name if provided."""
        if v is None:
            return v
        
        # Valid model names (UI format)
        valid_models = {
            'chirp_batch', 'chirp_standard',
            'long_batch', 'long_standard',
            'short_batch', 'short_standard',
            # Also support direct API names
            'chirp', 'long', 'short'
        }
        
        if v not in valid_models:
            raise ValueError(f"Invalid model: {v}. Valid models: {sorted(valid_models)}")
        
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "model": "long_standard"
            }
        }


class EstimateCostRequest(BaseModel):
    """Request model for cost estimation."""
    
    provider: Optional[str] = Field(None, description="Provider name (e.g., 'google', 'whisper')")
    model: Optional[str] = Field(None, description="Model name (e.g., 'chirp_batch')")
    duration_minutes: float = Field(..., gt=0, description="Audio duration in minutes")
    
    class Config:
        json_schema_extra = {
            "example": {
                "provider": "google",
                "model": "chirp_batch",
                "duration_minutes": 75.0
            }
        }


class EstimateProcessingTimeRequest(BaseModel):
    """Request model for processing time estimation.
    
    Note: This is typically used as query parameters, not a body.
    This model exists for validation and documentation purposes.
    """
    
    model: str = Field(..., description="Model name (e.g., 'chirp_standard')")
    duration_minutes: float = Field(..., gt=0, description="Audio duration in minutes")
    
    class Config:
        json_schema_extra = {
            "example": {
                "model": "chirp_standard",
                "duration_minutes": 5.0
            }
        }

