"""
Voice-to-Text Web Application

Simple FastAPI app for transcribing audio files using Google Speech-to-Text.
"""

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import os
from dotenv import load_dotenv

from app.utils.transcribe import get_transcription_service

# Load environment variables from .env file
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="Voice-to-Text Transcription Service",
    description="Upload audio files and get text transcriptions",
    version="1.0.0"
)

# Mount static files (for serving the HTML UI)
static_path = Path(__file__).parent / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

# Initialize transcription service
# Can swap "google" for "whisper" here when ready
STT_PROVIDER = os.getenv("STT_PROVIDER", "google")
transcription_service = get_transcription_service(STT_PROVIDER)


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
        "provider": STT_PROVIDER
    }


@app.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    """
    Transcribe uploaded audio file.

    Accepts: mp3, wav, m4a, ogg, flac
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
        raise HTTPException(
            status_code=500,
            detail=f"Error reading file: {str(e)}"
        )

    # Validate file size (max 10MB for now)
    max_size_mb = 10
    if len(audio_bytes) > max_size_mb * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: {max_size_mb}MB"
        )

    # Transcribe
    try:
        result = transcription_service.transcribe(audio_bytes, file_extension)
    except Exception as e:
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

    # Return result
    return JSONResponse(content={
        "success": True,
        "filename": file.filename,
        "transcript": result["transcript"],
        "confidence": result["confidence"],
        "word_count": result["metadata"].get("total_words", 0),
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
        "stt_provider": STT_PROVIDER,
        "google_credentials_configured": "GOOGLE_APPLICATION_CREDENTIALS" in os.environ,
        "max_file_size_mb": 10,
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
