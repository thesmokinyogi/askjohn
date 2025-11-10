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
            # Extract file extension from URI for format-specific config
            file_extension = gcs_uri.split('.')[-1].lower() if '.' in gcs_uri else None

            # Configure recognition
            config = self._build_config(language_code, audio_encoding=file_extension)

            # Create recognition request
            file_metadata = cloud_speech.BatchRecognizeFileMetadata(uri=gcs_uri)

            request = cloud_speech.BatchRecognizeRequest(
                recognizer=f"projects/{self.project_id}/locations/global/recognizers/_",
                config=config,
                files=[file_metadata],
                recognition_output_config=cloud_speech.RecognitionOutputConfig(
                    inline_response_config=cloud_speech.InlineOutputConfig()
                ),
            )

            # Start batch recognition (async operation)
            logger.info(f"Starting batch recognition for: {gcs_uri}")
            logger.info(f"File metadata: {file_metadata}")
            logger.info(f"Config: auto_decoding={hasattr(config, 'auto_decoding_config')}, model={config.model}, lang={config.language_codes}")
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

    def _build_config(self, language_code: str, audio_encoding: str = None) -> cloud_speech.RecognitionConfig:
        """
        Build recognition configuration with optimal settings.

        Args:
            language_code: Language for recognition
            audio_encoding: Audio file extension (e.g., 'm4a', 'mp3', 'wav').
                          M4A requires explicit config - not supported by auto-detect.

        Returns:
            RecognitionConfig object
        """
        # V2 API uses simple model names like "long", "short", "chirp_3"
        # Not full resource paths
        logger.info(f"Building config with model: {self.model}, encoding: {audio_encoding}")

        # Choose decoding config based on audio format
        # M4A requires explicit config - NOT supported by AutoDetectDecodingConfig
        # Auto-detect supports: WAV, FLAC, MP3, OGG_OPUS, WEBM_OPUS
        if audio_encoding and audio_encoding.upper() == 'M4A':
            decoding_config_kwargs = {
                'explicit_decoding_config': cloud_speech.ExplicitDecodingConfig(
                    encoding=cloud_speech.ExplicitDecodingConfig.AudioEncoding.M4A_AAC,
                )
            }
            logger.info("Using ExplicitDecodingConfig for M4A format")
        else:
            # Auto-detect for MP3, WAV, FLAC, OGG, WEBM
            decoding_config_kwargs = {
                'auto_decoding_config': cloud_speech.AutoDetectDecodingConfig()
            }
            logger.info("Using AutoDetectDecodingConfig")

        # TODO: Fix phrase hints syntax for V2 API
        # V2 has different syntax than V1 for custom vocabulary
        # Temporarily disabled to get transcription working
        # phrase_hints = cloud_speech.SpeechAdaptation.AdaptationPhraseSet(
        #     phrases=[{"value": phrase, "boost": 15} for phrase in self.yoga_vocabulary]
        # )

        config = cloud_speech.RecognitionConfig(
            **decoding_config_kwargs,
            language_codes=[language_code],
            model=self.model,  # Use model name directly, not resource path
            features=cloud_speech.RecognitionFeatures(
                enable_automatic_punctuation=True,
                enable_word_time_offsets=True,
                enable_word_confidence=True,
            ),
            # TODO: Re-enable after fixing phrase hints syntax
            # adaptation=cloud_speech.SpeechAdaptation(
            #     phrase_sets=[phrase_hints]
            # ),
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
            # DEBUG: Log response structure
            logger.info(f"Response type: {type(response)}")
            logger.info(f"Response has results: {hasattr(response, 'results')}")

            # Check for response-level metadata/errors
            if hasattr(response, 'total_billed_duration'):
                logger.info(f"Total billed duration: {response.total_billed_duration}")

            if hasattr(response, 'results'):
                logger.info(f"Results type: {type(response.results)}")
                logger.info(f"Results length: {len(response.results) if response.results else 0}")
                logger.info(f"Results keys: {list(response.results.keys()) if response.results else []}")

            # Extract results from response
            # V2 response structure is different from V1
            results = []
            total_confidence = 0.0
            word_details = []

            # Iterate through results (keyed by GCS URI)
            for uri, result in response.results.items():
                logger.info(f"Processing URI: {uri}")
                logger.info(f"Result type: {type(result)}")
                logger.info(f"Result has transcript: {hasattr(result, 'transcript')}")

                # Check for errors in this file's result
                if hasattr(result, 'error'):
                    logger.error(f"Error in result for {uri}: {result.error}")
                    continue

                if hasattr(result, 'metadata'):
                    logger.info(f"Result metadata: {result.metadata}")

                # Parse transcript if present
                if hasattr(result, 'transcript') and result.transcript:
                    logger.info(f"Transcript type: {type(result.transcript)}")
                    logger.info(f"Transcript has results: {hasattr(result.transcript, 'results')}")

                    if hasattr(result.transcript, 'results'):
                        logger.info(f"Transcript results count: {len(result.transcript.results)}")

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
                else:
                    logger.warning(f"No transcript found in result for {uri}")

            # Combine results
            full_transcript = " ".join(results)
            avg_confidence = total_confidence / len(results) if results else 0.0

            logger.info(f"Parsed {len(results)} result segments, {len(word_details)} words")

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
            logger.error(f"Error parsing results: {e}", exc_info=True)
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
