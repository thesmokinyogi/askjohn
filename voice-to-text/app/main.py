"""
Voice-to-Text Web Application

FastAPI app for transcribing audio files using Google Speech-to-Text.
Supports both V1 (synchronous, <60 sec) and V2 (batch, any length).
"""

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import os
import logging
from dotenv import load_dotenv

# Import services
from app.services.transcribe_v2 import get_transcription_service_v2
from app.services.storage import CloudStorageService

# Load environment variables from .env file
load_dotenv()

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

# Provider-specific configuration
GOOGLE_MODEL = os.getenv("GOOGLE_MODEL", "long")  # Renamed from STT_MODEL
GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME")
GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT")

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
async def transcribe_audio(file: UploadFile = File(...)):
    """
    Transcribe uploaded audio file using configured provider.

    Current provider: Google Speech-to-Text V2 Batch API
    - Supports any audio length (up to 8 hours)
    - Uploads to Cloud Storage temporarily
    - Uses batch recognition
    - Better accuracy with Chirp models

    Future: Whisper, AssemblyAI, Deepgram support

    Accepts: mp3, wav, m4a, ogg, flac, mp4, mov
    Returns: Transcript with confidence score and word-level details
    """

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
            # Upload to Cloud Storage and extract metadata
            logger.info("Uploading to Cloud Storage...")
            gcs_uri, audio_metadata = storage_service.upload_audio(audio_bytes, file.filename)

            # Transcribe from Cloud Storage with actual audio metadata
            logger.info("Starting batch transcription...")
            result = transcription_service.transcribe(gcs_uri, audio_metadata=audio_metadata)

            # Clean up uploaded file
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

    # Return result
    return JSONResponse(content={
        "success": True,
        "filename": file.filename,
        "transcript": result["transcript"],
        "confidence": result["confidence"],
        "word_count": result["metadata"].get("total_words", 0),
        "provider": STT_PROVIDER,
        "model": result["metadata"].get("model", "unknown"),
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
