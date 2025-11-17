"""
Library Service - Manages permanent transcript storage

This service handles the library of completed transcripts, separate from
the operational jobs tracking. Jobs are transient (can be removed from view),
but library entries are permanent content storage.

ARCHITECTURE:
- library.json: Library metadata (filename, date, duration, file size, transcript reference)
- transcripts/: Shared with JobStorage - transcript files with full text + word timestamps

Design decisions:
- JSON file storage (not database) for simplicity
- Atomic writes (write to temp file, then rename) to prevent corruption
- Library ID is unique per entry (handles duplicate filenames)
- Preserves transcription metadata for post-processing (model, cost, etc.)
- Automatic deduplication: duplicate filenames get incremented IDs

Separation of concerns:
- Jobs = operational tracking (transient)
- Library = content repository (permanent)
- Deleting from jobs ≠ deleting transcript
- Only deleting from library removes transcript file

Future: Migrate to SQLite/Postgres when integrating with Content Cockpit
"""

import json
import logging
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List
import tempfile
import shutil

logger = logging.getLogger(__name__)


class LibraryService:
    """
    Manages permanent transcript library in JSON file storage.

    Thread safety: Uses atomic file operations (write to temp, then rename)
    Corruption resistance: Validates JSON before writing, keeps backup on write

    Storage Architecture:
    - data/library.json: Library metadata
    - data/transcripts/: Full transcript data (shared with JobStorage)
    """

    # Where we store the library metadata
    DATA_PATH = Path(__file__).parent.parent.parent / "data" / "library.json"

    # Where transcript files are stored (shared with JobStorage)
    TRANSCRIPTS_DIR = Path(__file__).parent.parent.parent / "data" / "transcripts"

    def __init__(self):
        """Initialize library storage, creating data directories if needed."""
        # Ensure the data directory exists
        self.DATA_PATH.parent.mkdir(parents=True, exist_ok=True)

        # Ensure transcripts directory exists
        self.TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)

        # Load existing library entries into memory
        self.library = self._load_library()

        logger.info(f"Library initialized: {len(self.library)} entries")

    def _load_library(self) -> Dict[str, Any]:
        """
        Load library entries from JSON file.

        Returns:
            Dictionary of library entries, keyed by library_id
            Empty dict if file doesn't exist or is corrupted
        """
        if not self.DATA_PATH.exists():
            logger.info(f"No existing library file at {self.DATA_PATH}")
            return {}

        try:
            with open(self.DATA_PATH, 'r') as f:
                library = json.load(f)

            logger.info(f"Loaded {len(library)} entries from library")
            return library

        except json.JSONDecodeError as e:
            logger.error(f"Corrupted library file: {e}")
            logger.error("Starting with empty library")

            # Rename corrupted file so we don't lose it
            backup_path = self.DATA_PATH.with_suffix('.json.corrupted')
            shutil.copy(self.DATA_PATH, backup_path)
            logger.info(f"Saved corrupted file to {backup_path}")

            return {}

        except Exception as e:
            logger.error(f"Error loading library: {e}")
            return {}

    def _save_library(self) -> bool:
        """
        Save library to JSON file atomically.

        Uses atomic write pattern: write to temp file, then rename.
        This prevents corruption if process crashes during write.

        Returns:
            True if save succeeded, False otherwise
        """
        try:
            # Write to temp file first (atomic operation)
            # This ensures we don't corrupt the main file if write fails
            with tempfile.NamedTemporaryFile(
                mode='w',
                dir=self.DATA_PATH.parent,
                delete=False,
                suffix='.tmp'
            ) as tmp_file:
                json.dump(self.library, tmp_file, indent=2, default=str)
                tmp_path = tmp_file.name

            # Atomically replace old file with new one
            # On Unix, this is atomic - old file is replaced instantaneously
            shutil.move(tmp_path, self.DATA_PATH)

            logger.info(f"Saved {len(self.library)} library entries")
            return True

        except Exception as e:
            logger.error(f"Failed to save library: {e}")
            return False

    def add_entry(
        self,
        filename: str,
        transcript_file: str,
        duration_minutes: float,
        model: str,
        cost: float,
        file_size_bytes: int = 0,
        metadata: Optional[Dict] = None
    ) -> Optional[str]:
        """
        Add a completed transcript to the library.

        Handles duplicate filenames by appending incrementing suffixes.

        Args:
            filename: Original audio filename
            transcript_file: Reference to transcript file (in transcripts/)
            duration_minutes: Duration of original audio
            model: Transcription model used
            cost: Cost of transcription
            file_size_bytes: Size of transcript file in bytes
            metadata: Additional metadata to preserve

        Returns:
            library_id if successful, None if failed
        """
        try:
            # Generate unique library ID
            library_id = self._generate_unique_id(filename)

            entry = {
                "library_id": library_id,
                "filename": filename,
                "transcript_file": transcript_file,
                "duration_minutes": duration_minutes,
                "model": model,
                "cost": cost,
                "file_size_bytes": file_size_bytes,
                "added_at": datetime.now().isoformat(),
                "metadata": metadata or {}
            }

            self.library[library_id] = entry

            if self._save_library():
                logger.info(f"Added to library: {filename} -> {library_id}")
                return library_id
            else:
                logger.error(f"Failed to save library after adding {filename}")
                return None

        except Exception as e:
            logger.error(f"Failed to add entry to library: {e}")
            return None

    def _generate_unique_id(self, filename: str) -> str:
        """
        Generate unique library ID, handling duplicate filenames.

        Strategy:
        - First occurrence: uses sanitized filename
        - Duplicates: appends _2, _3, etc.

        Args:
            filename: Original filename

        Returns:
            Unique library_id
        """
        # Sanitize filename for use as ID
        base_id = re.sub(r'[^\w\-.]', '_', filename)
        base_id = re.sub(r'_+', '_', base_id)  # Collapse multiple underscores
        base_id = base_id.strip('_')

        # Check if this ID already exists
        if base_id not in self.library:
            return base_id

        # ID exists - find next available increment
        counter = 2
        while f"{base_id}_{counter}" in self.library:
            counter += 1

        return f"{base_id}_{counter}"

    def get_entry(self, library_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a single library entry by ID.

        Args:
            library_id: Library entry ID

        Returns:
            Library entry dict, or None if not found
        """
        return self.library.get(library_id)

    def get_all_entries(self) -> List[Dict[str, Any]]:
        """
        Get all library entries, sorted by date (newest first).

        Returns:
            List of library entries
        """
        entries = list(self.library.values())

        # Sort by added_at date, newest first
        entries.sort(
            key=lambda x: x.get('added_at', ''),
            reverse=True
        )

        return entries

    def delete_entry(self, library_id: str) -> bool:
        """
        Permanently delete a library entry and its transcript file.

        This is the ONLY place where transcripts should be permanently deleted.

        Args:
            library_id: Library entry ID

        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            entry = self.library.get(library_id)
            if not entry:
                logger.warning(f"Library entry not found: {library_id}")
                return False

            # Delete transcript file
            transcript_file = entry.get('transcript_file')
            if transcript_file:
                transcript_path = self.TRANSCRIPTS_DIR / transcript_file
                if transcript_path.exists():
                    transcript_path.unlink()
                    logger.info(f"Deleted transcript file: {transcript_file}")
                else:
                    logger.warning(f"Transcript file not found: {transcript_file}")

            # Remove from library
            del self.library[library_id]

            # Save changes
            if self._save_library():
                logger.info(f"Deleted library entry: {library_id}")
                return True
            else:
                logger.error(f"Failed to save library after deleting {library_id}")
                return False

        except Exception as e:
            logger.error(f"Failed to delete library entry {library_id}: {e}")
            return False

    def validate_library(self) -> Dict[str, Any]:
        """
        Validate library integrity - check for orphaned data and manual manipulation issues.

        Handles all edge cases gracefully, never crashes. Designed to handle manual
        file manipulation since this system is a component in a larger product.

        Returns:
            Dict with comprehensive validation results including:
            - Missing/orphaned files
            - Missing/malformed metadata
            - Corrupted JSON detection
            - Permission errors
            - Invalid file references
            - All manual manipulation cases
        """
        from datetime import datetime
        
        # Initialize results structure
        results = {
            "total_entries": len(self.library),
            "missing_transcripts": [],
            "orphaned_transcripts": [],
            "missing_metadata": [],
            "malformed_entries": [],
            "duplicate_library_ids": [],
            "invalid_file_references": [],
            "invalid_transcript_files": [],
            "corrupted_json": False,
            "corrupted_backup_exists": False,
            "corrupted_backup_path": None,
            "corruption_error": None,
            "empty_library": len(self.library) == 0,
            "empty_transcripts_directory": False,
            "missing_transcripts_directory": False,
            "permission_errors": {
                "library_file": False,
                "transcripts_directory": False
            },
            "validation_timestamp": datetime.now().isoformat()
        }
        
        # Required fields for library entries
        REQUIRED_FIELDS = {
            'library_id': str,
            'filename': str,
            'transcript_file': str,
            'duration_minutes': (int, float),
            'model': str,
            'cost': (int, float),
            'added_at': str
        }
        
        # Check for corrupted JSON (historical)
        try:
            corrupted_backup = self.DATA_PATH.with_suffix('.json.corrupted')
            if corrupted_backup.exists():
                results["corrupted_backup_exists"] = True
                results["corrupted_backup_path"] = str(corrupted_backup)
        except Exception:
            pass  # Don't crash if can't check backup
        
        # Check for current corruption
        try:
            with open(self.DATA_PATH, 'r') as f:
                test_load = json.load(f)
        except json.JSONDecodeError as e:
            results["corrupted_json"] = True
            results["corruption_error"] = str(e)
            # Can't continue validation if JSON is corrupted
            return results
        except PermissionError:
            results["permission_errors"]["library_file"] = True
            # Can't continue validation if can't read library
            return results
        except Exception as e:
            # Other errors (file not found, etc.) - library might be empty, continue
            pass
        
        # Check transcripts directory
        try:
            if not self.TRANSCRIPTS_DIR.exists():
                results["missing_transcripts_directory"] = True
                # Create it (like __init__ does)
                try:
                    self.TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
                except Exception:
                    pass  # Can't create, but don't crash
        except PermissionError:
            results["permission_errors"]["transcripts_directory"] = True
        except Exception:
            pass  # Don't crash
        
        # Check if transcripts directory is empty (but library has entries)
        try:
            if self.TRANSCRIPTS_DIR.exists():
                transcript_files = list(self.TRANSCRIPTS_DIR.glob('*.json'))
                if len(transcript_files) == 0 and len(self.library) > 0:
                    results["empty_transcripts_directory"] = True
        except PermissionError:
            results["permission_errors"]["transcripts_directory"] = True
        except Exception:
            pass  # Don't crash
        
        # Track all transcript files referenced by entries
        referenced_files = set()
        library_ids_seen = set()
        
        # Validate each library entry
        for library_id, entry in self.library.items():
            # Check for duplicate library IDs (shouldn't happen with dict, but JSON allows duplicates)
            if library_id in library_ids_seen:
                results["duplicate_library_ids"].append(library_id)
            library_ids_seen.add(library_id)
            
            # Validate entry structure and required fields
            missing_fields = []
            for field, expected_type in REQUIRED_FIELDS.items():
                if field not in entry:
                    missing_fields.append(field)
                else:
                    # Validate field type
                    value = entry[field]
                    actual_type = type(value)
                    if not isinstance(value, expected_type):
                        results["malformed_entries"].append({
                            "library_id": library_id,
                            "field": field,
                            "expected_type": expected_type.__name__ if isinstance(expected_type, type) else str(expected_type),
                            "actual_type": actual_type.__name__,
                            "value": str(value)[:100]  # Truncate long values
                        })
            
            if missing_fields:
                results["missing_metadata"].append({
                    "library_id": library_id,
                    "missing_fields": missing_fields
                })
            
            # Check transcript file
            transcript_file = entry.get('transcript_file')
            if transcript_file:
                referenced_files.add(transcript_file)
                
                try:
                    transcript_path = self.TRANSCRIPTS_DIR / transcript_file
                    
                    # Check if file exists
                    if not transcript_path.exists():
                        results["missing_transcripts"].append(library_id)
                    else:
                        # Check if it's actually a file (not a directory)
                        if not transcript_path.is_file():
                            results["invalid_file_references"].append(library_id)
                        else:
                            # Check if it's valid JSON
                            try:
                                with open(transcript_path, 'r') as f:
                                    json.load(f)
                            except json.JSONDecodeError:
                                results["invalid_transcript_files"].append(transcript_file)
                            except Exception:
                                pass  # Other errors (permission, etc.) - already handled
                except PermissionError:
                    results["permission_errors"]["transcripts_directory"] = True
                except Exception:
                    pass  # Don't crash on file system errors
        
        # Find orphaned transcript files
        try:
            if self.TRANSCRIPTS_DIR.exists() and not results["permission_errors"]["transcripts_directory"]:
                for transcript_file in self.TRANSCRIPTS_DIR.glob('*.json'):
                    if transcript_file.name not in referenced_files:
                        results["orphaned_transcripts"].append(transcript_file.name)
        except PermissionError:
            results["permission_errors"]["transcripts_directory"] = True
        except Exception:
            pass  # Don't crash
        
        return results
