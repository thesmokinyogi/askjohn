#!/usr/bin/env python3
"""
Script to check and update a stuck job status.

Usage:
    python scripts/check_stuck_job.py <job_id>
"""

import sys
import os
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.services.jobs import get_job_storage
from app.services.orchestrator import TranscriptionOrchestrator
from app.dependencies import get_orchestrator
from app.services.transcribe_v2 import get_transcription_service_v2
from app.config import GOOGLE_CLOUD_PROJECT, SPEECH_LOCATION

def check_job_status(job_id: str):
    """Check and update job status."""
    job_storage = get_job_storage()
    job = job_storage.get_job(job_id, include_transcript=False)
    
    if not job:
        print(f"❌ Job not found: {job_id}")
        return
    
    print(f"📋 Job: {job['filename']}")
    print(f"   Status: {job['status']}")
    print(f"   Submitted: {job['submitted_at']}")
    print(f"   Updated: {job['updated_at']}")
    print(f"   Model: {job['model']}")
    
    if job['status'] in ['complete', 'failed']:
        print(f"✅ Job is already {job['status']}")
        return
    
    print(f"\n🔄 Checking status with Google...")
    
    try:
        orchestrator = get_orchestrator()
        
        # Get model name for transcription service
        model_name = job['model'].replace('_batch', '').replace('_standard', '')
        
        transcription_service = get_transcription_service_v2(
            project_id=GOOGLE_CLOUD_PROJECT,
            model=model_name,
            location=SPEECH_LOCATION
        )
        
        # Check status
        result = orchestrator.check_job_status(
            job_id=job_id,
            transcription_service=transcription_service
        )
        
        print(f"✅ Status check result: {result['status']}")
        
        if result['status'] == 'complete':
            print(f"   ✓ Job completed successfully!")
            print(f"   Cost: ${result.get('actual_cost', 0):.4f}")
            if result.get('transcript'):
                print(f"   Transcript length: {len(result['transcript'])} chars")
        elif result['status'] == 'processing':
            print(f"   ⏳ Job is still processing on Google's side")
        elif result['status'] == 'failed':
            print(f"   ❌ Job failed: {result.get('error', 'Unknown error')}")
        
    except Exception as e:
        print(f"❌ Error checking status: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/check_stuck_job.py <job_id>")
        print("\nExample:")
        print("  python scripts/check_stuck_job.py 'projects/.../operations/v2-...'")
        sys.exit(1)
    
    job_id = sys.argv[1]
    check_job_status(job_id)

