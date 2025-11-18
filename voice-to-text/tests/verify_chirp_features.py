#!/usr/bin/env python3
"""
Verify that chirp transcription includes:
1. Word timings (for post-processing)
2. Confidence handling (should be None, not 0.0)
"""

import json
import sys
from pathlib import Path
from datetime import datetime

def verify_latest_chirp_job():
    """Verify the most recent chirp job has word timings and proper confidence handling."""
    
    # Load jobs
    jobs_file = Path(__file__).parent.parent / "data" / "jobs.json"
    if not jobs_file.exists():
        print("ERROR: jobs.json not found")
        return False
    
    with open(jobs_file) as f:
        jobs = json.load(f)
    
    # Find chirp jobs
    chirp_jobs = [
        (job_id, job) 
        for job_id, job in jobs.items() 
        if 'chirp' in job.get('model', '').lower() and job.get('status') == 'complete'
    ]
    
    if not chirp_jobs:
        print("No completed chirp jobs found")
        return False
    
    # Get most recent
    latest_id, latest_job = max(chirp_jobs, key=lambda x: x[1].get('completed_at', ''))
    
    print("=" * 80)
    print("VERIFYING CHIRP FEATURES")
    print("=" * 80)
    print(f"Job ID: {latest_id}")
    print(f"Model: {latest_job.get('model')}")
    print(f"Completed: {latest_job.get('completed_at')}")
    print()
    
    # Check confidence
    confidence = latest_job.get('confidence')
    print("1. CONFIDENCE HANDLING:")
    if confidence is None:
        print("   ✓ Confidence is None (correct - chirp doesn't support it)")
        conf_ok = True
    elif confidence == 0.0:
        print("   ✗ Confidence is 0.0 (should be None)")
        conf_ok = False
    else:
        print(f"   ⚠️  Confidence is {confidence} (unexpected for chirp)")
        conf_ok = False
    print()
    
    # Check transcript file for word timings
    transcript_file = latest_job.get('transcript_file')
    if not transcript_file:
        print("2. WORD TIMINGS:")
        print("   ✗ No transcript file found")
        return False
    
    transcript_path = Path(__file__).parent.parent / "data" / "transcripts" / transcript_file
    if not transcript_path.exists():
        print("2. WORD TIMINGS:")
        print(f"   ✗ Transcript file not found: {transcript_file}")
        return False
    
    with open(transcript_path) as f:
        transcript_data = json.load(f)
    
    print("2. WORD TIMINGS:")
    words = transcript_data.get('words', [])
    if words:
        print(f"   ✓ Found {len(words)} words with timings")
        
        # Check if words have timing data
        sample_word = words[0] if words else {}
        has_start = 'start_time' in sample_word or 'start_offset' in sample_word
        has_end = 'end_time' in sample_word or 'end_offset' in sample_word
        
        if has_start and has_end:
            print("   ✓ Words have start and end timestamps")
            print(f"   Sample word: '{sample_word.get('word', 'N/A')}' "
                  f"({sample_word.get('start_time', sample_word.get('start_offset', 'N/A'))}s - "
                  f"{sample_word.get('end_time', sample_word.get('end_offset', 'N/A'))}s)")
            timings_ok = True
        else:
            print("   ✗ Words missing timing data")
            print(f"   Sample word keys: {list(sample_word.keys())}")
            timings_ok = False
    else:
        print("   ✗ No word-level data found")
        print("   This means word timings were not enabled")
        timings_ok = False
    print()
    
    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    if conf_ok and timings_ok:
        print("✅ ALL CHECKS PASSED")
        print("   - Confidence handled correctly (None)")
        print("   - Word timings present and usable")
        return True
    else:
        print("⚠️  SOME ISSUES FOUND")
        if not conf_ok:
            print("   - Confidence handling needs fix")
        if not timings_ok:
            print("   - Word timings missing or incomplete")
        return False


if __name__ == "__main__":
    success = verify_latest_chirp_job()
    sys.exit(0 if success else 1)

