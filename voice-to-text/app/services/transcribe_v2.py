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

    # Audio format configuration
    # Formats supported by AutoDetectDecodingConfig (per Google documentation)
    AUTO_DETECT_FORMATS = {
        'wav', 'flac', 'mp3', 'ogg', 'opus', 'webm'
    }

    # AudioEncoding values - try library enum first, fall back to integers
    # Trust the library as source of truth when available
    try:
        M4A_AAC = cloud_speech.ExplicitDecodingConfig.AudioEncoding.M4A_AAC
        MP4_AAC = cloud_speech.ExplicitDecodingConfig.AudioEncoding.MP4_AAC
        MOV_AAC = cloud_speech.ExplicitDecodingConfig.AudioEncoding.MOV_AAC
    except AttributeError:
        # Fallback for older library versions without enum attributes
        # Values from Google Speech V2 API specification
        M4A_AAC = 11
        MP4_AAC = 10
        MOV_AAC = 12

    # Formats requiring ExplicitDecodingConfig
    # Maps file extension -> AudioEncoding value (enum or int)
    EXPLICIT_ENCODING_MAP = {
        'm4a': M4A_AAC,
        'mp4': MP4_AAC,
        'mov': MOV_AAC,
    }

    def __init__(self, project_id: str, model: str = "long", location: str = "us"):
        """
        Initialize V2 Speech client.

        Args:
            project_id: Google Cloud project ID
            model: Model to use (chirp_3, long, short)
            location: Google Cloud location (default: us)
                     V2 models require regional location, not 'global'
        """
        self.project_id = project_id
        self.model = model
        self.location = location
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

        logger.info(f"Initialized Speech V2 service: model={model}, location={location}, project={project_id}")

    def submit_job(self, gcs_uri: str, language_code: str = "en-US", audio_metadata: Optional[Dict] = None):
        """
        Submit a transcription job to Google Cloud WITHOUT waiting for completion.

        This is for job-based architecture where we return immediately with a job ID
        and check status later.

        Args:
            gcs_uri: Google Cloud Storage URI (gs://bucket/path/file.ext)
            language_code: Language code (default: en-US)
            audio_metadata: Audio file metadata (sample_rate, channels, etc.)

        Returns:
            operation: Google LongRunningOperation object
                      Use operation.operation.name to get job ID
                      Use operation.done() to check status later
        """
        try:
            # Build recognition config
            config = self._build_config(
                audio_encoding=gcs_uri.split('.')[-1],  # Extract extension
                language_code=language_code,
                audio_metadata=audio_metadata
            )

            # Create batch recognition request
            file_metadata = cloud_speech.BatchRecognizeFileMetadata(uri=gcs_uri)
            request = cloud_speech.BatchRecognizeRequest(
                recognizer=f"projects/{self.project_id}/locations/{self.location}/recognizers/_",
                config=config,
                files=[file_metadata],
                recognition_output_config=cloud_speech.RecognitionOutputConfig(
                    inline_response_config=cloud_speech.InlineOutputConfig()
                ),
            )

            # Submit batch recognition job
            # This returns IMMEDIATELY with an operation object
            # The actual transcription happens asynchronously in Google's queue
            logger.info(f"Submitting batch recognition job for: {gcs_uri}")
            logger.info(f"Model: {config.model}, Language: {config.language_codes}")
            operation = self.client.batch_recognize(request=request)

            # Extract job ID for logging
            job_id = operation.operation.name
            logger.info(f"Job submitted successfully: {job_id}")

            # Return the operation object (caller can extract job ID and store it)
            return operation

        except Exception as e:
            logger.error(f"Error submitting transcription job: {e}")
            raise

    def check_job_status(self, job_id: str) -> Dict:
        """
        Check the status of a transcription job by reconnecting to Google's operation.

        This is the core of our polling architecture - we can check status at any time
        by using the job_id (which is Google's operation name).

        Args:
            job_id: Google operation name (e.g., "projects/.../operations/123")

        Returns:
            Dict with status information:
            {
                "done": True/False,
                "status": "queued|processing|complete|failed",
                "transcript": "..." (if complete),
                "confidence": 0.95 (if complete),
                "words": [...] (if complete),
                "error": "..." (if failed),
                "metadata": {...} (if complete)
            }
        """
        try:
            # Reconnect to the operation using its name (job_id)
            # This is Google's way of letting us check on jobs we submitted earlier
            # The operation name is stable - we can use it hours or days later
            logger.info(f"Checking status for job: {job_id}")
            operation = self.client.get_operation(name=job_id)

            # Check if operation is done (non-blocking check)
            # This returns immediately - doesn't wait for completion
            is_done = operation.done

            if not is_done:
                # Job is still queued or processing
                logger.info(f"Job {job_id} is still in progress")
                return {
                    "done": False,
                    "status": "processing",  # Could be queued or actively processing
                    "transcript": None,
                    "confidence": None,
                    "words": None,
                    "error": None,
                    "metadata": None
                }

            # Job is done - check for errors first
            if operation.error.code != 0:
                # Operation completed with error
                error_message = f"Google error {operation.error.code}: {operation.error.message}"
                logger.error(f"Job {job_id} failed: {error_message}")
                return {
                    "done": True,
                    "status": "failed",
                    "transcript": None,
                    "confidence": None,
                    "words": None,
                    "error": error_message,
                    "metadata": None
                }

            # Job completed successfully - parse results
            # operation.response contains the BatchRecognizeResponse
            logger.info(f"Job {job_id} completed successfully, parsing results...")
            results = self._parse_results(operation.response)

            # Add done flag to results
            results["done"] = True

            # Map success field to status for consistency
            if results.get("success"):
                results["status"] = "complete"
            else:
                results["status"] = "failed"

            return results

        except Exception as e:
            logger.error(f"Error checking job status: {e}")
            return {
                "done": False,
                "status": "error",
                "transcript": None,
                "confidence": None,
                "words": None,
                "error": f"Error checking status: {str(e)}",
                "metadata": None
            }

    def transcribe(self, gcs_uri: str, language_code: str = "en-US", audio_metadata: Optional[Dict] = None) -> Dict:
        """
        Transcribe audio file from Cloud Storage using batch recognition.

        Args:
            gcs_uri: Google Cloud Storage URI (gs://bucket/path/file.ext)
            language_code: Language code (default: en-US)
            audio_metadata: Audio file metadata (sample_rate, channels, etc.)

        Returns:
            Dict with transcript, confidence, words, and metadata
        """
        try:
            # Extract file extension from URI for format-specific config
            file_extension = gcs_uri.split('.')[-1].lower() if '.' in gcs_uri else None

            # Configure recognition with actual audio metadata
            config = self._build_config(language_code, audio_encoding=file_extension, audio_metadata=audio_metadata)

            # Create recognition request
            file_metadata = cloud_speech.BatchRecognizeFileMetadata(uri=gcs_uri)

            request = cloud_speech.BatchRecognizeRequest(
                recognizer=f"projects/{self.project_id}/locations/{self.location}/recognizers/_",
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
            # Timeout based on model:
            # - Standard tier: typically 1-3 minutes, allow up to 30 min for safety
            # - Batch tier: up to 24 hours, but we'll timeout at 1 hour for sanity
            # User should use standard tier for immediate results
            timeout_seconds = 3600  # 1 hour
            logger.info(f"Polling with {timeout_seconds}s timeout (model={self.model})...")
            response = operation.result(timeout=timeout_seconds)

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

    def _build_config(self, language_code: str, audio_encoding: str = None, audio_metadata: Optional[Dict] = None) -> cloud_speech.RecognitionConfig:
        """
        Build recognition configuration with optimal settings.

        Args:
            language_code: Language for recognition
            audio_encoding: Audio file extension (e.g., 'm4a', 'mp3', 'wav').
                          Determines whether to use auto-detect or explicit decoding.
            audio_metadata: Actual audio file metadata (sample_rate, channels).
                          If provided, uses actual values instead of defaults.

        Returns:
            RecognitionConfig object
        """
        logger.info(f"Building config with model: {self.model}, encoding: {audio_encoding}")

        # Normalize encoding to lowercase for lookup
        encoding_lower = audio_encoding.lower() if audio_encoding else None

        # Determine decoding config based on format capabilities
        if encoding_lower in self.EXPLICIT_ENCODING_MAP:
            # Format requires explicit encoding configuration
            audio_encoding_value = self.EXPLICIT_ENCODING_MAP[encoding_lower]

            # ExplicitDecodingConfig REQUIRES sample_rate and channels
            # Omitting them causes protobuf to use 0, which is "out of range"
            # Use actual audio metadata (extracted via pydub in storage.py)
            if audio_metadata:
                sample_rate = audio_metadata.get('sample_rate', 16000)
                channels = audio_metadata.get('channels', 1)
                logger.info(f"Using actual audio metadata: {sample_rate}Hz, {channels} channel(s)")
            else:
                # This should not happen (we extract metadata in storage.py)
                # But provide fallback just in case
                sample_rate = 16000
                channels = 1
                logger.error("BUG: No audio metadata provided! Using fallback defaults.")

            decoding_config_kwargs = {
                'explicit_decoding_config': cloud_speech.ExplicitDecodingConfig(
                    encoding=audio_encoding_value,
                    sample_rate_hertz=sample_rate,
                    audio_channel_count=channels
                )
            }
            # Handle both enum objects (with .name) and integers (without)
            encoding_name = getattr(audio_encoding_value, 'name', audio_encoding_value)
            logger.info(f"ExplicitDecodingConfig: encoding={encoding_name}, sample_rate={sample_rate}Hz, channels={channels}")

        elif encoding_lower in self.AUTO_DETECT_FORMATS:
            # Format supported by auto-detect
            decoding_config_kwargs = {
                'auto_decoding_config': cloud_speech.AutoDetectDecodingConfig()
            }
            logger.info(f"Using AutoDetectDecodingConfig for {encoding_lower.upper()}")

        else:
            # Unknown format - try auto-detect with warning
            logger.warning(
                f"Unknown audio format '{audio_encoding}'. "
                f"Supported formats: {sorted(self.AUTO_DETECT_FORMATS | set(self.EXPLICIT_ENCODING_MAP.keys()))}. "
                f"Attempting auto-detection..."
            )
            decoding_config_kwargs = {
                'auto_decoding_config': cloud_speech.AutoDetectDecodingConfig()
            }

        # TODO: Fix phrase hints syntax for V2 API
        # V2 has different syntax than V1 for custom vocabulary
        # Temporarily disabled to get transcription working
        # phrase_hints = cloud_speech.SpeechAdaptation.AdaptationPhraseSet(
        #     phrases=[{"value": phrase, "boost": 15} for phrase in self.yoga_vocabulary]
        # )

        config = cloud_speech.RecognitionConfig(
            **decoding_config_kwargs,
            language_codes=[language_code],
            model=self.model,
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
            # Extract results from response
            results = []
            total_confidence = 0.0
            word_details = []

            # Iterate through results (keyed by GCS URI)
            for uri, result in response.results.items():
                # Check for errors FIRST (before looking at transcript)
                if hasattr(result, 'error') and result.error.code != 0:
                    logger.error(f"Google returned error for {uri}: {result.error}")
                    continue

                # Log metadata if present (shows billed duration)
                if hasattr(result, 'metadata'):
                    logger.info(f"Billed duration: {result.metadata.total_billed_duration}")

                # Parse transcript if present
                if hasattr(result, 'transcript') and result.transcript:
                    if hasattr(result.transcript, 'results'):
                        segment_count = len(result.transcript.results)

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

                        logger.info(f"Processed {segment_count} segments, {len(word_details)} words")
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


def get_transcription_service_v2(project_id: str, model: str = "long", location: str = "us") -> GoogleSpeechV2Service:
    """
    Factory function to create V2 transcription service.

    Args:
        project_id: Google Cloud project ID
        model: Model to use (chirp_3, long, short)
        location: Google Cloud location (default: us)
                 V2 models require regional location, not 'global'

    Returns:
        GoogleSpeechV2Service instance
    """
    return GoogleSpeechV2Service(project_id=project_id, model=model, location=location)
