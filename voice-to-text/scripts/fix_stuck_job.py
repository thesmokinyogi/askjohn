#!/usr/bin/env python3
"""
Script to fix a stuck job by checking its status and updating it.

Usage:
    python scripts/fix_stuck_job.py <job_id>
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def fix_stuck_job(job_id: str):
    """Fix a stuck job by updating its status."""
    jobs_file = project_root / "data" / "jobs.json"
    
    # Load jobs
    with open(jobs_file, 'r') as f:
        jobs = json.load(f)
    
    if job_id not in jobs:
        print(f"❌ Job not found: {job_id}")
        return
    
    job = jobs[job_id]
    print(f"📋 Job: {job['filename']}")
    print(f"   Current status: {job['status']}")
    print(f"   Submitted: {job['submitted_at']}")
    
    # Check if there's a complete job with the same filename
    same_filename_jobs = [j for j in jobs.values() if j['filename'] == job['filename']]
    complete_jobs = [j for j in same_filename_jobs if j['status'] == 'complete']
    
    if complete_jobs:
        print(f"\n✅ Found {len(complete_jobs)} complete job(s) with the same filename:")
        for cj in complete_jobs:
            print(f"   - {cj['job_id']} (completed: {cj.get('completed_at', 'N/A')})")
        
        print(f"\n💡 Since there's a complete job, you can:")
        print(f"   1. Delete this stuck job (recommended)")
        print(f"   2. Mark it as failed")
        print(f"   3. Leave it (it will update when status is checked)")
        
        response = input("\nDelete this stuck job? (y/n): ").strip().lower()
        if response == 'y':
            del jobs[job_id]
            with open(jobs_file, 'w') as f:
                json.dump(jobs, f, indent=2)
            print(f"✅ Deleted stuck job: {job_id}")
        else:
            # Mark as failed
            job['status'] = 'failed'
            job['error'] = 'Duplicate job - another job with same filename completed successfully'
            job['updated_at'] = datetime.now().isoformat()
            job['completed_at'] = datetime.now().isoformat()
            
            jobs[job_id] = job
            with open(jobs_file, 'w') as f:
                json.dump(jobs, f, indent=2)
            print(f"✅ Marked job as failed: {job_id}")
    else:
        print(f"\n⚠️  No complete job found with same filename.")
        print(f"   This job might actually still be processing.")
        print(f"   Try checking status via the API endpoint: /api/v1/jobs/{job_id}/status")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/fix_stuck_job.py <job_id>")
        print("\nExample:")
        print("  python scripts/fix_stuck_job.py 'projects/.../operations/v2-...'")
        sys.exit(1)
    
    job_id = sys.argv[1]
    fix_stuck_job(job_id)

