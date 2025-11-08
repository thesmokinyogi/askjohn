"""
Modular transcription service.

This module handles audio transcription using Google Speech-to-Text.
Designed to be swappable - could replace with Whisper, AssemblyAI, etc.
"""

from typing import Dict, Optional
from google.cloud import speech
import io


class TranscriptionService:
    """
    Abstract transcription interface.
    Makes it easy to swap providers later.
    """

    def transcribe(self, audio_bytes: bytes, audio_format: str = "mp3") -> Dict:
        """
        Transcribe audio bytes to text.

        Args:
            audio_bytes: Raw audio file bytes
            audio_format: Audio format (mp3, wav, m4a, etc.)

        Returns:
            Dict with transcript, confidence, and metadata
        """
        raise NotImplementedError("Subclass must implement transcribe()")


class GoogleSTTService(TranscriptionService):
    """
    Google Speech-to-Text implementation.
    """

    def __init__(self):
        """Initialize Google Speech client."""
        self.client = speech.SpeechClient()

        # Yoga-specific vocabulary hints
        self.yoga_vocabulary = [
            "asana", "pranayama", "shavasana", "namaste",
            "downward facing dog", "downward dog", "adho mukha svanasana",
            "warrior one", "warrior two", "warrior three",
            "virabhadrasana", "tadasana", "mountain pose",
            "child's pose", "balasana", "sun salutation", "surya namaskar",
            "vinyasa", "ujjayi", "chakra", "Sanskrit",
            "savasana", "corpse pose", "tree pose", "vrksasana",
            "triangle pose", "trikonasana", "plank pose",
            "cobra pose", "bhujangasana", "upward dog", "urdhva mukha svanasana"
        ]

    def transcribe(self, audio_bytes: bytes, audio_format: str = "mp3") -> Dict:
        """
        Transcribe audio using Google Speech-to-Text.

        Args:
            audio_bytes: Raw audio file bytes
            audio_format: Audio format (mp3, wav, m4a, etc.)

        Returns:
            Dict with:
                - transcript: Full text transcription
                - confidence: Average confidence score (0.0 to 1.0)
                - words: List of word-level details with timestamps
                - metadata: Processing information
        """

        # Map file formats to Google encoding types
        # Note: Google STT doesn't support MP3/M4A directly - use ENCODING_UNSPECIFIED for auto-detection
        encoding_map = {
            "mp3": speech.RecognitionConfig.AudioEncoding.ENCODING_UNSPECIFIED,  # Auto-detect
            "wav": speech.RecognitionConfig.AudioEncoding.LINEAR16,
            "m4a": speech.RecognitionConfig.AudioEncoding.ENCODING_UNSPECIFIED,  # Auto-detect
            "mp4": speech.RecognitionConfig.AudioEncoding.ENCODING_UNSPECIFIED,  # Auto-detect
            "mov": speech.RecognitionConfig.AudioEncoding.ENCODING_UNSPECIFIED,  # Auto-detect
            "ogg": speech.RecognitionConfig.AudioEncoding.OGG_OPUS,
            "flac": speech.RecognitionConfig.AudioEncoding.FLAC,
        }

        encoding = encoding_map.get(audio_format.lower(), speech.RecognitionConfig.AudioEncoding.ENCODING_UNSPECIFIED)

        # Configure recognition
        config = speech.RecognitionConfig(
            encoding=encoding,
            language_code="en-US",

            # Enable useful features
            enable_automatic_punctuation=True,
            enable_word_time_offsets=True,  # Get timestamps for each word
            enable_word_confidence=True,     # Confidence per word

            # Use video model (optimized for clear speech like yoga instruction)
            model="video",
            use_enhanced=True,  # Premium model for better accuracy

            # Add yoga-specific vocabulary hints
            speech_contexts=[
                speech.SpeechContext(
                    phrases=self.yoga_vocabulary,
                    boost=15  # Increase likelihood of these terms
                )
            ],
        )

        # Create audio object
        audio = speech.RecognitionAudio(content=audio_bytes)

        # Perform transcription
        # Note: This is synchronous. For long audio (>60 sec), use long_running_recognize
        try:
            response = self.client.recognize(config=config, audio=audio)
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "transcript": "",
                "confidence": 0.0,
                "words": [],
                "metadata": {"error_type": type(e).__name__}
            }

        # Parse results
        if not response.results:
            return {
                "success": False,
                "error": "No speech detected in audio",
                "transcript": "",
                "confidence": 0.0,
                "words": [],
                "metadata": {}
            }

        # Extract transcript and metadata
        transcript_parts = []
        all_words = []
        confidences = []

        for result in response.results:
            alternative = result.alternatives[0]  # Best alternative
            transcript_parts.append(alternative.transcript)
            confidences.append(alternative.confidence)

            # Extract word-level details
            for word_info in alternative.words:
                all_words.append({
                    "word": word_info.word,
                    "start_time": word_info.start_time.total_seconds(),
                    "end_time": word_info.end_time.total_seconds(),
                    "confidence": word_info.confidence if hasattr(word_info, 'confidence') else None
                })

        # Calculate average confidence
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

        return {
            "success": True,
            "transcript": " ".join(transcript_parts),
            "confidence": avg_confidence,
            "words": all_words,
            "metadata": {
                "num_segments": len(response.results),
                "total_words": len(all_words),
                "audio_format": audio_format,
                "model": "google-video-enhanced"
            }
        }


class WhisperSTTService(TranscriptionService):
    """
    Placeholder for Whisper implementation.
    Swap this in if Google isn't meeting needs.
    """

    def transcribe(self, audio_bytes: bytes, audio_format: str = "mp3") -> Dict:
        """Whisper transcription - not implemented yet."""
        raise NotImplementedError("Whisper service not yet implemented. Use GoogleSTTService.")


# Factory function for easy swapping
def get_transcription_service(provider: str = "google") -> TranscriptionService:
    """
    Get transcription service by provider name.

    Args:
        provider: "google" or "whisper"

    Returns:
        TranscriptionService instance
    """
    if provider == "google":
        return GoogleSTTService()
    elif provider == "whisper":
        return WhisperSTTService()
    else:
        raise ValueError(f"Unknown provider: {provider}. Use 'google' or 'whisper'")
