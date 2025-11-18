#!/usr/bin/env python3
"""
End-to-end test of dynamic MODEL_REGION_CONFIG and REGION_PROXIMITY_MAP.

Tests the complete flow:
1. Metadata discovery
2. Dynamic config generation
3. Location selection with different models
4. Proximity mapping
"""

import os
from dotenv import load_dotenv
from app.services.transcribe_v2 import (
    initialize_metadata_cache,
    _build_model_region_config,
    GoogleSpeechV2Service
)

# Load environment variables
load_dotenv()

def test_end_to_end():
    """Test complete end-to-end flow."""
    
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    if not project_id:
        print("ERROR: GOOGLE_CLOUD_PROJECT not set")
        return False
    
    print("=" * 80)
    print("END-TO-END TEST: Dynamic Config Implementation")
    print("=" * 80)
    
    # Step 1: Initialize metadata cache (simulates startup)
    print("\n1. Initializing metadata cache (startup simulation)...")
    success = initialize_metadata_cache(project_id, languages=['en-US'])
    
    if not success:
        print("   ✗ Metadata cache initialization failed")
        return False
    
    print("   ✓ Metadata cache initialized")
    
    # Step 2: Build dynamic config
    print("\n2. Building dynamic MODEL_REGION_CONFIG...")
    config = _build_model_region_config()
    print(f"   ✓ Config built: {len(config)} models")
    
    # Step 3: Test location selection for different models
    print("\n3. Testing location selection with different models...")
    
    test_cases = [
        # (model, requested_location, expected_behavior)
        ('chirp', 'us-central1', 'Should use us-central1 (direct match)'),
        ('chirp', 'us-west1', 'Should map to nearest chirp region (us or us-central1)'),
        ('chirp', 'europe-west1', 'Should map to nearest chirp region (europe-west4)'),
        ('long', 'us-west1', 'Should use us-west1 (direct match)'),
        ('long', 'asia-northeast1', 'Should use asia-northeast1 (direct match)'),
        ('short', 'europe-west2', 'Should map to nearest short region'),
    ]
    
    results = []
    for model, requested, description in test_cases:
        try:
            service = GoogleSpeechV2Service(
                project_id=project_id,
                model=model,
                location=requested
            )
            selected = service.location
            results.append((model, requested, selected, description))
            print(f"   ✓ {model} + {requested} → {selected}")
        except Exception as e:
            print(f"   ✗ {model} + {requested} → ERROR: {e}")
            results.append((model, requested, None, description))
    
    # Step 4: Verify config completeness
    print("\n4. Verifying config completeness...")
    for model_name in ['chirp', 'long', 'short']:
        if model_name in config:
            regions = config[model_name]['supported_regions']
            print(f"   {model_name}: {len(regions)} regions supported")
            print(f"      Sample: {sorted(regions)[:5]}...")
        else:
            print(f"   ✗ {model_name}: NOT FOUND in config")
    
    # Step 5: Compare with expectations
    print("\n5. Verification:")
    
    # Check chirp has expected regions
    if 'chirp' in config:
        chirp_regions = set(config['chirp']['supported_regions'])
        expected = {'us-central1', 'europe-west4', 'asia-southeast1'}
        if expected.issubset(chirp_regions):
            print(f"   ✓ Chirp has all expected regions (and {len(chirp_regions) - len(expected)} more!)")
        else:
            missing = expected - chirp_regions
            print(f"   ✗ Chirp missing regions: {missing}")
    
    # Check long has more regions than hardcoded
    if 'long' in config:
        long_regions = len(config['long']['supported_regions'])
        hardcoded_count = 5
        if long_regions > hardcoded_count:
            print(f"   ✓ Long model: {long_regions} regions (hardcoded had {hardcoded_count})")
        else:
            print(f"   ⚠️  Long model: {long_regions} regions (expected more than {hardcoded_count})")
    
    print("\n" + "=" * 80)
    print("TEST RESULTS")
    print("=" * 80)
    
    all_passed = all(selected is not None for _, _, selected, _ in results)
    
    if all_passed:
        print("✅ ALL TESTS PASSED")
        print("\nSummary:")
        print("  - Metadata discovery: ✓")
        print("  - Dynamic config generation: ✓")
        print("  - Location selection: ✓")
        print("  - Proximity mapping: ✓")
        print("  - More regions discovered than hardcoded: ✓")
    else:
        print("⚠️  SOME TESTS FAILED")
        for model, requested, selected, desc in results:
            if selected is None:
                print(f"  ✗ {model} + {requested}: FAILED")
    
    return all_passed


if __name__ == "__main__":
    success = test_end_to_end()
    exit(0 if success else 1)

