"""
Job-related API endpoints.

Handles job listing, status checking, and deletion.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Path
from fastapi.responses import JSONResponse
from typing import Optional

from app.models.responses import JobStatusResponse, JobListResponse, SuccessResponse
from app.services.jobs import JobStorageService
from app.services.transcribe_v2 import GoogleSpeechV2Service, get_transcription_service_v2
from app.services.orchestrator import TranscriptionOrchestrator
from app.dependencies import get_orchestrator

logger = logging.getLogger(__name__)

# Create router for this module
router = APIRouter()


def get_job_storage() -> JobStorageService:
    """Dependency: Get job storage service."""
    from app.services.jobs import get_job_storage
    return get_job_storage()


def _get_transcription_service_for_job(
    job_id: str,
    job_storage: JobStorageService
) -> GoogleSpeechV2Service:
    """
    Helper function to get transcription service for a specific job.
    
    We need to create a service with the correct model for the job.
    This is a workaround until we refactor service initialization.
    """
    # Get job to determine model
    job = job_storage.get_job(job_id, include_transcript=False)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    
    # Map UI model to API model
    model_mapping = {
        'chirp_batch': 'chirp',
        'chirp_standard': 'chirp',
        'long_batch': 'long',
        'long_standard': 'long',
        'short_batch': 'short',
        'short_standard': 'short',
        'chirp': 'chirp',
        'long': 'long',
        'short': 'short'
    }
    
    ui_model = job.get("model", "long")
    api_model = model_mapping.get(ui_model, "long")
    
    # Get project and location from environment (temporary - should be in config)
    import os
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    # For now, use default location - this should come from config
    location = "us-central1"  # TODO: Get from config
    
    return get_transcription_service_v2(
        project_id=project_id,
        model=api_model,
        location=location
    )


@router.get("/jobs", response_model=JobListResponse)
async def list_jobs(
    status: Optional[str] = None,
    limit: int = 100,
    job_storage: JobStorageService = Depends(get_job_storage)
):
    """
    List all transcription jobs.
    
    This endpoint powers the Jobs page - shows all transcriptions the user has run.
    Jobs are sorted by submission time (newest first).
    
    Args:
        status: Filter by status (queued, processing, complete, failed)
        limit: Maximum number of jobs to return (default 100)
        
    Returns:
        JobListResponse with jobs list and statistics
    """
    try:
        # Get filtered and sorted list of jobs
        jobs_list = job_storage.list_jobs(
            status=status,
            limit=limit,
            include_transcripts=True
        )
        
        # Get overall statistics
        stats = job_storage.get_stats()
        
        return JobListResponse(
            jobs=jobs_list,
            stats=stats,
            count=len(jobs_list)
        )
        
    except Exception as e:
        logger.error(f"Error listing jobs: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error listing jobs: {str(e)}"
        )


@router.get("/jobs/{job_id:path}/status", response_model=JobStatusResponse)
async def check_job_status(
    job_id: str = Path(..., description="Job identifier"),
    job_storage: JobStorageService = Depends(get_job_storage),
    orchestrator: TranscriptionOrchestrator = Depends(get_orchestrator)
):
    """
    Check the status of a transcription job.
    
    This is the polling endpoint - clients call this repeatedly to check if their
    transcription is done yet. It's designed to be fast and non-blocking.
    
    Args:
        job_id: Google operation name (returned from /transcribe)
        
    Returns:
        JobStatusResponse with current job status and results (if complete)
    """
    try:
        # Get transcription service for this job
        transcription_service = _get_transcription_service_for_job(job_id, job_storage)
        
        # Use orchestrator to check status
        result = orchestrator.check_job_status(
            job_id=job_id,
            transcription_service=transcription_service
        )
        
        return JobStatusResponse(**result)
        
    except ValueError as e:
        # Job not found or other validation error
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error checking job status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error checking job status: {str(e)}"
        )


@router.post("/jobs/{job_id:path}/reparse", response_model=JobStatusResponse)
async def reparse_job(
    job_id: str = Path(..., description="Job identifier"),
    job_storage: JobStorageService = Depends(get_job_storage),
    orchestrator: TranscriptionOrchestrator = Depends(get_orchestrator)
):
    """
    Force re-parse a completed job's transcript.
    
    Useful when parsing logic has been fixed and you want to re-extract
    the transcript from an existing completed job.
    
    Args:
        job_id: The Google operation name (full path with slashes)
        
    Returns:
        JobStatusResponse with re-parsed transcript
    """
    try:
        # Get job to verify it exists and is complete
        job = job_storage.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
        
        # Allow re-parsing of complete or failed jobs (failed might be due to parsing errors)
        if job["status"] not in ["complete", "failed"]:
            raise HTTPException(
                status_code=400, 
                detail=f"Job status is '{job['status']}'. Only completed or failed jobs can be re-parsed."
            )
        
        # Temporarily mark as processing to bypass cache
        original_status = job["status"]
        job_storage.update_job(job_id, {"status": "processing"})
        
        try:
            # Get transcription service for this job
            transcription_service = _get_transcription_service_for_job(job_id, job_storage)
            
            # Re-check job status (this will re-download and parse with new code)
            result = orchestrator.check_job_status(
                job_id=job_id,
                transcription_service=transcription_service
            )
            
            return JobStatusResponse(**result)
            
        except Exception as e:
            # Restore original status on error
            job_storage.update_job(job_id, {"status": original_status})
            raise
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error re-parsing job {job_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to re-parse job: {str(e)}")


@router.delete("/jobs/{job_id:path}", response_model=SuccessResponse)
async def delete_job(
    job_id: str = Path(..., description="Job identifier"),
    job_storage: JobStorageService = Depends(get_job_storage)
):
    """
    Delete a transcription job and its transcript file.
    
    Args:
        job_id: The Google operation name (full path with slashes)
        
    Returns:
        SuccessResponse confirming deletion
    """
    try:
        job_storage.delete_job(job_id)
        
        return SuccessResponse(
            success=True,
            message="Job deleted successfully",
            job_id=job_id
        )
        
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    except Exception as e:
        logger.error(f"Error deleting job {job_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete job: {str(e)}")

