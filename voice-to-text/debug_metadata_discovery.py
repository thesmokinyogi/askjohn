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
from google.cloud.speech_v2.types import LocationsMetadata
from google.cloud.location import locations_pb2
from google.protobuf.json_format import MessageToDict
from dotenv import load_dotenv

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

            # Alternative 3: Unpack Any to LocationsMetadata (Gemini's solution)
            logger.info(f"\n   C. Unpack Any to LocationsMetadata:")
            try:
                # Check if metadata contains LocationsMetadata
                if loc.metadata.Is(LocationsMetadata.pb()):
                    logger.info(f"      ✓ metadata.Is(LocationsMetadata) = True")

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

                            # Show model features structure
                            logger.info(f"      model_metadata type: {type(model_metadata)}")
                            logger.info(f"      model_metadata attributes: {[attr for attr in dir(model_metadata) if not attr.startswith('_')][:15]}")

                            if hasattr(model_metadata, 'model_features'):
                                logger.info(f"      ✓ model_metadata.model_features exists")
                                logger.info(f"      type: {type(model_metadata.model_features)}")
                                logger.info(f"      Sample: {str(model_metadata.model_features)[:300]}")
                    else:
                        logger.info(f"      No languages found in metadata")
                else:
                    logger.info(f"      metadata does not contain LocationsMetadata")

            except Exception as e:
                logger.error(f"      ✗ Unpacking failed: {type(e).__name__}: {e}")
                import traceback
                logger.error(f"      {traceback.format_exc()}")

        logger.info("\n" + "=" * 80)
        logger.info("OBSERVATION COMPLETE")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"Fatal error during observation: {type(e).__name__}: {e}", exc_info=True)

if __name__ == "__main__":
    observe_metadata_discovery()
