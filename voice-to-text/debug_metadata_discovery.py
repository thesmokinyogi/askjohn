#!/usr/bin/env python3
"""
DEBUG OBSERVATION PLATFORM
Copy of server code stripped down to just auth + metadata discovery
Purpose: Observe what proto-plus dict conversion actually returns
"""

import os
import json
import logging
from google.cloud.speech_v2 import SpeechClient
from google.cloud.speech_v2.proto.cloud_speech_pb2 import LocationsMetadata
from google.cloud.location import locations_pb2
from google.protobuf.json_format import MessageToDict
from google.protobuf.struct_pb2 import Struct
from google.api_core.client_options import ClientOptions
from dotenv import load_dotenv

# Try importing Config and GetConfigRequest (Gemini's suggestion)
try:
    from google.cloud.speech_v2.types import Config, GetConfigRequest
    CONFIG_AVAILABLE = True
except ImportError as e:
    CONFIG_AVAILABLE = False
    CONFIG_IMPORT_ERROR = str(e)

# Load environment variables from .env file (same as server does)
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def observe_metadata_discovery():
    """
    Observe proto-plus behavior with extensive logging
    """
    logger.info("=" * 80)
    logger.info("STARTING OBSERVATION: Proto-plus dict conversion")
    logger.info("=" * 80)

    # Get project ID from environment
    project_id = os.environ.get('GOOGLE_CLOUD_PROJECT')
    if not project_id:
        logger.error("GOOGLE_CLOUD_PROJECT environment variable not set")
        return

    logger.info(f"Project ID: {project_id}")

    try:
        # Create Speech V2 client (uses ADC - same auth as server)
        client = SpeechClient()
        logger.info("✓ SpeechClient created successfully")

        # Query locations
        request = locations_pb2.ListLocationsRequest(name=f"projects/{project_id}")
        logger.info(f"Querying locations for project: {project_id}")

        response = client.list_locations(request=request)
        logger.info(f"✓ Response received: {len(response.locations)} locations")

        # Observe FIRST location in detail
        if not response.locations:
            logger.error("No locations returned!")
            return

        loc = response.locations[0]
        location_id = loc.location_id

        logger.info("\n" + "=" * 80)
        logger.info(f"OBSERVING FIRST LOCATION: {location_id}")
        logger.info("=" * 80)

        # OBSERVATION 1: What type is this object?
        logger.info(f"\n1. OBJECT TYPE:")
        logger.info(f"   type(loc) = {type(loc)}")
        logger.info(f"   type(loc).__name__ = {type(loc).__name__}")
        logger.info(f"   type(loc).__module__ = {type(loc).__module__}")

        # OBSERVATION 2: What attributes does it have?
        logger.info(f"\n2. OBJECT ATTRIBUTES:")
        attrs = [attr for attr in dir(loc) if not attr.startswith('_')]
        logger.info(f"   Public attributes: {attrs[:20]}")  # First 20

        # OBSERVATION 3: Try dict() conversion
        logger.info(f"\n3. ATTEMPTING dict() CONVERSION:")
        try:
            location_dict = dict(loc)
            logger.info(f"   ✓ dict(loc) succeeded!")
            logger.info(f"   type(location_dict) = {type(location_dict)}")
            logger.info(f"   Keys: {list(location_dict.keys())}")

            # OBSERVATION 4: What's in each key?
            logger.info(f"\n4. EXAMINING EACH KEY:")
            for key in location_dict.keys():
                value = location_dict[key]
                logger.info(f"   '{key}':")
                logger.info(f"      type = {type(value)}")
                logger.info(f"      value = {str(value)[:200]}")  # First 200 chars

            # OBSERVATION 5: Focus on metadata field
            logger.info(f"\n5. DEEP DIVE INTO 'metadata':")
            metadata = location_dict.get('metadata')
            if metadata is None:
                logger.warning("   'metadata' key is None!")
            else:
                logger.info(f"   type(metadata) = {type(metadata)}")
                logger.info(f"   isinstance(metadata, dict) = {isinstance(metadata, dict)}")

                if hasattr(metadata, '__dict__'):
                    logger.info(f"   metadata.__dict__.keys() = {list(metadata.__dict__.keys())[:10]}")

                if hasattr(metadata, 'keys'):
                    logger.info(f"   metadata.keys() = {list(metadata.keys())[:10]}")

                # Try converting metadata to dict
                logger.info(f"\n6. ATTEMPTING dict(metadata):")
                try:
                    metadata_dict = dict(metadata)
                    logger.info(f"   ✓ dict(metadata) succeeded!")
                    logger.info(f"   Keys in metadata_dict: {list(metadata_dict.keys())[:10]}")

                    # OBSERVATION 7: What's in 'languages'?
                    if 'languages' in metadata_dict:
                        logger.info(f"\n7. EXAMINING 'languages':")
                        languages = metadata_dict['languages']
                        logger.info(f"   type(languages) = {type(languages)}")

                        if isinstance(languages, dict):
                            lang_codes = list(languages.keys())[:5]
                            logger.info(f"   Language codes (first 5): {lang_codes}")

                            if languages:
                                first_lang = list(languages.keys())[0]
                                lang_data = languages[first_lang]
                                logger.info(f"\n8. EXAMINING LANGUAGE '{first_lang}':")
                                logger.info(f"   type(lang_data) = {type(lang_data)}")

                                if isinstance(lang_data, dict):
                                    logger.info(f"   Keys: {list(lang_data.keys())}")

                                    # Show 'models' structure
                                    if 'models' in lang_data:
                                        models = lang_data['models']
                                        logger.info(f"\n9. EXAMINING 'models':")
                                        logger.info(f"   type(models) = {type(models)}")
                                        logger.info(f"   Number of models: {len(models) if isinstance(models, dict) else 'N/A'}")

                                        if isinstance(models, dict) and models:
                                            model_ids = list(models.keys())[:3]
                                            logger.info(f"   Model IDs (first 3): {model_ids}")

                                            first_model = list(models.keys())[0]
                                            model_data = models[first_model]
                                            logger.info(f"\n10. EXAMINING MODEL '{first_model}':")
                                            logger.info(f"   type(model_data) = {type(model_data)}")

                                            if isinstance(model_data, dict):
                                                logger.info(f"   Keys: {list(model_data.keys())}")
                                                logger.info(f"\n   Full model structure:")
                                                logger.info(f"   {json.dumps(model_data, indent=6, default=str)}")
                    else:
                        logger.warning("   'languages' key not found in metadata_dict!")

                except Exception as e:
                    logger.error(f"   ✗ dict(metadata) failed: {type(e).__name__}: {e}")
                    logger.info(f"\n   Trying alternative: vars(metadata)")
                    try:
                        metadata_vars = vars(metadata)
                        logger.info(f"   ✓ vars(metadata) succeeded!")
                        logger.info(f"   Keys: {list(metadata_vars.keys())[:10]}")
                    except Exception as e2:
                        logger.error(f"   ✗ vars(metadata) also failed: {e2}")

        except Exception as e:
            logger.error(f"   ✗ dict(loc) failed: {type(e).__name__}: {e}")
            logger.info(f"\n   Stack trace:", exc_info=True)

            # Try alternative approaches
            logger.info(f"\n   TRYING ALTERNATIVES:")

            # Alternative 1: MessageToDict (for raw protobuf)
            logger.info(f"\n   A. MessageToDict(loc):")
            try:
                location_dict = MessageToDict(loc)
                logger.info(f"      ✓ MessageToDict succeeded!")
                logger.info(f"      Keys: {list(location_dict.keys())}")

                metadata_dict = location_dict.get('metadata', {})
                logger.info(f"      metadata keys: {list(metadata_dict.keys())[:10] if metadata_dict else 'None'}")

                if 'languages' in metadata_dict:
                    logger.info(f"      Found 'languages' in metadata!")
                    logger.info(f"      Sample: {str(metadata_dict['languages'])[:300]}")
            except Exception as e:
                logger.error(f"      ✗ MessageToDict failed: {e}")

            # Alternative 2: Direct attribute access
            logger.info(f"\n   B. Direct attribute access:")
            try:
                logger.info(f"      loc.location_id = {loc.location_id}")
                logger.info(f"      loc.name = {loc.name}")
                logger.info(f"      type(loc.metadata) = {type(loc.metadata)}")
                logger.info(f"      loc.metadata = {str(loc.metadata)[:200]}")
            except Exception as e:
                logger.error(f"      Failed: {e}")

            # Alternative 3: Unpack Any to Struct (generic protobuf structure)
            logger.info(f"\n   C. Unpack Any to Struct:")
            try:
                # Unpack to generic Struct
                struct_metadata = Struct()
                loc.metadata.Unpack(struct_metadata)
                logger.info(f"      ✓ Unpacked to Struct successfully!")

                # Convert Struct to dict using MessageToDict
                metadata_dict = MessageToDict(struct_metadata)
                logger.info(f"      ✓ Converted Struct to dict")
                logger.info(f"      Keys: {list(metadata_dict.keys())[:10]}")

                # Check for 'languages' in the dict
                if 'languages' in metadata_dict:
                    logger.info(f"      ✓ Found 'languages' key!")
                    languages = metadata_dict['languages']
                    logger.info(f"      Number of languages: {len(languages) if isinstance(languages, dict) else 'N/A'}")

                    if isinstance(languages, dict) and languages:
                        # Show first language
                        first_lang = list(languages.keys())[0]
                        lang_data = languages[first_lang]
                        logger.info(f"      First language: {first_lang}")
                        logger.info(f"      Language data type: {type(lang_data)}")
                        logger.info(f"      Language data keys: {list(lang_data.keys())[:10] if isinstance(lang_data, dict) else 'N/A'}")

                        # Check for models
                        if isinstance(lang_data, dict) and 'models' in lang_data:
                            models = lang_data['models']
                            logger.info(f"      ✓ Found 'models' key!")
                            logger.info(f"      Number of models: {len(models) if isinstance(models, dict) else 'N/A'}")

                            if isinstance(models, dict) and models:
                                # Show first model
                                first_model = list(models.keys())[0]
                                model_data = models[first_model]
                                logger.info(f"      First model: {first_model}")
                                logger.info(f"      Model data type: {type(model_data)}")

                                if isinstance(model_data, dict):
                                    logger.info(f"      Model keys: {list(model_data.keys())}")
                                    logger.info(f"      Full model data sample:")
                                    logger.info(f"      {json.dumps(model_data, indent=8, default=str)[:500]}")
                else:
                    logger.info(f"      No 'languages' key found")
                    logger.info(f"      Available keys: {list(metadata_dict.keys())}")

            except Exception as e:
                logger.error(f"      ✗ Unpacking failed: {type(e).__name__}: {e}")
                import traceback
                logger.error(f"      {traceback.format_exc()}")

            # Alternative 4: Unpack Any to LocationsMetadata from internal proto (Gemini's corrected solution)
            logger.info(f"\n   D. Unpack Any to LocationsMetadata (internal proto path):")
            try:
                # Check if metadata contains LocationsMetadata
                if loc.metadata.Is(LocationsMetadata.DESCRIPTOR):
                    logger.info(f"      ✓ metadata.Is(LocationsMetadata.DESCRIPTOR) = True")

                    # Unpack the Any object
                    location_metadata = LocationsMetadata()
                    loc.metadata.Unpack(location_metadata)
                    logger.info(f"      ✓ Unpacked successfully!")

                    # Check what's in languages
                    if location_metadata.languages:
                        logger.info(f"      ✓ Found {len(location_metadata.languages)} languages")

                        # Show first language
                        first_lang = list(location_metadata.languages.keys())[0]
                        lang_metadata = location_metadata.languages[first_lang]
                        logger.info(f"      First language: {first_lang}")

                        if lang_metadata.models:
                            logger.info(f"      Found {len(lang_metadata.models)} models for {first_lang}")

                            # Show first model
                            first_model = list(lang_metadata.models.keys())[0]
                            model_metadata = lang_metadata.models[first_model]
                            logger.info(f"      First model: {first_model}")

                            # Show model_features structure
                            logger.info(f"      model_metadata attributes: {[attr for attr in dir(model_metadata) if not attr.startswith('_')][:15]}")

                            if hasattr(model_metadata, 'model_features'):
                                logger.info(f"      ✓ model_metadata.model_features exists")
                                logger.info(f"      type: {type(model_metadata.model_features)}")

                                # Show structure
                                if first_model in model_metadata.model_features:
                                    features_obj = model_metadata.model_features[first_model]
                                    logger.info(f"      features_obj type: {type(features_obj)}")
                                    logger.info(f"      features_obj attributes: {[attr for attr in dir(features_obj) if not attr.startswith('_')][:10]}")

                                    if hasattr(features_obj, 'model_feature'):
                                        logger.info(f"      ✓ features_obj.model_feature exists (list of features)")
                                        logger.info(f"      Number of features: {len(features_obj.model_feature)}")

                                        # Show first few features
                                        for i, feature in enumerate(features_obj.model_feature[:5]):
                                            logger.info(f"         Feature {i+1}: {feature.feature} ({feature.release_state})")
                    else:
                        logger.info(f"      No languages found in metadata")
                else:
                    logger.info(f"      metadata does not contain LocationsMetadata")

            except Exception as e:
                logger.error(f"      ✗ Unpacking failed: {type(e).__name__}: {e}")
                import traceback
                logger.error(f"      {traceback.format_exc()}")

            # Alternative 5: Use get_config() API (Gemini's recommended approach)
            logger.info(f"\n   E. Use get_config() API (Speech V2-specific):")

            if not CONFIG_AVAILABLE:
                logger.error(f"      ✗ Config/GetConfigRequest not available")
                logger.error(f"      Import error: {CONFIG_IMPORT_ERROR}")
            else:
                logger.info(f"      ✓ Config and GetConfigRequest imported successfully")

                try:
                    # Use us-west1 as test region (matches our GCS bucket)
                    test_region = "us-west1"
                    logger.info(f"      Testing with region: {test_region}")

                    # Create regional client
                    regional_client = SpeechClient(
                        client_options=ClientOptions(
                            api_endpoint=f"{test_region}-speech.googleapis.com"
                        )
                    )
                    logger.info(f"      ✓ Created regional client for {test_region}")

                    # Build config resource name
                    config_name = f"projects/{project_id}/locations/{test_region}/config"
                    logger.info(f"      Config resource: {config_name}")

                    # Call get_config()
                    config_request = GetConfigRequest(name=config_name)
                    config_response = regional_client.get_config(request=config_request)
                    logger.info(f"      ✓ get_config() succeeded!")
                    logger.info(f"      type(config_response) = {type(config_response)}")

                    # Examine Config structure
                    logger.info(f"\n      Config object attributes:")
                    config_attrs = [attr for attr in dir(config_response) if not attr.startswith('_')]
                    logger.info(f"      {config_attrs[:15]}")

                    # Check for languages
                    if hasattr(config_response, 'languages'):
                        logger.info(f"\n      ✓ config_response.languages exists")
                        logger.info(f"      type(languages) = {type(config_response.languages)}")

                        if config_response.languages:
                            logger.info(f"      Number of languages: {len(config_response.languages)}")

                            # Show first language
                            lang_codes = list(config_response.languages.keys())[:5]
                            logger.info(f"      Language codes (first 5): {lang_codes}")

                            if config_response.languages:
                                first_lang = list(config_response.languages.keys())[0]
                                lang_metadata = config_response.languages[first_lang]
                                logger.info(f"\n      First language: {first_lang}")
                                logger.info(f"      type(lang_metadata) = {type(lang_metadata)}")

                                # Check for models
                                if hasattr(lang_metadata, 'models'):
                                    logger.info(f"      ✓ lang_metadata.models exists")
                                    logger.info(f"      Number of models: {len(lang_metadata.models)}")

                                    model_ids = list(lang_metadata.models.keys())[:5]
                                    logger.info(f"      Model IDs (first 5): {model_ids}")

                                    # Examine first model
                                    if lang_metadata.models:
                                        first_model = list(lang_metadata.models.keys())[0]
                                        model_metadata = lang_metadata.models[first_model]
                                        logger.info(f"\n      First model: {first_model}")
                                        logger.info(f"      type(model_metadata) = {type(model_metadata)}")

                                        model_attrs = [attr for attr in dir(model_metadata) if not attr.startswith('_')]
                                        logger.info(f"      model_metadata attributes: {model_attrs[:15]}")

                                        # Check for model_features
                                        if hasattr(model_metadata, 'model_features'):
                                            logger.info(f"\n      ✓ model_metadata.model_features exists")
                                            logger.info(f"      type = {type(model_metadata.model_features)}")

                                            if first_model in model_metadata.model_features:
                                                features_obj = model_metadata.model_features[first_model]
                                                logger.info(f"      features_obj type: {type(features_obj)}")

                                                if hasattr(features_obj, 'model_feature'):
                                                    logger.info(f"      ✓ features_obj.model_feature exists")
                                                    logger.info(f"      Number of features: {len(features_obj.model_feature)}")

                                                    # Show first few features
                                                    logger.info(f"\n      Features for {first_model}:")
                                                    for i, feature in enumerate(features_obj.model_feature[:5]):
                                                        logger.info(f"         {i+1}. {feature.feature} ({feature.release_state})")
                                        else:
                                            logger.warning(f"      model_metadata has no 'model_features' attribute")
                                else:
                                    logger.warning(f"      lang_metadata has no 'models' attribute")
                        else:
                            logger.warning(f"      config_response.languages is empty")
                    else:
                        logger.warning(f"      config_response has no 'languages' attribute")

                except Exception as e:
                    logger.error(f"      ✗ get_config() approach failed: {type(e).__name__}: {e}")
                    import traceback
                    logger.error(f"      {traceback.format_exc()}")

        logger.info("\n" + "=" * 80)
        logger.info("OBSERVATION COMPLETE")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"Fatal error during observation: {type(e).__name__}: {e}", exc_info=True)

if __name__ == "__main__":
    observe_metadata_discovery()
