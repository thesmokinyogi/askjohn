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

V2 Regional Architecture:
- Chirp models REQUIRE regional endpoints (NOT global)
- Client endpoint must match recognizer resource location
- Different models support different regions
"""

from google.cloud.speech_v2 import SpeechClient
from google.cloud.speech_v2.types import cloud_speech
from google.cloud.location import locations_pb2
from google.api_core.client_options import ClientOptions
from google.api_core import operations_v1
from google.protobuf.json_format import MessageToDict
from typing import Dict, Optional, Set
import logging
import time

logger = logging.getLogger(__name__)

# ============================================================================
# MODULE-LEVEL FEATURE CACHE
# ============================================================================
# Pre-warmed on service startup, lives for process lifetime
# Key: (model, language) -> Value: set of supported feature keys
_FEATURE_CACHE: Dict[tuple, Set[str]] = {}
_CACHE_LOADED = False

# ============================================================================
# FEATURE MAPPING TABLE
# ============================================================================
# Maps RecognitionFeatures protobuf fields → Locations API feature keys
# Source: Gemini analysis of Google Speech V2 documentation (2025-11-12)
# Reference: MDs/Speech-to-Text Model Feature Support.md
FEATURE_MAPPING = {
    'profanity_filter': 'profanity_filter',
    'enable_word_time_offsets': 'word_level_timestamps',
    'enable_word_confidence': 'word_level_confidence',
    'enable_automatic_punctuation': 'automatic_punctuation',
    'enable_spoken_punctuation': 'spoken_punctuation',
    'enable_spoken_emojis': 'spoken_emojis',
    'diarization_config': 'speaker_diarization',
    # Note: max_alternatives is a standard config parameter, not a queryable feature
    # Note: multi_channel_mode is a parameter, not a feature flag
}

# ============================================================================
# MINIMAL STATIC FALLBACK
# ============================================================================
# Emergency fallback if Locations API is unavailable
# ONLY includes combinations that have explicitly failed in production
# Format: (model, feature_key)
KNOWN_UNSUPPORTED = {
    ('chirp', 'word_level_confidence'),
    ('chirp_2', 'word_level_confidence'),
}


# ============================================================================
# FEATURE DETECTION FUNCTIONS
# ============================================================================

def initialize_feature_cache(project_id: str, location: str, models: list[str], languages: list[str] = None):
    """
    Pre-warm feature cache on service startup.

    Queries Locations API once for configured models and languages.
    Retries on failure, falls back to minimal static data if unavailable.

    Args:
        project_id: Google Cloud project ID
        location: Regional location (e.g., 'us-central1')
        models: List of models to pre-warm (e.g., ['chirp', 'latest_long'])
        languages: List of languages (defaults to ['en-US'])

    Returns:
        bool: True if cache loaded successfully, False if using fallback
    """
    global _FEATURE_CACHE, _CACHE_LOADED

    if languages is None:
        languages = ['en-US']

    # Retry with exponential backoff
    retry_delays = [1, 2, 4]  # Total: ~7 seconds

    for attempt, delay in enumerate(retry_delays + [None]):
        try:
            # Query Locations API for each model/language combination
            for model in models:
                for language in languages:
                    features = _query_locations_api(project_id, location, model, language)
                    _FEATURE_CACHE[(model, language)] = features
                    logger.info(f"✓ Loaded features for {model}/{language}: {len(features)} supported")

            _CACHE_LOADED = True
            logger.info(f"Feature cache initialized: {len(_FEATURE_CACHE)} model/language combinations")
            return True

        except Exception as e:
            if delay is not None:
                logger.warning(
                    f"Locations API unavailable (attempt {attempt + 1}/{len(retry_delays)}): {e}. "
                    f"Retrying in {delay}s..."
                )
                time.sleep(delay)
            else:
                # All retries exhausted
                logger.error(
                    f"⚠️  DEGRADED: Locations API unavailable after {len(retry_delays)} retries. "
                    f"Using minimal static fallback. Feature detection may be incorrect. "
                    f"Error: {e}"
                )
                _CACHE_LOADED = False
                return False

    return False


def _query_locations_api(project_id: str, location: str, model: str, language: str) -> Set[str]:
    """
    Query Locations API to discover supported features for a model/language.

    Navigates the metadata hierarchy:
    Location → languages[language] → models[model] → modelFeatures

    Args:
        project_id: Google Cloud project ID
        location: Regional location (e.g., 'us-central1')
        model: Model identifier (e.g., 'chirp', 'latest_long')
        language: BCP-47 language code (e.g., 'en-US')

    Returns:
        Set of feature keys supported by this model/language combination

    Raises:
        Exception: If API call fails or metadata structure unexpected
    """
    # Create client with regional endpoint
    api_endpoint = f"{location}-speech.googleapis.com"
    client = SpeechClient(
        client_options=ClientOptions(api_endpoint=api_endpoint)
    )

    # Query locations for this project
    request = locations_pb2.ListLocationsRequest(
        name=f"projects/{project_id}"
    )

    response = client.list_locations(request=request)

    # Find our target location
    for loc in response.locations:
        if loc.location_id == location:
            # Parse metadata structure
            # Structure: location.metadata → languages (map) → models (map) → modelFeatures
            # metadata is a protobuf Struct - convert to dict for easier access
            if not loc.metadata:
                raise ValueError(f"No metadata available for location {location}")

            metadata_dict = MessageToDict(loc.metadata, preserving_proto_field_name=True)

            logger.debug(f"Location {location} metadata keys: {list(metadata_dict.keys())}")

            # Navigate to language
            languages_map = metadata_dict.get('languages', {})
            language_metadata = languages_map.get(language)

            if not language_metadata:
                raise ValueError(f"Language {language} not found in location {location}")

            # Navigate to model
            models_map = language_metadata.get('models', {})
            model_metadata = models_map.get(model)

            if not model_metadata:
                raise ValueError(f"Model {model} not found for language {language} in location {location}")

            # Extract features
            model_features = model_metadata.get('modelFeatures', {})
            feature_list = model_features.get('modelFeature', [])

            # Extract feature names (ignore releaseState for now)
            supported_features = set()
            for feature_obj in feature_list:
                if hasattr(feature_obj, 'feature'):
                    supported_features.add(feature_obj.feature)
                elif isinstance(feature_obj, dict):
                    supported_features.add(feature_obj.get('feature'))

            logger.debug(f"Discovered features for {model}/{language}: {supported_features}")
            return supported_features

    raise ValueError(f"Location {location} not found in project {project_id}")


def get_supported_features(model: str, language: str = 'en-US') -> Set[str]:
    """
    Get supported features for a model/language combination.

    Fast lookup from pre-warmed cache. Falls back to static data if cache not loaded.

    Args:
        model: Model identifier (e.g., 'chirp', 'latest_long')
        language: BCP-47 language code (defaults to 'en-US')

    Returns:
        Set of feature keys supported by this model/language
    """
    global _FEATURE_CACHE, _CACHE_LOADED

    # Check cache first (fast path)
    cache_key = (model, language)
    if cache_key in _FEATURE_CACHE:
        return _FEATURE_CACHE[cache_key]

    # Cache not loaded or model not in cache
    if not _CACHE_LOADED:
        logger.warning(
            f"Feature cache not loaded. Using minimal fallback for {model}/{language}. "
            f"Some features may be incorrectly disabled."
        )
        return _get_fallback_features(model)

    # Model not in cache (shouldn't happen with pre-warming, but handle gracefully)
    logger.error(
        f"Unexpected cache miss for {model}/{language}. "
        f"Model may not be configured for pre-warming. Using fallback."
    )
    return _get_fallback_features(model)


def _get_fallback_features(model: str) -> Set[str]:
    """
    Emergency fallback when Locations API unavailable.

    Returns safe minimal feature set: only features known to work.
    Blocks features that have explicitly failed in production.

    Args:
        model: Model identifier

    Returns:
        Set of feature keys (conservative - only known-safe features)
    """
    # Start with universally safe features (work on all models)
    safe_features = {
        'automatic_punctuation',
        'word_level_timestamps',
    }

    # Remove features known to be unsupported for this model
    unsupported = {feature for (m, feature) in KNOWN_UNSUPPORTED if m == model}
    return safe_features - unsupported


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

    # Model-specific region requirements
    # Based on Google Cloud Speech V2 documentation (2025)
    # Source: https://docs.cloud.google.com/speech-to-text/v2/docs/chirp_2-model
    MODEL_REGION_CONFIG = {
        'chirp': {
            'requires_regional': True,
            'supported_regions': ['us-central1', 'europe-west4', 'asia-southeast1'],
            'default_region': 'us-central1',
            'description': 'Chirp (Universal Speech Model) - requires specific regional endpoints'
        },
        'long': {
            'requires_regional': False,  # Can use global, but regional recommended for data residency
            'supported_regions': ['us-central1', 'us-west1', 'us-east1', 'europe-west1', 'asia-southeast1'],
            'default_region': 'us-central1',
            'description': 'Long-form transcription model - flexible regional support'
        },
        'short': {
            'requires_regional': False,
            'supported_regions': ['us-central1', 'us-west1', 'us-east1', 'europe-west1', 'asia-southeast1'],
            'default_region': 'us-central1',
            'description': 'Short-form transcription model - flexible regional support'
        }
    }

    # Geographic region mapping for proximity-based fallback
    # Used when requested region doesn't support the model
    REGION_PROXIMITY_MAP = {
        # US regions
        'us-west1': ['us-central1', 'us-west2', 'us-east1'],
        'us-west2': ['us-central1', 'us-west1', 'us-east1'],
        'us-west3': ['us-central1', 'us-west1', 'us-east1'],
        'us-west4': ['us-central1', 'us-west1', 'us-east1'],
        'us-east1': ['us-central1', 'us-east4', 'us-west1'],
        'us-east4': ['us-east1', 'us-central1', 'us-west1'],
        'us-east5': ['us-east1', 'us-central1', 'us-west1'],
        'us-central1': ['us-central1'],  # Already optimal
        # Europe regions
        'europe-west1': ['europe-west4', 'europe-west2', 'europe-west3'],
        'europe-west2': ['europe-west1', 'europe-west4', 'europe-west3'],
        'europe-west3': ['europe-west1', 'europe-west4', 'europe-west2'],
        'europe-west4': ['europe-west4'],  # Already optimal for Chirp
        # Asia regions
        'asia-southeast1': ['asia-southeast1'],  # Already optimal for Chirp
        'asia-northeast1': ['asia-southeast1', 'asia-south1'],
        'asia-south1': ['asia-southeast1', 'asia-northeast1'],
    }

    def __init__(self, project_id: str, model: str = "long", location: str = "us"):
        """
        Initialize V2 Speech client with model-aware regional configuration.

        Args:
            project_id: Google Cloud project ID
            model: Model to use (chirp, long, short)
            location: Requested Google Cloud location
                     Will be validated and mapped to supported region if needed

        The client is initialized with a regional endpoint that matches the
        final selected location, as required by V2 architecture for Chirp models.
        """
        self.project_id = project_id
        self.model = model

        # Select and validate location based on model requirements
        self.location = self._select_optimal_location(location, model)

        # Initialize client with REGIONAL endpoint
        # This is CRITICAL for Chirp models - they cannot use global endpoint
        # The endpoint MUST match the location used in the recognizer path
        api_endpoint = f"{self.location}-speech.googleapis.com"

        logger.info(f"Initializing Speech V2 client: model={model}, location={self.location}, endpoint={api_endpoint}")

        self.client = SpeechClient(
            client_options=ClientOptions(
                api_endpoint=api_endpoint
            )
        )

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

        logger.info(f"Initialized Speech V2 service: model={model}, location={self.location}, project={project_id}")

    def _select_optimal_location(self, requested_location: str, model: str) -> str:
        """
        Select the optimal location for the given model based on availability.

        Strategy:
        1. If requested location supports model → use it
        2. Otherwise, map to nearest supported region
        3. Fallback to model's default region

        Args:
            requested_location: Location requested by caller (e.g., from bucket region)
            model: Model to use (chirp, long, short)

        Returns:
            Validated location that supports the model
        """
        # Get model configuration
        model_config = self.MODEL_REGION_CONFIG.get(model, {})

        if not model_config:
            logger.warning(f"Unknown model '{model}', using default location 'us-central1'")
            return 'us-central1'

        supported_regions = model_config.get('supported_regions', [])
        default_region = model_config.get('default_region', 'us-central1')

        # If requested location is already supported, use it
        if requested_location in supported_regions:
            logger.info(f"✓ Using requested location '{requested_location}' for model '{model}'")
            return requested_location

        # Map to nearest supported region
        nearest = self._map_to_nearest_region(requested_location, supported_regions)
        if nearest:
            logger.info(f"Mapped location '{requested_location}' → '{nearest}' for model '{model}'")
            return nearest

        # Fallback to model's default region
        logger.warning(
            f"Location '{requested_location}' not supported for model '{model}', "
            f"using default '{default_region}'"
        )
        return default_region

    def _map_to_nearest_region(self, requested: str, available: list) -> Optional[str]:
        """
        Map a requested region to the nearest available region.

        Uses geographic proximity mapping to find the nearest supported region.

        Args:
            requested: Requested region (e.g., 'us-west1')
            available: List of available regions for the model

        Returns:
            Nearest available region, or None if no mapping found
        """
        # Check if we have a proximity mapping for this region
        nearby_regions = self.REGION_PROXIMITY_MAP.get(requested, [])

        # Find first nearby region that's available
        for region in nearby_regions:
            if region in available:
                return region

        # No proximity mapping found, try to infer from region prefix
        # e.g., "us-west1" → look for any "us-" region
        if '-' in requested:
            region_prefix = requested.split('-')[0]  # "us", "europe", "asia"
            for region in available:
                if region.startswith(region_prefix):
                    return region

        return None

    def submit_job(self, gcs_uri: str, language_code: str = "en-US", audio_metadata: Optional[Dict] = None, output_bucket: str = None):
        """
        Submit a transcription job to Google Cloud WITHOUT waiting for completion.

        This is for job-based architecture where we return immediately with a job ID
        and check status later.

        Args:
            gcs_uri: Google Cloud Storage URI (gs://bucket/path/file.ext)
            language_code: Language code (default: en-US)
            audio_metadata: Audio file metadata (sample_rate, channels, etc.)
            output_bucket: GCS bucket for results (default: same as audio bucket)

        Returns:
            operation: Google LongRunningOperation object
                      Use operation.operation.name to get job ID
                      Use operation.done() to check status later
        """
        try:
            # Extract bucket from gcs_uri if output_bucket not specified
            if not output_bucket:
                # Parse gs://bucket-name/path/file.ext
                output_bucket = gcs_uri.split('/')[2]

            # Build recognition config
            config = self._build_config(
                audio_encoding=gcs_uri.split('.')[-1],  # Extract extension
                language_code=language_code,
                audio_metadata=audio_metadata
            )

            # Create batch recognition request with GCS output
            # Following official pattern from python-docs-samples
            file_metadata = cloud_speech.BatchRecognizeFileMetadata(uri=gcs_uri)
            request = cloud_speech.BatchRecognizeRequest(
                recognizer=f"projects/{self.project_id}/locations/{self.location}/recognizers/_",
                config=config,
                files=[file_metadata],
                recognition_output_config=cloud_speech.RecognitionOutputConfig(
                    gcs_output_config=cloud_speech.GcsOutputConfig(
                        uri=f"gs://{output_bucket}/transcripts/"
                    )
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

    def check_job_status(self, job_id: str, gcs_uri: str = None) -> Dict:
        """
        Check the status of a transcription job by reconnecting to Google's operation.

        This is the core of our polling architecture - we can check status at any time
        by using the job_id (which is Google's operation name).

        Args:
            job_id: Google operation name (e.g., "projects/.../operations/123")
            gcs_uri: Original audio GCS URI (needed to look up results)

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

            # Use the operations client to check status
            # V2 requires using the operations_v1 client, not a method on SpeechClient
            operations_client = operations_v1.OperationsClient(self.client._transport.grpc_channel)
            operation = operations_client.get_operation(job_id)

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
            if hasattr(operation, 'error') and operation.error and operation.error.code != 0:
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

            # Job completed successfully - fetch results from GCS
            # Following official Google pattern from python-docs-samples
            logger.info(f"Job {job_id} completed successfully, fetching results from GCS...")

            if not gcs_uri:
                logger.error(f"Job {job_id} missing gcs_uri - cannot look up results")
                return {
                    "done": True,
                    "status": "failed",
                    "transcript": None,
                    "confidence": None,
                    "words": None,
                    "error": "Missing GCS URI - cannot retrieve results",
                    "metadata": None
                }

            # Unpack response to get BatchRecognizeResponse
            # Use the official helper from google-api-core (same as operation.result() uses internally)
            from google.api_core import protobuf_helpers

            batch_response = protobuf_helpers.from_any_pb(
                cloud_speech.BatchRecognizeResponse,
                operation.response
            )

            # Get GCS result URI from response
            # Results are keyed by the original audio URI
            if gcs_uri not in batch_response.results:
                logger.error(f"No results found for {gcs_uri}")
                return {
                    "done": True,
                    "status": "failed",
                    "transcript": None,
                    "confidence": None,
                    "words": None,
                    "error": f"No results found for audio file",
                    "metadata": None
                }

            file_result = batch_response.results[gcs_uri]
            result_gcs_uri = file_result.uri
            logger.info(f"Fetching results from {result_gcs_uri}")

            # Download results from GCS
            # Parse bucket and object path from gs://bucket/path/to/results.json
            import re
            from google.cloud import storage

            match = re.match(r"gs://([^/]+)/(.*)", result_gcs_uri)
            if not match:
                logger.error(f"Invalid GCS URI format: {result_gcs_uri}")
                return {
                    "done": True,
                    "status": "failed",
                    "transcript": None,
                    "confidence": None,
                    "words": None,
                    "error": "Invalid result URI format",
                    "metadata": None
                }

            output_bucket, output_object = match.group(1, 2)

            # Fetch results from GCS
            storage_client = storage.Client()
            bucket = storage_client.bucket(output_bucket)
            blob = bucket.blob(output_object)
            results_bytes = blob.download_as_bytes()

            # Parse JSON results
            # Following official pattern: BatchRecognizeResults.from_json()
            batch_recognize_results = cloud_speech.BatchRecognizeResults.from_json(
                results_bytes,
                ignore_unknown_fields=True
            )

            logger.info(f"Downloaded and parsed {len(batch_recognize_results.results)} result segments")

            # Extract transcript from results
            results = self._parse_batch_results(batch_recognize_results)

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

        # ===================================================================
        # DYNAMIC FEATURE DETECTION
        # ===================================================================
        # Query supported features for this model/language combination
        # Only enable features that are actually supported to prevent API errors
        supported_features = get_supported_features(self.model, language_code)

        # Build feature configuration dynamically
        feature_config = {}

        # Map desired features to API keys and check support
        # Automatic punctuation
        if 'automatic_punctuation' in supported_features:
            feature_config['enable_automatic_punctuation'] = True
        else:
            logger.info(f"Skipping automatic_punctuation (unsupported by {self.model}/{language_code})")

        # Word timestamps
        if 'word_level_timestamps' in supported_features:
            feature_config['enable_word_time_offsets'] = True
        else:
            logger.info(f"Skipping word_time_offsets (unsupported by {self.model}/{language_code})")

        # Word confidence scores
        if 'word_level_confidence' in supported_features:
            feature_config['enable_word_confidence'] = True
        else:
            logger.info(f"Skipping word_confidence (unsupported by {self.model}/{language_code})")

        # Log enabled features for debugging
        enabled_features = [k for k, v in feature_config.items() if v]
        logger.info(f"Enabled features for {self.model}/{language_code}: {enabled_features}")

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
            features=cloud_speech.RecognitionFeatures(**feature_config),
            # TODO: Re-enable after fixing phrase hints syntax
            # adaptation=cloud_speech.SpeechAdaptation(
            #     phrase_sets=[phrase_hints]
            # ),
        )

        return config

    def _parse_batch_results(self, batch_results: cloud_speech.BatchRecognizeResults) -> Dict:
        """
        Parse BatchRecognizeResults from GCS JSON file.

        This is simpler than parsing the operation response because the JSON
        is already deserialized into the proper structure.

        Args:
            batch_results: BatchRecognizeResults from GCS (deserialized JSON)

        Returns:
            Structured dict with transcript and metadata
        """
        try:
            results = []
            total_confidence = 0.0
            word_details = []

            # Iterate through results - this is already properly structured JSON
            for result in batch_results.results:
                if result.alternatives:
                    alternative = result.alternatives[0]  # Best alternative

                    # Append transcript
                    results.append(alternative.transcript)
                    total_confidence += alternative.confidence

                    # Extract word-level details if available
                    if hasattr(alternative, 'words') and alternative.words:
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

            logger.info(f"Parsed {len(results)} segments, {len(word_details)} words")

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
            logger.error(f"Error parsing GCS results: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Result parsing error: {str(e)}",
                "transcript": "",
                "confidence": 0.0,
                "words": [],
                "metadata": {"error_type": "parsing_error"}
            }

    def _parse_results(self, response) -> Dict:
        """
        Parse batch recognition response into structured format.

        Args:
            response: BatchRecognizeResponse from Google (from operation.response)

        Returns:
            Structured dict with transcript and metadata
        """
        try:
            # Extract results from response
            results = []
            total_confidence = 0.0
            word_details = []

            # DEBUG: Log response structure
            logger.info(f"====== RESPONSE DEBUG ======")
            logger.info(f"Response type: {type(response)}")
            logger.info(f"Response dir: {[attr for attr in dir(response) if not attr.startswith('_')][:20]}")
            logger.info(f"Has results: {hasattr(response, 'results')}")

            # V2 API: response.results is a map/dict-like object
            # Access it directly if it's a dict, or iterate if it's a repeated field
            if hasattr(response, 'results'):
                results_map = response.results

                # DEBUG: Detailed logging to understand structure
                logger.info(f"====== PARSING DEBUG ======")
                logger.info(f"Response type: {type(response)}")
                logger.info(f"Results type: {type(results_map)}")
                logger.info(f"Results has 'items': {hasattr(results_map, 'items')}")
                logger.info(f"Results has '__iter__': {hasattr(results_map, '__iter__')}")
                logger.info(f"Results is string: {isinstance(results_map, str)}")

                # Try to log first few chars if it's string-like
                try:
                    logger.info(f"Results repr: {repr(results_map)[:500]}")
                except:
                    pass

                # Handle different response structures
                # V2 with inline_response_config returns a dict/map
                if hasattr(results_map, 'items'):
                    # Dict-like access
                    items = list(results_map.items())
                    logger.info(f"Processing {len(items)} result entries")
                elif hasattr(results_map, '__iter__'):
                    # List-like or repeated field
                    items = [(i, item) for i, item in enumerate(results_map)]
                    logger.info(f"Processing {len(items)} result entries (list)")
                else:
                    # Single result object
                    items = [(None, results_map)]
                    logger.info("Processing single result entry")

                for uri_or_idx, result in items:
                    # Check for errors FIRST (before looking at transcript)
                    if hasattr(result, 'error') and result.error.code != 0:
                        logger.error(f"Google returned error for {uri_or_idx}: {result.error}")
                        continue

                    # Log metadata if present (shows billed duration)
                    if hasattr(result, 'metadata'):
                        logger.info(f"Billed duration: {result.metadata.total_billed_duration}")

                    # V2 API: Parse inline_result (used with inline_response_config)
                    # Structure: result.inline_result.transcript.results[]
                    if hasattr(result, 'inline_result') and result.inline_result:
                        inline_result = result.inline_result
                        if hasattr(inline_result, 'transcript') and inline_result.transcript:
                            transcript_results = inline_result.transcript.results
                            segment_count = len(transcript_results) if transcript_results else 0
                            logger.info(f"Found {segment_count} transcript segments")

                            for batch_result in transcript_results:
                                if batch_result.alternatives:
                                    alternative = batch_result.alternatives[0]

                                    results.append(alternative.transcript)
                                    total_confidence += alternative.confidence

                                    # Extract word-level details
                                    if hasattr(alternative, 'words'):
                                        for word_info in alternative.words:
                                            word_details.append({
                                                "word": word_info.word,
                                                "start_time": word_info.start_offset.total_seconds(),
                                                "end_time": word_info.end_offset.total_seconds(),
                                                "confidence": word_info.confidence if hasattr(word_info, 'confidence') else 0.0
                                            })

                            logger.info(f"Processed {segment_count} segments, {len(word_details)} words")
                        else:
                            logger.warning(f"inline_result has no transcript for {uri_or_idx}")
                    else:
                        logger.warning(f"No inline_result found for {uri_or_idx}")

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
