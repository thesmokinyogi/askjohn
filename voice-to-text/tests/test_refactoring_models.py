#!/usr/bin/env python3
"""
Test Pydantic models for refactoring.

Tests model validation, type checking, and basic structure.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime
from app.models import (
    TranscriptionResponse,
    JobStatusResponse,
    JobStatus,
    TranscribeRequest,
    EstimateCostRequest,
    EstimateProcessingTimeRequest,
    ErrorResponse,
    SuccessResponse,
)


def test_transcribe_request():
    """Test TranscribeRequest model."""
    print("Testing TranscribeRequest...")
    
    # Valid request
    req = TranscribeRequest(model="long_standard")
    assert req.model == "long_standard"
    print("  ✓ Valid model accepted")
    
    # None model (optional)
    req = TranscribeRequest(model=None)
    assert req.model is None
    print("  ✓ None model accepted")
    
    # Invalid model
    try:
        req = TranscribeRequest(model="invalid_model")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "Invalid model" in str(e)
        print("  ✓ Invalid model rejected")
    
    print("  ✓ TranscribeRequest tests passed\n")


def test_estimate_cost_request():
    """Test EstimateCostRequest model."""
    print("Testing EstimateCostRequest...")
    
    # Valid request
    req = EstimateCostRequest(
        provider="google",
        model="chirp_batch",
        duration_minutes=75.0
    )
    assert req.duration_minutes == 75.0
    print("  ✓ Valid request accepted")
    
    # Invalid duration (must be > 0)
    try:
        req = EstimateCostRequest(duration_minutes=0)
        assert False, "Should have raised ValidationError"
    except Exception as e:
        assert "greater than 0" in str(e).lower() or "gt" in str(e).lower()
        print("  ✓ Invalid duration rejected")
    
    print("  ✓ EstimateCostRequest tests passed\n")


def test_transcription_response():
    """Test TranscriptionResponse model."""
    print("Testing TranscriptionResponse...")
    
    # Valid response
    response = TranscriptionResponse(
        job_id="projects/123/operations/456",
        status=JobStatus.QUEUED,
        filename="test.mp3",
        model="long_standard",
        duration_minutes=5.0,
        estimated_cost=0.08,
        submitted_at=datetime.now(),
        check_status_url="/api/jobs/123/status"
    )
    assert response.job_id == "projects/123/operations/456"
    assert response.status == JobStatus.QUEUED
    print("  ✓ Valid response created")
    
    # Invalid cost (must be >= 0)
    try:
        response = TranscriptionResponse(
            job_id="test",
            status=JobStatus.QUEUED,
            filename="test.mp3",
            model="long",
            duration_minutes=5.0,
            estimated_cost=-1.0,  # Invalid
            submitted_at=datetime.now(),
            check_status_url="/api/jobs/123/status"
        )
        assert False, "Should have raised ValidationError"
    except Exception as e:
        assert "greater than or equal to 0" in str(e).lower() or "ge" in str(e).lower()
        print("  ✓ Invalid cost rejected")
    
    print("  ✓ TranscriptionResponse tests passed\n")


def test_job_status_response():
    """Test JobStatusResponse model."""
    print("Testing JobStatusResponse...")
    
    # Complete job
    response = JobStatusResponse(
        job_id="test",
        status=JobStatus.COMPLETE,
        filename="test.mp3",
        model="long",
        submitted_at=datetime.now(),
        transcript="Hello world",
        confidence=0.95,
        actual_cost=0.08,
        completed_at=datetime.now()
    )
    assert response.transcript == "Hello world"
    assert response.confidence == 0.95
    print("  ✓ Complete job response created")
    
    # Processing job
    response = JobStatusResponse(
        job_id="test",
        status=JobStatus.PROCESSING,
        filename="test.mp3",
        model="long",
        submitted_at=datetime.now(),
        message="Transcription in progress"
    )
    assert response.message == "Transcription in progress"
    print("  ✓ Processing job response created")
    
    # Invalid confidence (must be 0-1)
    try:
        response = JobStatusResponse(
            job_id="test",
            status=JobStatus.COMPLETE,
            filename="test.mp3",
            model="long",
            submitted_at=datetime.now(),
            confidence=1.5  # Invalid
        )
        assert False, "Should have raised ValidationError"
    except Exception as e:
        assert "less than or equal to 1" in str(e).lower() or "le" in str(e).lower()
        print("  ✓ Invalid confidence rejected")
    
    print("  ✓ JobStatusResponse tests passed\n")


def test_error_response():
    """Test ErrorResponse model."""
    print("Testing ErrorResponse...")
    
    error = ErrorResponse(
        error={
            "code": "INVALID_REQUEST",
            "message": "Invalid file type",
            "details": {"field": "file"},
            "request_id": "req_123"
        }
    )
    assert error.error["code"] == "INVALID_REQUEST"
    print("  ✓ Error response created")
    
    print("  ✓ ErrorResponse tests passed\n")


def test_success_response():
    """Test SuccessResponse model."""
    print("Testing SuccessResponse...")
    
    success = SuccessResponse(
        success=True,
        message="Job deleted successfully",
        job_id="projects/123/operations/456"
    )
    assert success.success is True
    assert success.job_id == "projects/123/operations/456"
    print("  ✓ Success response created")
    
    print("  ✓ SuccessResponse tests passed\n")


def test_model_imports():
    """Test that all models can be imported."""
    print("Testing model imports...")
    
    try:
        from app.models import (
            TranscriptionResponse,
            JobStatusResponse,
            JobListResponse,
            JobStatsResponse,
            LibraryListResponse,
            LibraryEntryResponse,
            BudgetResponse,
            PricingResponse,
            ProcessingTimeEstimateResponse,
            CostEstimateResponse,
            AudioMetadataResponse,
            ErrorResponse,
            SuccessResponse,
            TranscribeRequest,
            EstimateCostRequest,
            EstimateProcessingTimeRequest,
            JobStatus,
            JobModel,
        )
        print("  ✓ All models imported successfully")
    except ImportError as e:
        print(f"  ✗ Import error: {e}")
        raise
    
    print("  ✓ Import tests passed\n")


def main():
    """Run all tests."""
    print("=" * 70)
    print("Testing Pydantic Models")
    print("=" * 70)
    print()
    
    try:
        test_model_imports()
        test_transcribe_request()
        test_estimate_cost_request()
        test_transcription_response()
        test_job_status_response()
        test_error_response()
        test_success_response()
        
        print("=" * 70)
        print("✓ All model tests passed!")
        print("=" * 70)
        return 0
        
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

