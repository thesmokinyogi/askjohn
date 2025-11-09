"""
Google Cloud Speech-to-Text V2 Batch Recognition Service.

This service handles long audio transcription using Google's V2 API.
Supports audio of any length (up to 8 hours) via batch processing.

Key differences from V1:
- Uses batch_recognize instead of recognize
- Requires audio in Cloud Storage
- Async operation with polling
- Better models (Chirp 3)
- More features (speaker diarization, etc.)
"""

from google.cloud.speech_v2 import SpeechClient
from google.cloud.speech_v2.types import cloud_speech
from typing import Dict, Optional
import logging
import time

logger = logging.getLogger(__name__)


class GoogleSpeechV2Service:
    """
    Google Speech-to-Text V2 implementation with batch recognition.

    Handles:
    - Batch recognition for long audio
    - Multiple model support (Chirp 3, long, short)
    - Async operation polling
    - Yoga-specific vocabulary hints
    - Timestamp extraction
    """

    def __init__(self, project_id: str, model: str = "long"):
        """
        Initialize V2 Speech client.

        Args:
            project_id: Google Cloud project ID
            model: Model to use (chirp_3, long, short)
        """
        self.project_id = project_id
        self.model = model
        self.client = SpeechClient()

        # Yoga-specific vocabulary for better recognition
        self.yoga_vocabulary = [
            "asana", "pranayama", "shavasana", "savasana", "namaste",
            "downward facing dog", "adho mukha svanasana",
            "warrior one", "warrior two", "warrior three",
            "virabhadrasana",
            "sun salutation", "surya namaskar",
            "child's pose", "balasana",
            "mountain pose", "tadasana",
            "tree pose", "vrksasana",
            "triangle pose", "trikonasana",
            "plank pose", "phalakasana",
            "cobra pose", "bhujangasana",
            "upward dog", "urdhva mukha svanasana",
            "cat pose", "marjaryasana",
            "cow pose", "bitilasana",
            "pigeon pose", "kapotasana",
            "seated forward bend", "paschimottanasana",
            "bridge pose", "setu bandhasana",
            "corpse pose", "savasana",
            "vinyasa", "hatha", "yin", "restorative"
        ]

        logger.info(f"Initialized Speech V2 service: model={model}, project={project_id}")

    def transcribe(self, gcs_uri: str, language_code: str = "en-US") -> Dict:
        """
        Transcribe audio file from Cloud Storage using batch recognition.

        Args:
            gcs_uri: Google Cloud Storage URI (gs://bucket/path/file.ext)
            language_code: Language code (default: en-US)

        Returns:
            Dict with transcript, confidence, words, and metadata
        """
        try:
            # Configure recognition
            config = self._build_config(language_code)

            # Create recognition request
            request = cloud_speech.BatchRecognizeRequest(
                recognizer=f"projects/{self.project_id}/locations/global/recognizers/_",
                config=config,
                files=[cloud_speech.BatchRecognizeFileMetadata(uri=gcs_uri)],
                recognition_output_config=cloud_speech.RecognitionOutputConfig(
                    inline_response_config=cloud_speech.InlineOutputConfig()
                ),
            )

            # Start batch recognition (async operation)
            logger.info(f"Starting batch recognition for: {gcs_uri}")
            operation = self.client.batch_recognize(request=request)

            # Poll until complete
            logger.info("Waiting for transcription to complete...")
            response = operation.result(timeout=600)  # 10 minute timeout

            # Extract results
            return self._parse_results(response)

        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return {
                "success": False,
                "error": str(e),
                "transcript": "",
                "confidence": 0.0,
                "words": [],
                "metadata": {"error_type": "transcription_error"}
            }

    def _build_config(self, language_code: str) -> cloud_speech.RecognitionConfig:
        """
        Build recognition configuration with optimal settings.

        Args:
            language_code: Language for recognition

        Returns:
            RecognitionConfig object
        """
        # Build model name based on selection
        model_name = f"projects/{self.project_id}/locations/global/models/{self.model}"

        # Create phrase set for yoga vocabulary
        phrase_hints = cloud_speech.SpeechAdaptation.AdaptationPhraseSet(
            phrases=[{"value": phrase, "boost": 15} for phrase in self.yoga_vocabulary]
        )

        config = cloud_speech.RecognitionConfig(
            auto_decoding_config=cloud_speech.AutoDetectDecodingConfig(),
            language_codes=[language_code],
            model=model_name,
            features=cloud_speech.RecognitionFeatures(
                enable_automatic_punctuation=True,
                enable_word_time_offsets=True,
                enable_word_confidence=True,
            ),
            adaptation=cloud_speech.SpeechAdaptation(
                phrase_sets=[phrase_hints]
            ),
        )

        return config

    def _parse_results(self, response) -> Dict:
        """
        Parse batch recognition response into structured format.

        Args:
            response: BatchRecognizeResponse from Google

        Returns:
            Structured dict with transcript and metadata
        """
        try:
            # Extract results from response
            # V2 response structure is different from V1
            results = []
            total_confidence = 0.0
            word_details = []

            # Iterate through results
            for result in response.results.values():
                for batch_result in result.transcript.results:
                    if batch_result.alternatives:
                        alternative = batch_result.alternatives[0]

                        results.append(alternative.transcript)
                        total_confidence += alternative.confidence

                        # Extract word-level details
                        for word_info in alternative.words:
                            word_details.append({
                                "word": word_info.word,
                                "start_time": word_info.start_offset.total_seconds(),
                                "end_time": word_info.end_offset.total_seconds(),
                                "confidence": word_info.confidence if hasattr(word_info, 'confidence') else 0.0
                            })

            # Combine results
            full_transcript = " ".join(results)
            avg_confidence = total_confidence / len(results) if results else 0.0

            return {
                "success": True,
                "transcript": full_transcript,
                "confidence": avg_confidence,
                "words": word_details,
                "metadata": {
                    "total_words": len(word_details),
                    "model": self.model,
                    "language": "en-US",
                    "api_version": "v2"
                }
            }

        except Exception as e:
            logger.error(f"Error parsing results: {e}")
            return {
                "success": False,
                "error": f"Result parsing error: {str(e)}",
                "transcript": "",
                "confidence": 0.0,
                "words": [],
                "metadata": {"error_type": "parsing_error"}
            }


def get_transcription_service_v2(project_id: str, model: str = "long") -> GoogleSpeechV2Service:
    """
    Factory function to create V2 transcription service.

    Args:
        project_id: Google Cloud project ID
        model: Model to use (chirp_3, long, short)

    Returns:
        GoogleSpeechV2Service instance
    """
    return GoogleSpeechV2Service(project_id=project_id, model=model)
