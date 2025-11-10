"""
Voice-to-Text Web Application

FastAPI app for transcribing audio files using Google Speech-to-Text.
Supports both V1 (synchronous, <60 sec) and V2 (batch, any length).
"""

from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import os
import logging
from dotenv import load_dotenv

# Import services
from app.services.transcribe_v2 import get_transcription_service_v2
from app.services.storage import CloudStorageService
from app.services.pricing import get_pricing_service
from app.services.budget import get_budget_service

# Load environment variables from .env file
load_dotenv()

# ===== TEST MODE CONFIGURATION =====
# Set to True to skip upload and use cached file for faster testing
TEST_MODE_SKIP_UPLOAD = os.getenv("TEST_MODE_SKIP_UPLOAD", "false").lower() == "true"
TEST_GCS_URI = os.getenv("TEST_GCS_URI", "gs://voice-to-text-audio-jc/uploads/20251110_060326_Voice_Memo_-_2014-06-28_16_33_27_-_Chelsea_And_The_Magician.m4a")
TEST_AUDIO_METADATA = {
    'sample_rate': 44100,
    'channels': 1,
    'duration': 336.8,
    'codec': 'aac',
    'bit_rate': 'unknown'
}
# ===================================

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
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

# Get configuration from environment
STT_PROVIDER = os.getenv("STT_PROVIDER", "google")

# Budget configuration
MONTHLY_BUDGET = float(os.getenv("MONTHLY_BUDGET", "250.0"))

# Provider-specific configuration
GOOGLE_MODEL = os.getenv("GOOGLE_MODEL", "long")  # Renamed from STT_MODEL
GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME")
GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT")

# Initialize pricing and budget services
pricing_service = get_pricing_service()
budget_service = get_budget_service(monthly_budget=MONTHLY_BUDGET)

# Initialize services based on provider
if STT_PROVIDER == "google":
    # Validate Google-specific requirements
    if not GCS_BUCKET_NAME:
        raise ValueError("GCS_BUCKET_NAME must be set in .env when using Google provider")
    if not GOOGLE_CLOUD_PROJECT:
        raise ValueError("GOOGLE_CLOUD_PROJECT must be set in .env when using Google provider")

    # Initialize Google V2 services
    storage_service = CloudStorageService(
        bucket_name=GCS_BUCKET_NAME,
        project_id=GOOGLE_CLOUD_PROJECT
    )
    transcription_service = get_transcription_service_v2(
        project_id=GOOGLE_CLOUD_PROJECT,
        model=GOOGLE_MODEL
    )

    logger.info(f"Initialized Google provider: model={GOOGLE_MODEL}, bucket={GCS_BUCKET_NAME}")

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


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main UI page."""
    html_file = static_path / "index.html"
    if html_file.exists():
        return html_file.read_text()
    return "<h1>Voice-to-Text API</h1><p>UI not found. Visit /docs for API documentation.</p>"


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
            "api": "v2_batch"
        })

    return health_info


@app.post("/transcribe")
async def transcribe_audio(
    file: UploadFile = File(...),
    model: str = Form(None)
):
    """
    Transcribe uploaded audio file using configured provider.

    Current provider: Google Speech-to-Text V2 Batch API
    - Supports any audio length (up to 8 hours)
    - Uploads to Cloud Storage temporarily
    - Uses batch recognition
    - Better accuracy with Chirp models

    Future: Whisper, AssemblyAI, Deepgram support

    Args:
        file: Audio file to transcribe
        model: Model to use (e.g., 'chirp_batch', 'long_standard').
               Defaults to GOOGLE_MODEL from .env

    Accepts: mp3, wav, m4a, ogg, flac, mp4, mov
    Returns: Transcript with confidence score, word-level details, and cost info
    """

    # Use provided model or fall back to environment variable
    selected_model = model or GOOGLE_MODEL

    # Map UI model names to Google API model names
    # UI uses: chirp_batch, chirp_standard, long_batch, long_standard
    # Google API uses: chirp, long, short
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

    # Read file bytes
    try:
        audio_bytes = await file.read()
    except Exception as e:
        logger.error(f"Error reading file: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error reading file: {str(e)}"
        )

    # Validate file size (provider-specific)
    max_size_mb = 500 if STT_PROVIDER == "google" else 10
    if len(audio_bytes) > max_size_mb * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: {max_size_mb}MB"
        )

    logger.info(f"Processing file: {file.filename} ({len(audio_bytes)} bytes)")

    # Route to provider-specific transcription
    if STT_PROVIDER == "google":
        # Google: Upload to GCS, batch transcribe, cleanup
        gcs_uri = None
        try:
            # TEST MODE: Skip upload for faster iteration
            if TEST_MODE_SKIP_UPLOAD:
                logger.warning("⚠️  TEST MODE: Skipping upload, using cached file")
                gcs_uri = TEST_GCS_URI
                audio_metadata = TEST_AUDIO_METADATA
                logger.info(f"Using cached: {gcs_uri}")
                logger.info(f"Cached metadata: {audio_metadata['sample_rate']}Hz, {audio_metadata['channels']}ch")
            else:
                # Normal mode: Upload to Cloud Storage and extract metadata
                logger.info("Uploading to Cloud Storage...")
                gcs_uri, audio_metadata = storage_service.upload_audio(audio_bytes, file.filename)

            # Initialize transcription service with Google API model name
            model_transcription_service = get_transcription_service_v2(
                project_id=GOOGLE_CLOUD_PROJECT,
                model=google_api_model
            )

            # Transcribe from Cloud Storage with actual audio metadata
            logger.info(f"Starting batch transcription with model: {google_api_model} (UI: {selected_model})...")
            result = model_transcription_service.transcribe(gcs_uri, audio_metadata=audio_metadata)

            # Clean up uploaded file (skip if in test mode using cached file)
            if not TEST_MODE_SKIP_UPLOAD:
                logger.info("Cleaning up temporary file...")
                storage_service.delete_file(gcs_uri)

        except Exception as e:
            logger.error(f"Transcription error: {e}")
            # Clean up on error
            if gcs_uri:
                storage_service.delete_file(gcs_uri)
            raise HTTPException(
                status_code=500,
                detail=f"Transcription error: {str(e)}"
            )

    elif STT_PROVIDER == "whisper":
        # Whisper: Direct transcription (when implemented)
        try:
            result = transcription_service.transcribe(audio_bytes, file_extension)
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Transcription error: {str(e)}"
            )

    else:
        raise HTTPException(
            status_code=500,
            detail=f"Provider {STT_PROVIDER} not properly configured"
        )

    # Check if transcription was successful
    if not result.get("success", False):
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Unknown transcription error")
        )

    logger.info(f"Transcription complete: {result['metadata'].get('total_words', 0)} words")

    # Calculate cost and record in budget
    duration_seconds = result["metadata"].get("duration_seconds", 0)
    duration_minutes = duration_seconds / 60.0

    # Get free tier remaining
    free_tier_remaining = budget_service.get_free_tier_remaining(STT_PROVIDER)

    # Calculate cost
    cost_estimate = pricing_service.estimate_cost(
        provider=STT_PROVIDER,
        model=selected_model,
        duration_minutes=duration_minutes,
        free_tier_remaining=free_tier_remaining
    )

    # Record transcription in budget
    budget_service.record_transcription(
        provider=STT_PROVIDER,
        model=selected_model,
        duration_minutes=duration_minutes,
        cost=cost_estimate["total_cost"],
        free_minutes_used=cost_estimate["free_minutes_used"],
        filename=file.filename
    )

    logger.info(
        f"Cost: ${cost_estimate['total_cost']:.2f} "
        f"({cost_estimate['billable_minutes']:.1f} min @ ${cost_estimate['cost_per_minute']}/min)"
    )

    # Return result
    return JSONResponse(content={
        "success": True,
        "filename": file.filename,
        "transcript": result["transcript"],
        "confidence": result["confidence"],
        "word_count": result["metadata"].get("total_words", 0),
        "provider": STT_PROVIDER,
        "model": selected_model,
        "cost": {
            "total_cost": cost_estimate["total_cost"],
            "duration_minutes": duration_minutes,
            "billable_minutes": cost_estimate["billable_minutes"],
            "free_minutes_used": cost_estimate["free_minutes_used"],
            "cost_per_minute": cost_estimate["cost_per_minute"]
        },
        "details": {
            "words": result["words"],  # Word-level timestamps and confidence
            "metadata": result["metadata"]
        }
    })


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
    Get current budget summary.

    Returns:
        Budget summary with usage, remaining budget, free tier info
    """
    try:
        summary = budget_service.get_budget_summary(provider=STT_PROVIDER)
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


@app.post("/api/estimate-cost")
async def estimate_cost(request: dict):
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

        return JSONResponse(content=estimate)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error estimating cost: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
