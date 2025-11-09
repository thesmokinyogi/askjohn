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
STT_API_VERSION = os.getenv("STT_API_VERSION", "v2")
STT_MODEL = os.getenv("STT_MODEL", "long")
GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME")
GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT")

# Initialize services based on API version
if STT_API_VERSION == "v2":
    if not GCS_BUCKET_NAME:
        raise ValueError("GCS_BUCKET_NAME must be set in .env for V2 API")
    if not GOOGLE_CLOUD_PROJECT:
        raise ValueError("GOOGLE_CLOUD_PROJECT must be set in .env for V2 API")

    # Initialize V2 services
    storage_service = CloudStorageService(
        bucket_name=GCS_BUCKET_NAME,
        project_id=GOOGLE_CLOUD_PROJECT
    )
    transcription_service = get_transcription_service_v2(
        project_id=GOOGLE_CLOUD_PROJECT,
        model=STT_MODEL
    )

    logger.info(f"Initialized V2 services: model={STT_MODEL}, bucket={GCS_BUCKET_NAME}")

else:
    # V1 fallback (for testing)
    from app.services.transcribe_v1 import get_transcription_service
    transcription_service = get_transcription_service("google")
    storage_service = None
    logger.info("Initialized V1 service (synchronous, max 60 seconds)")


@app.on_event("startup")
async def startup_event():
    """Verify services on startup."""
    logger.info(f"Starting Voice-to-Text Service (API: {STT_API_VERSION})")

    if STT_API_VERSION == "v2":
        # Verify bucket access
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
    return {
        "status": "healthy",
        "service": "voice-to-text",
        "api_version": STT_API_VERSION,
        "model": STT_MODEL if STT_API_VERSION == "v2" else "video",
        "bucket": GCS_BUCKET_NAME if STT_API_VERSION == "v2" else None
    }


@app.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    """
    Transcribe uploaded audio file.

    V2 API:
    - Supports any audio length (up to 8 hours)
    - Uploads to Cloud Storage temporarily
    - Uses batch recognition
    - Better accuracy with Chirp models

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

    # Validate file size (500MB for V2, 10MB for V1)
    max_size_mb = 500 if STT_API_VERSION == "v2" else 10
    if len(audio_bytes) > max_size_mb * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: {max_size_mb}MB"
        )

    logger.info(f"Processing file: {file.filename} ({len(audio_bytes)} bytes)")

    # V2 API: Upload to GCS, transcribe, cleanup
    if STT_API_VERSION == "v2":
        gcs_uri = None
        try:
            # Upload to Cloud Storage
            logger.info("Uploading to Cloud Storage...")
            gcs_uri = storage_service.upload_audio(audio_bytes, file.filename)

            # Transcribe from Cloud Storage
            logger.info("Starting batch transcription...")
            result = transcription_service.transcribe(gcs_uri)

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

    # V1 API: Direct transcription
    else:
        try:
            result = transcription_service.transcribe(audio_bytes, file_extension)
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Transcription error: {str(e)}"
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
        "api_version": STT_API_VERSION,
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
    return {
        "api_version": STT_API_VERSION,
        "model": STT_MODEL if STT_API_VERSION == "v2" else "video",
        "gcs_bucket": GCS_BUCKET_NAME if STT_API_VERSION == "v2" else None,
        "google_credentials_configured": "GOOGLE_APPLICATION_CREDENTIALS" in os.environ,
        "max_file_size_mb": 500 if STT_API_VERSION == "v2" else 10,
        "supported_formats": ["mp3", "wav", "m4a", "ogg", "flac", "mp4", "mov"]
    }


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
