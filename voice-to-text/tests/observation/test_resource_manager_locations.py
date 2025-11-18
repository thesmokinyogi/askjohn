#!/usr/bin/env python3
"""
Test script to check if Cloud Resource Manager API can list all locations.

This tests Option 3 approach.
"""

import os
from dotenv import load_dotenv
from google.auth import default
from google.auth.transport.requests import Request as AuthRequest
from google.auth import exceptions as auth_exceptions
import requests
import json
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

def test_resource_manager_api():
    """Test Cloud Resource Manager API for listing locations."""
    
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    if not project_id:
        print("ERROR: GOOGLE_CLOUD_PROJECT not set")
        return False
    
    print(f"Testing Cloud Resource Manager API for project: {project_id}\n")
    
    try:
        # Get credentials
        print("1. Getting credentials...")
        try:
            credentials, _ = default(scopes=['https://www.googleapis.com/auth/cloud-platform'])
            auth_request = AuthRequest()
            credentials.refresh(auth_request)
            token = credentials.token
            print("   ✓ Got auth token")
        except (auth_exceptions.DefaultCredentialsError, auth_exceptions.RefreshError) as e:
            print(f"   ✗ Auth failed: {e}")
            return False
        
        # Try different Resource Manager endpoints
        endpoints_to_try = [
            f"https://cloudresourcemanager.googleapis.com/v1/projects/{project_id}/locations",
            f"https://cloudresourcemanager.googleapis.com/v3/projects/{project_id}/locations",
            f"https://cloudresourcemanager.googleapis.com/v1/projects/{project_id}",
        ]
        
        for endpoint in endpoints_to_try:
            print(f"\n2. Trying endpoint: {endpoint}")
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            
            try:
                response = requests.get(endpoint, headers=headers, timeout=10)
                print(f"   Status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"   Response keys: {list(data.keys())}")
                    
                    # Check for locations
                    if 'locations' in data:
                        locations = data['locations']
                        print(f"   ✓ Found 'locations' key with {len(locations)} items")
                        if locations:
                            print(f"   First location: {locations[0]}")
                    elif 'name' in data:
                        print(f"   Response is project info, not locations list")
                    else:
                        print(f"   Response structure: {json.dumps(data, indent=2)[:500]}")
                else:
                    print(f"   Response: {response.text[:200]}")
                    
            except requests.exceptions.RequestException as e:
                print(f"   ✗ Request failed: {e}")
        
        print(f"\n3. Alternative: Try Compute Engine regions API")
        # Compute Engine has a regions API that lists all GCP regions
        compute_endpoint = "https://compute.googleapis.com/compute/v1/regions"
        print(f"   Endpoint: {compute_endpoint}")
        
        try:
            response = requests.get(compute_endpoint, headers=headers, timeout=10)
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                if 'items' in data:
                    regions = data['items']
                    region_names = [r['name'] for r in regions]
                    print(f"   ✓ Found {len(region_names)} Compute Engine regions")
                    print(f"   Sample regions: {region_names[:10]}")
                    
                    # Compare with known locations
                    compute_set = set(region_names)
                    matches = compute_set & KNOWN_LOCATIONS
                    print(f"\n   Comparison:")
                    print(f"   Matches with known locations: {len(matches)}")
                    if matches:
                        print(f"   {sorted(matches)}")
                    
                    missing = KNOWN_LOCATIONS - compute_set
                    if missing:
                        print(f"   Missing from Compute regions: {sorted(missing)}")
                else:
                    print(f"   Response structure: {json.dumps(data, indent=2)[:500]}")
            else:
                print(f"   Response: {response.text[:200]}")
        except requests.exceptions.RequestException as e:
            print(f"   ✗ Request failed: {e}")
        
        print(f"\n4. Conclusion:")
        print(f"   Need to find an API that lists all GCP regions/locations")
        print(f"   Then filter to only Speech V2 supported locations")
        
        return True
        
    except Exception as e:
        print(f"\n✗ ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_resource_manager_api()
    exit(0 if success else 1)

