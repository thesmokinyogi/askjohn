#!/usr/bin/env python3
"""
Observation script to examine discovered metadata cache structure.

Purpose: Understand what data we have available to build MODEL_REGION_CONFIG
and REGION_PROXIMITY_MAP dynamically.

Following: WORKING_AGREEMENT.md - "Observe Before Implement"
"""

import os
from dotenv import load_dotenv
from app.services.transcribe_v2 import (
    discover_speech_metadata,
    initialize_metadata_cache,
    get_available_locations,
    get_available_models,
    get_supported_features
)
import json

# Load environment variables
load_dotenv()

def observe_cache_structure():
    """Observe the actual structure of discovered metadata caches."""
    
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    if not project_id:
        print("ERROR: GOOGLE_CLOUD_PROJECT not set")
        return False
    
    print("=" * 80)
    print("OBSERVATION: Metadata Cache Structure Analysis")
    print("=" * 80)
    
    # Step 1: Run metadata discovery
    print("\n1. Running metadata discovery...")
    success = initialize_metadata_cache(project_id, languages=['en-US'])
    
    if not success:
        print("   ✗ Metadata discovery failed")
        return False
    
    print("   ✓ Metadata discovery succeeded")
    
    # Step 2: Examine _AVAILABLE_LOCATIONS
    print("\n2. Examining _AVAILABLE_LOCATIONS:")
    locations = get_available_locations()
    print(f"   Total locations: {len(locations)}")
    print(f"   Locations: {sorted(locations)}")
    
    # Step 3: Examine _AVAILABLE_MODELS structure
    print("\n3. Examining _AVAILABLE_MODELS structure:")
    print("   (This is the key cache for building MODEL_REGION_CONFIG)")
    
    # Get models for a few locations to understand structure
    sample_locations = sorted(locations)[:5] if locations else []
    
    for location in sample_locations:
        models = get_available_models(location, 'en-US')
        print(f"   {location}: {sorted(models)}")
    
    # Step 4: Test cache inversion - model_id -> Set[locations]
    print("\n4. Testing cache inversion: model_id -> Set[locations]")
    print("   (This is what we need for MODEL_REGION_CONFIG)")
    
    # We need to access the internal cache to invert it
    # Let's use discover_speech_metadata directly to see the structure
    metadata = discover_speech_metadata(project_id, languages=['en-US'])
    
    models_by_location = metadata.get('models_by_location', {})
    print(f"   Total (location, language) combinations: {len(models_by_location)}")
    
    # Invert: model_id -> Set[locations]
    model_to_locations = {}
    for (location, language), model_ids in models_by_location.items():
        for model_id in model_ids:
            if model_id not in model_to_locations:
                model_to_locations[model_id] = set()
            model_to_locations[model_id].add(location)
    
    print(f"   Unique model IDs found: {len(model_to_locations)}")
    print("\n   Model -> Locations mapping:")
    for model_id, locs in sorted(model_to_locations.items()):
        print(f"     {model_id}: {sorted(locs)}")
    
    # Step 5: Compare with current MODEL_REGION_CONFIG
    print("\n5. Comparing with current MODEL_REGION_CONFIG:")
    current_config = {
        'chirp': ['us-central1', 'europe-west4', 'asia-southeast1'],
        'long': ['us-central1', 'us-west1', 'us-east1', 'europe-west1', 'asia-southeast1'],
        'short': ['us-central1', 'us-west1', 'us-east1', 'europe-west1', 'asia-southeast1']
    }
    
    print("   Current hardcoded config:")
    for model, regions in current_config.items():
        print(f"     {model}: {regions}")
    
    print("\n   Discovered from metadata:")
    for model_id in ['chirp', 'long', 'short', 'telephony', 'telephony_short']:
        if model_id in model_to_locations:
            discovered = sorted(model_to_locations[model_id])
            print(f"     {model_id}: {discovered}")
        else:
            print(f"     {model_id}: NOT FOUND in discovered metadata")
    
    # Step 6: Examine model name variations
    print("\n6. Examining model name variations:")
    all_model_ids = sorted(model_to_locations.keys())
    print(f"   All discovered model IDs: {all_model_ids}")
    
    # Check for variations
    chirp_variants = [m for m in all_model_ids if 'chirp' in m.lower()]
    long_variants = [m for m in all_model_ids if 'long' in m.lower()]
    short_variants = [m for m in all_model_ids if 'short' in m.lower()]
    
    if chirp_variants:
        print(f"   Chirp variants: {chirp_variants}")
    if long_variants:
        print(f"   Long variants: {long_variants}")
    if short_variants:
        print(f"   Short variants: {short_variants}")
    
    # Step 7: Examine REGION_PROXIMITY_MAP usage
    print("\n7. Understanding REGION_PROXIMITY_MAP:")
    print("   Current map structure: region -> [nearby_regions]")
    print("   Purpose: Find nearest supported region when requested region doesn't support model")
    print("   Need to understand: Is this geographic? Or just 'nearby in list'?")
    
    # Step 8: Test building MODEL_REGION_CONFIG dynamically
    print("\n8. Testing dynamic MODEL_REGION_CONFIG generation:")
    
    def build_model_region_config(model_to_locs):
        """Test function to build config from discovered data."""
        config = {}
        for model_id, locations in model_to_locs.items():
            locations_list = sorted(locations)
            config[model_id] = {
                'requires_regional': len(locations_list) > 0,
                'supported_regions': locations_list,
                'default_region': locations_list[0] if locations_list else 'us-central1'
            }
        return config
    
    dynamic_config = build_model_region_config(model_to_locations)
    
    print("   Sample dynamic config (first 3 models):")
    for i, (model_id, config) in enumerate(sorted(dynamic_config.items())[:3]):
        print(f"     {model_id}:")
        print(f"       requires_regional: {config['requires_regional']}")
        print(f"       supported_regions: {config['supported_regions'][:5]}...")  # First 5
        print(f"       default_region: {config['default_region']}")
    
    # Step 9: Questions to answer
    print("\n9. Questions to answer:")
    print("   [ ] Can we build MODEL_REGION_CONFIG from discovered metadata?")
    print("   [ ] How do we handle model name normalization? (chirp vs chirp_2)")
    print("   [ ] What does 'requires_regional' actually control?")
    print("   [ ] How should we choose default_region? (first? most common? specific logic?)")
    print("   [ ] Can we calculate proximity dynamically?")
    print("   [ ] What's the actual proximity logic? (geographic? naming-based?)")
    
    print("\n" + "=" * 80)
    print("OBSERVATION COMPLETE")
    print("=" * 80)
    
    return True


if __name__ == "__main__":
    success = observe_cache_structure()
    exit(0 if success else 1)

