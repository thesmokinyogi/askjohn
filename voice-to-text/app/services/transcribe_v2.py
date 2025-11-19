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
from google.protobuf.json_format import MessageToDict, Parse
from google.protobuf import struct_pb2
from google.auth import default
from google.auth.transport.requests import Request as AuthRequest
from google.auth import exceptions as auth_exceptions
import requests
import json
from typing import Dict, Optional, Set
import logging
import time

logger = logging.getLogger(__name__)

# ============================================================================
# REST API HELPER FOR METADATA DISCOVERY
# ============================================================================

def _discover_location_metadata_via_rest_api(project_id: str, location: str) -> Optional[dict]:
    """
    Query a single location's metadata via REST API (bypasses SDK limitations).
    
    This is the working approach discovered through empirical testing.
    The Python SDK doesn't expose LocationsMetadata protobuf descriptor,
    so we use REST API directly to get JSON response.
    
    Args:
        project_id: Google Cloud project ID
        location: Location ID (e.g., 'us-west1')
        
    Returns:
        dict with 'metadata' key containing location metadata, or None if failed
    """
    try:
        # Get credentials with explicit scopes (required for REST API)
        try:
            credentials, _ = default(scopes=['https://www.googleapis.com/auth/cloud-platform'])
            auth_request = AuthRequest()
            credentials.refresh(auth_request)
            token = credentials.token
            
            if not token:
                logger.error(f"Failed to get auth token for {location}")
                return None
                
        except (auth_exceptions.DefaultCredentialsError, auth_exceptions.RefreshError) as e:
            logger.error(f"Authentication failed for {location}: {e}")
            return None
        
        # Build REST API URL
        rest_url = f"https://{location}-speech.googleapis.com/v2/projects/{project_id}/locations/{location}"
        
        # Make GET request
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        response = requests.get(rest_url, headers=headers, timeout=10)
        
        # 404 is expected for regions that don't support Speech V2
        # This is normal behavior with the Probe List Strategy
        if response.status_code == 404:
            logger.debug(f"Location {location} does not support Speech V2 (404 - expected)")
            return None
        
        # Raise for other HTTP errors
        response.raise_for_status()
        
        # Parse JSON response
        try:
            return response.json()
        except json.JSONDecodeError as e:
            logger.warning(f"Invalid JSON response from {location}: {e}")
            return None
        
    except requests.exceptions.RequestException as e:
        # Handle other request exceptions (network errors, timeouts, etc.)
        logger.debug(f"REST API request failed for {location}: {e}")
        return None
    except Exception as e:
        logger.debug(f"Unexpected error querying {location} via REST API: {e}")
        return None


# ============================================================================
# MODULE-LEVEL METADATA CACHE
# ============================================================================
# Comprehensive Speech V2 metadata discovered from Locations API at startup
# This is the single source of truth for all regional/model configuration

# Available Speech V2 locations (regions that support the API)
_AVAILABLE_LOCATIONS: Set[str] = set()

# Available models per location/language
# Key: (location, language) -> Value: set of model IDs
_AVAILABLE_MODELS: Dict[tuple, Set[str]] = {}

# Supported features per model/language/location
# Key: (location, language, model) -> Value: set of feature keys
_FEATURE_CACHE: Dict[tuple, Set[str]] = {}

# Cache loaded flag
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
# METADATA DISCOVERY FUNCTIONS
# ============================================================================

def discover_speech_metadata(project_id: str, languages: list[str] = None) -> dict:
    """
    Query Locations API to discover ALL available Speech V2 metadata via REST API.

    This is the single source of truth for Speech V2 configuration.
    Replaces all hardcoded lists of regions, models, and features.
    
    Uses REST API directly because Python SDK doesn't expose LocationsMetadata protobuf.

    Args:
        project_id: Google Cloud project ID
        languages: Languages to query (defaults to ['en-US'])

    Returns:
        dict with keys:
            - 'available_locations': Set of location IDs that support Speech V2
            - 'models_by_location': Dict[(location, language)] -> Set[model_ids]
            - 'features_by_model': Dict[(location, language, model)] -> Set[feature_keys]
            - 'success': bool indicating if discovery succeeded
    """
    if languages is None:
        languages = ['en-US']

    logger.info("Discovering Speech V2 metadata via REST API...")

    # PROBE LIST STRATEGY (Recommended by Google Cloud Architecture)
    # There is no API endpoint that returns all Speech V2 locations programmatically.
    # The SDK list_locations() only returns locations where the project has resources.
    # Therefore, we maintain a canonical list of Google Cloud regions and probe each one
    # to discover which support Speech V2 dynamically.
    #
    # This list is based on documented GCP regions and should be updated when Google
    # announces new regions. The REST API metadata endpoint validates which regions
    # actually support Speech V2 at runtime.
    #
    # Reference: Google Cloud Architecture Pattern - "Probe List Strategy"
    PROBE_REGION_LIST = [
        # Multi-region endpoints
        'us', 'eu',  # Note: 'global' endpoint exists but uses different URL pattern
        # US regions
        'us-central1', 'us-east1', 'us-east4', 'us-west1', 'us-west2', 'us-west3', 'us-west4',
        # Europe regions
        'europe-west1', 'europe-west2', 'europe-west3', 'europe-west4', 'europe-west6',
        # Asia regions
        'asia-east1', 'asia-east2', 'asia-northeast1', 'asia-northeast2', 'asia-south1', 
        'asia-southeast1', 'asia-southeast2',
        # Other regions
        'australia-southeast1', 'northamerica-northeast1', 'southamerica-east1'
    ]

    available_locations = set()
    models_by_location = {}
    features_by_model = {}
    successful_locations = 0

    # Probe each region to discover which support Speech V2
    for location in PROBE_REGION_LIST:
        # Query this location via REST API
        data = _discover_location_metadata_via_rest_api(project_id, location)
        
        if not data or 'metadata' not in data:
            logger.debug(f"No metadata for location {location}, skipping")
            continue

        metadata = data['metadata']
        
        # Verify structure: metadata['languages']['models'][lang_code]
        if 'languages' not in metadata:
            logger.debug(f"No 'languages' in metadata for {location}, skipping")
            continue

        languages_obj = metadata['languages']
        
        if 'models' not in languages_obj:
            logger.debug(f"No 'models' in languages for {location}, skipping")
            continue

        models_by_lang = languages_obj['models']
        available_locations.add(location)
        successful_locations += 1

        # Extract models and features for each requested language
        for language in languages:
            if language not in models_by_lang:
                logger.debug(f"Language {language} not available in {location}")
                continue

            lang_data = models_by_lang[language]
            
            # Structure: lang_data['modelFeatures'][model_id]['modelFeature']
            if 'modelFeatures' not in lang_data:
                logger.debug(f"No 'modelFeatures' for {language} in {location}")
                continue

            model_features_container = lang_data['modelFeatures']
            
            if not isinstance(model_features_container, dict):
                logger.debug(f"modelFeatures is not a dict for {language} in {location}")
                continue

            # Track which models are available
            model_ids = list(model_features_container.keys())
            cache_key = (location, language)
            models_by_location[cache_key] = set(model_ids)

            # Extract features for each model
            for model_id, model_data in model_features_container.items():
                if not isinstance(model_data, dict):
                    continue
                    
                # Get feature list: model_data['modelFeature']
                feature_list = model_data.get('modelFeature', [])
                
                if not isinstance(feature_list, list):
                    continue

                # Extract feature names
                # Normalize feature names from API to our internal format
                # API returns "word_timestamps" but we use "word_level_timestamps"
                FEATURE_NAME_NORMALIZATION = {
                    'word_timestamps': 'word_level_timestamps',
                    'word_confidence': 'word_level_confidence',
                }
                
                supported_features = set()
                for feature_obj in feature_list:
                    if isinstance(feature_obj, dict):
                        feature_name = feature_obj.get('feature')
                        if feature_name:
                            # Normalize to our internal format
                            normalized = FEATURE_NAME_NORMALIZATION.get(feature_name, feature_name)
                            supported_features.add(normalized)

                # Store in features cache
                feature_key = (location, language, model_id)
                features_by_model[feature_key] = supported_features

                logger.debug(
                    f"  {location}/{language}/{model_id}: "
                    f"{len(supported_features)} features"
                )

    logger.info(
        f"✓ Discovered metadata: {successful_locations}/{len(PROBE_REGION_LIST)} locations probed, "
        f"{len(available_locations)} locations support Speech V2, "
        f"{len(models_by_location)} location/language combinations, "
        f"{len(features_by_model)} model/feature sets"
    )

    return {
        'available_locations': available_locations,
        'models_by_location': models_by_location,
        'features_by_model': features_by_model,
        'success': successful_locations > 0
    }


def initialize_metadata_cache(project_id: str, languages: list[str] = None) -> bool:
    """
    Pre-warm comprehensive metadata cache on service startup.

    Replaces the old initialize_feature_cache with a comprehensive discovery
    that populates ALL metadata caches from a single Locations API query.

    Args:
        project_id: Google Cloud project ID
        languages: Languages to discover (defaults to ['en-US'])

    Returns:
        bool: True if cache loaded successfully, False if using fallback
    """
    global _AVAILABLE_LOCATIONS, _AVAILABLE_MODELS, _FEATURE_CACHE, _CACHE_LOADED

    if languages is None:
        languages = ['en-US']

    # Retry with exponential backoff
    retry_delays = [1, 2, 4]  # Total: ~7 seconds

    for attempt, delay in enumerate(retry_delays + [None]):
        try:
            # Discover all metadata in one API call
            metadata = discover_speech_metadata(project_id, languages)

            # Validate discovery succeeded
            if not metadata.get('success', False):
                raise ValueError("Metadata discovery returned success=False")

            # Verify we got some data
            if not metadata.get('available_locations'):
                raise ValueError("No locations discovered")

            # Populate module-level caches
            _AVAILABLE_LOCATIONS = metadata['available_locations']
            _AVAILABLE_MODELS = metadata['models_by_location']
            _FEATURE_CACHE = metadata['features_by_model']
            _CACHE_LOADED = True

            # Log summary
            logger.info(f"✓ Metadata cache initialized successfully")
            logger.info(f"  Available locations: {sorted(_AVAILABLE_LOCATIONS)}")

            # Log available models per language
            for language in languages:
                # Find all locations that have this language
                models_for_lang = set()
                for (loc, lang), models in _AVAILABLE_MODELS.items():
                    if lang == language:
                        models_for_lang.update(models)

                if models_for_lang:
                    logger.info(f"  Available models for {language}: {sorted(models_for_lang)}")

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
                    f"Using minimal static fallback. Error: {e}"
                )
                logger.error(
                    "⚠️  Impact: Dynamic metadata discovery disabled. "
                    "Using hardcoded fallback data. Some configurations may fail at runtime."
                )
                _CACHE_LOADED = False
                return False

    return False


# ============================================================================
# METADATA ACCESSOR FUNCTIONS
# ============================================================================

def get_available_locations() -> Set[str]:
    """
    Get all Speech V2 locations discovered from the API.

    Returns:
        Set of location IDs (e.g., {'us-central1', 'europe-west1', ...})
    """
    return _AVAILABLE_LOCATIONS.copy() if _AVAILABLE_LOCATIONS else set()


def get_available_models(location: str, language: str = 'en-US') -> Set[str]:
    """
    Get all models available for a specific location/language.

    Args:
        location: Location ID (e.g., 'us-central1')
        language: BCP-47 language code (defaults to 'en-US')

    Returns:
        Set of model IDs available for this location/language
    """
    cache_key = (location, language)
    return _AVAILABLE_MODELS.get(cache_key, set()).copy()


def _choose_default_region(locations: list[str]) -> str:
    """
    Choose default region with preference for us-central1.
    
    Strategy:
    1. Prefer us-central1 if available
    2. Prefer us-* regions if available (but not multi-region 'us')
    3. Otherwise first in sorted list
    
    Args:
        locations: List of available locations
        
    Returns:
        Default location to use
    """
    if not locations:
        return 'us-central1'
    
    if 'us-central1' in locations:
        return 'us-central1'
    
    # Prefer US regions (but not multi-region 'us' endpoint)
    us_regions = [loc for loc in locations if loc.startswith('us-')]
    if us_regions:
        return sorted(us_regions)[0]
    
    # Fallback to first
    return sorted(locations)[0]


def _build_model_region_config() -> Dict[str, Dict]:
    """
    Build model → region config dynamically from discovered metadata.
    
    Groups model variants (chirp, chirp_2, chirp_3) under base names.
    Returns config with same structure as MODEL_REGION_CONFIG.
    
    Returns:
        Dict mapping model name to config dict with:
            - requires_regional: bool
            - supported_regions: list[str]
            - default_region: str
    """
    global _AVAILABLE_MODELS
    
    # Invert cache: (location, language) -> model_ids
    # To: model_id -> Set[locations]
    model_to_locations = {}
    for (location, language), model_ids in _AVAILABLE_MODELS.items():
        for model_id in model_ids:
            if model_id not in model_to_locations:
                model_to_locations[model_id] = set()
            model_to_locations[model_id].add(location)
    
    # Build config - handle model name normalization
    config = {}
    
    # Group model variants under base names
    # User says 'chirp' but metadata has 'chirp', 'chirp_2', 'chirp_3', 'chirp_telephony'
    base_models = {
        'chirp': ['chirp', 'chirp_2', 'chirp_3', 'chirp_telephony'],
        'long': ['long'],
        'short': ['short'],
        'telephony': ['telephony', 'telephony_short']
    }
    
    for base_name, variants in base_models.items():
        # Collect all locations for all variants
        all_locations = set()
        for variant in variants:
            if variant in model_to_locations:
                all_locations.update(model_to_locations[variant])
        
        if all_locations:
            locations_list = sorted(all_locations)
            config[base_name] = {
                'requires_regional': len(locations_list) > 0,
                'supported_regions': locations_list,
                'default_region': _choose_default_region(locations_list)
            }
    
    return config


def get_supported_features(model: str, language: str = 'en-US', location: str = None) -> Set[str]:
    """
    Get supported features for a model/language/location combination.

    Args:
        model: Model identifier (e.g., 'chirp', 'long')
        language: BCP-47 language code (defaults to 'en-US')
        location: Location ID (optional, will search all locations if not specified)

    Returns:
        Set of feature keys supported by this combination
    """
    global _FEATURE_CACHE, _CACHE_LOADED

    # If location specified, try direct lookup
    if location:
        cache_key = (location, language, model)
        if cache_key in _FEATURE_CACHE:
            return _FEATURE_CACHE[cache_key].copy()

    # Search all locations for this model/language
    for (loc, lang, mod), features in _FEATURE_CACHE.items():
        if mod == model and lang == language:
            logger.debug(f"Found features for {model}/{language} in location {loc}")
            return features.copy()

    # Cache miss - use fallback
    if not _CACHE_LOADED:
        logger.warning(f"Cache not loaded, using fallback for {model}/{language}")
        return _get_fallback_features(model)

    # Model not found in any location
    logger.warning(
        f"Model {model} not found for language {language} in any location. "
        f"Using empty feature set."
    )
    return set()


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
    # Built dynamically from discovered metadata (see _build_model_region_config())
    # No longer hardcoded - automatically discovers all supported regions
    # 
    # Note: This is a cached property that gets built from _AVAILABLE_MODELS cache
    # when metadata discovery completes. Falls back to minimal config if cache not loaded.

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

    def _get_model_region_config(self) -> Dict[str, Dict]:
        """
        Get model region config, building dynamically from discovered metadata.
        
        Returns:
            Dict mapping model name to config dict
        """
        global _AVAILABLE_MODELS, _CACHE_LOADED
        
        # Build config from discovered metadata
        if _CACHE_LOADED and _AVAILABLE_MODELS:
            return _build_model_region_config()
        
        # Fallback to minimal hardcoded config if cache not loaded
        logger.warning("Metadata cache not loaded, using minimal fallback config")
        return {
            'chirp': {
                'requires_regional': True,
                'supported_regions': ['us-central1', 'europe-west4', 'asia-southeast1'],
                'default_region': 'us-central1'
            },
            'long': {
                'requires_regional': False,
                'supported_regions': ['us-central1', 'us-west1', 'us-east1'],
                'default_region': 'us-central1'
            },
            'short': {
                'requires_regional': False,
                'supported_regions': ['us-central1', 'us-west1', 'us-east1'],
                'default_region': 'us-central1'
            }
        }

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
        # Get model configuration dynamically
        model_region_config = self._get_model_region_config()
        model_config = model_region_config.get(model, {})

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
        Map a requested region to the nearest available region using prefix matching.

        Uses region name prefix (continent) to find nearby regions.
        e.g., "us-west1" → finds any "us-*" region in available list
        e.g., "europe-west1" → finds any "europe-*" region in available list

        Args:
            requested: Requested region (e.g., 'us-west1')
            available: List of available regions for the model

        Returns:
            Nearest available region with same prefix, or None if no match
        """
        # Multi-region endpoints (us, eu) - check if they're directly available
        if requested in available:
            return requested
        
        # Extract continent prefix from region name
        # e.g., "us-west1" → "us", "europe-west1" → "europe"
        if '-' not in requested:
            # Multi-region endpoint without dash - check if available
            return requested if requested in available else None
        
        region_prefix = requested.split('-')[0]  # "us", "europe", "asia", etc.
        
        # Find first available region with same prefix
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
                # CRITICAL: Official Google examples include processing_strategy
                # This might be required for batch recognition to work correctly
                processing_strategy=cloud_speech.BatchRecognizeRequest.ProcessingStrategy.DYNAMIC_BATCHING,
            )

            # Submit batch recognition job
            # This returns IMMEDIATELY with an operation object
            # The actual transcription happens asynchronously in Google's queue
            logger.info(f"Submitting batch recognition job for: {gcs_uri}")
            logger.info(f"Model: {config.model}, Language: {config.language_codes}")
            
            # DEBUG: Log full config details to diagnose empty transcript issue
            if hasattr(config, 'features') and config.features:
                logger.info(f"DEBUG: RecognitionFeatures enabled: enable_word_time_offsets={getattr(config.features, 'enable_word_time_offsets', False)}, enable_word_confidence={getattr(config.features, 'enable_word_confidence', False)}, enable_automatic_punctuation={getattr(config.features, 'enable_automatic_punctuation', False)}")
            else:
                logger.warning("DEBUG: No RecognitionFeatures configured!")
            
            if hasattr(config, 'explicit_decoding_config') and config.explicit_decoding_config:
                logger.info(f"DEBUG: ExplicitDecodingConfig: encoding={getattr(config.explicit_decoding_config, 'encoding', 'N/A')}, sample_rate={getattr(config.explicit_decoding_config, 'sample_rate_hertz', 'N/A')}Hz, channels={getattr(config.explicit_decoding_config, 'audio_channel_count', 'N/A')}")
            elif hasattr(config, 'auto_decoding_config') and config.auto_decoding_config:
                logger.info("DEBUG: Using AutoDetectDecodingConfig")
            else:
                logger.warning("DEBUG: No decoding config specified!")
            
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
                # Try to determine actual status from operation metadata
                status = "processing"  # Default
                
                # Check if operation.metadata has status information
                if hasattr(operation, 'metadata') and operation.metadata:
                    # Metadata is a protobuf Any type - need to unpack it
                    try:
                        # Unpack the Any protobuf to get OperationMetadata
                        # cloud_speech is already imported at module level
                        operation_metadata = cloud_speech.OperationMetadata()
                        operation.metadata.Unpack(operation_metadata)
                        
                        logger.debug(f"Unpacked OperationMetadata: {operation_metadata}")
                        
                        # Check for progress_percent field (indicates active processing)
                        if hasattr(operation_metadata, 'progress_percent'):
                            progress = operation_metadata.progress_percent
                            if progress is not None:
                                # If progress is available, it's actively processing
                                status = "processing"
                                logger.debug(f"Job {job_id} is processing (progress: {progress}%)")
                            else:
                                # No progress yet - might be queued
                                status = "queued"
                                logger.debug(f"Job {job_id} appears to be queued (no progress)")
                        
                        # Check for state field (if available)
                        elif hasattr(operation_metadata, 'state'):
                            state = operation_metadata.state
                            if state == cloud_speech.OperationMetadata.State.QUEUED:
                                status = "queued"
                            elif state == cloud_speech.OperationMetadata.State.RUNNING:
                                status = "processing"
                            logger.debug(f"Job {job_id} state from metadata: {state}")
                        
                    except Exception as e:
                        logger.debug(f"Could not unpack/extract status from metadata: {e}")
                        # Fall back to default "processing" status
                
                logger.info(f"Job {job_id} is still in progress (status: {status})")
                return {
                    "done": False,
                    "status": status,
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
            
            # Extract billed duration from file_result.metadata (this is where it actually lives!)
            billed_duration_seconds = None
            if hasattr(file_result, 'metadata') and file_result.metadata:
                if hasattr(file_result.metadata, 'total_billed_duration'):
                    duration = file_result.metadata.total_billed_duration
                    if duration:
                        billed_duration_seconds = duration.total_seconds()
                        logger.info(f"Extracted billed duration from file_result.metadata: {billed_duration_seconds:.2f} seconds ({billed_duration_seconds / 60.0:.2f} minutes)")
                else:
                    logger.debug(f"DEBUG: file_result.metadata exists but has no total_billed_duration attribute")
                    logger.debug(f"DEBUG: file_result.metadata attributes: {[attr for attr in dir(file_result.metadata) if not attr.startswith('_')]}")
            else:
                logger.debug(f"DEBUG: file_result has no metadata attribute or metadata is None")
                logger.debug(f"DEBUG: file_result attributes: {[attr for attr in dir(file_result) if not attr.startswith('_')]}")

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

            # Parse JSON directly (bypassing Protobuf deserializer which fails to populate alternatives)
            # Per Gemini: The Protobuf from_json() method fails to deserialize the alternatives content
            # due to parsing impedance mismatch. Manual JSON parsing is more reliable.
            import json
            results_json = json.loads(results_bytes.decode('utf-8'))
            
            # Extract transcript from results using direct JSON parsing
            results = self._parse_batch_results_from_json(results_json)
            
            # Add billed_duration as top-level fields (not in metadata) to preserve data provenance
            # metadata contains only GCS JSON-derived data; billed_duration comes from operation response
            if billed_duration_seconds is not None:
                results['billed_duration_seconds'] = round(billed_duration_seconds, 2)
                results['billed_duration_minutes'] = round(billed_duration_seconds / 60.0, 2)
                logger.info(f"Added billed_duration to results: {results['billed_duration_minutes']:.2f} minutes")
            
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
            
            # DEBUG: Log full config details to diagnose empty transcript issue
            if hasattr(config, 'features') and config.features:
                logger.info(f"DEBUG: RecognitionFeatures enabled: enable_word_time_offsets={getattr(config.features, 'enable_word_time_offsets', False)}, enable_word_confidence={getattr(config.features, 'enable_word_confidence', False)}, enable_automatic_punctuation={getattr(config.features, 'enable_automatic_punctuation', False)}")
            else:
                logger.warning("DEBUG: No RecognitionFeatures configured!")
            
            # DEBUG: Check decoding config - protobuf messages can have attributes that exist but are "empty"
            explicit_val = getattr(config, 'explicit_decoding_config', None)
            auto_val = getattr(config, 'auto_decoding_config', None)
            
            logger.info(f"DEBUG: explicit_decoding_config type: {type(explicit_val)}, value: {explicit_val}")
            logger.info(f"DEBUG: auto_decoding_config type: {type(auto_val)}, value: {auto_val}")
            
            # Check if values are actually set (not None and not empty protobuf messages)
            if explicit_val is not None:
                # Check if it's a protobuf message that's actually populated
                try:
                    # Try to access a field to see if it's populated
                    encoding = getattr(explicit_val, 'encoding', None)
                    if encoding is not None:
                        logger.info(f"DEBUG: ExplicitDecodingConfig: encoding={encoding}, sample_rate={getattr(explicit_val, 'sample_rate_hertz', 'N/A')}Hz, channels={getattr(explicit_val, 'audio_channel_count', 'N/A')}")
                    else:
                        logger.warning("DEBUG: explicit_decoding_config exists but is empty/unpopulated")
                except Exception as e:
                    logger.warning(f"DEBUG: Error checking explicit_decoding_config: {e}")
            elif auto_val is not None:
                # AutoDetectDecodingConfig is typically an empty message (no fields)
                # Just check if it exists
                logger.info("DEBUG: Using AutoDetectDecodingConfig")
            else:
                logger.warning("DEBUG: No decoding config specified! (both are None)")
            
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
        supported_features = get_supported_features(self.model, language_code, self.location)

        # Build feature configuration dynamically
        feature_config = {}

        # Map desired features to API keys and check support
        # Automatic punctuation
        if 'automatic_punctuation' in supported_features:
            feature_config['enable_automatic_punctuation'] = True
        else:
            logger.info(f"Skipping automatic_punctuation (unsupported by {self.model}/{language_code})")

        # Word timestamps - CRITICAL: Always enable for debugging (per Gemini recommendation)
        # Even if not in supported_features, try to enable it to force verbose output
        # This helps diagnose why transcripts are empty
        if 'word_level_timestamps' in supported_features:
            feature_config['enable_word_time_offsets'] = True
            logger.info(f"✓ Enabled word_time_offsets (supported by {self.model}/{language_code})")
        else:
            # Try to enable anyway - some models may support it even if metadata doesn't indicate it
            feature_config['enable_word_time_offsets'] = True
            logger.warning(f"⚠️  Enabling word_time_offsets despite metadata saying unsupported (for debugging)")

        # Word confidence scores
        if 'word_level_confidence' in supported_features:
            feature_config['enable_word_confidence'] = True
        else:
            logger.info(f"Skipping word_confidence (unsupported by {self.model}/{language_code})")

        # Log enabled features for debugging
        enabled_features = [k for k, v in feature_config.items() if v]
        logger.info(f"Enabled features for {self.model}/{language_code}: {enabled_features}")

        # Build phrase hints for custom vocabulary (V2 API structure)
        # V2 uses inline_phrase_set with phrases as list of dicts with 'value' field
        # NOTE: Chirp models do NOT support speech adaptation (phrase hints)
        # Only enable for models that support it (e.g., long, short)
        adaptation = None
        if self.yoga_vocabulary:
            # Check if model supports adaptation
            # Chirp models (chirp, chirp_2, chirp_3, chirp_telephony) don't support adaptation
            chirp_models = {'chirp', 'chirp_2', 'chirp_3', 'chirp_telephony'}
            if self.model not in chirp_models:
                phrase_set = cloud_speech.SpeechAdaptation.AdaptationPhraseSet({
                    'inline_phrase_set': {
                        'phrases': [{'value': phrase} for phrase in self.yoga_vocabulary]
                    }
                })
                adaptation = cloud_speech.SpeechAdaptation(
                    phrase_sets=[phrase_set]
                )
                logger.debug(f"Added {len(self.yoga_vocabulary)} phrase hints for custom vocabulary")
            else:
                logger.info(f"Skipping phrase hints - {self.model} does not support speech adaptation")

        # Build config with adaptation if vocabulary exists
        # DEBUG: Log what's in decoding_config_kwargs before spreading
        logger.info(f"DEBUG: decoding_config_kwargs keys: {list(decoding_config_kwargs.keys())}")
        
        config_kwargs = {
            **decoding_config_kwargs,
            'language_codes': [language_code],
            'model': self.model,
            'features': cloud_speech.RecognitionFeatures(**feature_config),
        }
        if adaptation:
            config_kwargs['adaptation'] = adaptation
        
        # DEBUG: Log what's in config_kwargs before creating RecognitionConfig
        logger.info(f"DEBUG: config_kwargs keys: {list(config_kwargs.keys())}")
        
        config = cloud_speech.RecognitionConfig(**config_kwargs)
        
        # DEBUG: Verify decoding config is in the created config object
        logger.info(f"DEBUG: After creating RecognitionConfig - has explicit_decoding_config: {hasattr(config, 'explicit_decoding_config')}, has auto_decoding_config: {hasattr(config, 'auto_decoding_config')}")

        return config

    def _parse_batch_results_from_json(self, results_json) -> Dict:
        """
        Parse batch recognition results from raw JSON (bypassing Protobuf deserializer).
        
        Per Gemini: The Protobuf from_json() method fails to populate alternatives
        due to parsing impedance mismatch. This method parses the JSON directly.
        
        Args:
            results_json: Raw JSON dict from GCS file
            
        Returns:
            Structured dict with transcript and metadata
        """
        try:
            results = []
            word_details = []
            word_confidence_sum = 0.0
            word_count = 0
            
            # The GCS JSON structure: results is a list of segments
            # Handle both cases: top-level list or wrapped in 'results' field
            if isinstance(results_json, list):
                segments = results_json
            elif 'results' in results_json and isinstance(results_json['results'], list):
                segments = results_json['results']
            else:
                logger.error(f"Unexpected JSON structure: {type(results_json)}")
                return {
                    "success": False,
                    "transcript": "",
                    "confidence": None,
                    "words": [],
                    "metadata": {},
                    "error": "Unexpected JSON structure"
                }
            
            logger.info(f"Parsing {len(segments)} segments from JSON")
            
            # Extract transcript from alternatives array in each segment
            for segment in segments:
                if 'alternatives' in segment and segment['alternatives']:  # Check if alternatives array is not empty
                    # Get the first (best) alternative
                    # Edge case: alternatives might be a list or a single dict
                    top_alternative = segment['alternatives'][0] if isinstance(segment['alternatives'], list) else segment['alternatives']
                    
                    if 'transcript' in top_alternative:
                        transcript_text = top_alternative['transcript']
                        if transcript_text:  # Only add non-empty transcripts
                            results.append(transcript_text)
                        
                        # Extract word-level details if available
                        if 'words' in top_alternative and top_alternative['words']:
                            for word_info in top_alternative['words']:
                                word_conf = word_info.get('confidence', None)
                                if word_conf is not None and word_conf > 0:
                                    word_confidence_sum += word_conf
                                    word_count += 1
                                
                                # Extract timing information
                                start_time = 0.0
                                end_time = 0.0
                                if 'startOffset' in word_info:
                                    # Handle duration format (e.g., "1.5s" or {"seconds": 1, "nanos": 500000000})
                                    start_offset = word_info['startOffset']
                                    if isinstance(start_offset, str):
                                        start_time = float(start_offset.rstrip('s'))
                                    elif isinstance(start_offset, dict):
                                        start_time = start_offset.get('seconds', 0) + start_offset.get('nanos', 0) / 1e9
                                
                                if 'endOffset' in word_info:
                                    end_offset = word_info['endOffset']
                                    if isinstance(end_offset, str):
                                        end_time = float(end_offset.rstrip('s'))
                                    elif isinstance(end_offset, dict):
                                        end_time = end_offset.get('seconds', 0) + end_offset.get('nanos', 0) / 1e9
                                
                                word_details.append({
                                    "word": word_info.get('word', ''),
                                    "start_time": start_time,
                                    "end_time": end_time,
                                    "confidence": word_conf if word_conf is not None else 0.0
                                })
            
            # Combine results
            full_transcript = " ".join(results)
            
            # Calculate average confidence from word-level scores
            if word_count > 0 and word_confidence_sum > 0.0:
                avg_confidence = word_confidence_sum / word_count
            else:
                # Try to get from alternative-level confidence
                total_confidence = 0.0
                conf_count = 0
                for segment in segments:
                    if 'alternatives' in segment and segment['alternatives']:
                        top_alternative = segment['alternatives'][0] if isinstance(segment['alternatives'], list) else segment['alternatives']
                        alt_conf = top_alternative.get('confidence', None)
                        if alt_conf is not None and alt_conf > 0.0:
                            total_confidence += alt_conf
                            conf_count += 1
                
                if conf_count > 0:
                    avg_confidence = total_confidence / conf_count
                else:
                    avg_confidence = None
            
            # Extract billed duration from metadata if available
            # Note: billed_duration is typically extracted from operation response, not GCS JSON
            # This is a fallback check for edge cases where it might be in the JSON
            billed_duration_seconds = None
            
            # Check top-level metadata (unlikely but possible)
            if isinstance(results_json, dict) and 'metadata' in results_json:
                metadata = results_json['metadata']
                if isinstance(metadata, dict) and 'totalBilledDuration' in metadata:
                    duration = metadata['totalBilledDuration']
                    if isinstance(duration, str):
                        billed_duration_seconds = float(duration.rstrip('s'))
                    elif isinstance(duration, dict):
                        billed_duration_seconds = duration.get('seconds', 0) + duration.get('nanos', 0) / 1e9
            
            # Check if metadata is in the first segment (very unlikely)
            if billed_duration_seconds is None and segments:
                first_segment = segments[0] if segments else None
                if isinstance(first_segment, dict) and 'metadata' in first_segment:
                    seg_metadata = first_segment['metadata']
                    if isinstance(seg_metadata, dict) and 'totalBilledDuration' in seg_metadata:
                        duration = seg_metadata['totalBilledDuration']
                        if isinstance(duration, str):
                            billed_duration_seconds = float(duration.rstrip('s'))
                        elif isinstance(duration, dict):
                            billed_duration_seconds = duration.get('seconds', 0) + duration.get('nanos', 0) / 1e9
            
            logger.info(f"Parsed {len(results)} segments, {len(word_details)} words")
            if avg_confidence is not None:
                logger.info(f"Confidence: {avg_confidence:.4f}")
            else:
                logger.info("Confidence not available for this model")
            
            # Build metadata
            metadata = {
                "total_words": len(word_details),
                "model": self.model,
                "language": "en-US",
                "api_version": "v2"
            }
            
            if billed_duration_seconds is not None:
                metadata["billed_duration_seconds"] = round(billed_duration_seconds, 2)
                metadata["billed_duration_minutes"] = round(billed_duration_seconds / 60.0, 2)
            
            return {
                "success": True,
                "transcript": full_transcript,
                "confidence": avg_confidence,
                "words": word_details,
                "metadata": metadata
            }
            
        except Exception as e:
            logger.error(f"Error parsing batch results from JSON: {e}", exc_info=True)
            return {
                "success": False,
                "transcript": "",
                "confidence": None,
                "words": [],
                "metadata": {},
                "error": f"Result parsing error: {e}"
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

            # Extract billed duration from metadata (actual usage from Google)
            billed_duration_seconds = None
            for uri_or_idx, result in items:
                if hasattr(result, 'metadata') and result.metadata:
                    if hasattr(result.metadata, 'total_billed_duration'):
                        # total_billed_duration is a Duration protobuf
                        duration = result.metadata.total_billed_duration
                        if duration:
                            # Convert Duration to seconds
                            billed_duration_seconds = duration.total_seconds()
                            logger.info(f"Extracted billed duration: {billed_duration_seconds:.2f} seconds")
                            break  # Use first result's metadata

            # Combine results
            full_transcript = " ".join(results)
            avg_confidence = total_confidence / len(results) if results else 0.0

            logger.info(f"Parsed {len(results)} result segments, {len(word_details)} words")

            # Build metadata with actual billed duration from Google
            metadata = {
                "total_words": len(word_details),
                "model": self.model,
                "language": "en-US",
                "api_version": "v2"
            }
            
            # Include actual billed duration from Google (if available)
            if billed_duration_seconds is not None:
                metadata["billed_duration_seconds"] = round(billed_duration_seconds, 2)
                metadata["billed_duration_minutes"] = round(billed_duration_seconds / 60.0, 2)
                logger.info(f"Including billed duration in metadata: {metadata['billed_duration_minutes']:.2f} minutes")

            return {
                "success": True,
                "transcript": full_transcript,
                "confidence": avg_confidence,
                "words": word_details,
                "metadata": metadata
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
