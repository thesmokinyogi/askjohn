#!/usr/bin/env python3
"""
Job Cleanup Script

Detects and fixes:
1. Stuck processing jobs (processing > 1 hour)
2. Complete jobs missing library entries
3. Duplicate jobs
4. Orphaned jobs (complete but no transcript file)

Usage:
    python scripts/cleanup_jobs.py [--dry-run] [--fix-stuck] [--fix-library] [--fix-duplicates] [--fix-orphans]
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def load_jobs() -> Dict:
    """Load jobs.json"""
    jobs_file = project_root / "data" / "jobs.json"
    if not jobs_file.exists():
        return {}
    with open(jobs_file, 'r') as f:
        return json.load(f)

def save_jobs(jobs: Dict):
    """Save jobs.json"""
    jobs_file = project_root / "data" / "jobs.json"
    with open(jobs_file, 'w') as f:
        json.dump(jobs, f, indent=2)

def load_library() -> Dict:
    """Load library.json"""
    library_file = project_root / "data" / "library.json"
    if not library_file.exists():
        return {}
    with open(library_file, 'r') as f:
        return json.load(f)

def save_library(library: Dict):
    """Save library.json"""
    library_file = project_root / "data" / "library.json"
    with open(library_file, 'w') as f:
        json.dump(library, f, indent=2)

def find_stuck_jobs(jobs: Dict, hours: int = 1) -> List[Tuple[str, Dict]]:
    """Find jobs stuck in processing for > N hours"""
    stuck = []
    cutoff = datetime.now() - timedelta(hours=hours)
    
    for job_id, job in jobs.items():
        if job.get("status") != "processing":
            continue
        
        updated_at_str = job.get("updated_at") or job.get("submitted_at")
        if not updated_at_str:
            continue
        
        try:
            updated_at = datetime.fromisoformat(updated_at_str)
            if updated_at < cutoff:
                stuck.append((job_id, job))
        except (ValueError, TypeError):
            continue
    
    return stuck

def find_missing_library_jobs(jobs: Dict) -> List[Tuple[str, Dict]]:
    """Find complete jobs missing library entries"""
    missing = []
    transcripts_dir = project_root / "data" / "transcripts"
    
    for job_id, job in jobs.items():
        if job.get("status") != "complete":
            continue
        
        if not job.get("actual_cost") is not None:
            continue  # Not actually completed (no cost recorded)
        
        if job.get("library_id"):
            continue  # Already in library
        
        transcript_file = job.get("transcript_file")
        if not transcript_file:
            continue
        
        transcript_path = transcripts_dir / transcript_file
        if not transcript_path.exists():
            continue  # No transcript file, can't add to library
        
        missing.append((job_id, job))
    
    return missing

def find_duplicate_jobs(jobs: Dict) -> Dict[str, List[Tuple[str, Dict]]]:
    """Find duplicate jobs (same filename)"""
    by_filename = {}
    
    for job_id, job in jobs.items():
        filename = job.get("filename")
        if not filename:
            continue
        
        if filename not in by_filename:
            by_filename[filename] = []
        by_filename[filename].append((job_id, job))
    
    # Return only filenames with multiple jobs
    duplicates = {f: jobs_list for f, jobs_list in by_filename.items() if len(jobs_list) > 1}
    return duplicates

def find_orphaned_jobs(jobs: Dict) -> List[Tuple[str, Dict]]:
    """Find complete jobs with no transcript file"""
    orphaned = []
    transcripts_dir = project_root / "data" / "transcripts"
    
    for job_id, job in jobs.items():
        if job.get("status") != "complete":
            continue
        
        transcript_file = job.get("transcript_file")
        if not transcript_file:
            orphaned.append((job_id, job))
            continue
        
        transcript_path = transcripts_dir / transcript_file
        if not transcript_path.exists():
            orphaned.append((job_id, job))
    
    return orphaned

def add_to_library(job: Dict, dry_run: bool = False) -> Optional[str]:
    """Add a job to the library"""
    if dry_run:
        return "dry-run-library-id"
    
    try:
        from app.services.library import LibraryService
        from app.models.transcript import dict_to_transcript_metadata
        
        library_service = LibraryService()
        transcripts_dir = project_root / "data" / "transcripts"
        
        transcript_file = job.get("transcript_file")
        if not transcript_file:
            return None
        
        transcript_path = transcripts_dir / transcript_file
        if not transcript_path.exists():
            return None
        
        file_size_bytes = transcript_path.stat().st_size
        
        # Load transcript to get metadata
        with open(transcript_path, 'r') as f:
            transcript_data = json.load(f)
        
        metadata = dict_to_transcript_metadata(transcript_data.get("metadata", {}))
        
        library_id = library_service.add_entry(
            filename=job["filename"],
            transcript_file=transcript_file,
            duration_minutes=job["duration_minutes"],
            model=job["model"],
            cost=job.get("actual_cost", 0),
            file_size_bytes=file_size_bytes,
            metadata=metadata
        )
        
        return library_id
    except Exception as e:
        print(f"  ❌ Error adding to library: {e}")
        import traceback
        traceback.print_exc()
        return None

def fix_stuck_jobs(jobs: Dict, stuck: List[Tuple[str, Dict]], dry_run: bool = False):
    """Fix stuck jobs by checking their actual status"""
    print(f"\n{'[DRY RUN] ' if dry_run else ''}Fixing {len(stuck)} stuck job(s)...")
    
    for job_id, job in stuck:
        print(f"\n  Job: {job['filename']}")
        print(f"    ID: {job_id[:50]}...")
        print(f"    Status: {job['status']}")
        print(f"    Updated: {job.get('updated_at', 'N/A')}")
        
        if dry_run:
            print(f"    [DRY RUN] Would check status with Google API")
            continue
        
        # Try to check status via orchestrator
        try:
            from app.services.orchestrator import TranscriptionOrchestrator
            from app.dependencies import get_orchestrator
            from app.services.transcribe_v2 import get_transcription_service_v2
            from app.config import Config
            
            config = Config()
            orchestrator = get_orchestrator()
            
            # Get model for transcription service
            model_name = job['model'].replace('_batch', '').replace('_standard', '')
            
            transcription_service = get_transcription_service_v2(
                project_id=config.google_cloud_project,
                model=model_name,
                location="us-central1"  # TODO: Get from job or config
            )
            
            result = orchestrator.check_job_status(
                job_id=job_id,
                transcription_service=transcription_service
            )
            
            print(f"    ✅ Status check result: {result['status']}")
            
            if result['status'] in ['complete', 'failed']:
                print(f"    ✅ Job is actually {result['status']}, updating...")
                # Status will be updated by check_job_status
            else:
                print(f"    ⏳ Job is still {result['status']} on Google's side")
        
        except Exception as e:
            print(f"    ❌ Error checking status: {e}")
            # Mark as failed if we can't check
            if not dry_run:
                jobs[job_id]['status'] = 'failed'
                jobs[job_id]['error'] = f'Cleanup: Could not check status - {str(e)}'
                jobs[job_id]['updated_at'] = datetime.now().isoformat()
                jobs[job_id]['completed_at'] = datetime.now().isoformat()

def fix_missing_library(jobs: Dict, missing: List[Tuple[str, Dict]], dry_run: bool = False):
    """Fix complete jobs missing library entries"""
    print(f"\n{'[DRY RUN] ' if dry_run else ''}Fixing {len(missing)} job(s) missing from library...")
    
    for job_id, job in missing:
        print(f"\n  Job: {job['filename']}")
        print(f"    ID: {job_id[:50]}...")
        print(f"    Transcript file: {job.get('transcript_file', 'N/A')}")
        
        library_id = add_to_library(job, dry_run)
        
        if library_id:
            if not dry_run:
                jobs[job_id]['in_library'] = True
                jobs[job_id]['library_id'] = library_id
                jobs[job_id]['updated_at'] = datetime.now().isoformat()
            print(f"    ✅ Added to library: {library_id}")
        else:
            print(f"    ❌ Failed to add to library")

def fix_duplicates(jobs: Dict, duplicates: Dict[str, List[Tuple[str, Dict]]], dry_run: bool = False):
    """Fix duplicate jobs - keep most recent complete, mark others"""
    print(f"\n{'[DRY RUN] ' if dry_run else ''}Fixing {len(duplicates)} duplicate job group(s)...")
    
    for filename, job_list in duplicates.items():
        print(f"\n  Filename: {filename}")
        print(f"    Found {len(job_list)} job(s)")
        
        # Sort by submitted_at (most recent first)
        job_list.sort(key=lambda x: x[1].get('submitted_at', ''), reverse=True)
        
        # Find complete jobs
        complete_jobs = [j for j in job_list if j[1].get('status') == 'complete']
        
        if complete_jobs:
            # Keep most recent complete
            keep_job_id, keep_job = complete_jobs[0]
            print(f"    ✅ Keeping: {keep_job_id[:50]}... (complete)")
            
            # Mark others as duplicate
            for job_id, job in job_list:
                if job_id == keep_job_id:
                    continue
                
                if not dry_run:
                    jobs[job_id]['status'] = 'failed'
                    jobs[job_id]['error'] = f'Duplicate: Another job with same filename completed successfully'
                    jobs[job_id]['updated_at'] = datetime.now().isoformat()
                    jobs[job_id]['completed_at'] = datetime.now().isoformat()
                
                print(f"    {'[DRY RUN] ' if dry_run else ''}Marking as duplicate: {job_id[:50]}...")
        else:
            # No complete jobs - keep most recent
            keep_job_id, keep_job = job_list[0]
            print(f"    ⚠️  No complete jobs, keeping most recent: {keep_job_id[:50]}...")
            
            # Mark others
            for job_id, job in job_list[1:]:
                if not dry_run:
                    jobs[job_id]['status'] = 'failed'
                    jobs[job_id]['error'] = f'Duplicate: Multiple jobs with same filename'
                    jobs[job_id]['updated_at'] = datetime.now().isoformat()
                    jobs[job_id]['completed_at'] = datetime.now().isoformat()
                
                print(f"    {'[DRY RUN] ' if dry_run else ''}Marking as duplicate: {job_id[:50]}...")

def fix_orphans(jobs: Dict, orphaned: List[Tuple[str, Dict]], dry_run: bool = False):
    """Fix orphaned jobs (complete but no transcript file)"""
    print(f"\n{'[DRY RUN] ' if dry_run else ''}Fixing {len(orphaned)} orphaned job(s)...")
    
    for job_id, job in orphaned:
        print(f"\n  Job: {job['filename']}")
        print(f"    ID: {job_id[:50]}...")
        print(f"    Transcript file: {job.get('transcript_file', 'N/A')}")
        
        if not dry_run:
            jobs[job_id]['status'] = 'failed'
            jobs[job_id]['error'] = 'Orphaned: Transcript file missing'
            jobs[job_id]['updated_at'] = datetime.now().isoformat()
            jobs[job_id]['completed_at'] = datetime.now().isoformat()
        
        print(f"    {'[DRY RUN] ' if dry_run else ''}Marking as failed: Missing transcript file")

def main():
    parser = argparse.ArgumentParser(description='Clean up stuck and problematic jobs')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without making changes')
    parser.add_argument('--fix-stuck', action='store_true', help='Fix stuck processing jobs')
    parser.add_argument('--fix-library', action='store_true', help='Fix complete jobs missing from library')
    parser.add_argument('--fix-duplicates', action='store_true', help='Fix duplicate jobs')
    parser.add_argument('--fix-orphans', action='store_true', help='Fix orphaned jobs')
    parser.add_argument('--all', action='store_true', help='Fix all issues')
    
    args = parser.parse_args()
    
    if not any([args.fix_stuck, args.fix_library, args.fix_duplicates, args.fix_orphans, args.all]):
        # Default: just report
        args.all = False
        print("No fix options specified. Use --all or specific --fix-* options.")
        print("Running in report-only mode...\n")
    
    jobs = load_jobs()
    
    print(f"📋 Analyzing {len(jobs)} job(s)...\n")
    
    # Find issues
    stuck = find_stuck_jobs(jobs, hours=1)
    missing_library = find_missing_library_jobs(jobs)
    duplicates = find_duplicate_jobs(jobs)
    orphaned = find_orphaned_jobs(jobs)
    
    # Report
    print("=" * 60)
    print("ISSUES FOUND:")
    print("=" * 60)
    print(f"  Stuck processing jobs (>1 hour): {len(stuck)}")
    print(f"  Complete jobs missing library: {len(missing_library)}")
    print(f"  Duplicate job groups: {len(duplicates)}")
    print(f"  Orphaned jobs (no transcript): {len(orphaned)}")
    
    if not any([args.fix_stuck, args.fix_library, args.fix_duplicates, args.fix_orphans, args.all]):
        print("\n💡 Use --all or specific --fix-* options to fix issues")
        return
    
    # Fix issues
    if args.all or args.fix_stuck:
        if stuck:
            fix_stuck_jobs(jobs, stuck, args.dry_run)
            if not args.dry_run:
                save_jobs(jobs)
    
    if args.all or args.fix_library:
        if missing_library:
            fix_missing_library(jobs, missing_library, args.dry_run)
            if not args.dry_run:
                save_jobs(jobs)
    
    if args.all or args.fix_duplicates:
        if duplicates:
            fix_duplicates(jobs, duplicates, args.dry_run)
            if not args.dry_run:
                save_jobs(jobs)
    
    if args.all or args.fix_orphans:
        if orphaned:
            fix_orphans(jobs, orphaned, args.dry_run)
            if not args.dry_run:
                save_jobs(jobs)
    
    if not args.dry_run:
        print("\n✅ Cleanup complete!")
    else:
        print("\n[DRY RUN] No changes made")

if __name__ == "__main__":
    main()

