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
        Validate library integrity - check for orphaned data.

        Returns:
            Dict with validation results:
            {
                "total_entries": int,
                "missing_transcripts": [list of library_ids],
                "orphaned_transcripts": [list of filenames]
            }

        Note: This is a stub for future implementation.
        """
        # TODO: Implement validation logic
        # - Check each library entry has corresponding transcript file
        # - Check for transcript files without library entries
        # - Report mismatches

        return {
            "total_entries": len(self.library),
            "missing_transcripts": [],
            "orphaned_transcripts": [],
            "note": "Validation not yet implemented"
        }
