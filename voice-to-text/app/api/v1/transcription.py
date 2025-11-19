"""
Transcription API endpoints.

Handles transcription submission and audio metadata detection.
"""

import logging
import tempfile
import os
from pathlib import Path
from fastapi import APIRouter, Depends, File, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse
from typing import Optional

from app.models.responses import TranscriptionResponse, AudioMetadataResponse
from app.services.orchestrator import TranscriptionOrchestrator
from app.services.audio_metadata import AudioMetadataService
from app.services.transcribe_v2 import is_metadata_ready
from app.services.request_queue import get_request_queue
from datetime import datetime
import uuid

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
    # Stream file to temp file instead of loading into memory
    # This allows handling large files without memory issues
    # Capture filename early to avoid scoping issues in exception handlers
    filename = getattr(file, 'filename', None) if file else None
    temp_path = None
    
    try:
        # Validate file object
        if not file:
            raise HTTPException(status_code=400, detail="File is required")
        
        if not filename:
            raise HTTPException(status_code=400, detail="Filename is required")
        
        # Get file extension for temp file
        file_extension = Path(filename).suffix or '.tmp'
        
        # Stream upload to temp file (chunk by chunk, ~8KB buffer)
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
                temp_path = temp_file.name
                chunk_size = 8192  # 8KB chunks
                total_size = 0
                
                # Stream file to disk
                while True:
                    try:
                        chunk = await file.read(chunk_size)
                        if not chunk:
                            break
                        temp_file.write(chunk)
                        total_size += len(chunk)
                    except Exception as e:
                        logger.error(f"Error reading/writing file chunk: {e}", exc_info=True)
                        raise HTTPException(
                            status_code=500,
                            detail=f"Error processing file upload: {str(e)}"
                        )
        except OSError as e:
            logger.error(f"Error creating/writing temp file: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Error writing file to disk: {str(e)}"
            )
        
        # Verify temp file was created and get size
        if not os.path.exists(temp_path):
            logger.error(f"Temp file was not created: {temp_path}")
            raise HTTPException(
                status_code=500,
                detail="Failed to create temporary file"
            )
        
        file_size = os.path.getsize(temp_path)
        logger.info(f"Streamed file to temp: {temp_path} ({file_size} bytes, filename={filename})")
        
        # Check if metadata is ready
        if not is_metadata_ready():
            # Queue the request until metadata discovery completes
            # Create job record immediately (so it appears on jobs page)
            job_storage = get_job_storage()
            job_id = f"job-{uuid.uuid4()}"
            request_id = str(uuid.uuid4())
            
            # Create job record with queued status
            job_record = job_storage.create_job(
                job_id=job_id,
                filename=filename,
                model=model or "default",
                tier=None,  # Will be determined when processed
                duration_minutes=0.0,  # Will be calculated when processed
                estimated_cost=0.0,  # Will be calculated when processed
                gcs_uri=None  # Will be set when uploaded
            )
            
            # Update job record with queue reference
            job_storage.update_job(job_id, {
                "queue_request_id": request_id,
                "status": "queued"
            })
            
            # Add to queue
            queue_service = get_request_queue()
            queued = await queue_service.enqueue(
                file_path=temp_path,
                filename=filename,
                model=model,
                request_id=request_id,
                job_id=job_id
            )
            
            if not queued:
                # Queue is full - delete job record and clean up
                try:
                    job_storage.delete_job(job_id)
                except Exception:
                    pass
                if temp_path and os.path.exists(temp_path):
                    try:
                        os.unlink(temp_path)
                    except Exception:
                        pass
                raise HTTPException(
                    status_code=503,
                    detail="System is initializing and queue is full. Please try again in a moment."
                )
            
            # Don't delete temp file - it will be cleaned up by queue processor
            # Return queued response with all required fields
            return TranscriptionResponse(
                job_id=job_id,
                status="queued",
                filename=filename,
                model=model or "default",
                duration_minutes=0.0,  # Will be calculated when processed
                estimated_cost=0.0,
                submitted_at=datetime.now(),
                check_status_url=f"/api/v1/jobs/{job_id}/status",
                message="System is initializing. Your job will start automatically once the system is ready."
            )
        
        # Metadata is ready - process immediately
        # Submit transcription using orchestrator (from file path, not memory)
        result = orchestrator.submit_transcription_from_file(
            file_path=temp_path,
            filename=filename,
            model=model
        )
        
        return TranscriptionResponse(**result)
        
    except HTTPException:
        # Re-raise HTTP exceptions (already properly formatted)
        raise
    except ValueError as e:
        # Validation errors from orchestrator
        logger.error(f"Validation error: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Use captured filename - no need to access file in exception handler
        filename_str = filename or 'unknown'
        logger.error(
            f"Error submitting transcription job: {e} "
            f"(filename={filename_str}, temp_path={temp_path})",
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=f"Error submitting transcription: {str(e)}"
        )
    finally:
        # Clean up temp file ONLY if not queued
        # Queued requests need the file to persist until processed
        if temp_path and os.path.exists(temp_path):
            # Check if this request was queued (by checking if it's still in queue)
            # If metadata is ready, we processed it, so clean up
            # If metadata not ready, it was queued, so keep it
            if is_metadata_ready():
                try:
                    os.unlink(temp_path)
                    logger.debug(f"Cleaned up temp file: {temp_path}")
                except Exception as e:
                    logger.warning(f"Failed to clean up temp file {temp_path}: {e}")
            # If not ready, file is queued - queue processor will clean it up


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
    # Capture filename early to avoid scoping issues in exception handlers
    filename = getattr(file, 'filename', None) if file else None
    
    try:
        # Read file bytes
        audio_bytes = await file.read()
        
        # Extract metadata
        metadata = metadata_service.analyze_bytes(audio_bytes, filename)
        
        # Add duration in minutes for convenience
        metadata["duration_minutes"] = metadata["duration"] / 60.0
        metadata["filename"] = filename
        
        logger.info(
            f"Detected duration for {filename}: "
            f"{metadata['duration_minutes']:.1f} min, "
            f"{metadata['format']}, {metadata['codec']}"
        )
        
        return AudioMetadataResponse(**metadata)
        
    except Exception as e:
        # Use captured filename - no need to access file in exception handler
        filename_str = filename or 'unknown'
        logger.error(f"Error detecting duration for {filename_str}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error detecting duration: {str(e)}"
        )

