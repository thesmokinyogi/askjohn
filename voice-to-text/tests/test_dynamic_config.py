#!/usr/bin/env python3
"""
Test script to verify dynamic MODEL_REGION_CONFIG generation works.

Following: WORKING_AGREEMENT.md - "Verify Before Trust"
"""

import os
from dotenv import load_dotenv
from app.services.transcribe_v2 import (
    initialize_metadata_cache,
    _build_model_region_config,
    _choose_default_region,
    GoogleSpeechV2Service
)

# Load environment variables
load_dotenv()

def test_dynamic_config():
    """Test that dynamic config generation works correctly."""
    
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    if not project_id:
        print("ERROR: GOOGLE_CLOUD_PROJECT not set")
        return False
    
    print("=" * 80)
    print("TESTING: Dynamic MODEL_REGION_CONFIG Generation")
    print("=" * 80)
    
    # Step 1: Initialize metadata cache
    print("\n1. Initializing metadata cache...")
    success = initialize_metadata_cache(project_id, languages=['en-US'])
    
    if not success:
        print("   ✗ Metadata cache initialization failed")
        return False
    
    print("   ✓ Metadata cache initialized")
    
    # Step 2: Build dynamic config
    print("\n2. Building dynamic MODEL_REGION_CONFIG...")
    try:
        config = _build_model_region_config()
        print(f"   ✓ Config built successfully")
        print(f"   Models in config: {sorted(config.keys())}")
    except Exception as e:
        print(f"   ✗ Error building config: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Step 3: Verify config structure
    print("\n3. Verifying config structure...")
    for model_name, model_config in sorted(config.items()):
        print(f"\n   {model_name}:")
        print(f"     requires_regional: {model_config.get('requires_regional')}")
        print(f"     supported_regions: {len(model_config.get('supported_regions', []))} regions")
        print(f"       {sorted(model_config.get('supported_regions', []))[:5]}...")  # First 5
        print(f"     default_region: {model_config.get('default_region')}")
    
    # Step 4: Test default region selection
    print("\n4. Testing default region selection...")
    test_cases = [
        (['us-central1', 'europe-west4', 'asia-southeast1'], 'us-central1'),
        (['europe-west4', 'asia-southeast1'], 'europe-west4'),  # No us-central1
        (['asia-southeast1'], 'asia-southeast1'),  # Only one
    ]
    
    for locations, expected in test_cases:
        result = _choose_default_region(locations)
        status = "✓" if result == expected else "✗"
        print(f"   {status} {locations} → {result} (expected {expected})")
    
    # Step 5: Test location selection with dynamic config
    print("\n5. Testing location selection with dynamic config...")
    try:
        service = GoogleSpeechV2Service(
            project_id=project_id,
            model='chirp',
            location='us-west1'  # Not in chirp's supported regions
        )
        print(f"   ✓ Service initialized")
        print(f"   Selected location: {service.location}")
        print(f"   (Should map us-west1 to nearest chirp region)")
    except Exception as e:
        print(f"   ✗ Error creating service: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Step 6: Compare with hardcoded config
    print("\n6. Comparing with hardcoded config:")
    hardcoded_chirp = ['us-central1', 'europe-west4', 'asia-southeast1']
    dynamic_chirp = sorted(config.get('chirp', {}).get('supported_regions', []))
    
    print(f"   Hardcoded chirp regions: {hardcoded_chirp}")
    print(f"   Dynamic chirp regions: {dynamic_chirp}")
    
    if set(hardcoded_chirp) == set(dynamic_chirp):
        print("   ✓ Regions match!")
    else:
        missing = set(hardcoded_chirp) - set(dynamic_chirp)
        extra = set(dynamic_chirp) - set(hardcoded_chirp)
        if missing:
            print(f"   ⚠️  Missing in dynamic: {missing}")
        if extra:
            print(f"   ✅ Extra in dynamic (better!): {extra}")
    
    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)
    
    return True


if __name__ == "__main__":
    success = test_dynamic_config()
    exit(0 if success else 1)

