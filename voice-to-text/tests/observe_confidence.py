#!/usr/bin/env python3
"""
OBSERVATION: What confidence values are actually being returned?

Following WORKING_AGREEMENT.md - "Observe Before Implement"
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.transcribe_v2 import GoogleSpeechV2Service
from app.services.storage import CloudStorageService

load_dotenv()

def observe_confidence():
    """Observe actual confidence values from a real transcription."""
    
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    bucket_name = os.getenv("GCS_BUCKET_NAME")
    
    # Use a recent job ID or GCS URI from a completed transcription
    # You can get this from the UI or from data/jobs.json
    
    print("=" * 80)
    print("OBSERVATION: Confidence Values")
    print("=" * 80)
    print()
    print("This script needs:")
    print("1. A completed job_id (from /api/jobs/{job_id}/status)")
    print("2. Or a GCS URI of a completed transcription")
    print()
    print("To get a job_id:")
    print("- Check the browser console when viewing a job")
    print("- Or look in data/jobs.json for recent jobs")
    print()
    
    # Check if we can inspect a recent job
    jobs_file = Path(__file__).parent.parent / "data" / "jobs.json"
    if jobs_file.exists():
        import json
        with open(jobs_file) as f:
            jobs = json.load(f)
        
        # Find a completed job
        completed = [j for j in jobs if j.get("status") == "complete"]
        if completed:
            latest = completed[-1]
            job_id = latest.get("job_id")
            gcs_uri = latest.get("gcs_uri")
            
            print(f"Found completed job: {job_id}")
            print(f"GCS URI: {gcs_uri}")
            print()
            
            # Initialize service
            service = GoogleSpeechV2Service(project_id, latest.get("model", "long"))
            
            # Check status
            print("Checking job status...")
            status = service.check_job_status(job_id, gcs_uri)
            
            print()
            print("=" * 80)
            print("OBSERVED DATA:")
            print("=" * 80)
            print(f"Status: {status.get('status')}")
            print(f"Done: {status.get('done')}")
            print(f"Confidence: {status.get('confidence')} (type: {type(status.get('confidence'))})")
            print(f"Has transcript: {bool(status.get('transcript'))}")
            print(f"Transcript length: {len(status.get('transcript', ''))}")
            print()
            
            # Inspect word-level confidence if available
            words = status.get('words', [])
            if words:
                print(f"Word count: {len(words)}")
                word_confs = [w.get('confidence', 0) for w in words if w.get('confidence') is not None]
                if word_confs:
                    print(f"Words with confidence: {len(word_confs)}")
                    print(f"Average word confidence: {sum(word_confs) / len(word_confs):.3f}")
                    print(f"Min confidence: {min(word_confs):.3f}")
                    print(f"Max confidence: {max(word_confs):.3f}")
                else:
                    print("⚠️  No word-level confidence found")
            else:
                print("⚠️  No word-level data found")
            
            print()
            print("=" * 80)
            print("RAW RESPONSE (first 500 chars):")
            print("=" * 80)
            import json
            print(json.dumps(status, indent=2, default=str)[:500])
            
        else:
            print("No completed jobs found. Run a transcription first.")
    else:
        print("No jobs.json file found. Run a transcription first.")

if __name__ == "__main__":
    observe_confidence()

