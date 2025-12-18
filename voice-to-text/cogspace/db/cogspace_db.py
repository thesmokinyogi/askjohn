#!/usr/bin/env python3
"""
COGSPACE Per-Project Database Manager
=====================================
SQLite database with auto-migration from DNA schema.

IMPORTANT: Database Location Architecture
-----------------------------------------
This file (cogspace/db/cogspace_db.py) contains DATABASE UTILITIES.
The actual session data is stored at: .cogspace/cogspace.db (project root)

    my-project/
    ├── .cogspace/
    │   └── cogspace.db    ← ACTUAL SESSION DATA (SQLite)
    ├── cogspace/
    │   └── db/
    │       └── cogspace_db.py   ← THIS FILE (utilities)

Each project has its own .cogspace/cogspace.db that stores session history.
Schema lives in DNA source and auto-applies on wake.

Usage:
    from cogspace_db import COGSpaceDB

    # Per-project database (recommended)
    db = COGSpaceDB(project_root="/path/to/project")

    # Or explicit path
    db = COGSpaceDB(db_path="/path/to/.cogspace/cogspace.db")

Version: 1.1.0
Part of: COGSPACE v55.0.0
"""

import os
import sys
import json
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from glob import glob


class COGSpaceDB:
    """Per-project COGSPACE database with auto-migration."""

    def __init__(self, project_root: str = None, db_path: str = None, schema_dir: str = None):
        """
        Initialize database connection.

        Args:
            project_root: Project directory (will use .cogspace/cogspace.db)
            db_path: Explicit database path (overrides project_root)
            schema_dir: Directory containing schema files (auto-detected from DNA)
        """
        # Determine database path
        if db_path:
            self.db_path = db_path
        elif project_root:
            self.db_path = os.path.join(project_root, ".cogspace", "cogspace.db")
        else:
            # Default to current directory
            self.db_path = os.path.join(os.getcwd(), ".cogspace", "cogspace.db")

        # Ensure directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        # Find schema directory
        self.schema_dir = schema_dir or self._find_schema_dir()

        # Auto-migrate on init
        self._ensure_schema_current()

    def _find_schema_dir(self) -> Optional[str]:
        """Find schema directory from DNA source."""
        # Check common locations
        locations = [
            # Test DNA (current development)
            "/Volumes/FOUR-TB/cogspace-dna-source/test-db-integration/cogspace/db",
            # Production DNA
            "/Volumes/FOUR-TB/cogspace-dna-source/current/cogspace/db",
            # Local cogspace directory
            os.path.join(os.path.dirname(self.db_path), "..", "cogspace", "db"),
            # Relative to this file
            os.path.join(os.path.dirname(__file__), "."),
        ]

        for loc in locations:
            if os.path.exists(os.path.join(loc, "schema_version.json")):
                return loc

        return None

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with proper settings."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _get_local_schema_version(self) -> int:
        """Get current schema version from database."""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    "SELECT MAX(version) FROM schema_version"
                )
                result = cursor.fetchone()
                return result[0] if result[0] else 0
        except sqlite3.OperationalError:
            # Table doesn't exist yet
            return 0

    def _get_dna_schema_version(self) -> int:
        """Get target schema version from DNA source."""
        if not self.schema_dir:
            return 0

        version_file = os.path.join(self.schema_dir, "schema_version.json")
        if os.path.exists(version_file):
            with open(version_file) as f:
                data = json.load(f)
                return data.get("version", 0)
        return 0

    def _ensure_schema_current(self):
        """Apply any pending migrations from DNA source."""
        local_version = self._get_local_schema_version()
        dna_version = self._get_dna_schema_version()

        if local_version < dna_version:
            print(f"📦 Upgrading database schema: v{local_version} → v{dna_version}")

            # Apply each migration in order
            migrations_dir = os.path.join(self.schema_dir, "migrations")
            if os.path.exists(migrations_dir):
                migration_files = sorted(glob(os.path.join(migrations_dir, "*.sql")))

                for mig_file in migration_files:
                    # Extract version from filename (e.g., 001_initial.sql -> 1)
                    filename = os.path.basename(mig_file)
                    try:
                        mig_version = int(filename.split("_")[0])
                    except ValueError:
                        continue

                    if mig_version > local_version:
                        self._apply_migration(mig_file, mig_version)

            print(f"✅ Database schema current (v{dna_version})")

    def _apply_migration(self, migration_file: str, version: int):
        """Apply a single migration file."""
        print(f"   Applying migration {version}: {os.path.basename(migration_file)}")

        with open(migration_file) as f:
            sql = f.read()

        with self._get_connection() as conn:
            conn.executescript(sql)

    # =========================================================================
    # Session Management
    # =========================================================================

    def create_session(self, session_id: str, project_name: str,
                       project_path: str = None, trigger_type: str = "manual",
                       cogspace_version: str = None) -> bool:
        """Create a new session record."""
        try:
            with self._get_connection() as conn:
                conn.execute("""
                    INSERT INTO sessions (id, project_name, project_path,
                                         session_start, trigger_type, cogspace_version)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (session_id, project_name, project_path,
                      datetime.now().isoformat(), trigger_type, cogspace_version))
            return True
        except sqlite3.IntegrityError:
            # Session already exists
            return False

    def complete_session(self, session_id: str, sleep_message: str = None,
                        continuity_score: int = 100, duration_seconds: int = None,
                        message_count: int = 0) -> bool:
        """Complete a session with final data.

        v54.0.0: Added message_count parameter for database-JSON parity.
        """
        try:
            with self._get_connection() as conn:
                conn.execute("""
                    UPDATE sessions
                    SET session_end = ?, sleep_message = ?,
                        continuity_score = ?, duration_seconds = ?,
                        message_count = ?
                    WHERE id = ?
                """, (datetime.now().isoformat(), sleep_message,
                      continuity_score, duration_seconds, message_count, session_id))
            return True
        except Exception as e:
            print(f"Error completing session: {e}", file=sys.stderr)
            return False

    def get_session(self, session_id: str) -> Optional[Dict]:
        """Get a session by ID."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM sessions WHERE id = ?", (session_id,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_recent_sessions(self, limit: int = 5, days: int = 7) -> List[Dict]:
        """Get recent sessions."""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()

        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT s.*,
                       wn.session_story,
                       mm.work_summary
                FROM sessions s
                LEFT JOIN work_narratives wn ON s.id = wn.session_id
                LEFT JOIN mental_models mm ON s.id = mm.session_id
                WHERE s.session_end > ? OR s.session_end IS NULL
                ORDER BY s.session_end DESC NULLS FIRST
                LIMIT ?
            """, (cutoff, limit))
            return [dict(row) for row in cursor.fetchall()]

    # =========================================================================
    # Mental Models
    # =========================================================================

    def save_mental_model(self, session_id: str, model: Dict) -> bool:
        """Save mental model for a session (v51.0.0 - expanded fields)."""
        try:
            with self._get_connection() as conn:
                # v51.0.0: Try expanded schema first, fall back to v1 schema
                try:
                    conn.execute("""
                        INSERT INTO mental_models
                        (session_id, current_understanding, work_summary, key_concepts, domain_knowledge,
                         work_description, current_focus, understanding_level, problem_complexity,
                         cognitive_state, technical_definitions, project_patterns)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        session_id,
                        model.get("currentUnderstanding", ""),
                        model.get("workSummary", ""),
                        json.dumps(model.get("keyConcepts", [])),
                        json.dumps(model.get("domainKnowledge", {})),
                        model.get("workDescription", ""),
                        model.get("currentFocus", ""),
                        model.get("understandingLevel", ""),
                        model.get("problemComplexity", ""),
                        json.dumps(model.get("cognitiveState", {})),
                        json.dumps(model.get("technicalDefinitions", [])),
                        json.dumps(model.get("projectPatterns", {}))
                    ))
                except Exception:
                    # Fall back to v1 schema (columns may not exist yet)
                    conn.execute("""
                        INSERT INTO mental_models
                        (session_id, current_understanding, work_summary, key_concepts, domain_knowledge)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        session_id,
                        model.get("currentUnderstanding", ""),
                        model.get("workSummary", ""),
                        json.dumps(model.get("keyConcepts", [])),
                        json.dumps(model.get("domainKnowledge", {}))
                    ))
            return True
        except Exception as e:
            print(f"Error saving mental model: {e}", file=sys.stderr)
            return False

    # =========================================================================
    # Work Narratives
    # =========================================================================

    def save_work_narrative(self, session_id: str, narrative: Dict) -> bool:
        """Save work narrative for a session."""
        try:
            with self._get_connection() as conn:
                conn.execute("""
                    INSERT INTO work_narratives
                    (session_id, session_story, previous_chapter, current_chapter,
                     next_chapter, narrative_complexity, achievements, challenges)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    session_id,
                    narrative.get("sessionStory", ""),
                    narrative.get("previousChapter", ""),
                    narrative.get("currentChapter", ""),
                    narrative.get("nextChapter", ""),
                    narrative.get("narrativeComplexity", ""),
                    json.dumps(narrative.get("achievements", [])),
                    json.dumps(narrative.get("challenges", []))
                ))
            return True
        except Exception as e:
            print(f"Error saving work narrative: {e}", file=sys.stderr)
            return False

    # =========================================================================
    # Developer Notes
    # =========================================================================

    def add_note(self, session_id: str, developer: str, content: str,
                 note_type: str = "general") -> bool:
        """Add a developer note."""
        try:
            with self._get_connection() as conn:
                conn.execute("""
                    INSERT INTO developer_notes
                    (session_id, developer_name, note_content, note_type)
                    VALUES (?, ?, ?, ?)
                """, (session_id, developer, content, note_type))
            return True
        except Exception as e:
            print(f"Error adding note: {e}", file=sys.stderr)
            return False

    def get_recent_notes(self, limit: int = 10) -> List[Dict]:
        """Get recent developer notes."""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM developer_notes
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]

    # =========================================================================
    # Search
    # =========================================================================

    def search_sessions(self, query: str, limit: int = 10) -> List[Dict]:
        """Full-text search across sessions."""
        with self._get_connection() as conn:
            # Search in multiple fields
            cursor = conn.execute("""
                SELECT DISTINCT s.*,
                       wn.session_story,
                       mm.work_summary
                FROM sessions s
                LEFT JOIN work_narratives wn ON s.id = wn.session_id
                LEFT JOIN mental_models mm ON s.id = mm.session_id
                WHERE s.sleep_message LIKE ?
                   OR wn.session_story LIKE ?
                   OR mm.work_summary LIKE ?
                ORDER BY s.session_end DESC
                LIMIT ?
            """, (f"%{query}%", f"%{query}%", f"%{query}%", limit))
            return [dict(row) for row in cursor.fetchall()]

    # =========================================================================
    # Statistics
    # =========================================================================

    def get_stats(self) -> Dict:
        """Get database statistics."""
        with self._get_connection() as conn:
            stats = {}

            # Total sessions
            cursor = conn.execute("SELECT COUNT(*) FROM sessions")
            stats["total_sessions"] = cursor.fetchone()[0]

            # Sessions in last 7 days
            cutoff = (datetime.now() - timedelta(days=7)).isoformat()
            cursor = conn.execute(
                "SELECT COUNT(*) FROM sessions WHERE session_end > ?", (cutoff,)
            )
            stats["sessions_last_7_days"] = cursor.fetchone()[0]

            # Average continuity score
            cursor = conn.execute(
                "SELECT AVG(continuity_score) FROM sessions WHERE continuity_score IS NOT NULL"
            )
            avg = cursor.fetchone()[0]
            stats["avg_continuity_score"] = round(avg, 1) if avg else 0

            # Total notes
            cursor = conn.execute("SELECT COUNT(*) FROM developer_notes")
            stats["total_notes"] = cursor.fetchone()[0]

            return stats


# CLI interface
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="COGSPACE Database Manager")
    parser.add_argument("--project", "-p", help="Project root directory")
    parser.add_argument("--db", help="Database path")
    parser.add_argument("command", choices=["init", "stats", "sessions", "migrate"],
                       help="Command to run")

    args = parser.parse_args()

    db = COGSpaceDB(project_root=args.project, db_path=args.db)

    if args.command == "init":
        print(f"✅ Database initialized at: {db.db_path}")
        print(f"   Schema version: {db._get_local_schema_version()}")

    elif args.command == "stats":
        stats = db.get_stats()
        print(json.dumps(stats, indent=2))

    elif args.command == "sessions":
        sessions = db.get_recent_sessions(limit=10)
        for s in sessions:
            print(f"  {s['id']}: {s.get('sleep_message', 'No message')[:50]}")

    elif args.command == "migrate":
        # Force re-check migrations
        db._ensure_schema_current()
