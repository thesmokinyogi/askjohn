#!/usr/bin/env python3
"""
Test Pydantic models for the refactored system.

Tests request/response models independently to verify validation boundaries.
"""

import sys
import json
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pydantic import ValidationError
from app.models.requests import TranscribeRequest, EstimateCostRequest, EstimateProcessingTimeRequest
from app.models.responses import (
    TranscriptionResponse, JobStatusResponse, JobListResponse,
    BudgetResponse, ErrorResponse, SuccessResponse,
    ProcessingTimeEstimateResponse, CostEstimateResponse,
    LibraryEntryResponse, LibraryListResponse
)
from app.models.job import JobModel, JobStatus


def test_transcribe_request():
    """Test TranscribeRequest model validation."""
    print("\n=== Testing TranscribeRequest ===")
    
    # Valid cases
    print("✓ Valid model: chirp_batch")
    req = TranscribeRequest(model="chirp_batch")
    assert req.model == "chirp_batch"
    
    print("✓ Valid model: long_standard")
    req = TranscribeRequest(model="long_standard")
    assert req.model == "long_standard"
    
    print("✓ None model (optional)")
    req = TranscribeRequest(model=None)
    assert req.model is None
    
    # Invalid cases
    print("✗ Invalid model: invalid_model")
    try:
        req = TranscribeRequest(model="invalid_model")
        assert False, "Should have raised ValidationError"
    except ValidationError as e:
        assert "Invalid model" in str(e.errors()[0]['msg'])
        print(f"  ✓ Correctly rejected: {e.errors()[0]['msg']}")
    
    print("✓ All TranscribeRequest tests passed")


def test_estimate_cost_request():
    """Test EstimateCostRequest model validation."""
    print("\n=== Testing EstimateCostRequest ===")
    
    # Valid cases
    print("✓ Valid request")
    req = EstimateCostRequest(
        provider="google",
        model="chirp_batch",
        duration_minutes=5.0
    )
    assert req.duration_minutes == 5.0
    
    # Invalid cases
    print("✗ Negative duration")
    try:
        req = EstimateCostRequest(
            provider="google",
            model="chirp_batch",
            duration_minutes=-1.0
        )
        assert False, "Should have raised ValidationError"
    except ValidationError as e:
        assert "greater than 0" in str(e.errors()[0]['msg']).lower()
        print(f"  ✓ Correctly rejected: {e.errors()[0]['msg']}")
    
    print("✗ Zero duration")
    try:
        req = EstimateCostRequest(
            provider="google",
            model="chirp_batch",
            duration_minutes=0.0
        )
        assert False, "Should have raised ValidationError"
    except ValidationError as e:
        assert "greater than 0" in str(e.errors()[0]['msg']).lower()
        print(f"  ✓ Correctly rejected: {e.errors()[0]['msg']}")
    
    print("✓ All EstimateCostRequest tests passed")


def test_estimate_processing_time_request():
    """Test EstimateProcessingTimeRequest model validation."""
    print("\n=== Testing EstimateProcessingTimeRequest ===")
    
    # Valid cases
    print("✓ Valid request")
    req = EstimateProcessingTimeRequest(
        model="chirp_batch",
        duration_minutes=5.0
    )
    assert req.model == "chirp_batch"
    assert req.duration_minutes == 5.0
    
    # Invalid cases
    print("✗ Missing model (required)")
    try:
        req = EstimateProcessingTimeRequest(duration_minutes=5.0)
        assert False, "Should have raised ValidationError"
    except ValidationError as e:
        print(f"  ✓ Correctly rejected: {e.errors()[0]['msg']}")
    
    print("✗ Negative duration")
    try:
        req = EstimateProcessingTimeRequest(
            model="chirp_batch",
            duration_minutes=-1.0
        )
        assert False, "Should have raised ValidationError"
    except ValidationError as e:
        assert "greater than 0" in str(e.errors()[0]['msg']).lower()
        print(f"  ✓ Correctly rejected: {e.errors()[0]['msg']}")
    
    print("✓ All EstimateProcessingTimeRequest tests passed")


def test_response_models():
    """Test response model serialization."""
    print("\n=== Testing Response Models ===")
    
    # TranscriptionResponse
    print("✓ TranscriptionResponse serialization")
    response = TranscriptionResponse(
        job_id="test_job_123",
        status=JobStatus.QUEUED,
        filename="test.mp3",
        model="chirp_batch",
        duration_minutes=5.0,
        estimated_cost=0.02,
        submitted_at=datetime.now(),
        check_status_url="/api/v1/jobs/test_job_123"
    )
    json_str = response.json()
    data = json.loads(json_str)
    assert data["job_id"] == "test_job_123"
    assert data["status"] == "queued"
    print("  ✓ Valid JSON structure")
    
    # JobStatusResponse with all fields
    print("✓ JobStatusResponse with all fields")
    response = JobStatusResponse(
        job_id="test_job_123",
        status=JobStatus.COMPLETE,
        filename="test.mp3",
        model="chirp_batch",
        submitted_at=datetime.now(),
        completed_at=datetime.now(),
        transcript="Hello world",
        confidence=0.95,
        actual_cost=0.02,
        in_library=True,
        library_id="lib_123"
    )
    json_str = response.json()
    data = json.loads(json_str)
    assert data["transcript"] == "Hello world"
    assert data["confidence"] == 0.95
    print("  ✓ Valid JSON structure")
    
    # JobStatusResponse with None fields
    print("✓ JobStatusResponse with None fields")
    response = JobStatusResponse(
        job_id="test_job_123",
        status=JobStatus.QUEUED,
        filename="test.mp3",
        model="chirp_batch",
        submitted_at=datetime.now(),
        transcript=None,
        confidence=None,
        actual_cost=None
    )
    json_str = response.json()
    data = json.loads(json_str)
    assert data["transcript"] is None
    assert data["confidence"] is None
    print("  ✓ Valid JSON structure with None fields")
    
    # ErrorResponse
    print("✓ ErrorResponse structure")
    response = ErrorResponse(
        error={
            "code": "INVALID_REQUEST",
            "message": "Invalid file type",
            "details": {"field": "file"},
            "request_id": "req_123"
        }
    )
    json_str = response.json()
    data = json.loads(json_str)
    assert "error" in data
    assert data["error"]["code"] == "INVALID_REQUEST"
    print("  ✓ Valid error format")
    
    # SuccessResponse
    print("✓ SuccessResponse structure")
    response = SuccessResponse(
        success=True,
        message="Job deleted successfully",
        job_id="test_job_123"
    )
    json_str = response.json()
    data = json.loads(json_str)
    assert data["success"] is True
    assert data["message"] == "Job deleted successfully"
    print("  ✓ Valid success format")
    
    # ProcessingTimeEstimateResponse
    print("✓ ProcessingTimeEstimateResponse")
    response = ProcessingTimeEstimateResponse(
        estimated_seconds=120.0,
        confidence="high",
        base_time_seconds=30.0,
        rate_per_minute_seconds=18.0,
        sample_count=10,
        r_squared=0.95
    )
    json_str = response.json()
    data = json.loads(json_str)
    assert data["estimated_seconds"] == 120.0
    assert data["confidence"] == "high"
    print("  ✓ Valid JSON structure")
    
    # CostEstimateResponse
    print("✓ CostEstimateResponse")
    response = CostEstimateResponse(
        total_cost=0.02,
        cost_per_minute=0.004,
        billable_minutes=5.0,
        free_minutes_used=0.0,
        free_tier_remaining=60.0
    )
    json_str = response.json()
    data = json.loads(json_str)
    assert data["total_cost"] == 0.02
    print("  ✓ Valid JSON structure")
    
    print("✓ All response model tests passed")


def test_job_model():
    """Test JobModel domain model."""
    print("\n=== Testing JobModel ===")
    
    # Valid JobModel with all required fields
    print("✓ JobModel with all required fields")
    job = JobModel(
        job_id="test_job_123",
        filename="test.mp3",
        model="chirp_batch",
        status=JobStatus.QUEUED,
        submitted_at=datetime.now()
    )
    assert job.job_id == "test_job_123"
    assert job.status == JobStatus.QUEUED
    print("  ✓ Accepts all required fields")
    
    # JobModel with optional fields
    print("✓ JobModel with optional fields")
    job = JobModel(
        job_id="test_job_123",
        filename="test.mp3",
        model="chirp_batch",
        tier="batch",
        status=JobStatus.COMPLETE,
        submitted_at=datetime.now(),
        duration_minutes=5.0,
        estimated_cost=0.02,
        gcs_uri="gs://bucket/test.mp3",
        completed_at=datetime.now(),
        transcript="Hello world",
        confidence=0.95,
        actual_cost=0.02,
        in_library=True,
        library_id="lib_123"
    )
    assert job.tier == "batch"
    assert job.confidence == 0.95
    print("  ✓ Accepts optional fields")
    
    # JobModel serialization
    print("✓ JobModel serialization")
    json_str = job.json()
    data = json.loads(json_str)
    assert data["job_id"] == "test_job_123"
    assert data["status"] == "complete"
    print("  ✓ Valid JSON structure")
    
    # JobStatus enum values
    print("✓ JobStatus enum values")
    assert JobStatus.QUEUED == "queued"
    assert JobStatus.PROCESSING == "processing"
    assert JobStatus.COMPLETE == "complete"
    assert JobStatus.FAILED == "failed"
    print("  ✓ All enum values valid")
    
    print("✓ All JobModel tests passed")


def main():
    """Run all model tests."""
    print("=" * 60)
    print("Testing Refactored System Pydantic Models")
    print("=" * 60)
    
    try:
        test_transcribe_request()
        test_estimate_cost_request()
        test_estimate_processing_time_request()
        test_response_models()
        test_job_model()
        
        print("\n" + "=" * 60)
        print("✅ ALL MODEL TESTS PASSED")
        print("=" * 60)
        return 0
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

