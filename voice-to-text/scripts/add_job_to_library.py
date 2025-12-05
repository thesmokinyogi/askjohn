#!/usr/bin/env python3
"""
Add a completed job to the library if it was missed.

This script can be used to manually add a job to the library if the
automatic addition failed (e.g., due to a bug that's now fixed).

Usage:
    python scripts/add_job_to_library.py <job_id>
"""

import json
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.jobs import get_job_storage
from app.services.library import LibraryService
from app.models.transcript import dict_to_transcript_metadata

def add_job_to_library(job_id: str):
    """Add a completed job to the library."""
    job_storage = get_job_storage()
    library_service = LibraryService()
    
    # Get job record
    job = job_storage.get_job(job_id, include_transcript=True)
    if not job:
        print(f"❌ Job not found: {job_id}")
        return False
    
    # Check if already in library
    if job.get("in_library") and job.get("library_id"):
        print(f"✅ Job already in library: {job.get('library_id')}")
        return True
    
    # Check if job is complete
    if job.get("status") != "complete":
        print(f"❌ Job is not complete (status: {job.get('status')})")
        return False
    
    # Check if transcript file exists
    transcript_file = job.get("transcript_file")
    if not transcript_file:
        print(f"❌ Job has no transcript file")
        return False
    
    # Load transcript to get metadata
    transcript_path = job_storage.TRANSCRIPTS_DIR / transcript_file
    if not transcript_path.exists():
        print(f"❌ Transcript file not found: {transcript_path}")
        return False
    
    with open(transcript_path, 'r') as f:
        transcript_data = json.load(f)
    
    # Get metadata from transcript file
    metadata_dict = transcript_data.get("metadata", {})
    metadata = dict_to_transcript_metadata(metadata_dict)
    
    # Get file size
    file_size_bytes = transcript_path.stat().st_size
    
    # Add to library
    library_id = library_service.add_entry(
        filename=job["filename"],
        transcript_file=transcript_file,
        duration_minutes=job["duration_minutes"],
        model=job["model"],
        cost=job.get("actual_cost", job.get("estimated_cost", 0.0)),
        file_size_bytes=file_size_bytes,
        metadata=metadata
    )
    
    if library_id:
        # Update job record
        job_storage.update_job(job_id, {
            "in_library": True,
            "library_id": library_id
        })
        print(f"✅ Added job to library: {library_id}")
        return True
    else:
        print(f"❌ Failed to add job to library")
        return False


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/add_job_to_library.py <job_id>")
        sys.exit(1)
    
    job_id = sys.argv[1]
    success = add_job_to_library(job_id)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

