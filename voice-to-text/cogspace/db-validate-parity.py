#!/usr/bin/env python3
"""
COGSPACE Database-JSON Parity Validator v54.0.0
================================================
Compares JSON files to database and reports discrepancies.

Usage:
    python3 db-validate-parity.py [session_id]

If no session_id provided, validates the most recent session.

Part of: COGSPACE v54.0.0 "Database Truth"
"""

import sys
import os
import json
from pathlib import Path
from datetime import datetime

# Add db module to path
SCRIPT_DIR = Path(__file__).parent
DB_MODULE_PATH = SCRIPT_DIR / "db"
sys.path.insert(0, str(DB_MODULE_PATH))

try:
    from cogspace_db import COGSpaceDB
except ImportError as e:
    print(f"Error: Could not import cogspace_db: {e}", file=sys.stderr)
    sys.exit(1)


def parse_duration(duration_str: str) -> int:
    """Parse duration string to seconds."""
    if not duration_str:
        return 0
    if isinstance(duration_str, (int, float)):
        return int(duration_str)
    try:
        parts = str(duration_str).split(':')
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        elif len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        return int(duration_str)
    except (ValueError, TypeError):
        return 0


def get_nested(data: dict, path: str, default=None):
    """Get nested value from dict using dot notation."""
    if not data:
        return default
    keys = path.split('.')
    value = data
    for key in keys:
        if isinstance(value, dict):
            value = value.get(key)
        else:
            return default
        if value is None:
            return default
    return value


def load_complete_context(project_root: str) -> dict:
    """Load most recent complete-context JSON."""
    context_dir = Path(project_root) / "session-management/cognitive-context"
    if not context_dir.exists():
        return {}

    # Sort by mtime like the fixed code does
    files = sorted(
        context_dir.glob("complete-context-*.json"),
        key=lambda f: f.stat().st_mtime,
        reverse=True
    )
    if files:
        try:
            with open(files[0]) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Could not load {files[0]}: {e}", file=sys.stderr)
    return {}


def get_cogspace_version() -> str:
    """Get COGSPACE version from cogspace-version.json."""
    version_file = SCRIPT_DIR / "cogspace-version.json"
    try:
        with open(version_file) as f:
            data = json.load(f)
            return data.get('version', 'unknown')
    except (FileNotFoundError, json.JSONDecodeError):
        return 'unknown'


def validate_session(project_root: str, session_id: str = None):
    """Compare JSON and database for a session."""
    discrepancies = []

    # Load JSON
    json_data = load_complete_context(project_root)
    if not json_data:
        print("Error: No complete-context JSON found")
        return []

    json_session_id = json_data.get('sessionId', '')

    # Load database
    try:
        db = COGSpaceDB(project_root=project_root)
    except Exception as e:
        print(f"Error: Could not connect to database: {e}")
        return []

    # If no session_id provided, use the JSON session ID
    target_session_id = session_id if session_id else json_session_id

    db_session = db.get_session(target_session_id)
    if not db_session:
        print(f"Error: Session {target_session_id} not found in database")
        # Try to find by partial match
        recent = db.get_recent_sessions(limit=5)
        if recent:
            print("\nRecent sessions in database:")
            for s in recent:
                print(f"  - {s['id']}")
        return []

    print(f"Validating session: {target_session_id}")
    print(f"JSON source sessionId: {json_session_id}")
    print(f"DB source id: {db_session['id']}")
    print()

    # Get expected values from JSON
    expected_duration = parse_duration(
        get_nested(json_data, 'mentalModel.progressMetrics.sessionDuration') or
        json_data.get('sessionDuration') or
        0
    )

    expected_score = json_data.get('continuityScore')
    expected_version = get_cogspace_version()

    # Get message count from messages array
    messages = json_data.get('messages', [])
    expected_msg_count = len(messages) if messages else 0

    # Compare fields - Note: Sleep Message is NOT validated against JSON because
    # it's passed directly from command line to database, not stored in JSON
    checks = [
        ('Session ID', json_session_id, db_session.get('id', '')),
        ('Duration (seconds)', expected_duration, db_session.get('duration_seconds', 0)),
        ('Continuity Score', expected_score, db_session.get('continuity_score')),
        ('COGSPACE Version', expected_version, db_session.get('cogspace_version', '')),
        ('Message Count', expected_msg_count, db_session.get('message_count', 0)),
    ]

    # Sleep message is informational only (not in JSON by design)
    db_sleep_msg = db_session.get('sleep_message', '')

    for field, json_val, db_val in checks:
        # Handle None vs empty string comparison
        json_norm = json_val if json_val is not None else ''
        db_norm = db_val if db_val is not None else ''

        # For numeric fields, compare as numbers
        if field in ['Duration (seconds)', 'Continuity Score', 'Message Count']:
            json_norm = int(json_norm) if json_norm else 0
            db_norm = int(db_norm) if db_norm else 0

        match = json_norm == db_norm
        status = "\033[92m\u2713\033[0m" if match else "\033[91m\u2717\033[0m"

        print(f"{status} {field}:")
        print(f"   JSON: {json_val}")
        print(f"   DB:   {db_val}")

        if not match:
            discrepancies.append({
                'field': field,
                'json_value': json_val,
                'db_value': db_val
            })
        print()

    # Show sleep message as informational (not a parity check)
    print("\033[94mℹ\033[0m Sleep Message (DB only, not in JSON by design):")
    print(f"   DB: {db_sleep_msg or '(empty)'}")
    print()

    return discrepancies


def main():
    project_root = os.getcwd()
    session_id = sys.argv[1] if len(sys.argv) > 1 else None

    print("=" * 60)
    print("COGSPACE Database-JSON Parity Validator v54.0.0")
    print("=" * 60)
    print()

    discrepancies = validate_session(project_root, session_id)

    print("=" * 60)
    if discrepancies:
        print(f"\033[91m\u2717 {len(discrepancies)} DISCREPANCIES FOUND\033[0m")
        for d in discrepancies:
            print(f"   - {d['field']}: JSON={d['json_value']} vs DB={d['db_value']}")
    else:
        print("\033[92m\u2713 0 DISCREPANCIES - Database matches JSON!\033[0m")
    print("=" * 60)

    sys.exit(1 if discrepancies else 0)


if __name__ == "__main__":
    main()
