#!/usr/bin/env python3
"""
COGSPACE Agent ID Backfill Tool

Backfills agent_id for existing conversation_messages by reading from
original JSONL files. This recovers distributed consciousness attribution
for historical sessions.

Usage:
    python3 backfill-agent-ids.py [--dry-run] [--session SESSION_ID]

Author: Clarity Engineering Director
Version: Reads from cogspace-version.json (single source of truth)
"""

import json
import sqlite3
import sys
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from collections import defaultdict

# Default paths
DEFAULT_DB = ".cogspace/cogspace.db"
CLAUDE_PROJECTS_DIR = os.path.expanduser("~/.claude/projects")
SCRIPT_DIR = Path(__file__).parent.parent  # Points to cogspace/


def get_cogspace_version() -> str:
    """Get COGSPACE version from cogspace-version.json (single source of truth)."""
    version_file = SCRIPT_DIR / "cogspace-version.json"
    try:
        with open(version_file) as f:
            data = json.load(f)
            return data.get('version', 'unknown')
    except (FileNotFoundError, json.JSONDecodeError):
        return 'unknown'


def get_project_jsonl_dir(project_root: str) -> Optional[str]:
    """Get the Claude Code JSONL directory for this project."""
    abs_path = os.path.abspath(project_root)
    encoded_path = abs_path.replace("/", "-")
    jsonl_dir = os.path.join(CLAUDE_PROJECTS_DIR, encoded_path)
    if os.path.exists(jsonl_dir):
        return jsonl_dir
    return None


def get_sessions_needing_backfill(db_path: str) -> List[Dict]:
    """Find sessions with messages missing agent_id."""
    sessions = []
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Find sessions with NULL agent_id in their messages
        cursor.execute("""
            SELECT
                s.id,
                s.session_start,
                s.session_end,
                COUNT(cm.id) as total_messages,
                SUM(CASE WHEN cm.agent_id IS NULL THEN 1 ELSE 0 END) as null_agent_count,
                s.original_jsonl_path
            FROM sessions s
            JOIN conversation_messages cm ON cm.session_id = s.id
            GROUP BY s.id
            HAVING null_agent_count > 0
            ORDER BY s.session_start DESC
        """)

        for row in cursor.fetchall():
            sessions.append({
                'id': row[0],
                'session_start': row[1],
                'session_end': row[2],
                'total_messages': row[3],
                'null_agent_count': row[4],
                'original_jsonl_path': row[5]
            })

        conn.close()
    except Exception as e:
        print(f"⚠️  Error querying sessions: {e}", file=sys.stderr)

    return sessions


def find_jsonl_files_for_session(jsonl_dir: str, session_id: str, session_start: str, session_end: str) -> List[Dict]:
    """Find JSONL files that might belong to this session based on timestamps."""
    files = []

    if not os.path.exists(jsonl_dir):
        return files

    # Parse session timestamps
    try:
        if session_start:
            start_ts = datetime.fromisoformat(session_start.replace('Z', '+00:00')).timestamp()
        else:
            start_ts = 0

        if session_end:
            end_ts = datetime.fromisoformat(session_end.replace('Z', '+00:00')).timestamp()
        else:
            end_ts = datetime.now().timestamp()
    except:
        # If parsing fails, use wide range
        start_ts = 0
        end_ts = datetime.now().timestamp()

    # Add padding for timestamp matching
    start_ts -= 300  # 5 minutes before
    end_ts += 300    # 5 minutes after

    for filename in os.listdir(jsonl_dir):
        if not filename.endswith('.jsonl'):
            continue

        filepath = os.path.join(jsonl_dir, filename)
        stat = os.stat(filepath)

        # Check if file was modified within session timeframe
        if stat.st_mtime < start_ts or stat.st_mtime > end_ts:
            continue

        # Determine file type
        is_agent = filename.startswith('agent-')
        agent_id = None

        if is_agent:
            match = re.match(r'agent-([a-f0-9]{8})\.jsonl', filename)
            if match:
                agent_id = match.group(1)

        files.append({
            'path': filepath,
            'filename': filename,
            'mtime': stat.st_mtime,
            'is_agent': is_agent,
            'agent_id': agent_id
        })

    return files


def extract_messages_with_agents(jsonl_files: List[Dict]) -> Dict[str, str]:
    """Extract message content to agent_id mapping from JSONL files.

    Returns a dict mapping (content_hash) -> agent_id
    """
    content_to_agent = {}

    for file_info in jsonl_files:
        filepath = file_info['path']
        file_agent_id = file_info.get('agent_id')

        try:
            with open(filepath, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        entry = json.loads(line)

                        # Get agent_id from entry or fallback to file-level
                        entry_agent_id = entry.get('agentId') or file_agent_id

                        if not entry_agent_id:
                            continue

                        # Extract message content for matching
                        entry_type = entry.get('type', '')
                        if entry_type not in ('user', 'assistant'):
                            continue

                        content = entry.get('message', {}).get('content', '')
                        if isinstance(content, list):
                            text_parts = []
                            for item in content:
                                if isinstance(item, dict) and item.get('type') == 'text':
                                    text_parts.append(item.get('text', ''))
                            content = '\n'.join(text_parts)

                        if content:
                            # Use first 500 chars as key (for matching)
                            content_key = content[:500].strip()
                            if content_key:
                                content_to_agent[content_key] = entry_agent_id

                    except json.JSONDecodeError:
                        continue

        except Exception as e:
            print(f"⚠️  Error reading {filepath}: {e}", file=sys.stderr)

    return content_to_agent


def backfill_session(db_path: str, session: Dict, jsonl_dir: str, dry_run: bool = False) -> Tuple[int, int]:
    """Backfill agent_id for a single session.

    Returns (updated_count, skipped_count)
    """
    session_id = session['id']

    # Find JSONL files for this session
    jsonl_files = find_jsonl_files_for_session(
        jsonl_dir,
        session_id,
        session.get('session_start'),
        session.get('session_end')
    )

    if not jsonl_files:
        return 0, session['null_agent_count']

    # Extract content -> agent_id mapping
    content_to_agent = extract_messages_with_agents(jsonl_files)

    if not content_to_agent:
        return 0, session['null_agent_count']

    # Update database
    updated = 0
    skipped = 0

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Get messages needing update
        cursor.execute("""
            SELECT id, content FROM conversation_messages
            WHERE session_id = ? AND agent_id IS NULL
        """, (session_id,))

        for row in cursor.fetchall():
            msg_id = row[0]
            content = row[1] or ''
            content_key = content[:500].strip()

            if content_key in content_to_agent:
                agent_id = content_to_agent[content_key]

                if not dry_run:
                    cursor.execute("""
                        UPDATE conversation_messages
                        SET agent_id = ?
                        WHERE id = ?
                    """, (agent_id, msg_id))

                updated += 1
            else:
                skipped += 1

        if not dry_run:
            conn.commit()

        conn.close()

    except Exception as e:
        print(f"⚠️  Error updating session {session_id}: {e}", file=sys.stderr)

    return updated, skipped


def main():
    """Main function for agent_id backfill."""
    import argparse

    parser = argparse.ArgumentParser(description="COGSPACE Agent ID Backfill Tool")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be updated without making changes")
    parser.add_argument("--session", type=str, help="Backfill specific session ID")
    parser.add_argument("--db", type=str, default=DEFAULT_DB, help="Database path")
    args = parser.parse_args()

    version = get_cogspace_version()
    print(f"""
╔══════════════════════════════════════════════════════════════════╗
║  COGSPACE v{version} - Agent ID Backfill                         ║
║  Recovering distributed consciousness attribution                ║
╚══════════════════════════════════════════════════════════════════╝
""")

    if args.dry_run:
        print("🔍 DRY RUN MODE - No changes will be made\n")

    # Find JSONL directory
    jsonl_dir = get_project_jsonl_dir(os.getcwd())
    if not jsonl_dir:
        print("⚠️  Could not find Claude Code JSONL directory for this project")
        return 1

    print(f"📂 JSONL Directory: {jsonl_dir}")
    print(f"🗄️  Database: {args.db}")
    print()

    # Check database exists
    if not os.path.exists(args.db):
        print("❌ Database not found. Run wake.sh first to initialize.")
        return 1

    # Get sessions needing backfill
    sessions = get_sessions_needing_backfill(args.db)

    if args.session:
        sessions = [s for s in sessions if s['id'] == args.session]

    if not sessions:
        print("✅ No sessions need agent_id backfill!")
        return 0

    print(f"📋 Found {len(sessions)} session(s) needing backfill:\n")

    total_updated = 0
    total_skipped = 0

    for session in sessions:
        print(f"   📍 Session: {session['id']}")
        print(f"      Messages: {session['total_messages']} total, {session['null_agent_count']} missing agent_id")

        updated, skipped = backfill_session(args.db, session, jsonl_dir, args.dry_run)

        total_updated += updated
        total_skipped += skipped

        if updated > 0:
            print(f"      ✅ Updated: {updated} messages")
        if skipped > 0:
            print(f"      ⏭️  Skipped: {skipped} messages (no matching JSONL)")
        print()

    print("=" * 60)
    print(f"📊 Summary:")
    print(f"   ✅ Updated: {total_updated} messages")
    print(f"   ⏭️  Skipped: {total_skipped} messages")

    if args.dry_run:
        print("\n💡 Run without --dry-run to apply changes")

    return 0


if __name__ == '__main__':
    sys.exit(main())
