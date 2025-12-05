#!/usr/bin/env python3
"""
Deduplicate Budget Tracking Entries

Removes duplicate transcription entries from budget_tracking.json.
Duplicates are identified by matching duration_minutes, cost, and model.

Usage:
    python scripts/deduplicate_budget.py [--execute]
    
Options:
    --execute: Actually perform the deduplication (default is dry-run)
"""

import json
import sys
from pathlib import Path
from collections import defaultdict
from datetime import datetime
import shutil

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

BUDGET_FILE = Path('data/budget_tracking.json')


def deduplicate_budget(execute: bool = False):
    """
    Deduplicate budget tracking entries.
    
    Args:
        execute: If True, actually perform the deduplication. If False, dry-run.
    """
    if not BUDGET_FILE.exists():
        print(f"❌ Budget file not found: {BUDGET_FILE}")
        return
    
    # Load budget data
    with open(BUDGET_FILE, 'r') as f:
        data = json.load(f)
    
    # Create backup
    if execute:
        backup_path = BUDGET_FILE.with_suffix('.json.backup')
        shutil.copy(BUDGET_FILE, backup_path)
        print(f"✓ Created backup: {backup_path}")
    
    # Process each provider
    for provider_name, provider_data in data.get("providers", {}).items():
        transcriptions = provider_data.get("transcriptions", [])
        
        if not transcriptions:
            continue
        
        print(f"\n--- Processing {provider_name} provider ---")
        print(f"Original entries: {len(transcriptions)}")
        
        # Group entries by unique key (duration, cost, model, timestamp)
        # We'll keep the first occurrence of each unique job
        seen = {}
        unique_entries = []
        duplicates_removed = 0
        
        for entry in transcriptions:
            # Create a unique key: (duration, cost, model)
            # Using timestamp as tiebreaker to keep the earliest
            key = (
                entry.get("duration_minutes"),
                entry.get("cost"),
                entry.get("model", "")
            )
            
            # Check if we've seen this exact combination
            if key in seen:
                # This is a duplicate - skip it
                duplicates_removed += 1
                print(f"  Removing duplicate: {entry.get('duration_minutes')} min @ ${entry.get('cost', 0):.2f} ({entry.get('model', 'unknown')}) - {entry.get('timestamp', 'no timestamp')}")
            else:
                # First occurrence - keep it
                seen[key] = True
                unique_entries.append(entry)
        
        # Update the transcriptions list
        provider_data["transcriptions"] = unique_entries
        
        # Recalculate total_cost from unique entries
        old_total = provider_data.get("total_cost", 0.0)
        new_total = round(sum(e.get("cost", 0) for e in unique_entries), 2)
        provider_data["total_cost"] = new_total
        
        print(f"Unique entries: {len(unique_entries)}")
        print(f"Duplicates removed: {duplicates_removed}")
        print(f"Old total_cost: ${old_total:.2f}")
        print(f"New total_cost: ${new_total:.2f}")
        print(f"Savings: ${old_total - new_total:.2f}")
    
    # Update last_updated timestamp
    data["last_updated"] = datetime.now().isoformat()
    
    # Save if executing
    if execute:
        with open(BUDGET_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"\n✓ Saved deduplicated budget data to {BUDGET_FILE}")
    else:
        print(f"\n⚠️  DRY RUN - No changes made. Use --execute to apply changes.")
    
    return data


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Deduplicate budget tracking entries")
    parser.add_argument("--execute", action="store_true", help="Actually perform the deduplication")
    args = parser.parse_args()
    
    print("=" * 60)
    print("Budget Deduplication Script")
    print("=" * 60)
    
    if not args.execute:
        print("\n⚠️  DRY RUN MODE - No changes will be made")
        print("   Use --execute to actually perform deduplication\n")
    
    deduplicate_budget(execute=args.execute)
    
    print("\n" + "=" * 60)
    print("Done!")
    print("=" * 60)


if __name__ == "__main__":
    main()

