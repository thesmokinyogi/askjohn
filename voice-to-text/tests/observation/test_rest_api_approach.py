#!/usr/bin/env python3
"""
Minimal test script to verify REST API approach before implementation.

This tests the exact pattern we'll use in discover_speech_metadata().
"""

import os
from dotenv import load_dotenv
from google.auth import default
from google.auth.transport.requests import Request as AuthRequest
import requests
import json

# Load environment variables
load_dotenv()

def test_rest_api_discovery():
    """Test REST API approach for metadata discovery."""
    
    # Get project ID from environment
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    if not project_id:
        print("ERROR: GOOGLE_CLOUD_PROJECT not set")
        return False
    
    print(f"Testing REST API discovery for project: {project_id}")
    
    # Test region
    test_region = "us-west1"
    
    try:
        # Get credentials with explicit scopes (G.2 approach that worked)
        print(f"\n1. Getting credentials with explicit scopes...")
        credentials, _ = default(scopes=['https://www.googleapis.com/auth/cloud-platform'])
        auth_request = AuthRequest()
        credentials.refresh(auth_request)
        token = credentials.token
        print(f"   ✓ Got auth token")
        
        # Build REST API URL
        rest_url = f"https://{test_region}-speech.googleapis.com/v2/projects/{project_id}/locations/{test_region}"
        print(f"\n2. REST endpoint: {rest_url}")
        
        # Make request
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        print(f"3. Making GET request...")
        response = requests.get(rest_url, headers=headers, timeout=10)
        response.raise_for_status()
        print(f"   ✓ Request succeeded! Status: {response.status_code}")
        
        # Parse response
        data = response.json()
        print(f"\n4. Parsing response structure...")
        
        # Verify structure matches observed pattern
        if 'metadata' not in data:
            print(f"   ✗ ERROR: 'metadata' not found in response")
            print(f"   Response keys: {list(data.keys())}")
            return False
        
        metadata = data['metadata']
        print(f"   ✓ 'metadata' found")
        
        if 'languages' not in metadata:
            print(f"   ✗ ERROR: 'languages' not found in metadata")
            print(f"   Metadata keys: {list(metadata.keys())}")
            return False
        
        languages_obj = metadata['languages']
        print(f"   ✓ 'languages' found")
        
        if 'models' not in languages_obj:
            print(f"   ✗ ERROR: 'models' not found in languages")
            print(f"   Languages keys: {list(languages_obj.keys())}")
            return False
        
        models_by_lang = languages_obj['models']
        print(f"   ✓ 'models' container found")
        print(f"   Number of languages: {len(models_by_lang)}")
        
        # Test extracting features for en-US
        if 'en-US' not in models_by_lang:
            print(f"   ✗ ERROR: 'en-US' not found in models")
            print(f"   Available languages: {list(models_by_lang.keys())[:10]}")
            return False
        
        lang_data = models_by_lang['en-US']
        print(f"   ✓ 'en-US' found")
        
        if 'modelFeatures' not in lang_data:
            print(f"   ✗ ERROR: 'modelFeatures' not found in en-US data")
            print(f"   en-US keys: {list(lang_data.keys())}")
            return False
        
        model_features = lang_data['modelFeatures']
        print(f"   ✓ 'modelFeatures' container found")
        
        if not isinstance(model_features, dict):
            print(f"   ✗ ERROR: modelFeatures is not a dict")
            return False
        
        model_ids = list(model_features.keys())
        print(f"   ✓ Model IDs found: {model_ids[:5]}...")
        
        # Test extracting features from first model
        if not model_ids:
            print(f"   ✗ ERROR: No models found")
            return False
        
        first_model_id = model_ids[0]
        model_data = model_features[first_model_id]
        
        if 'modelFeature' not in model_data:
            print(f"   ✗ ERROR: 'modelFeature' not found in {first_model_id}")
            print(f"   Model keys: {list(model_data.keys())}")
            return False
        
        feature_list = model_data['modelFeature']
        print(f"   ✓ 'modelFeature' array found in {first_model_id}")
        print(f"   Number of features: {len(feature_list)}")
        
        # Extract feature names
        feature_names = []
        for feature_obj in feature_list:
            if isinstance(feature_obj, dict):
                feature_name = feature_obj.get('feature')
                if feature_name:
                    feature_names.append(feature_name)
        
        print(f"   ✓ Extracted {len(feature_names)} feature names")
        print(f"   First 5 features: {feature_names[:5]}")
        
        print(f"\n✅ SUCCESS! REST API approach works correctly.")
        print(f"   Structure path verified: metadata['languages']['models'][lang_code]['modelFeatures'][model_id]['modelFeature']")
        return True
        
    except Exception as e:
        print(f"\n✗ ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_rest_api_discovery()
    exit(0 if success else 1)

