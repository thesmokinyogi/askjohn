#!/usr/bin/env python3
"""
Test script to check what SDK list_locations() returns.

This will help us decide between:
- Option 2.5: SDK Only (if it returns all locations)
- Option 3: Cloud Resource Manager (if SDK doesn't return all)
"""

import os
from dotenv import load_dotenv
from google.cloud.speech_v2 import SpeechClient
from google.cloud.location import locations_pb2
import logging

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Known locations from hardcoded list (for comparison)
KNOWN_LOCATIONS = {
    'us', 'us-central1', 'us-east1', 'us-east4', 'us-west1', 'us-west2', 'us-west3', 'us-west4',
    'europe-west1', 'europe-west2', 'europe-west3', 'europe-west4', 'europe-west6',
    'asia-east1', 'asia-east2', 'asia-northeast1', 'asia-northeast2', 'asia-south1', 'asia-southeast1',
    'australia-southeast1', 'northamerica-northeast1', 'southamerica-east1'
}

def test_sdk_list_locations():
    """Test what SDK list_locations() returns."""
    
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    if not project_id:
        print("ERROR: GOOGLE_CLOUD_PROJECT not set")
        return False
    
    print(f"Testing SDK list_locations() for project: {project_id}\n")
    
    try:
        # Create client
        print("1. Creating SpeechClient...")
        client = SpeechClient()
        print("   ✓ Client created")
        
        # Query locations
        print("\n2. Querying locations...")
        request = locations_pb2.ListLocationsRequest(
            name=f"projects/{project_id}"
        )
        
        response = client.list_locations(request=request)
        print(f"   ✓ Got response")
        
        # Extract location IDs
        location_ids = [loc.location_id for loc in response.locations]
        location_set = set(location_ids)
        
        print(f"\n3. Results:")
        print(f"   Total locations returned: {len(location_ids)}")
        print(f"   Location IDs: {sorted(location_ids)}")
        
        # Compare with known locations
        print(f"\n4. Comparison with known locations:")
        print(f"   Known locations: {len(KNOWN_LOCATIONS)}")
        print(f"   SDK returned: {len(location_set)}")
        
        # Find matches
        matches = location_set & KNOWN_LOCATIONS
        missing_from_sdk = KNOWN_LOCATIONS - location_set
        extra_in_sdk = location_set - KNOWN_LOCATIONS
        
        print(f"\n5. Analysis:")
        print(f"   ✓ Matches: {len(matches)} locations")
        if matches:
            print(f"      {sorted(matches)}")
        
        if missing_from_sdk:
            print(f"\n   ⚠️  Missing from SDK ({len(missing_from_sdk)} locations):")
            print(f"      {sorted(missing_from_sdk)}")
            print(f"      → SDK doesn't return all known locations!")
        else:
            print(f"\n   ✅ All known locations found in SDK response!")
        
        if extra_in_sdk:
            print(f"\n   ℹ️  Extra locations in SDK ({len(extra_in_sdk)} locations):")
            print(f"      {sorted(extra_in_sdk)}")
            print(f"      → SDK found additional locations!")
        
        # Check location objects
        print(f"\n6. Location object details:")
        if response.locations:
            first_loc = response.locations[0]
            print(f"   First location ID: {first_loc.location_id}")
            print(f"   First location name: {first_loc.name}")
            print(f"   Has metadata: {first_loc.metadata is not None}")
            if first_loc.metadata:
                print(f"   Metadata type: {type(first_loc.metadata)}")
        
        # Decision
        print(f"\n7. Decision:")
        if not missing_from_sdk:
            print(f"   ✅ Option 2.5 (SDK Only) will work!")
            print(f"      SDK returns all known locations, no hardcoded list needed.")
        else:
            print(f"   ⚠️  Option 2.5 (SDK Only) may miss some locations")
            print(f"      Missing: {sorted(missing_from_sdk)}")
            print(f"      Consider Option 3 (Cloud Resource Manager) instead")
        
        return True
        
    except Exception as e:
        print(f"\n✗ ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_sdk_list_locations()
    exit(0 if success else 1)

