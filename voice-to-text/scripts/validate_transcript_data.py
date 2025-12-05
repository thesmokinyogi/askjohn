#!/usr/bin/env python3
"""
Data Validation Script for Transcript Metadata

Validates all transcript files and library entries to ensure they conform
to the TranscriptMetadata schema.

Usage:
    python scripts/validate_transcript_data.py [--fix]

Options:
    --fix: Attempt to fix invalid entries (creates backup first)
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime
import shutil

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.models.transcript import dict_to_transcript_metadata, transcript_metadata_to_dict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def validate_transcript_files(fix: bool = False) -> tuple[int, int, List[Dict[str, Any]]]:
    """
    Validate all transcript files.
    
    Args:
        fix: If True, attempt to fix invalid entries
        
    Returns:
        Tuple of (valid_count, invalid_count, invalid_entries)
    """
    transcripts_dir = Path('data/transcripts')
    invalid_entries = []
    valid_count = 0
    
    if not transcripts_dir.exists():
        logger.warning(f"Transcripts directory not found: {transcripts_dir}")
        return (0, 0, [])
    
    transcript_files = list(transcripts_dir.glob('*.json'))
    logger.info(f"Validating {len(transcript_files)} transcript files...")
    
    for transcript_file in transcript_files:
        try:
            with open(transcript_file) as f:
                data = json.load(f)
            
            # Check if metadata exists
            if 'metadata' not in data:
                invalid_entries.append({
                    'file': transcript_file.name,
                    'type': 'transcript',
                    'issue': 'Missing metadata field',
                    'data': data
                })
                if fix:
                    _fix_missing_metadata(transcript_file, data)
                continue
            
            metadata_dict = data['metadata']
            
            # Try to convert to model (validates structure)
            try:
                metadata_model = dict_to_transcript_metadata(metadata_dict)
                valid_count += 1
            except Exception as e:
                invalid_entries.append({
                    'file': transcript_file.name,
                    'type': 'transcript',
                    'issue': f'Invalid metadata structure: {e}',
                    'metadata': metadata_dict
                })
                if fix:
                    _fix_invalid_metadata(transcript_file, data, metadata_dict)
        except json.JSONDecodeError as e:
            invalid_entries.append({
                'file': transcript_file.name,
                'type': 'transcript',
                'issue': f'Invalid JSON: {e}',
                'data': None
            })
        except Exception as e:
            invalid_entries.append({
                'file': transcript_file.name,
                'type': 'transcript',
                'issue': f'Error reading file: {e}',
                'data': None
            })
    
    return (valid_count, len(invalid_entries), invalid_entries)


def validate_library_entries(fix: bool = False) -> tuple[int, int, List[Dict[str, Any]]]:
    """
    Validate all library entries.
    
    Args:
        fix: If True, attempt to fix invalid entries
        
    Returns:
        Tuple of (valid_count, invalid_count, invalid_entries)
    """
    library_file = Path('data/library.json')
    invalid_entries = []
    valid_count = 0
    
    if not library_file.exists():
        logger.warning(f"Library file not found: {library_file}")
        return (0, 0, [])
    
    # Create backup before fixing
    if fix:
        backup_path = library_file.with_suffix('.json.backup')
        shutil.copy(library_file, backup_path)
        logger.info(f"Created backup: {backup_path}")
    
    with open(library_file) as f:
        library = json.load(f)
    
    logger.info(f"Validating {len(library)} library entries...")
    
    for library_id, entry in library.items():
        if 'metadata' not in entry:
            invalid_entries.append({
                'library_id': library_id,
                'type': 'library',
                'issue': 'Missing metadata field',
                'entry': entry
            })
            if fix:
                entry['metadata'] = _create_minimal_metadata()
            continue
        
        metadata_dict = entry['metadata']
        
        # Try to convert to model (validates structure)
        try:
            metadata_model = dict_to_transcript_metadata(metadata_dict)
            valid_count += 1
        except Exception as e:
            invalid_entries.append({
                'library_id': library_id,
                'type': 'library',
                'issue': f'Invalid metadata structure: {e}',
                'metadata': metadata_dict
            })
            if fix:
                entry['metadata'] = _fix_metadata_dict(metadata_dict)
    
    # Save fixed library if fixing
    if fix and invalid_entries:
        with open(library_file, 'w') as f:
            json.dump(library, f, indent=2)
        logger.info(f"Fixed {len(invalid_entries)} library entries")
    
    return (valid_count, len(invalid_entries), invalid_entries)


def _create_minimal_metadata() -> Dict[str, Any]:
    """Create minimal valid metadata."""
    return {
        "total_words": 0,
        "model": "unknown",
        "language": "en-US",
        "api_version": "v2"
    }


def _fix_metadata_dict(metadata_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Fix invalid metadata dict by converting to model and back."""
    try:
        metadata_model = dict_to_transcript_metadata(metadata_dict)
        return transcript_metadata_to_dict(metadata_model)
    except Exception:
        # If conversion fails, return minimal valid metadata
        return _create_minimal_metadata()


def _fix_missing_metadata(transcript_file: Path, data: Dict[str, Any]) -> None:
    """Fix transcript file with missing metadata."""
    # Create backup
    backup_path = transcript_file.with_suffix('.json.backup')
    shutil.copy(transcript_file, backup_path)
    
    # Add minimal metadata
    data['metadata'] = _create_minimal_metadata()
    
    # Write fixed file
    with open(transcript_file, 'w') as f:
        json.dump(data, f, indent=2)
    
    logger.info(f"Fixed {transcript_file.name} (added missing metadata)")


def _fix_invalid_metadata(transcript_file: Path, data: Dict[str, Any], metadata_dict: Dict[str, Any]) -> None:
    """Fix transcript file with invalid metadata."""
    # Create backup
    backup_path = transcript_file.with_suffix('.json.backup')
    shutil.copy(transcript_file, backup_path)
    
    # Fix metadata
    data['metadata'] = _fix_metadata_dict(metadata_dict)
    
    # Write fixed file
    with open(transcript_file, 'w') as f:
        json.dump(data, f, indent=2)
    
    logger.info(f"Fixed {transcript_file.name} (corrected invalid metadata)")


def main():
    """Main validation function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Validate transcript data')
    parser.add_argument('--fix', action='store_true', help='Attempt to fix invalid entries')
    args = parser.parse_args()
    
    print("=== Transcript Data Validation ===\n")
    
    # Validate transcript files
    transcript_valid, transcript_invalid, transcript_issues = validate_transcript_files(fix=args.fix)
    
    # Validate library entries
    library_valid, library_invalid, library_issues = validate_library_entries(fix=args.fix)
    
    # Report results
    print(f"\n=== Validation Results ===\n")
    print(f"Transcript Files:")
    print(f"  ✓ Valid: {transcript_valid}")
    print(f"  ✗ Invalid: {transcript_invalid}")
    
    print(f"\nLibrary Entries:")
    print(f"  ✓ Valid: {library_valid}")
    print(f"  ✗ Invalid: {library_invalid}")
    
    total_valid = transcript_valid + library_valid
    total_invalid = transcript_invalid + library_invalid
    
    print(f"\nTotal:")
    print(f"  ✓ Valid: {total_valid}")
    print(f"  ✗ Invalid: {total_invalid}")
    
    # Report issues
    if transcript_issues or library_issues:
        print(f"\n=== Issues Found ===\n")
        
        if transcript_issues:
            print("Invalid Transcript Files:")
            for item in transcript_issues:
                print(f"  - {item['file']}: {item['issue']}")
            print()
        
        if library_issues:
            print("Invalid Library Entries:")
            for item in library_issues:
                print(f"  - {item['library_id']}: {item['issue']}")
            print()
        
        if not args.fix:
            print("💡 Tip: Run with --fix to attempt automatic fixes (creates backups first)")
            sys.exit(1)
    else:
        print("\n✅ All data is valid!")
        sys.exit(0)


if __name__ == '__main__':
    main()

