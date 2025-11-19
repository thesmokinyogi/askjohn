#!/usr/bin/env python3
"""
Cleanup script to remove duplicate library entries.

For each filename, keeps only the most recent transcription (by added_at date).
Deletes older duplicates and their transcript files.
"""

import json
import sys
from pathlib import Path
from collections import defaultdict
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.library import LibraryService

def cleanup_duplicates(dry_run=True):
    """
    Remove duplicate library entries, keeping only the most recent for each filename.
    
    Args:
        dry_run: If True, only report what would be deleted without actually deleting
    """
    library_service = LibraryService()
    
    # Group entries by filename
    by_filename = defaultdict(list)
    for library_id, entry in library_service.library.items():
        filename = entry.get('filename', '')
        by_filename[filename].append({
            'library_id': library_id,
            'entry': entry
        })
    
    # Find duplicates
    duplicates = {f: entries for f, entries in by_filename.items() if len(entries) > 1}
    
    if not duplicates:
        print("✓ No duplicates found in library")
        return
    
    print(f"Found {len(duplicates)} files with duplicates:")
    total_to_delete = 0
    
    for filename, entries in sorted(duplicates.items(), key=lambda x: len(x[1]), reverse=True):
        print(f"\n  {filename}: {len(entries)} entries")
        
        # Sort by added_at date, newest first
        entries.sort(
            key=lambda x: x['entry'].get('added_at', ''),
            reverse=True
        )
        
        # Keep the first (most recent), delete the rest
        to_keep = entries[0]
        to_delete = entries[1:]
        
        print(f"    ✓ Keeping: {to_keep['library_id']} (added: {to_keep['entry'].get('added_at', 'N/A')})")
        
        for entry_info in to_delete:
            total_to_delete += 1
            print(f"    ✗ Would delete: {entry_info['library_id']} (added: {entry_info['entry'].get('added_at', 'N/A')})")
            print(f"      Transcript: {entry_info['entry'].get('transcript_file', 'N/A')}")
    
    print(f"\n{'DRY RUN: ' if dry_run else ''}Would delete {total_to_delete} duplicate entries")
    
    if not dry_run:
        print("\nDeleting duplicates...")
        deleted_count = 0
        
        for filename, entries in duplicates.items():
            # Sort and get entries to delete (all except most recent)
            entries.sort(
                key=lambda x: x['entry'].get('added_at', ''),
                reverse=True
            )
            to_delete = entries[1:]
            
            for entry_info in to_delete:
                library_id = entry_info['library_id']
                if library_service.delete_entry(library_id):
                    deleted_count += 1
                    print(f"  ✓ Deleted: {library_id}")
                else:
                    print(f"  ✗ Failed to delete: {library_id}")
        
        print(f"\n✓ Cleanup complete: Deleted {deleted_count} duplicate entries")
        print(f"  Remaining entries: {len(library_service.library)}")
    else:
        print("\nThis was a dry run. Run with --execute to actually delete duplicates.")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Cleanup duplicate library entries")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually delete duplicates (default is dry run)"
    )
    
    args = parser.parse_args()
    cleanup_duplicates(dry_run=not args.execute)

