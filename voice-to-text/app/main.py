"""
Voice-to-Text Web Application

FastAPI app for transcribing audio files using Google Speech-to-Text.
Supports both V1 (synchronous, <60 sec) and V2 (batch, any length).
"""

from fastapi import FastAPI, File, UploadFile, HTTPException, Form, Body
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from typing import Dict, Any
import os
import json
import logging
from datetime import datetime
from dotenv import load_dotenv

# Import services
from app.services.transcribe_v2 import (
    get_transcription_service_v2,
    initialize_metadata_cache,
    get_available_locations,
    get_available_models
)
from app.services.storage import CloudStorageService
from app.services.pricing import get_pricing_service
from app.services.budget import get_budget_service
from app.services.processing_time import get_processing_time_service
from app.services.jobs import get_job_storage
from app.services.audio_metadata import get_audio_metadata_service
from app.services.library import LibraryService

# Import new API structure
from app.api.v1 import api_router
from app.api.v1.errors import register_error_handlers
from app.config import get_config

# Load environment variables from .env file
load_dotenv()

# Get configuration (using new Config class)
config = get_config()

# ===== TEST MODE CONFIGURATION =====
# Using Config class (backward compatible variables below)
# ===================================
# Keep old variables for backward compatibility
TEST_MODE_SKIP_UPLOAD = config.test_mode_skip_upload
TEST_GCS_URI = config.test_gcs_uri
TEST_AUDIO_METADATA = config.test_audio_metadata

# Configure logging
# Set up both console and file logging
import logging.handlers
log_dir = Path(__file__).parent.parent / "logs"
log_dir.mkdir(exist_ok=True)
log_file = log_dir / "server.log"

# Create formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)

# File handler (rotating, max 10MB, keep 5 backups)
file_handler = logging.handlers.RotatingFileHandler(
    log_file,
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5
)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(formatter)

# Configure root logger
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.addHandler(console_handler)
root_logger.addHandler(file_handler)

logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Voice-to-Text Transcription Service",
    description="Upload audio files and get text transcriptions using Google Speech-to-Text V2",
    version="2.0.0"
)

# Mount static files (for serving the HTML UI)
static_path = Path(__file__).parent / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

# Register error handlers (must be before including routers)
register_error_handlers(app)

# Include API v1 router
app.include_router(api_router)

# Get configuration values (using Config class, keeping old variable names for backward compatibility)
STT_PROVIDER = config.stt_provider
MONTHLY_BUDGET = config.monthly_budget
GOOGLE_MODEL = config.google_model
GCS_BUCKET_NAME = config.gcs_bucket_name
GOOGLE_CLOUD_PROJECT = config.google_cloud_project

# Initialize pricing, budget, job storage, library, and processing time services
pricing_service = get_pricing_service()
budget_service = get_budget_service(monthly_budget=MONTHLY_BUDGET)
job_storage = get_job_storage()
library_service = LibraryService()
processing_time_service = get_processing_time_service()

# Initialize services based on provider
if STT_PROVIDER == "google":
    # Validate Google-specific requirements
    if not GCS_BUCKET_NAME:
        raise ValueError("GCS_BUCKET_NAME must be set in .env when using Google provider")
    if not GOOGLE_CLOUD_PROJECT:
        raise ValueError("GOOGLE_CLOUD_PROJECT must be set in .env when using Google provider")

    # Initialize storage service first
    storage_service = CloudStorageService(
        bucket_name=GCS_BUCKET_NAME,
        project_id=GOOGLE_CLOUD_PROJECT
    )

    # Detect optimal Speech V2 location based on bucket location
    # This aligns API region with storage region for optimal latency
    SPEECH_LOCATION = storage_service.detect_speech_location()

    # Initialize transcription service with detected location
    transcription_service = get_transcription_service_v2(
        project_id=GOOGLE_CLOUD_PROJECT,
        model=GOOGLE_MODEL,
        location=SPEECH_LOCATION
    )

    logger.info(f"Initialized Google provider: model={GOOGLE_MODEL}, bucket={GCS_BUCKET_NAME}, location={SPEECH_LOCATION}")

elif STT_PROVIDER == "whisper":
    # Whisper provider (not yet implemented)
    raise NotImplementedError(
        "Whisper provider not yet implemented. "
        "Set STT_PROVIDER=google in .env to use Google Speech-to-Text."
    )

else:
    raise ValueError(
        f"Unknown STT_PROVIDER: {STT_PROVIDER}. "
        f"Supported providers: google, whisper (whisper not yet implemented)"
    )


@app.on_event("startup")
async def startup_event():
    """Verify services on startup."""
    logger.info(f"Starting Voice-to-Text Service (Provider: {STT_PROVIDER})")

    if STT_PROVIDER == "google":
        # Verify bucket access for Google provider
        if not storage_service.verify_bucket_access():
            logger.error(f"Cannot access GCS bucket: {GCS_BUCKET_NAME}")
            logger.error("Please verify bucket exists and credentials are correct")

        # Discover all available Speech V2 metadata from Locations API
        # This is the single source of truth for regions, models, and features
        logger.info("Discovering Speech V2 metadata from Locations API...")

        primary_languages = ['en-US']

        cache_loaded = initialize_metadata_cache(
            project_id=GOOGLE_CLOUD_PROJECT,
            languages=primary_languages
        )

        if cache_loaded:
            logger.info("✓ Metadata discovery complete - using dynamic configuration")

            # Log what we discovered for this location
            available_locs = get_available_locations()
            logger.info(f"  Discovered {len(available_locs)} Speech V2 locations")

            if SPEECH_LOCATION in available_locs:
                logger.info(f"  ✓ Current location '{SPEECH_LOCATION}' is supported")
            else:
                logger.warning(f"  ⚠️  Current location '{SPEECH_LOCATION}' not in discovered locations")
                logger.warning(f"     Available: {sorted(available_locs)}")

            # Log available models for our location
            available_models = get_available_models(SPEECH_LOCATION, 'en-US')
            if available_models:
                logger.info(f"  Models available in {SPEECH_LOCATION}: {sorted(available_models)}")
            else:
                logger.warning(f"  No models found for {SPEECH_LOCATION}/en-US")
        else:
            logger.warning("⚠️  Metadata discovery failed - using hardcoded fallback")


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main UI page."""
    html_file = static_path / "index.html"
    if html_file.exists():
        return html_file.read_text()
    return "<h1>Voice-to-Text API</h1><p>UI not found. Visit /docs for API documentation.</p>"


@app.get("/jobs", response_class=HTMLResponse)
async def jobs_page():
    """Serve the jobs list page."""
    html_file = static_path / "jobs.html"
    if html_file.exists():
        return html_file.read_text()
    return "<h1>Jobs Page Not Found</h1><p><a href='/'>Back to Home</a></p>"


@app.get("/library", response_class=HTMLResponse)
async def library_page():
    """Serve the library page."""
    html_file = static_path / "library.html"
    if html_file.exists():
        return html_file.read_text()
    return "<h1>Library Page Not Found</h1><p><a href='/'>Back to Home</a></p>"


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    health_info = {
        "status": "healthy",
        "service": "voice-to-text",
        "provider": STT_PROVIDER,
    }

    # Add provider-specific info
    if STT_PROVIDER == "google":
        health_info.update({
            "model": GOOGLE_MODEL,
            "bucket": GCS_BUCKET_NAME,
            "location": SPEECH_LOCATION,
            "api": "v2_batch"
        })

    return health_info


@app.post("/transcribe")
async def transcribe_audio(
    file: UploadFile = File(...),
    model: str = Form(None)
):
    """
    Submit a transcription job and return immediately with job ID.

    NEW JOB-BASED ARCHITECTURE:
    - Uploads audio to Cloud Storage
    - Submits transcription job to Google
    - Returns IMMEDIATELY with job ID (doesn't wait for completion)
    - User checks status later via /api/jobs/{job_id}/status

    This allows batch processing (up to 24 hours) without timeouts.

    Args:
        file: Audio file to transcribe
        model: Model to use (e.g., 'chirp_batch', 'long_standard')

    Returns:
        {
            "job_id": "projects/.../operations/123",
            "status": "queued",
            "submitted_at": "2025-11-10T...",
            "estimated_cost": 1.20
        }
    """

    # ===== STEP 1: Validate and prepare file =====

    # Use provided model or fall back to environment variable
    selected_model = model or GOOGLE_MODEL

    # Map UI model names to Google API model names
    # UI: chirp_batch, chirp_standard, long_batch, long_standard
    # API: chirp, long, short
    model_mapping = {
        'chirp_batch': 'chirp',
        'chirp_standard': 'chirp',
        'long_batch': 'long',
        'long_standard': 'long',
        'short_batch': 'short',
        'short_standard': 'short',
        # Also support direct API names
        'chirp': 'chirp',
        'long': 'long',
        'short': 'short'
    }

    google_api_model = model_mapping.get(selected_model, 'long')
    logger.info(f"Model selection: UI={selected_model}, API={google_api_model}")

    # Validate file type
    allowed_extensions = ["mp3", "wav", "m4a", "ogg", "flac", "mp4", "mov"]
    file_extension = file.filename.split(".")[-1].lower() if "." in file.filename else ""

    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(allowed_extensions)}"
        )

    # Read file bytes into memory
    try:
        audio_bytes = await file.read()
    except Exception as e:
        logger.error(f"Error reading file: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error reading file: {str(e)}"
        )

    # Validate file size
    max_size_mb = 500 if STT_PROVIDER == "google" else 10
    if len(audio_bytes) > max_size_mb * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: {max_size_mb}MB"
        )

    logger.info(f"Processing file: {file.filename} ({len(audio_bytes)} bytes)")

    # ===== STEP 2: Upload to Cloud Storage =====

    gcs_uri = None
    try:
        # TEST MODE: Skip upload for faster testing
        if TEST_MODE_SKIP_UPLOAD:
            logger.warning("⚠️  TEST MODE: Skipping upload, using cached file")
            gcs_uri = TEST_GCS_URI
            audio_metadata = TEST_AUDIO_METADATA
        else:
            # Normal mode: Upload to GCS and extract metadata
            logger.info("Uploading to Cloud Storage...")
            gcs_uri, audio_metadata = storage_service.upload_audio(audio_bytes, file.filename)
            logger.info(f"Uploaded to: {gcs_uri}")

        # ===== STEP 3: Calculate estimated cost =====

        # Get duration from metadata
        duration_minutes = audio_metadata.get('duration', 0) / 60.0

        # Get free tier remaining
        free_tier_remaining = budget_service.get_free_tier_remaining(STT_PROVIDER)

        # Estimate cost (before job starts)
        cost_estimate = pricing_service.estimate_cost(
            provider=STT_PROVIDER,
            model=selected_model,
            duration_minutes=duration_minutes,
            free_tier_remaining=free_tier_remaining
        )

        logger.info(
            f"Estimated cost: ${cost_estimate['total_cost']:.2f} "
            f"({cost_estimate['billable_minutes']:.1f} min @ ${cost_estimate['cost_per_minute']}/min)"
        )

        # ===== STEP 4: Submit transcription job (NON-BLOCKING) =====

        # Initialize transcription service with API model name and detected location
        model_transcription_service = get_transcription_service_v2(
            project_id=GOOGLE_CLOUD_PROJECT,
            model=google_api_model,
            location=SPEECH_LOCATION
        )

        # Submit job - this returns IMMEDIATELY (doesn't wait)
        logger.info(f"Submitting transcription job with model: {google_api_model}")
        operation = model_transcription_service.submit_job(
            gcs_uri=gcs_uri,
            audio_metadata=audio_metadata
        )

        # Extract the job ID from the operation
        # This is Google's unique identifier for this operation
        # We'll use it later to check status and get results
        job_id = operation.operation.name
        logger.info(f"Job submitted successfully: {job_id}")

        # ===== STEP 5: Store job record =====

        # Create job record in our storage
        # This lets us track and list jobs later
        job_record = job_storage.create_job(
            job_id=job_id,
            filename=file.filename,
            model=selected_model,
            duration_minutes=duration_minutes,
            estimated_cost=cost_estimate['total_cost'],
            gcs_uri=gcs_uri  # Store for GCS result lookup
        )

        # ===== STEP 6: Return immediately =====

        # We're done! User gets job ID back in < 1 second
        # They can check status later via /api/jobs/{job_id}/status
        return JSONResponse(content={
            "job_id": job_id,
            "status": "queued",
            "filename": file.filename,
            "model": selected_model,
            "duration_minutes": round(duration_minutes, 1),
            "estimated_cost": cost_estimate['total_cost'],
            "submitted_at": job_record["submitted_at"],
            "check_status_url": f"/api/jobs/{job_id}/status"
        })

    except Exception as e:
        logger.error(f"Error submitting transcription job: {e}")

        # Clean up uploaded file on error
        if gcs_uri and not TEST_MODE_SKIP_UPLOAD:
            try:
                storage_service.delete_file(gcs_uri)
            except:
                pass  # Best effort cleanup

        raise HTTPException(
            status_code=500,
            detail=f"Error submitting transcription: {str(e)}"
        )


@app.get("/api/jobs/{job_id:path}/status")
async def check_job_status(job_id: str):
    """
    Check the status of a transcription job.

    This is the polling endpoint - clients call this repeatedly to check if their
    transcription is done yet. It's designed to be fast and non-blocking.

    Args:
        job_id: Google operation name (returned from /transcribe)

    Returns:
        {
            "job_id": "projects/.../operations/123",
            "status": "queued|processing|complete|failed",
            "filename": "audio.mp3",
            "submitted_at": "2025-11-10T...",
            "transcript": "..." (if complete),
            "confidence": 0.95 (if complete),
            "actual_cost": 1.20 (if complete),
            "error": "..." (if failed)
        }
    """
    try:
        # ===== STEP 1: Get job record from our storage =====

        # This gives us metadata we stored when job was submitted
        # (filename, model, estimated cost, etc.)
        # For in-progress jobs, don't load transcript (it doesn't exist yet)
        job_record = job_storage.get_job(job_id, include_transcript=False)

        if not job_record:
            # Job ID not found in our records
            raise HTTPException(
                status_code=404,
                detail=f"Job not found: {job_id}"
            )

        # ===== STEP 2: Check Google's operation status =====

        # If job is already marked complete/failed in our records, return cached result
        # This avoids unnecessary API calls to Google for jobs we've already processed
        if job_record["status"] in ["complete", "failed"]:
            logger.info(f"Returning cached status for job {job_id}: {job_record['status']}")

            # For completed jobs, load the transcript from file
            if job_record["status"] == "complete":
                job_with_transcript = job_storage.get_job(job_id, include_transcript=True)
                return JSONResponse(content={
                    "job_id": job_id,
                    "status": job_with_transcript["status"],
                    "in_library": job_with_transcript.get("in_library", False),
                    "library_id": job_with_transcript.get("library_id"),
                    "filename": job_with_transcript["filename"],
                    "model": job_with_transcript["model"],
                    "submitted_at": job_with_transcript["submitted_at"],
                    "completed_at": job_with_transcript.get("completed_at"),
                    "transcript": job_with_transcript.get("transcript"),  # Loaded from file
                    "confidence": job_with_transcript.get("confidence"),
                    "actual_cost": job_with_transcript.get("actual_cost")
                })

            # For failed jobs, just return error
            return JSONResponse(content={
                "job_id": job_id,
                "status": job_record["status"],
                "filename": job_record["filename"],
                "model": job_record["model"],
                "submitted_at": job_record["submitted_at"],
                "completed_at": job_record.get("completed_at"),
                "error": job_record.get("error")
            })

        # Job is still in progress - check Google for updates
        logger.info(f"Checking Google operation status for job {job_id}")

        # Reconnect to Google's operation and check status
        # This is non-blocking - returns immediately
        # Pass gcs_uri for GCS result lookup
        status_result = transcription_service.check_job_status(
            job_id=job_id,
            gcs_uri=job_record.get("gcs_uri")
        )
        
        # If Google says it's processing and we haven't tracked processing_started_at yet, set it now
        # This handles cases where status check happens after processing has already started
        if status_result.get("status") == "processing" and not job_record.get("processing_started_at"):
            from datetime import datetime
            job_storage.update_job(job_id, {
                "processing_started_at": datetime.now().isoformat()
            })
            logger.info(f"Detected job {job_id} is processing, setting processing_started_at")

        # ===== STEP 3: Update our job record if status changed =====

        if status_result["done"]:
            # Job finished (either successfully or with error)

            if status_result["status"] == "complete":
                # Success! Update job record with results
                logger.info(f"Job {job_id} completed successfully")

                # Calculate actual cost and free minutes from billed duration
                # Use actual billed duration from Google's API response (not estimated)
                metadata = status_result.get("metadata", {})
                billed_duration_minutes = metadata.get("billed_duration_minutes")
                
                # Fall back to estimated duration if Google didn't provide billed duration
                if billed_duration_minutes is None:
                    logger.warning(f"Job {job_id} missing billed_duration_minutes in metadata, using estimated duration")
                    billed_duration_minutes = job_record["duration_minutes"]
                else:
                    logger.info(f"Using actual billed duration from Google: {billed_duration_minutes:.2f} minutes")
                
                # Get current free tier remaining
                from app.services.budget import get_budget_service
                budget_service = get_budget_service()
                free_tier_remaining = budget_service.get_free_tier_remaining(STT_PROVIDER)
                
                # Calculate actual free minutes used and billable minutes
                actual_free_minutes_used = min(billed_duration_minutes, free_tier_remaining)
                actual_billable_minutes = max(0, billed_duration_minutes - free_tier_remaining)
                
                # Calculate actual cost
                cost_per_minute = pricing_service.get_cost_per_minute(STT_PROVIDER, job_record["model"])
                actual_cost = actual_billable_minutes * cost_per_minute
                
                # For now, use estimated cost if actual calculation fails
                if actual_cost is None or actual_cost < 0:
                    actual_cost = job_record["estimated_cost"]

                # Update job record in storage
                # Include words in metadata for post-processing
                metadata = status_result.get("metadata", {}).copy()
                if "words" in status_result:
                    metadata["words"] = status_result["words"]
                
                job_storage.mark_complete(
                    job_id=job_id,
                    transcript=status_result["transcript"],
                    confidence=status_result["confidence"],
                    actual_cost=actual_cost,
                    metadata=metadata
                )

                # Record processing time for feedback loop
                # Use processing_started_at if available (excludes queueing time)
                # Fall back to submitted_at if processing_started_at not tracked
                from datetime import datetime
                completed_at = datetime.now()
                
                # Prefer processing_started_at to exclude queueing time
                if job_record.get("processing_started_at"):
                    start_time = datetime.fromisoformat(job_record["processing_started_at"])
                    processing_time_seconds = (completed_at - start_time).total_seconds()
                    logger.info(f"Using processing_started_at for time calculation (excludes queueing)")
                else:
                    # Fallback: use submitted_at (includes queueing time)
                    submitted_at = datetime.fromisoformat(job_record["submitted_at"])
                    processing_time_seconds = (completed_at - submitted_at).total_seconds()
                    logger.warning(f"processing_started_at not available, using submitted_at (includes queueing time)")
                
                processing_time_service.record_processing_time(
                    model=job_record["model"],
                    audio_duration_minutes=job_record["duration_minutes"],
                    processing_time_seconds=processing_time_seconds,
                    job_id=job_id
                )

                # Update budget service with actual usage
                # This tracks our monthly spending
                budget_service.record_transcription(
                    provider=STT_PROVIDER,
                    model=job_record["model"],
                    duration_minutes=billed_duration_minutes,
                    cost=actual_cost,
                    free_minutes_used=actual_free_minutes_used
                )

                # Add to library - permanent storage for completed transcripts
                # Get updated job record to access transcript_file
                updated_job = job_storage.get_job(job_id)
                transcript_file = updated_job.get("transcript_file")

                # Calculate transcript file size
                file_size_bytes = 0
                if transcript_file:
                    transcript_path = job_storage.TRANSCRIPTS_DIR / transcript_file
                    if transcript_path.exists():
                        file_size_bytes = transcript_path.stat().st_size

                # Add entry to library
                library_id = library_service.add_entry(
                    filename=job_record["filename"],
                    transcript_file=transcript_file,
                    duration_minutes=job_record["duration_minutes"],
                    model=job_record["model"],
                    cost=actual_cost,
                    file_size_bytes=file_size_bytes,
                    metadata=status_result.get("metadata")
                )

                # Update job record to indicate it's in library
                if library_id:
                    job_storage.update_job(job_id, {
                        "in_library": True,
                        "library_id": library_id
                    })
                    logger.info(f"Added job {job_id} to library as {library_id}")

                # Return complete result
                return JSONResponse(content={
                    "job_id": job_id,
                    "status": "complete",
                    "in_library": True,
                    "library_id": library_id,
                    "filename": job_record["filename"],
                    "model": job_record["model"],
                    "submitted_at": job_record["submitted_at"],
                    "completed_at": datetime.now().isoformat(),
                    "transcript": status_result["transcript"],
                    "confidence": status_result["confidence"],
                    "actual_cost": actual_cost,
                    "metadata": status_result.get("metadata")
                })

            else:
                # Job failed - update record with error
                logger.error(f"Job {job_id} failed: {status_result.get('error')}")

                job_storage.mark_failed(
                    job_id=job_id,
                    error=status_result.get("error", "Unknown error")
                )

                return JSONResponse(content={
                    "job_id": job_id,
                    "status": "failed",
                    "filename": job_record["filename"],
                    "model": job_record["model"],
                    "submitted_at": job_record["submitted_at"],
                    "completed_at": datetime.now().isoformat(),
                    "error": status_result.get("error")
                })

        # ===== STEP 4: Job still processing, return current status =====

        # Job is still queued or processing at Google
        # Update our record to show it's in progress (not just queued)
        # Track when processing actually starts (if not already tracked)
        from datetime import datetime
        updates = {}
        
        if job_record["status"] == "queued":
            # Transitioning from queued to processing
            updates["status"] = "processing"
            updates["processing_started_at"] = datetime.now().isoformat()
            logger.info(f"Job {job_id} transitioned from queued to processing")
        elif job_record["status"] == "processing" and not job_record.get("processing_started_at"):
            # Already processing but processing_started_at wasn't set (e.g., job created before this feature)
            # Set it now (approximation - actual start was earlier)
            updates["processing_started_at"] = datetime.now().isoformat()
            logger.info(f"Job {job_id} was already processing, setting processing_started_at now (approximation)")
        
        if updates:
            job_storage.update_job(job_id, updates)

        return JSONResponse(content={
            "job_id": job_id,
            "status": "processing",
            "filename": job_record["filename"],
            "model": job_record["model"],
            "submitted_at": job_record["submitted_at"],
            "message": "Transcription in progress. Check again in a few seconds."
        })

    except HTTPException:
        # Re-raise HTTP exceptions (like 404 Not Found)
        raise
    except Exception as e:
        logger.error(f"Error checking job status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error checking job status: {str(e)}"
        )


@app.delete("/api/jobs/{job_id:path}")
async def delete_job(job_id: str):
    """
    Delete a transcription job and its transcript file.

    Args:
        job_id: The Google operation name (full path with slashes)

    Returns:
        {"success": true, "job_id": "..."}
    """
    try:
        job_storage.delete_job(job_id)

        return JSONResponse(content={
            "success": True,
            "job_id": job_id,
            "message": "Job deleted successfully"
        })

    except KeyError:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    except Exception as e:
        logger.error(f"Error deleting job {job_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete job: {str(e)}")


@app.get("/api/jobs")
async def list_jobs(status: str = None, limit: int = 100):
    """
    List all transcription jobs.

    This endpoint powers the Jobs page - shows all transcriptions the user has run.
    Jobs are sorted by submission time (newest first).

    Args:
        status: Filter by status (queued, processing, complete, failed)
        limit: Maximum number of jobs to return (default 100)

    Returns:
        {
            "jobs": [
                {
                    "job_id": "projects/.../operations/123",
                    "filename": "audio.mp3",
                    "model": "long_standard",
                    "status": "complete",
                    "submitted_at": "2025-11-10T...",
                    "duration_minutes": 5.2,
                    "estimated_cost": 0.12,
                    "transcript": "..." (if complete)
                },
                ...
            ],
            "stats": {
                "total_jobs": 42,
                "by_status": {"complete": 35, "processing": 2, "failed": 5},
                "total_cost": 12.34
            }
        }
    """
    try:
        # Get filtered and sorted list of jobs
        # Include transcripts so Jobs page can display them
        jobs_list = job_storage.list_jobs(
            status=status,
            limit=limit,
            include_transcripts=True  # Load transcript data for completed jobs
        )

        # Get overall statistics
        stats = job_storage.get_stats()

        return JSONResponse(content={
            "jobs": jobs_list,
            "stats": stats,
            "count": len(jobs_list)
        })

    except Exception as e:
        logger.error(f"Error listing jobs: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error listing jobs: {str(e)}"
        )


@app.get("/config")
async def get_config():
    """
    Get current configuration.
    Useful for debugging.
    """
    config = {
        "provider": STT_PROVIDER,
        "max_file_size_mb": 500 if STT_PROVIDER == "google" else 10,
        "supported_formats": ["mp3", "wav", "m4a", "ogg", "flac", "mp4", "mov"]
    }

    # Add provider-specific config
    if STT_PROVIDER == "google":
        config.update({
            "model": GOOGLE_MODEL,
            "gcs_bucket": GCS_BUCKET_NAME,
            "google_credentials_configured": "GOOGLE_APPLICATION_CREDENTIALS" in os.environ,
            "api": "v2_batch"
        })

    return config


@app.get("/api/budget")
async def get_budget():
    """
    Get current budget summary for all providers.

    Returns:
        Budget summary with usage, remaining budget, free tier info for all providers
    """
    try:
        # Get summary for all providers (no provider filter)
        summary = budget_service.get_budget_summary(provider=None)
        return JSONResponse(content=summary)
    except Exception as e:
        logger.error(f"Error getting budget summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/pricing")
async def get_pricing():
    """
    Get pricing information for all providers and models.

    Returns:
        Complete pricing configuration
    """
    try:
        pricing = pricing_service.get_all_pricing()
        return JSONResponse(content=pricing)
    except Exception as e:
        logger.error(f"Error getting pricing: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/pricing/{provider}")
async def get_provider_pricing(provider: str):
    """
    Get pricing for specific provider.

    Args:
        provider: Provider name (e.g., 'google', 'whisper')

    Returns:
        Provider pricing configuration
    """
    try:
        pricing = pricing_service.get_provider_pricing(provider)
        return JSONResponse(content=pricing)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting provider pricing: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/detect-duration")
async def detect_duration(file: UploadFile = File(...)):
    """
    Extract audio metadata (duration, format, codec) from uploaded file.

    This is server-side metadata extraction that works regardless of how
    files arrive (UI, API, batch, Content Cockpit).

    Args:
        file: Uploaded audio file

    Returns:
        {
            "duration": 125.5,  # seconds
            "duration_minutes": 2.09,  # minutes
            "format": "mp3",
            "codec": "mp3",
            "sample_rate": 44100,
            "channels": 2,
            "bit_rate": 128000,
            "file_size": 1024000,  # bytes
            "filename": "audio.mp3"
        }
    """
    try:
        # Read file bytes
        audio_bytes = await file.read()

        # Get metadata service
        metadata_service = get_audio_metadata_service()

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

        return JSONResponse(content=metadata)

    except Exception as e:
        logger.error(f"Error detecting duration for {file.filename}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error detecting duration: {str(e)}"
        )


@app.get("/api/estimate-processing-time")
async def estimate_processing_time(model: str, duration_minutes: float):
    """
    Get estimated processing time for a transcription job.

    Uses learned estimates from historical data, with fallback to hardcoded values.

    Args:
        model: Model name (e.g., 'chirp_standard', 'long_standard')
        duration_minutes: Audio duration in minutes

    Returns:
        Dict with estimated_seconds, confidence, and model details
    """
    try:
        if duration_minutes <= 0:
            raise HTTPException(status_code=400, detail="duration_minutes must be > 0")

        estimate = processing_time_service.get_estimate(
            model=model,
            audio_duration_minutes=duration_minutes
        )

        return JSONResponse(content=estimate)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error estimating processing time: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/estimate-cost")
async def estimate_cost(request: Dict[str, Any] = Body(...)):
    """
    Estimate cost for a transcription.

    Request body:
        {
            "provider": "google",
            "model": "chirp_batch",
            "duration_minutes": 75.0
        }

    Returns:
        Cost estimate with breakdown
    """
    try:
        provider = request.get("provider", STT_PROVIDER)
        model = request.get("model", GOOGLE_MODEL)
        duration_minutes = request.get("duration_minutes", 0)

        logger.info(f"Cost estimate request: provider={provider}, model={model}, duration={duration_minutes}")

        if duration_minutes <= 0:
            raise HTTPException(status_code=400, detail="duration_minutes must be > 0")

        # Get free tier remaining
        free_tier_remaining = budget_service.get_free_tier_remaining(provider)

        # Calculate estimate
        estimate = pricing_service.estimate_cost(
            provider=provider,
            model=model,
            duration_minutes=duration_minutes,
            free_tier_remaining=free_tier_remaining
        )

        logger.info(f"Cost estimate result: ${estimate['total_cost']:.2f} for {duration_minutes} minutes")

        return JSONResponse(content=estimate)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error estimating cost: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# LIBRARY ENDPOINTS
# ============================================================================

@app.get("/api/library")
async def list_library():
    """
    Get all library entries (sorted by date, newest first).

    Returns:
        List of library entries with metadata
    """
    try:
        entries = library_service.get_all_entries()

        return JSONResponse(content={
            "entries": entries,
            "total": len(entries)
        })

    except Exception as e:
        logger.error(f"Error listing library: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error listing library: {str(e)}"
        )


@app.get("/api/library/{library_id}")
async def get_library_entry(library_id: str):
    """
    Get a specific library entry with full transcript.

    Args:
        library_id: Library entry ID

    Returns:
        Library entry with transcript loaded
    """
    try:
        entry = library_service.get_entry(library_id)

        if not entry:
            raise HTTPException(
                status_code=404,
                detail=f"Library entry not found: {library_id}"
            )

        # Load transcript from file
        transcript_file = entry.get("transcript_file")
        if transcript_file:
            transcript_path = library_service.TRANSCRIPTS_DIR / transcript_file
            if transcript_path.exists():
                with open(transcript_path, 'r') as f:
                    transcript_data = json.load(f)
                entry["transcript"] = transcript_data.get("transcript")
                entry["words"] = transcript_data.get("words")

        return JSONResponse(content=entry)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting library entry {library_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting library entry: {str(e)}"
        )


@app.get("/api/library/{library_id}/download/text")
async def download_library_text(library_id: str):
    """
    Download library entry transcript as plain text.

    Args:
        library_id: Library entry ID

    Returns:
        Plain text file download
    """
    try:
        entry = library_service.get_entry(library_id)

        if not entry:
            raise HTTPException(
                status_code=404,
                detail=f"Library entry not found: {library_id}"
            )

        # Load transcript from file
        transcript_file = entry.get("transcript_file")
        if not transcript_file:
            raise HTTPException(
                status_code=404,
                detail="No transcript available for this entry"
            )

        transcript_path = library_service.TRANSCRIPTS_DIR / transcript_file
        if not transcript_path.exists():
            raise HTTPException(
                status_code=404,
                detail="Transcript file not found"
            )

        with open(transcript_path, 'r') as f:
            transcript_data = json.load(f)

        transcript_text = transcript_data.get("transcript", "")

        # Return as downloadable text file
        from fastapi.responses import Response
        filename = entry.get("filename", "transcript")
        # Remove extension and add .txt
        filename_base = filename.rsplit('.', 1)[0]

        return Response(
            content=transcript_text,
            media_type="text/plain",
            headers={
                "Content-Disposition": f'attachment; filename="{filename_base}.txt"'
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading library text {library_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error downloading text: {str(e)}"
        )


@app.get("/api/library/{library_id}/download/json")
async def download_library_json(library_id: str):
    """
    Download library entry transcript as JSON.

    Args:
        library_id: Library entry ID

    Returns:
        JSON file download with full transcript data
    """
    try:
        entry = library_service.get_entry(library_id)

        if not entry:
            raise HTTPException(
                status_code=404,
                detail=f"Library entry not found: {library_id}"
            )

        # Load transcript from file
        transcript_file = entry.get("transcript_file")
        if not transcript_file:
            raise HTTPException(
                status_code=404,
                detail="No transcript available for this entry"
            )

        transcript_path = library_service.TRANSCRIPTS_DIR / transcript_file
        if not transcript_path.exists():
            raise HTTPException(
                status_code=404,
                detail="Transcript file not found"
            )

        with open(transcript_path, 'r') as f:
            transcript_data = json.load(f)

        # Return as downloadable JSON file
        from fastapi.responses import Response
        filename = entry.get("filename", "transcript")
        # Remove extension and add .json
        filename_base = filename.rsplit('.', 1)[0]

        return Response(
            content=json.dumps(transcript_data, indent=2),
            media_type="application/json",
            headers={
                "Content-Disposition": f'attachment; filename="{filename_base}.json"'
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading library JSON {library_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error downloading JSON: {str(e)}"
        )


@app.delete("/api/library/{library_id}")
async def delete_library_entry(library_id: str):
    """
    Permanently delete a library entry and its transcript file.

    This is the ONLY place where transcripts are permanently deleted.

    Args:
        library_id: Library entry ID

    Returns:
        {"success": true, "library_id": "..."}
    """
    try:
        success = library_service.delete_entry(library_id)

        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Library entry not found: {library_id}"
            )

        return JSONResponse(content={
            "success": True,
            "library_id": library_id,
            "message": "Library entry deleted permanently"
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting library entry {library_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting library entry: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn

    # Run the server
    # In production, you'd use: uvicorn app.main:app --host 0.0.0.0 --port 8000
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True  # Auto-reload on code changes during development
    )
