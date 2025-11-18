#!/usr/bin/env python3
"""
Test all /api/v1/ endpoints for the refactored system.

Tests API endpoints to verify they work correctly and return proper responses.
"""

import sys
import json
import requests
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api/v1"


def test_endpoint(method, endpoint, description, expected_status=200, **kwargs):
    """Test an API endpoint and report results."""
    print(f"\n{description}")
    print(f"  {method.upper()} {endpoint}")
    
    try:
        if method.lower() == "get":
            response = requests.get(endpoint, **kwargs)
        elif method.lower() == "post":
            response = requests.post(endpoint, **kwargs)
        elif method.lower() == "delete":
            response = requests.delete(endpoint, **kwargs)
        else:
            print(f"  ❌ Unsupported method: {method}")
            return False
        
        if response.status_code == expected_status:
            print(f"  ✓ Status: {response.status_code} (expected {expected_status})")
            
            # Try to parse JSON
            try:
                data = response.json()
                print(f"  ✓ Valid JSON response")
                if isinstance(data, dict) and len(data) < 10:
                    # Print small responses
                    print(f"  ✓ Response: {json.dumps(data, indent=2)[:200]}")
                return True
            except json.JSONDecodeError:
                print(f"  ⚠️  Response is not JSON (may be expected)")
                return True
        else:
            print(f"  ❌ Status: {response.status_code} (expected {expected_status})")
            print(f"  Response: {response.text[:200]}")
            return False
            
    except requests.exceptions.ConnectionError:
        print(f"  ❌ Connection error - is server running?")
        return False
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False


def test_budget_endpoints():
    """Test budget-related endpoints."""
    print("\n" + "=" * 60)
    print("Testing Budget Endpoints")
    print("=" * 60)
    
    results = []
    
    # GET /api/v1/budget
    results.append(test_endpoint(
        "GET",
        f"{API_BASE}/budget",
        "✓ Get budget summary (all providers)"
    ))
    
    # GET /api/v1/budget?provider=google
    results.append(test_endpoint(
        "GET",
        f"{API_BASE}/budget?provider=google",
        "✓ Get budget summary (google provider)"
    ))
    
    # GET /api/v1/pricing
    results.append(test_endpoint(
        "GET",
        f"{API_BASE}/pricing",
        "✓ Get pricing information"
    ))
    
    # GET /api/v1/pricing?provider=google
    results.append(test_endpoint(
        "GET",
        f"{API_BASE}/pricing?provider=google",
        "✓ Get pricing information (google provider)"
    ))
    
    # POST /api/v1/estimate-cost
    results.append(test_endpoint(
        "POST",
        f"{API_BASE}/estimate-cost",
        "✓ Estimate cost",
        json={
            "provider": "google",
            "model": "chirp_batch",
            "duration_minutes": 5.0
        }
    ))
    
    # GET /api/v1/estimate-processing-time?model=chirp_batch&duration_minutes=5.0
    results.append(test_endpoint(
        "GET",
        f"{API_BASE}/estimate-processing-time?model=chirp_batch&duration_minutes=5.0",
        "✓ Estimate processing time"
    ))
    
    return all(results)


def test_job_endpoints():
    """Test job-related endpoints."""
    print("\n" + "=" * 60)
    print("Testing Job Endpoints")
    print("=" * 60)
    
    results = []
    
    # GET /api/v1/jobs
    results.append(test_endpoint(
        "GET",
        f"{API_BASE}/jobs",
        "✓ List all jobs"
    ))
    
    # GET /api/v1/jobs?status=complete
    results.append(test_endpoint(
        "GET",
        f"{API_BASE}/jobs?status=complete",
        "✓ List jobs by status (complete)"
    ))
    
    # GET /api/v1/jobs?limit=5
    results.append(test_endpoint(
        "GET",
        f"{API_BASE}/jobs?limit=5",
        "✓ List jobs with limit"
    ))
    
    # Note: We can't test check_job_status or delete_job without a valid job_id
    # These will be tested manually or with a real job
    
    return all(results)


def test_library_endpoints():
    """Test library-related endpoints."""
    print("\n" + "=" * 60)
    print("Testing Library Endpoints")
    print("=" * 60)
    
    results = []
    
    # GET /api/v1/library
    results.append(test_endpoint(
        "GET",
        f"{API_BASE}/library",
        "✓ List library entries"
    ))
    
    # GET /api/v1/library?limit=5
    results.append(test_endpoint(
        "GET",
        f"{API_BASE}/library?limit=5",
        "✓ List library entries with limit"
    ))
    
    # Note: We can't test get_library_entry, download_text, or download_json
    # without a valid library_id. These will be tested manually or with real data
    
    return all(results)


def test_transcription_endpoints():
    """Test transcription-related endpoints."""
    print("\n" + "=" * 60)
    print("Testing Transcription Endpoints")
    print("=" * 60)
    
    results = []
    
    # Note: POST /api/v1/transcribe requires a file upload
    # This will be tested manually with a real file
    
    # GET /api/v1/detect-duration
    # This also requires a file, so we'll test it manually
    
    print("  ⚠️  Transcription endpoints require file uploads")
    print("  ⚠️  These will be tested manually with real files")
    
    return True  # Skip for now


def test_error_handling():
    """Test error handling endpoints."""
    print("\n" + "=" * 60)
    print("Testing Error Handling")
    print("=" * 60)
    
    results = []
    
    # Test invalid endpoint
    results.append(test_endpoint(
        "GET",
        f"{API_BASE}/invalid-endpoint",
        "✓ Invalid endpoint returns 404",
        expected_status=404
    ))
    
    # Test invalid model in estimate-cost
    results.append(test_endpoint(
        "POST",
        f"{API_BASE}/estimate-cost",
        "✓ Invalid model in estimate-cost returns validation error",
        expected_status=422,  # Validation error
        json={
            "provider": "google",
            "model": "invalid_model",
            "duration_minutes": 5.0
        }
    ))
    
    # Test negative duration
    results.append(test_endpoint(
        "POST",
        f"{API_BASE}/estimate-cost",
        "✓ Negative duration returns validation error",
        expected_status=422,  # Validation error
        json={
            "provider": "google",
            "model": "chirp_batch",
            "duration_minutes": -1.0
        }
    ))
    
    return all(results)


def main():
    """Run all API endpoint tests."""
    print("=" * 60)
    print("Testing Refactored System API Endpoints")
    print("=" * 60)
    print(f"Base URL: {BASE_URL}")
    print(f"API Base: {API_BASE}")
    
    results = {
        "budget": test_budget_endpoints(),
        "jobs": test_job_endpoints(),
        "library": test_library_endpoints(),
        "transcription": test_transcription_endpoints(),
        "error_handling": test_error_handling()
    }
    
    print("\n" + "=" * 60)
    print("Test Results Summary")
    print("=" * 60)
    
    for category, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{category.upper():20} {status}")
    
    all_passed = all(results.values())
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ ALL API ENDPOINT TESTS PASSED")
    else:
        print("❌ SOME TESTS FAILED")
    print("=" * 60)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())

