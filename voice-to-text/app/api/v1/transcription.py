"""
Transcription API endpoints.

Handles transcription submission and audio metadata detection.
"""

import logging
from fastapi import APIRouter, Depends, File, UploadFile, Form
from fastapi.responses import JSONResponse
from typing import Optional

from app.models.responses import TranscriptionResponse, AudioMetadataResponse
from app.services.orchestrator import TranscriptionOrchestrator
from app.services.audio_metadata import AudioMetadataService

logger = logging.getLogger(__name__)

# Create router for this module
router = APIRouter()


from app.dependencies import get_orchestrator


def get_audio_metadata_service() -> AudioMetadataService:
    """Dependency: Get audio metadata service."""
    from app.services.audio_metadata import get_audio_metadata_service
    return get_audio_metadata_service()


@router.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_audio(
    file: UploadFile = File(...),
    model: Optional[str] = Form(None),
    orchestrator: TranscriptionOrchestrator = Depends(get_orchestrator)
):
    """
    Submit a transcription job and return immediately with job ID.
    
    NEW JOB-BASED ARCHITECTURE:
    - Uploads audio to Cloud Storage
    - Submits transcription job to Google
    - Returns IMMEDIATELY with job ID (doesn't wait for completion)
    - User checks status later via /api/v1/jobs/{job_id}/status
    
    This allows batch processing (up to 24 hours) without timeouts.
    
    Args:
        file: Audio file to transcribe
        model: Model to use (e.g., 'chirp_batch', 'long_standard')
        
    Returns:
        TranscriptionResponse with job_id, status, and estimated cost
    """
    try:
        # Read file bytes
        audio_bytes = await file.read()
        
        # Submit transcription using orchestrator
        result = orchestrator.submit_transcription(
            filename=file.filename,
            audio_bytes=audio_bytes,
            model=model
        )
        
        return TranscriptionResponse(**result)
        
    except ValueError as e:
        # Validation errors from orchestrator
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error submitting transcription job: {e}")
        from fastapi import HTTPException
        raise HTTPException(
            status_code=500,
            detail=f"Error submitting transcription: {str(e)}"
        )


@router.post("/detect-duration", response_model=AudioMetadataResponse)
async def detect_duration(
    file: UploadFile = File(...),
    metadata_service: AudioMetadataService = Depends(get_audio_metadata_service)
):
    """
    Extract audio metadata (duration, format, codec) from uploaded file.
    
    This is server-side metadata extraction that works regardless of how
    files arrive (UI, API, batch, Content Cockpit).
    
    Args:
        file: Uploaded audio file
        
    Returns:
        AudioMetadataResponse with duration, format, codec, sample_rate, etc.
    """
    try:
        # Read file bytes
        audio_bytes = await file.read()
        
        # Extract metadata
        metadata = metadata_service.analyze_bytes(audio_bytes, file.filename)
        
        # Add duration in minutes for convenience
        metadata["duration_minutes"] = metadata["duration"] / 60.0
        metadata["filename"] = file.filename
        
        logger.info(
            f"Detected duration for {file.filename}: "
            f"{metadata['duration_minutes']:.1f} min, "
            f"{metadata['format']}, {metadata['codec']}"
        )
        
        return AudioMetadataResponse(**metadata)
        
    except Exception as e:
        logger.error(f"Error detecting duration for {file.filename}: {e}")
        from fastapi import HTTPException
        raise HTTPException(
            status_code=500,
            detail=f"Error detecting duration: {str(e)}"
        )

