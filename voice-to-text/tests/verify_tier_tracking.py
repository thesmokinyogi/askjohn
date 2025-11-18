"""
Verification script to check tier tracking in existing job records.

This script:
1. Loads all existing jobs from storage
2. Checks which jobs have tier information
3. Reports statistics on tier usage
4. Shows examples of jobs with/without tier

Run this after adding tier tracking to see the current state.
"""

import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.jobs import JobStorageService


def verify_tier_tracking():
    """Verify tier tracking in job records."""
    print("=" * 60)
    print("Tier Tracking Verification")
    print("=" * 60)
    print()
    
    # Load job storage
    job_storage = JobStorageService()
    jobs = job_storage.list_jobs(limit=1000, include_transcripts=False)
    
    if not jobs:
        print("No jobs found in storage.")
        return
    
    print(f"Total jobs found: {len(jobs)}")
    print()
    
    # Analyze tier information
    jobs_with_tier = []
    jobs_without_tier = []
    tier_counts = {"batch": 0, "standard": 0, None: 0}
    
    for job in jobs:
        tier = job.get("tier")
        if tier:
            jobs_with_tier.append(job)
            tier_counts[tier] = tier_counts.get(tier, 0) + 1
        else:
            jobs_without_tier.append(job)
            tier_counts[None] = tier_counts[None] + 1
    
    # Print statistics
    print("Tier Statistics:")
    print(f"  Jobs with tier: {len(jobs_with_tier)}")
    print(f"  Jobs without tier: {len(jobs_without_tier)}")
    print()
    print("Tier Breakdown:")
    print(f"  batch: {tier_counts.get('batch', 0)}")
    print(f"  standard: {tier_counts.get('standard', 0)}")
    print(f"  null/undefined: {tier_counts.get(None, 0)}")
    print()
    
    # Show examples
    if jobs_with_tier:
        print("Example jobs WITH tier:")
        for job in jobs_with_tier[:3]:
            print(f"  - {job.get('job_id', 'unknown')[:50]}...")
            print(f"    Model: {job.get('model')}, Tier: {job.get('tier')}")
        print()
    
    if jobs_without_tier:
        print("Example jobs WITHOUT tier (legacy):")
        for job in jobs_without_tier[:3]:
            print(f"  - {job.get('job_id', 'unknown')[:50]}...")
            print(f"    Model: {job.get('model')}, Tier: {job.get('tier', 'MISSING')}")
        print()
    
    # Check model names for tier inference
    print("Model Name Analysis:")
    model_tier_map = {}
    for job in jobs:
        model = job.get("model", "")
        tier = job.get("tier")
        
        if model not in model_tier_map:
            model_tier_map[model] = {"with_tier": 0, "without_tier": 0, "tiers": {}}
        
        if tier:
            model_tier_map[model]["with_tier"] += 1
            model_tier_map[model]["tiers"][tier] = model_tier_map[model]["tiers"].get(tier, 0) + 1
        else:
            model_tier_map[model]["without_tier"] += 1
    
    for model, stats in sorted(model_tier_map.items()):
        print(f"  {model}:")
        print(f"    With tier: {stats['with_tier']}, Without: {stats['without_tier']}")
        if stats['tiers']:
            print(f"    Tier breakdown: {stats['tiers']}")
    print()
    
    # Recommendations
    print("Recommendations:")
    if jobs_without_tier:
        print(f"  ⚠️  {len(jobs_without_tier)} legacy jobs don't have tier information.")
        print("     These are from before tier tracking was added.")
        print("     New jobs will automatically include tier.")
    else:
        print("  ✅ All jobs have tier information!")
    
    if tier_counts.get('batch', 0) > 0 or tier_counts.get('standard', 0) > 0:
        print(f"  ✅ Tier tracking is working - found {tier_counts.get('batch', 0) + tier_counts.get('standard', 0)} jobs with tier")
    
    print()
    print("=" * 60)


if __name__ == "__main__":
    verify_tier_tracking()

