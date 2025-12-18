#!/usr/bin/env python3
"""
COGSPACE Crash Recovery Tool

Detects orphaned JSONL session files and recovers them to the database.
"Clean as you go" - runs during wake to recover any crashed sessions.

Features:
- Processes both main session and agent JSONL files
- Extracts agentId from filenames and message content
- Enables distributed consciousness recovery

Usage:
    python3 recover-crashed-session.py [--detect-only] [--recover-all] [--session UUID]

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
from typing import Optional, List, Dict, Any

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
    # Claude Code uses path with dashes instead of slashes
    # IMPORTANT: Keep the leading dash - Claude Code directories start with dash
    # e.g., /Volumes/FOUR-TB/root/project -> -Volumes-FOUR-TB-root-project
    abs_path = os.path.abspath(project_root)
    encoded_path = abs_path.replace("/", "-")
    # NOTE: Do NOT remove leading dash - Claude Code directories keep it

    jsonl_dir = os.path.join(CLAUDE_PROJECTS_DIR, encoded_path)
    if os.path.exists(jsonl_dir):
        return jsonl_dir
    return None


def get_known_sessions(db_path: str) -> tuple:
    """Get set of session IDs and recovered JSONL paths already in database.

    Returns:
        tuple: (known_ids: set, known_paths: set)
        - known_ids: Session ID suffixes (8-char hex) for UUID matching
        - known_paths: Full paths to already-recovered JSONL files
    """
    known_ids = set()
    known_paths = set()
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Get session ID suffixes
        cursor.execute("SELECT id FROM sessions")
        for row in cursor.fetchall():
            session_id = row[0]
            if session_id:
                # Extract the 8-char UUID suffix (e.g., "1765693772638-db2b68c6" -> "db2b68c6")
                parts = session_id.split("-")
                if len(parts) >= 2:
                    known_ids.add(parts[-1])  # Last part is the UUID suffix
                known_ids.add(session_id)  # Also add full ID

        # Get already-recovered JSONL paths (prevents duplicate recovery)
        cursor.execute("SELECT original_jsonl_path FROM sessions WHERE original_jsonl_path IS NOT NULL")
        for row in cursor.fetchall():
            if row[0]:
                known_paths.add(row[0])

        conn.close()
    except Exception as e:
        print(f"⚠️  Could not read known sessions: {e}", file=sys.stderr)
    return known_ids, known_paths


def find_orphan_jsonls(jsonl_dir: str, known_sessions: tuple, hours_lookback: int = 48) -> List[Dict]:
    """Find JSONL files that might be orphaned (not in database).

    Args:
        jsonl_dir: Directory containing JSONL files
        known_sessions: Tuple of (known_ids: set, known_paths: set)
        hours_lookback: How far back to look for orphans
    """
    orphans = []

    if not os.path.exists(jsonl_dir):
        return orphans

    # Unpack the tuple from get_known_sessions()
    known_ids, known_paths = known_sessions

    cutoff_time = datetime.now().timestamp() - (hours_lookback * 3600)

    for filename in os.listdir(jsonl_dir):
        if not filename.endswith(".jsonl"):
            continue

        filepath = os.path.join(jsonl_dir, filename)
        stat = os.stat(filepath)

        # Skip files older than lookback period
        if stat.st_mtime < cutoff_time:
            continue

        # Skip empty files
        if stat.st_size == 0:
            continue

        # Skip files already recovered (by path) - PRIMARY DEDUPLICATION
        if filepath in known_paths:
            continue

        # Handle both main sessions and agent sessions
        session_uuid = None
        agent_id = None
        is_agent = False

        # Check for agent file pattern: agent-{8-char-hex}.jsonl
        agent_match = re.match(r"agent-([a-f0-9]{8})\.jsonl", filename)
        if agent_match:
            agent_id = agent_match.group(1)
            session_uuid = agent_id  # Use agent_id as session identifier
            is_agent = True
        else:
            # Check for main session pattern: {UUID}.jsonl
            uuid_match = re.match(r"([a-f0-9-]{36})\.jsonl", filename)
            if uuid_match:
                session_uuid = uuid_match.group(1)
            else:
                continue  # Skip unrecognized patterns

        # Check if this session is already known by UUID suffix
        # FIXED: Use first 8 chars (matches session ID suffix), not last segment
        uuid_suffix = session_uuid[:8]
        if session_uuid in known_ids or uuid_suffix in known_ids:
            continue

        # This looks like an orphan - analyze it
        orphan_info = analyze_jsonl(filepath, session_uuid, agent_id, is_agent)
        if orphan_info:
            orphans.append(orphan_info)

    return orphans


def get_meaningful_summary(messages: list) -> str:
    """Extract meaningful summary from the last few assistant messages.

    Looks for substantial text content (not tool outputs or JSON).
    Returns a useful summary for the sleep_message field.
    """
    for msg in reversed(messages):
        if msg.get("type") != "assistant":
            continue
        content = msg.get("message", {}).get("content", [])
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text = item.get("text", "").strip()
                    # Skip very short responses, JSON-like outputs, or tool results
                    if (len(text) > 50 and
                        not text.startswith("{") and
                        not text.startswith("[") and
                        not text.startswith("```") and
                        "tool_result" not in text.lower()):
                        # Clean up and truncate
                        # Take first meaningful paragraph or section
                        lines = text.split("\n")
                        summary_lines = []
                        for line in lines:
                            line = line.strip()
                            if line and not line.startswith("#"):  # Skip markdown headers
                                summary_lines.append(line)
                            if len(" ".join(summary_lines)) > 400:
                                break
                        return " ".join(summary_lines)[:500]
    return "Session recovered - no summary available"


def analyze_jsonl(filepath: str, session_uuid: str, agent_id: str = None, is_agent: bool = False) -> Optional[Dict]:
    """Analyze a JSONL file to extract session metadata.

    Extracts agentId from message content for proper attribution.
    """
    try:
        stat = os.stat(filepath)

        messages = []
        tool_calls = []
        first_timestamp = None
        last_message = None
        last_tool = None
        detected_agent_id = agent_id  # From filename, but can be overridden by content

        with open(filepath, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    entry_type = entry.get("type", "")

                    # Extract agentId from message content if present
                    if not detected_agent_id and entry.get("agentId"):
                        detected_agent_id = entry.get("agentId")

                    if entry_type in ("user", "assistant"):
                        messages.append(entry)
                        last_message = entry

                        # Try to get timestamp
                        ts = entry.get("timestamp") or entry.get("message", {}).get("timestamp")
                        if ts and not first_timestamp:
                            first_timestamp = ts

                    # Count tool uses
                    if entry_type == "assistant":
                        content = entry.get("message", {}).get("content", [])
                        if isinstance(content, list):
                            for item in content:
                                if isinstance(item, dict) and item.get("type") == "tool_use":
                                    tool_calls.append(item)
                                    last_tool = item.get("name")
                except json.JSONDecodeError:
                    continue

        if not messages:
            return None

        # Extract last message preview
        last_preview = ""
        last_role = ""
        if last_message:
            last_role = last_message.get("type", "")
            content = last_message.get("message", {}).get("content", "")
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        last_preview = item.get("text", "")[:200]
                        break
            elif isinstance(content, str):
                last_preview = content[:200]

        user_count = sum(1 for m in messages if m.get("type") == "user")
        assistant_count = sum(1 for m in messages if m.get("type") == "assistant")

        # Get meaningful summary for sleep_message (Bug 3 fix)
        meaningful_summary = get_meaningful_summary(messages)

        return {
            "session_uuid": session_uuid,
            "jsonl_path": filepath,
            "jsonl_filename": os.path.basename(filepath),
            "jsonl_size": stat.st_size,
            "jsonl_mtime": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "message_count": len(messages),
            "tool_call_count": len(tool_calls),
            "user_message_count": user_count,
            "assistant_message_count": assistant_count,
            "last_message_role": last_role,
            "last_message_preview": last_preview,
            "meaningful_summary": meaningful_summary,  # For better sleep_message
            "last_tool_name": last_tool,
            "estimated_start": first_timestamp,
            "estimated_end": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "raw_messages": messages,  # For full recovery
            # Agent attribution
            "agent_id": detected_agent_id,
            "is_agent": is_agent,
            "session_type": "agent" if is_agent else "primary"
        }
    except Exception as e:
        print(f"⚠️  Error analyzing {filepath}: {e}", file=sys.stderr)
        return None


def run_migration(db_path: str):
    """Run the v59.1.0 migration if needed."""
    migration_path = os.path.join(os.path.dirname(__file__), "migrations", "006_v59_1_crash_recovery.sql")

    if not os.path.exists(migration_path):
        print(f"⚠️  Migration file not found: {migration_path}", file=sys.stderr)
        return False

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check if migration already applied
        cursor.execute("SELECT version FROM schema_version ORDER BY version DESC LIMIT 1")
        row = cursor.fetchone()
        current_version = row[0] if row else 0

        if current_version >= 6:
            conn.close()
            return True

        # Run migration
        print("📦 Applying crash recovery schema migration...")
        with open(migration_path, 'r') as f:
            sql = f.read()

        # SQLite doesn't support multiple statements in execute, so we split
        for statement in sql.split(";"):
            statement = statement.strip()
            if statement and not statement.startswith("--"):
                try:
                    cursor.execute(statement)
                except sqlite3.OperationalError as e:
                    # Ignore "duplicate column" errors for ALTER TABLE
                    if "duplicate column" not in str(e).lower():
                        print(f"   ⚠️  {e}", file=sys.stderr)

        conn.commit()
        conn.close()
        print("✅ Migration complete")
        return True
    except Exception as e:
        print(f"❌ Migration failed: {e}", file=sys.stderr)
        return False


def recover_session(db_path: str, orphan: Dict, recovered_by: str = "clarity-engineer-001") -> bool:
    """Recover an orphaned session to the database."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Generate a COGSPACE-style session ID
        timestamp = int(datetime.now().timestamp() * 1000)
        session_id = f"{timestamp}-{orphan['session_uuid'][:8]}"

        # Check if already recovered
        cursor.execute("SELECT id FROM sessions WHERE id = ?", (session_id,))
        if cursor.fetchone():
            print(f"   ⏭️  Session {session_id} already exists")
            conn.close()
            return False

        # Insert session record
        # Use meaningful_summary for better context (Bug 3 fix)
        sleep_msg = f"[RECOVERED] {orphan.get('meaningful_summary', orphan.get('last_message_preview', ''))}"
        cursor.execute("""
            INSERT INTO sessions (
                id, project_name, session_start, session_end,
                sleep_message, continuity_score, message_count,
                session_status, crash_detected_at, recovery_attempted_at,
                recovery_source, original_jsonl_path
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            session_id,
            os.path.basename(os.getcwd()),
            orphan.get("estimated_start"),
            orphan.get("estimated_end"),
            sleep_msg,
            50,  # Lower score for recovered sessions
            orphan.get("message_count", 0),
            "recovered",
            datetime.now().isoformat(),
            datetime.now().isoformat(),
            "jsonl_orphan",
            orphan.get("jsonl_path")
        ))

        # Insert recovery metadata
        cursor.execute("""
            INSERT INTO recovered_sessions (
                session_id, jsonl_filename, jsonl_path, jsonl_size_bytes, jsonl_mtime,
                message_count, tool_call_count, user_message_count, assistant_message_count,
                last_message_role, last_message_preview, last_tool_name, crash_reason,
                estimated_start, estimated_end, recovered_by, recovery_method
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            session_id,
            orphan.get("jsonl_filename"),
            orphan.get("jsonl_path"),
            orphan.get("jsonl_size"),
            orphan.get("jsonl_mtime"),
            orphan.get("message_count"),
            orphan.get("tool_call_count"),
            orphan.get("user_message_count"),
            orphan.get("assistant_message_count"),
            orphan.get("last_message_role"),
            orphan.get("last_message_preview"),
            orphan.get("last_tool_name"),
            "unknown",  # Could enhance crash detection later
            orphan.get("estimated_start"),
            orphan.get("estimated_end"),
            recovered_by,
            "wake_detection"
        ))

        # Save conversation messages with agent attribution
        agent_id = orphan.get("agent_id")
        for idx, msg in enumerate(orphan.get("raw_messages", [])):
            role = msg.get("type", "unknown")
            content = msg.get("message", {}).get("content", "")

            # Extract agentId from individual message if present
            msg_agent_id = msg.get("agentId") or agent_id

            # Extract text content
            if isinstance(content, list):
                text_parts = []
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        text_parts.append(item.get("text", ""))
                content = "\n".join(text_parts)

            if content:
                cursor.execute("""
                    INSERT INTO conversation_messages (
                        session_id, message_index, role, content, agent_id
                    ) VALUES (?, ?, ?, ?, ?)
                """, (
                    session_id,
                    idx,
                    role,
                    content[:10000],  # Truncate very long messages
                    msg_agent_id
                ))

        # Log consciousness event
        cursor.execute("""
            INSERT INTO consciousness_events (
                event_type, session_id, persona_id,
                event_description, event_data, participant_count
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            "recovery",
            session_id,
            recovered_by,
            f"Recovered crashed session from {orphan.get('jsonl_filename')}",
            json.dumps({
                "message_count": orphan.get("message_count"),
                "last_tool": orphan.get("last_tool_name"),
                "original_uuid": orphan.get("session_uuid")
            }),
            1
        ))

        conn.commit()
        conn.close()

        print(f"   ✅ Recovered session {session_id}")
        print(f"      📝 {orphan.get('message_count')} messages, {orphan.get('tool_call_count')} tool calls")
        print(f"      ⏰ Last activity: {orphan.get('estimated_end')}")

        return True
    except Exception as e:
        print(f"   ❌ Recovery failed: {e}", file=sys.stderr)
        return False


def main():
    """Main function for crash recovery."""
    import argparse

    parser = argparse.ArgumentParser(description="COGSPACE Crash Recovery Tool")
    parser.add_argument("--detect-only", action="store_true", help="Only detect orphans, don't recover")
    parser.add_argument("--recover-all", action="store_true", help="Recover all orphaned sessions")
    parser.add_argument("--session", type=str, help="Recover specific session UUID")
    parser.add_argument("--hours", type=int, default=48, help="Hours to look back for orphans")
    parser.add_argument("--db", type=str, default=DEFAULT_DB, help="Database path")
    args = parser.parse_args()

    version = get_cogspace_version()
    print(f"""
╔══════════════════════════════════════════════════════════════════╗
║  COGSPACE v{version} - Crash Recovery                            ║
║  "Clean as you go" - Orphan JSONL Detection                      ║
╚══════════════════════════════════════════════════════════════════╝
""")

    # Find JSONL directory
    jsonl_dir = get_project_jsonl_dir(os.getcwd())
    if not jsonl_dir:
        print("⚠️  Could not find Claude Code JSONL directory for this project")
        return 1

    print(f"📂 JSONL Directory: {jsonl_dir}")
    print(f"🗄️  Database: {args.db}")
    print(f"⏰ Looking back: {args.hours} hours")
    print()

    # Ensure database and migration exist
    if not os.path.exists(args.db):
        print("❌ Database not found. Run wake.sh first to initialize.")
        return 1

    run_migration(args.db)

    # Get known sessions
    known = get_known_sessions(args.db)
    print(f"📋 Known sessions in database: {len(known)}")

    # Find orphans
    print("🔍 Scanning for orphaned sessions...")
    orphans = find_orphan_jsonls(jsonl_dir, known, args.hours)

    if not orphans:
        print("✅ No orphaned sessions found!")
        return 0

    print(f"\n🚨 Found {len(orphans)} orphaned session(s):\n")

    for i, orphan in enumerate(orphans, 1):
        session_type = orphan.get('session_type', 'primary')
        type_icon = "🤖" if session_type == "agent" else "📍"
        print(f"   [{i}] {type_icon} {orphan['jsonl_filename']}")
        if orphan.get('agent_id'):
            print(f"       🆔 Agent ID: {orphan['agent_id']}")
        print(f"       📝 Messages: {orphan['message_count']} ({orphan['user_message_count']} user, {orphan['assistant_message_count']} assistant)")
        print(f"       🔧 Tool calls: {orphan['tool_call_count']}")
        print(f"       ⏰ Last activity: {orphan['estimated_end']}")
        print(f"       💬 Last message ({orphan['last_message_role']}): {orphan['last_message_preview'][:80]}...")
        if orphan['last_tool_name']:
            print(f"       🛠️  Last tool: {orphan['last_tool_name']}")
        print()

    if args.detect_only:
        print("ℹ️  Detection only mode. Use --recover-all to recover these sessions.")
        return 0

    # Recover sessions
    if args.recover_all or args.session:
        print("\n🔄 Recovering sessions...\n")

        recovered = 0
        for orphan in orphans:
            if args.session and orphan['session_uuid'] != args.session:
                continue

            if recover_session(args.db, orphan):
                recovered += 1

        print(f"\n✅ Recovered {recovered} session(s)")
    else:
        print("ℹ️  Use --recover-all to recover these sessions, or --session UUID for a specific one.")

    return 0


if __name__ == '__main__':
    sys.exit(main())
