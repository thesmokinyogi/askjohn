"""
Unified transcript metadata models for cross-service consumption.

This module defines standardized data structures for transcript metadata
that can be consumed by Content Cockpit, Contextual Librarian, and other services.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class WordTimestamp(BaseModel):
    """Word-level timestamp with confidence."""
    
    word: str = Field(..., description="Transcribed word")
    start_time: float = Field(..., ge=0, description="Start time in seconds")
    end_time: float = Field(..., ge=0, description="End time in seconds")
    confidence: Optional[float] = Field(None, ge=0, le=1, description="Confidence score (0-1)")


class TranscriptMetadata(BaseModel):
    """Unified metadata schema for all transcript contexts.
    
    This schema is used consistently across:
    - Transcript files (data/transcripts/*.json) - Core metadata stored here
    - Library entries (library.json) - Copy of transcript metadata
    - API responses - Standardized format
    - Cross-service integration (Content Cockpit, Contextual Librarian)
    
    Note: Job records (jobs.json) don't store metadata - they reference transcript files.
    Metadata is stored in transcript files and copied to library entries.
    
    Current structure (observed from actual data):
    - total_words: int
    - model: str
    - language: str
    - api_version: str
    
    Extended structure (for future use):
    - All current fields (required for backward compatibility)
    - New optional fields (tags, project_id, etc.) for schema communication
    """
    
    # Core Fields (Current Structure - Required for Backward Compatibility)
    total_words: int = Field(..., ge=0, description="Total number of words (current field name)")
    model: str = Field(..., description="Model used for transcription (e.g., 'chirp_batch')")
    language: str = Field(..., description="Language code (e.g., 'en-US')")
    api_version: str = Field(..., description="API version (e.g., 'v2')")
    
    # Extended Fields (Optional - For Future Use)
    job_id: Optional[str] = Field(None, description="Google operation ID")
    billed_duration_seconds: Optional[float] = Field(None, ge=0, description="Actual billed duration in seconds")
    billed_duration_minutes: Optional[float] = Field(None, ge=0, description="Actual billed duration in minutes")
    channel: Optional[str] = Field(None, description="Channel selection for stereo files: 'auto', 'left', 'right', or None (all channels)")
    
    # Extensibility - Test fields for schema communication
    tags: List[str] = Field(default_factory=list, description="Tags for categorization (e.g., ['yoga', 'meditation'])")
    project_id: Optional[str] = Field(None, description="Project identifier for grouping transcripts")
    content_type: Optional[str] = Field(None, description="Type of content (e.g., 'class', 'voice_note', 'interview')")
    speaker_id: Optional[str] = Field(None, description="Speaker identifier (for multi-speaker content)")
    
    # Custom metadata for future extensions
    custom_metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional custom metadata")
    
    # Computed/Aggregated Fields (Not stored, computed when needed)
    @property
    def word_count(self) -> int:
        """Alias for total_words (for consistency with TranscriptOutput)."""
        return self.total_words
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class TranscriptContent(BaseModel):
    """Transcript content (text and word timestamps)."""
    
    transcript: str = Field(..., description="Full transcript text")
    words: List[WordTimestamp] = Field(default_factory=list, description="Word-level timestamps")


class TranscriptOutput(BaseModel):
    """Standardized transcript output for cross-service consumption.
    
    This is the canonical format for passing transcripts to:
    - Content Cockpit (media processing pipeline)
    - Contextual Librarian (semantic search and analysis)
    - Other downstream services
    
    This model extends TranscriptMetadata with additional context fields
    that are available at the job/library level but not in transcript files.
    """
    
    # Identity
    transcript_id: str = Field(..., description="Unique transcript identifier (library_id)")
    source_filename: str = Field(..., description="Original audio filename")
    source_uri: Optional[str] = Field(None, description="GCS URI of source file")
    
    # Content
    content: TranscriptContent = Field(..., description="Transcript text and word timestamps")
    
    # Metadata (unified schema - extends TranscriptMetadata with job-level fields)
    metadata: TranscriptMetadata = Field(..., description="Unified metadata")
    
    # Job-Level Fields (Not in transcript file, but available from job record)
    confidence: Optional[float] = Field(None, ge=0, le=1, description="Average confidence score (0-1)")
    duration_seconds: float = Field(..., ge=0, description="Audio duration in seconds")
    cost_usd: float = Field(..., ge=0, description="Cost in USD")
    processing_time_seconds: Optional[float] = Field(None, ge=0, description="Processing time in seconds")
    
    # Timestamps
    created_at: datetime = Field(..., description="When transcription was created")
    completed_at: Optional[datetime] = Field(None, description="When transcription completed")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# ============================================================================
# Conversion Functions
# ============================================================================

def dict_to_transcript_metadata(data: Dict[str, Any]) -> TranscriptMetadata:
    """
    Convert current dict-based metadata to TranscriptMetadata model.
    
    Handles backward compatibility with existing structure:
    - total_words (current field name)
    - model, language, api_version (required)
    - Optional extended fields (tags, project_id, etc.)
    
    Args:
        data: Dict with metadata (from transcript file or library entry)
        
    Returns:
        TranscriptMetadata model instance
        
    Raises:
        ValidationError: If required fields are missing or invalid
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # Extract core required fields with defaults
        total_words = data.get("total_words", 0)
        model = data.get("model", "unknown")
        language = data.get("language", "en-US")
        api_version = data.get("api_version", "v2")
        
        # Filter out non-metadata fields (e.g., "words" is transcript content, not metadata)
        # This prevents ValidationError if words accidentally included in metadata dict
        if "words" in data:
            logger.warning(
                f"Found 'words' field in metadata dict - filtering out. "
                f"'words' is transcript content, not metadata. "
                f"Data keys: {list(data.keys())}"
            )
        filtered_data = {k: v for k, v in data.items() if k not in ["words"]}
        
        # Extract optional extended fields
        return TranscriptMetadata(
            total_words=total_words,
            model=model,
            language=language,
            api_version=api_version,
            job_id=filtered_data.get("job_id"),
            billed_duration_seconds=filtered_data.get("billed_duration_seconds"),
            billed_duration_minutes=filtered_data.get("billed_duration_minutes"),
            channel=filtered_data.get("channel"),
            tags=filtered_data.get("tags", []),
            project_id=filtered_data.get("project_id"),
            content_type=filtered_data.get("content_type"),
            speaker_id=filtered_data.get("speaker_id"),
            custom_metadata=filtered_data.get("custom_metadata", {})
        )
    except Exception as e:
        logger.warning(f"Error converting dict to TranscriptMetadata: {e}, data: {data}")
        # Return minimal valid metadata as fallback
        return TranscriptMetadata(
            total_words=data.get("total_words", 0),
            model=data.get("model", "unknown"),
            language=data.get("language", "en-US"),
            api_version=data.get("api_version", "v2")
        )


def transcript_metadata_to_dict(metadata: TranscriptMetadata) -> Dict[str, Any]:
    """
    Convert TranscriptMetadata model to dict for JSON storage.
    
    Maintains backward compatibility with current structure.
    
    Args:
        metadata: TranscriptMetadata model instance
        
    Returns:
        Dict compatible with current storage format
    """
    result = {
        "total_words": metadata.total_words,
        "model": metadata.model,
        "language": metadata.language,
        "api_version": metadata.api_version
    }
    
    # Add optional fields if present
    if metadata.job_id:
        result["job_id"] = metadata.job_id
    if metadata.billed_duration_seconds is not None:
        result["billed_duration_seconds"] = metadata.billed_duration_seconds
    if metadata.billed_duration_minutes is not None:
        result["billed_duration_minutes"] = metadata.billed_duration_minutes
    if metadata.channel:
        result["channel"] = metadata.channel
    if metadata.tags:
        result["tags"] = metadata.tags
    if metadata.project_id:
        result["project_id"] = metadata.project_id
    if metadata.content_type:
        result["content_type"] = metadata.content_type
    if metadata.speaker_id:
        result["speaker_id"] = metadata.speaker_id
    if metadata.custom_metadata:
        result["custom_metadata"] = metadata.custom_metadata
    
    return result

