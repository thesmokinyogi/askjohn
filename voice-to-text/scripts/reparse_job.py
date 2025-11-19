#!/usr/bin/env python3
"""
Utility script to re-parse a completed transcription job.

This is useful when the parsing logic has been fixed and we want to
re-extract the transcript from an existing completed job.
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.jobs import get_job_storage
from app.services.transcribe_v2 import get_transcription_service_v2
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def reparse_job(job_id: str):
    """Re-parse a completed job's transcript."""
    
    # Get job storage
    job_storage = get_job_storage()
    
    # Get job record
    job = job_storage.get_job(job_id)
    if not job:
        print(f"Job not found: {job_id}")
        return False
    
    if job["status"] != "complete":
        print(f"Job is not complete (status: {job['status']})")
        return False
    
    print(f"Re-parsing job: {job['filename']}")
    print(f"Model: {job['model']}")
    print(f"GCS URI: {job.get('gcs_uri')}")
    
    # Map UI model to API model
    model_mapping = {
        'chirp_batch': 'chirp',
        'chirp_standard': 'chirp',
        'long_batch': 'long',
        'long_standard': 'long',
        'short_batch': 'short',
        'short_standard': 'short',
        'chirp': 'chirp',
        'long': 'long',
        'short': 'short'
    }
    
    ui_model = job.get("model", "long")
    api_model = model_mapping.get(ui_model, "long")
    
    # Get project and location
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    location = "us-central1"  # Default location
    
    # Create transcription service
    transcription_service = get_transcription_service_v2(
        project_id=project_id,
        model=api_model,
        location=location
    )
    
    # Re-check job status (this will re-download and parse with new code)
    print("\nRe-checking job status and re-parsing transcript...")
    try:
        status_result = transcription_service.check_job_status(
            job_id=job_id,
            gcs_uri=job.get("gcs_uri")
        )
        
        if status_result.get("status") == "complete" and status_result.get("transcript"):
            transcript = status_result["transcript"]
            confidence = status_result.get("confidence")
            words = status_result.get("words", [])
            metadata = status_result.get("metadata", {})
            
            print(f"\n✓ Successfully re-parsed transcript!")
            print(f"  Transcript length: {len(transcript)} characters")
            print(f"  Preview: {transcript[:200]}...")
            print(f"  Confidence: {confidence}")
            print(f"  Words: {len(words)}")
            
            # Update job record with new transcript
            # Note: billed_duration not available when re-parsing from GCS JSON (it's in operation response)
            job_storage.mark_complete(
                job_id=job_id,
                transcript=transcript,
                confidence=confidence,
                actual_cost=job.get("actual_cost", 0),
                metadata=metadata,
                billed_duration_minutes=None,  # Not available when re-parsing
                billed_duration_seconds=None   # Not available when re-parsing
            )
            
            print(f"\n✓ Job record updated with new transcript")
            return True
        else:
            print(f"\n✗ Failed to re-parse: {status_result.get('error', 'Unknown error')}")
            print(f"  Status: {status_result.get('status')}")
            print(f"  Has transcript: {bool(status_result.get('transcript'))}")
            return False
            
    except Exception as e:
        print(f"\n✗ Error re-parsing job: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/reparse_job.py <job_id>")
        print("\nExample:")
        print("  python scripts/reparse_job.py projects/123090535665/locations/us-central1/operations/v2-6ab19c89-0000-2b4a-855a-34c7e91e9aa3")
        sys.exit(1)
    
    job_id = sys.argv[1]
    success = reparse_job(job_id)
    sys.exit(0 if success else 1)

