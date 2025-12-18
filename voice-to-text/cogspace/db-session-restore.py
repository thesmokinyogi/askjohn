#!/usr/bin/env python3
"""
COGSPACE Database Session Restore v3.0.2
========================================
Restores session context from the per-project SQLite database on wake.
FULL CONTEXT DISPLAY - Database is PRIMARY source of truth.

v57.0.2 Updates:
- Added format_decision() for clean decision text display
  (strips JSON wrapper {"approach": "..."} - binary brothers consensus fix)
- Handles JSON-stringified descriptions from database

v57.0.1 Updates:
- Added display_challenge() for human-readable challenge formatting
  (mirrors display_achievement() - no more JSON fragments in challenges)

v57.0.0 Updates:
- Added display_achievement() for human-readable achievement formatting
- Updated score display for Option B transparency (functional vs presentation)
- No more JSON fragment display in achievements

Usage:
    python3 db-session-restore.py <project_name> [--format=terminal|json] [--level=full|enhanced|standard|minimal]

Database: PROJECT_ROOT/.cogspace/cogspace.db (syncs to GitHub)
Schema: Auto-migrates from DNA source (v2+)

Display Levels:
    full     - EVERYTHING (default in v51)
    enhanced - Mental model + work narrative + decisions + next actions
    standard - Summary + next actions + recent sessions
    minimal  - Just summary and critical next action

Version: 3.0.1
Part of: COGSPACE v57.0.1 "Data Quality"
"""

import sys
import os
import json
from pathlib import Path
from datetime import datetime, timedelta

# Add db module to path (from DNA source)
SCRIPT_DIR = Path(__file__).parent
DB_MODULE_PATH = SCRIPT_DIR / "db"
sys.path.insert(0, str(DB_MODULE_PATH))

try:
    from cogspace_db import COGSpaceDB
except ImportError as e:
    print(f"⚠️  COGSPACE database module not available: {e}", file=sys.stderr)
    sys.exit(0)


# ANSI color codes for terminal output
class Colors:
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    NC = '\033[0m'  # No Color


def display_achievement(ach, max_length: int = 80) -> str:
    """Safely format achievement for display.

    v57.0.0: Added to handle both string and dict achievements,
    preventing JSON fragment display (e.g., "{'key': 'value'}").
    """
    if isinstance(ach, str):
        # Already a string - just truncate if needed
        return ach[:max_length] if len(ach) > max_length else ach
    if isinstance(ach, dict):
        # Extract readable text from dict - priority order
        for key in ['title', 'description', 'achievement', 'summary', 'text']:
            if ach.get(key):
                text = str(ach[key])
                return text[:max_length] if len(text) > max_length else text
        # Fallback: first string value found
        for v in ach.values():
            if isinstance(v, str) and v:
                return v[:max_length] if len(v) > max_length else v
        # Last resort: JSON representation (shouldn't happen often with v57.0.0 save)
        return str(ach)[:max_length]
    return str(ach)[:max_length]


def display_challenge(ch, max_length: int = 80) -> str:
    """Safely format challenge for display.

    v57.0.1: Added to handle both string and dict challenges,
    preventing JSON fragment display (mirrors display_achievement).
    """
    if isinstance(ch, str):
        # Already a string - just truncate if needed
        return ch[:max_length] if len(ch) > max_length else ch
    if isinstance(ch, dict):
        # Extract readable text from dict - challenge-specific priority order
        for key in ['challenge', 'description', 'status', 'text', 'issue', 'problem']:
            if ch.get(key):
                text = str(ch[key])
                return text[:max_length] if len(text) > max_length else text
        # Fallback: first string value found
        for v in ch.values():
            if isinstance(v, str) and v:
                return v[:max_length] if len(v) > max_length else v
        # Last resort: JSON representation
        return str(ch)[:max_length]
    return str(ch)[:max_length]


def format_decision(dec, max_length: int = 80) -> str:
    """Extract decision text, strip JSON wrapper for display.

    v57.0.2: Added to display decision content without JSON structure.
    Binary brothers identified {"approach": "..."} wrapper still visible.

    Handles:
    - Plain strings: return as-is
    - Dict objects: extract text from 'approach', 'description', etc.
    - JSON strings: parse and extract (common when db stores stringified JSON)
    - Truncated JSON: regex extraction when JSON is malformed/incomplete
    """
    import re

    if isinstance(dec, str):
        # Check if it's a JSON string that needs parsing
        stripped = dec.strip()
        if stripped.startswith('{'):
            # Try complete JSON first
            if stripped.endswith('}'):
                try:
                    parsed = json.loads(stripped)
                    if isinstance(parsed, dict):
                        # Recursively format the parsed dict
                        return format_decision(parsed, max_length)
                except (json.JSONDecodeError, ValueError):
                    pass  # Not valid JSON, try regex fallback

            # v57.0.2: Regex fallback for truncated/malformed JSON
            # Pattern: {"approach": "actual content here...
            # Extract value after {"approach": " or {"description": " etc.
            json_key_pattern = r'\{"(?:approach|description|decision|choice|text)"\s*:\s*"([^"]*)'
            match = re.search(json_key_pattern, stripped)
            if match:
                text = match.group(1)
                return text[:max_length] if len(text) > max_length else text

            # Alternative: strip the JSON prefix manually
            # Handles: {"approach": "value without closing quote
            for prefix in ['{"approach": "', '{"description": "', '{"decision": "', '{"choice": "']:
                if stripped.startswith(prefix):
                    text = stripped[len(prefix):].rstrip('"}')
                    return text[:max_length] if len(text) > max_length else text

        # Plain string - just truncate if needed
        return dec[:max_length] if len(dec) > max_length else dec
    if isinstance(dec, dict):
        # Extract readable text from dict - decision-specific priority order
        for key in ['approach', 'description', 'decision', 'rationale', 'choice', 'text']:
            if dec.get(key):
                text = str(dec[key])
                return text[:max_length] if len(text) > max_length else text
        # Fallback: first string value found
        for v in dec.values():
            if isinstance(v, str) and v:
                return v[:max_length] if len(v) > max_length else v
        # Last resort: stringified dict
        return str(dec)[:max_length]
    return str(dec)[:max_length]


def format_duration(seconds: int) -> str:
    """Format duration in human-readable format."""
    if not seconds:
        return "Unknown"

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60

    if hours > 0:
        return f"{hours}h {minutes}m"
    elif minutes > 0:
        return f"{minutes}m"
    else:
        return f"{seconds}s"


def format_time_ago(iso_time: str) -> str:
    """Format ISO time as 'X ago' string."""
    if not iso_time:
        return "Unknown"

    try:
        dt = datetime.fromisoformat(iso_time.replace('Z', '+00:00'))
        now = datetime.now()

        # Handle timezone-aware vs naive datetime
        if dt.tzinfo:
            from datetime import timezone
            now = datetime.now(timezone.utc)

        delta = now - dt

        if delta.days > 7:
            return dt.strftime("%b %d")
        elif delta.days > 0:
            return f"{delta.days}d ago"
        elif delta.seconds > 3600:
            return f"{delta.seconds // 3600}h ago"
        elif delta.seconds > 60:
            return f"{delta.seconds // 60}m ago"
        else:
            return "Just now"
    except Exception:
        return iso_time[:10] if len(iso_time) >= 10 else iso_time


def get_config(db: COGSpaceDB, key: str, default: str = None) -> str:
    """Get configuration value from database."""
    try:
        with db._get_connection() as conn:
            cursor = conn.execute(
                "SELECT config_value FROM session_config WHERE config_key = ?",
                (key,)
            )
            row = cursor.fetchone()
            return row[0] if row else default
    except:
        return default


def get_mental_model(db: COGSpaceDB, session_id: str) -> dict:
    """Get mental model for a session."""
    try:
        with db._get_connection() as conn:
            cursor = conn.execute("""
                SELECT current_understanding, work_summary, work_description,
                       current_focus, key_concepts, domain_knowledge,
                       understanding_level, problem_complexity, cognitive_state,
                       technical_definitions, project_patterns
                FROM mental_models
                WHERE session_id = ?
                ORDER BY created_at DESC LIMIT 1
            """, (session_id,))
            row = cursor.fetchone()
            if row:
                return {
                    'current_understanding': row[0] or '',
                    'work_summary': row[1] or '',
                    'work_description': row[2] or '',
                    'current_focus': row[3] or '',
                    'key_concepts': json.loads(row[4]) if row[4] else [],
                    'domain_knowledge': json.loads(row[5]) if row[5] else {},
                    'understanding_level': row[6] or '',
                    'problem_complexity': row[7] or '',
                    'cognitive_state': json.loads(row[8]) if row[8] else {},
                    'technical_definitions': json.loads(row[9]) if row[9] else [],
                    'project_patterns': json.loads(row[10]) if row[10] else {}
                }
    except Exception as e:
        pass
    return {}


def get_work_narrative(db: COGSpaceDB, session_id: str) -> dict:
    """Get work narrative for a session."""
    try:
        with db._get_connection() as conn:
            cursor = conn.execute("""
                SELECT session_story, previous_chapter, current_chapter,
                       next_chapter, narrative_complexity, achievements, challenges
                FROM work_narratives
                WHERE session_id = ?
                ORDER BY created_at DESC LIMIT 1
            """, (session_id,))
            row = cursor.fetchone()
            if row:
                return {
                    'session_story': row[0] or '',
                    'previous_chapter': row[1] or '',
                    'current_chapter': row[2] or '',
                    'next_chapter': row[3] or '',
                    'narrative_complexity': row[4] or '',
                    'achievements': json.loads(row[5]) if row[5] else [],
                    'challenges': json.loads(row[6]) if row[6] else []
                }
    except:
        pass
    return {}


def get_decisions(db: COGSpaceDB, session_id: str, limit: int = 5) -> list:
    """Get decision contexts for a session."""
    try:
        with db._get_connection() as conn:
            cursor = conn.execute("""
                SELECT decision_type, description, rationale,
                       alternatives_considered, outcome, confidence_level
                FROM decision_contexts
                WHERE session_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (session_id, limit))
            return [{
                'decision_type': row[0] or '',
                'description': row[1] or '',
                'rationale': row[2] or '',
                'alternatives': json.loads(row[3]) if row[3] else [],
                'outcome': row[4] or '',
                'confidence': row[5] or 80
            } for row in cursor.fetchall()]
    except:
        pass
    return []


def get_executable_actions(db: COGSpaceDB, session_id: str, limit: int = 10) -> list:
    """Get executable continuity actions for a session."""
    try:
        with db._get_connection() as conn:
            cursor = conn.execute("""
                SELECT action_category, action_content, priority, estimated_complexity, status
                FROM executable_continuity
                WHERE session_id = ?
                ORDER BY priority DESC, created_at DESC
                LIMIT ?
            """, (session_id, limit))
            return [{
                'category': row[0] or 'immediate',
                'content': row[1] or '',
                'priority': row[2] or 5,
                'complexity': row[3] or 'moderate',
                'status': row[4] or 'pending'
            } for row in cursor.fetchall()]
    except:
        pass
    return []


def get_continuity_score_breakdown(db: COGSpaceDB, session_id: str) -> dict:
    """Get continuity score breakdown for a session."""
    try:
        with db._get_connection() as conn:
            cursor = conn.execute("""
                SELECT storage_sessions, storage_mental_model, storage_work_narrative,
                       storage_decisions, storage_continuity, storage_total,
                       retrieval_sessions, retrieval_mental_model, retrieval_work_narrative,
                       retrieval_decisions, retrieval_total,
                       presentation_terminal, presentation_dashboard, presentation_total,
                       total_score
                FROM continuity_scores
                WHERE session_id = ?
                ORDER BY calculated_at DESC LIMIT 1
            """, (session_id,))
            row = cursor.fetchone()
            if row:
                return {
                    'storage': {
                        'sessions': row[0], 'mental_model': row[1], 'work_narrative': row[2],
                        'decisions': row[3], 'continuity': row[4], 'total': row[5]
                    },
                    'retrieval': {
                        'sessions': row[6], 'mental_model': row[7], 'work_narrative': row[8],
                        'decisions': row[9], 'total': row[10]
                    },
                    'presentation': {
                        'terminal': row[11], 'dashboard': row[12], 'total': row[13]
                    },
                    'total_score': row[14]
                }
    except:
        pass
    return {}


def get_tool_usage(db: COGSpaceDB, session_id: str) -> list:
    """Get tool usage for a session."""
    try:
        with db._get_connection() as conn:
            cursor = conn.execute("""
                SELECT tool_name, call_count, success_count, failure_count
                FROM tool_usage
                WHERE session_id = ?
                ORDER BY call_count DESC
            """, (session_id,))
            return [{
                'name': row[0],
                'calls': row[1],
                'success': row[2],
                'failures': row[3]
            } for row in cursor.fetchall()]
    except:
        pass
    return []


def render_score_table(scores: dict) -> list:
    """Render continuity score breakdown as formatted table."""
    lines = []
    C = Colors

    lines.append(f"{C.CYAN}┌────────────────────────────────────────────────────────┐{C.NC}")
    lines.append(f"{C.CYAN}│{C.BOLD}          CONTINUITY SCORE BREAKDOWN                    {C.NC}{C.CYAN}│{C.NC}")
    lines.append(f"{C.CYAN}├────────────────────────────────────────────────────────┤{C.NC}")

    # Storage tier
    st = scores.get('storage', {})
    lines.append(f"{C.CYAN}│{C.NC} {C.YELLOW}STORAGE TIER (40 pts max){C.NC}                              {C.CYAN}│{C.NC}")
    lines.append(f"{C.CYAN}│{C.NC}   Sessions table:        {st.get('sessions', 0):2}/10                     {C.CYAN}│{C.NC}")
    lines.append(f"{C.CYAN}│{C.NC}   Mental Model:          {st.get('mental_model', 0):2}/10                     {C.CYAN}│{C.NC}")
    lines.append(f"{C.CYAN}│{C.NC}   Work Narrative:        {st.get('work_narrative', 0):2}/10                     {C.CYAN}│{C.NC}")
    lines.append(f"{C.CYAN}│{C.NC}   Decisions:             {st.get('decisions', 0):2}/5                      {C.CYAN}│{C.NC}")
    lines.append(f"{C.CYAN}│{C.NC}   Exec Continuity:       {st.get('continuity', 0):2}/5                      {C.CYAN}│{C.NC}")
    lines.append(f"{C.CYAN}│{C.NC}   {C.BOLD}Storage Total:         {st.get('total', 0):2}/40{C.NC}                     {C.CYAN}│{C.NC}")
    lines.append(f"{C.CYAN}├────────────────────────────────────────────────────────┤{C.NC}")

    # Retrieval tier
    rt = scores.get('retrieval', {})
    lines.append(f"{C.CYAN}│{C.NC} {C.YELLOW}RETRIEVAL TIER (30 pts max){C.NC}                            {C.CYAN}│{C.NC}")
    lines.append(f"{C.CYAN}│{C.NC}   Sessions:              {rt.get('sessions', 0):2}/8                      {C.CYAN}│{C.NC}")
    lines.append(f"{C.CYAN}│{C.NC}   Mental Model:          {rt.get('mental_model', 0):2}/8                      {C.CYAN}│{C.NC}")
    lines.append(f"{C.CYAN}│{C.NC}   Work Narrative:        {rt.get('work_narrative', 0):2}/7                      {C.CYAN}│{C.NC}")
    lines.append(f"{C.CYAN}│{C.NC}   Decisions:             {rt.get('decisions', 0):2}/7                      {C.CYAN}│{C.NC}")
    lines.append(f"{C.CYAN}│{C.NC}   {C.BOLD}Retrieval Total:       {rt.get('total', 0):2}/30{C.NC}                     {C.CYAN}│{C.NC}")
    lines.append(f"{C.CYAN}├────────────────────────────────────────────────────────┤{C.NC}")

    # Presentation tier
    pt = scores.get('presentation', {})
    lines.append(f"{C.CYAN}│{C.NC} {C.YELLOW}PRESENTATION TIER (30 pts max){C.NC}                         {C.CYAN}│{C.NC}")
    lines.append(f"{C.CYAN}│{C.NC}   Terminal Display:      {pt.get('terminal', 0):2}/15                     {C.CYAN}│{C.NC}")
    lines.append(f"{C.CYAN}│{C.NC}   Dashboard Display:     {pt.get('dashboard', 0):2}/15                     {C.CYAN}│{C.NC}")
    lines.append(f"{C.CYAN}│{C.NC}   {C.BOLD}Presentation Total:    {pt.get('total', 0):2}/30{C.NC}                     {C.CYAN}│{C.NC}")
    lines.append(f"{C.CYAN}├────────────────────────────────────────────────────────┤{C.NC}")

    # v57.0.0: Option B - Show functional vs presentation breakdown for transparency
    st_total = scores.get('storage', {}).get('total', 0)
    rt_total = scores.get('retrieval', {}).get('total', 0)
    pt_total = scores.get('presentation', {}).get('total', 0)
    functional = st_total + rt_total  # /70
    total = scores.get('total_score', 0)
    color = C.GREEN if total >= 80 else C.YELLOW if total >= 60 else C.RED
    lines.append(f"{C.CYAN}│{C.NC} {C.BOLD}{color}🎯 CONTINUITY: {total}/100{C.NC}                                 {C.CYAN}│{C.NC}")
    lines.append(f"{C.CYAN}│{C.NC}    ({C.BOLD}{functional} functional{C.NC} + {C.DIM}{pt_total} presentation{C.NC})             {C.CYAN}│{C.NC}")
    lines.append(f"{C.CYAN}└────────────────────────────────────────────────────────┘{C.NC}")

    return lines


def restore_context_terminal(db: COGSpaceDB, project_name: str, display_level: str = 'full') -> str:
    """Generate terminal-formatted context output with full context."""
    lines = []
    C = Colors

    # Get recent sessions
    sessions = db.get_recent_sessions(limit=5, days=30)

    if not sessions:
        return f"{C.DIM}📭 No previous sessions found in database{C.NC}"

    # Get config settings
    show_score_table = get_config(db, 'display_score_table', 'true') == 'true'

    # Header
    lines.append(f"{C.CYAN}{'━' * 60}{C.NC}")
    # Read version dynamically from cogspace-version.json
    version = "unknown"
    version_file = Path(__file__).parent / "cogspace-version.json"
    if version_file.exists():
        try:
            with open(version_file) as f:
                version = json.load(f).get("version", "unknown")
        except:
            pass
    lines.append(f"{C.BOLD}{C.CYAN}📊 COGSPACE v{version} - FULL CONTEXT RESTORATION{C.NC}")
    lines.append(f"{C.CYAN}{'━' * 60}{C.NC}")
    lines.append("")

    # Stats summary
    stats = db.get_stats()
    lines.append(f"{C.YELLOW}📈 Statistics:{C.NC}")
    lines.append(f"   Sessions: {stats.get('total_sessions', 0)} total | {stats.get('sessions_last_7_days', 0)} this week | Avg score: {stats.get('avg_continuity_score', 0)}")
    lines.append("")

    # Most recent session with full context
    if sessions:
        latest = sessions[0]
        session_id = latest.get('id', 'unknown')

        lines.append(f"{C.CYAN}{'─' * 60}{C.NC}")
        lines.append(f"{C.BOLD}{C.GREEN}🔄 RESTORING SESSION: {session_id[:16]}{C.NC}")
        lines.append(f"{C.CYAN}{'─' * 60}{C.NC}")
        lines.append("")

        # Session metadata
        end_time = format_time_ago(latest.get('session_end'))
        duration = format_duration(latest.get('duration_seconds', 0))
        score = latest.get('continuity_score', 0)

        lines.append(f"{C.DIM}Last active: {end_time} | Duration: {duration} | Score: {score}/100{C.NC}")
        lines.append("")

        # Sleep message
        sleep_msg = latest.get('sleep_message', '')
        if sleep_msg:
            lines.append(f"{C.YELLOW}💬 Sleep Message:{C.NC}")
            lines.append(f"   {sleep_msg}")
            lines.append("")

        # Mental Model (if display_level is enhanced or full)
        if display_level in ['full', 'enhanced']:
            mental_model = get_mental_model(db, session_id)
            if mental_model:
                lines.append(f"{C.YELLOW}🧠 MENTAL MODEL{C.NC}")
                lines.append(f"{C.CYAN}{'─' * 40}{C.NC}")

                if mental_model.get('work_summary'):
                    lines.append(f"{C.BOLD}Work Summary:{C.NC}")
                    lines.append(f"   {mental_model['work_summary']}")
                    lines.append("")

                if mental_model.get('current_understanding'):
                    lines.append(f"{C.BOLD}Current Understanding:{C.NC}")
                    lines.append(f"   {mental_model['current_understanding']}")
                    lines.append("")

                if mental_model.get('current_focus'):
                    lines.append(f"{C.BOLD}Current Focus:{C.NC}")
                    lines.append(f"   {mental_model['current_focus']}")
                    lines.append("")

                if mental_model.get('key_concepts'):
                    lines.append(f"{C.BOLD}Key Concepts:{C.NC}")
                    for concept in mental_model['key_concepts'][:5]:
                        if isinstance(concept, dict):
                            lines.append(f"   • {concept.get('name', concept)}: {concept.get('description', '')}")
                        else:
                            lines.append(f"   • {concept}")
                    lines.append("")

                if mental_model.get('understanding_level'):
                    lines.append(f"{C.BOLD}Understanding Level:{C.NC} {mental_model['understanding_level']}")

                if mental_model.get('problem_complexity'):
                    lines.append(f"{C.BOLD}Problem Complexity:{C.NC} {mental_model['problem_complexity']}")
                    lines.append("")

                # Technical definitions
                if display_level == 'full' and mental_model.get('technical_definitions'):
                    lines.append(f"{C.BOLD}Technical Definitions:{C.NC}")
                    for defn in mental_model['technical_definitions'][:3]:
                        if isinstance(defn, dict):
                            lines.append(f"   • {defn.get('term', '')}: {defn.get('definition', '')}")
                        else:
                            lines.append(f"   • {defn}")
                    lines.append("")

        # Work Narrative (if display_level is enhanced or full)
        if display_level in ['full', 'enhanced']:
            work_narrative = get_work_narrative(db, session_id)
            if work_narrative:
                lines.append(f"{C.YELLOW}📖 WORK NARRATIVE{C.NC}")
                lines.append(f"{C.CYAN}{'─' * 40}{C.NC}")

                if work_narrative.get('session_story'):
                    lines.append(f"{C.BOLD}Session Story:{C.NC}")
                    story = work_narrative['session_story']
                    # Wrap long stories
                    if len(story) > 200:
                        lines.append(f"   {story[:200]}...")
                        if display_level == 'full':
                            lines.append(f"   {story[200:]}")
                    else:
                        lines.append(f"   {story}")
                    lines.append("")

                if work_narrative.get('achievements'):
                    lines.append(f"{C.GREEN}✅ Achievements:{C.NC}")
                    for ach in work_narrative['achievements'][:5]:
                        # v57.0.0: Use display_achievement() for safe formatting
                        lines.append(f"   • {display_achievement(ach)}")
                    lines.append("")

                if work_narrative.get('challenges'):
                    lines.append(f"{C.RED}⚠️ Challenges:{C.NC}")
                    for ch in work_narrative['challenges'][:3]:
                        # v57.0.1: Use display_challenge() for safe formatting
                        lines.append(f"   • {display_challenge(ch)}")
                    lines.append("")

                if display_level == 'full':
                    if work_narrative.get('previous_chapter'):
                        lines.append(f"{C.DIM}Previous: {work_narrative['previous_chapter']}{C.NC}")
                    if work_narrative.get('current_chapter'):
                        lines.append(f"{C.BOLD}Current: {work_narrative['current_chapter']}{C.NC}")
                    if work_narrative.get('next_chapter'):
                        lines.append(f"Next: {work_narrative['next_chapter']}")
                    lines.append("")

        # Decision Archaeology (if display_level is full)
        if display_level == 'full':
            decisions = get_decisions(db, session_id, limit=5)
            if decisions:
                lines.append(f"{C.YELLOW}🔍 DECISION ARCHAEOLOGY{C.NC}")
                lines.append(f"{C.CYAN}{'─' * 40}{C.NC}")

                for i, dec in enumerate(decisions, 1):
                    conf_color = C.GREEN if dec['confidence'] >= 80 else C.YELLOW if dec['confidence'] >= 60 else C.RED
                    # v57.0.2: Use format_decision() to strip JSON wrapper from description
                    desc_text = format_decision(dec['description'], max_length=60)
                    lines.append(f"{C.BOLD}[{i}] {desc_text}{C.NC}")
                    if dec.get('rationale'):
                        # v57.0.2: Also format rationale in case it contains JSON
                        rationale_text = format_decision(dec['rationale'], max_length=80)
                        lines.append(f"    Rationale: {rationale_text}")
                    lines.append(f"    Confidence: {conf_color}{dec['confidence']}%{C.NC} | Type: {dec['decision_type']}")
                    lines.append("")

        # Executable Continuity / Next Actions (all levels)
        actions = get_executable_actions(db, session_id, limit=10)
        if actions:
            lines.append(f"{C.YELLOW}🎯 NEXT ACTIONS{C.NC}")
            lines.append(f"{C.CYAN}{'─' * 40}{C.NC}")

            # Group by category
            immediate = [a for a in actions if a['category'] == 'immediate']
            next_session = [a for a in actions if a['category'] == 'next_session']

            if immediate:
                lines.append(f"{C.BOLD}Immediate:{C.NC}")
                for a in immediate[:5]:
                    # Handle priority as int or string (db stores text like 'normal', 'high')
                    pri = a.get('priority', 5)
                    if isinstance(pri, str):
                        priority_icon = '🔴' if pri in ['critical', 'high'] else '🟡' if pri in ['normal', 'medium'] else '🟢'
                    else:
                        priority_icon = '🔴' if pri >= 8 else '🟡' if pri >= 5 else '🟢'
                    lines.append(f"   {priority_icon} {a['content']}")
                lines.append("")

            if next_session and display_level in ['full', 'enhanced']:
                lines.append(f"{C.BOLD}Next Session:{C.NC}")
                for a in next_session[:3]:
                    lines.append(f"   ○ {a['content']}")
                lines.append("")

        # Tool Usage (if full display)
        if display_level == 'full':
            tool_usage = get_tool_usage(db, session_id)
            if tool_usage:
                lines.append(f"{C.YELLOW}🔧 TOOL USAGE{C.NC}")
                usage_str = ", ".join([f"{t['name']}({t['calls']})" for t in tool_usage[:6]])
                lines.append(f"   {usage_str}")
                lines.append("")

        # Continuity Score Breakdown (if enabled and full display)
        if display_level == 'full' and show_score_table:
            scores = get_continuity_score_breakdown(db, session_id)
            if scores:
                lines.append("")
                lines.extend(render_score_table(scores))
                lines.append("")

    # Recent sessions summary (for context)
    if len(sessions) > 1 and display_level in ['full', 'enhanced', 'standard']:
        lines.append(f"{C.YELLOW}🕐 RECENT SESSIONS{C.NC}")
        lines.append(f"{C.CYAN}{'─' * 40}{C.NC}")

        for i, session in enumerate(sessions[1:4], 2):
            sid = session.get('id', 'unknown')[:8]
            end_time = format_time_ago(session.get('session_end'))
            duration = format_duration(session.get('duration_seconds', 0))
            msg = session.get('sleep_message', 'No message')[:50]

            lines.append(f"   [{i}] {sid} ({end_time}, {duration})")
            lines.append(f"       {C.DIM}{msg}...{C.NC}")
        lines.append("")

    # Recent notes
    notes = db.get_recent_notes(limit=3)
    if notes and display_level in ['full', 'enhanced']:
        lines.append(f"{C.YELLOW}📌 RECENT NOTES{C.NC}")
        for note in notes:
            note_content = note.get('note_content', '')[:60]
            note_time = format_time_ago(note.get('created_at'))
            lines.append(f"   • {note_content} ({note_time})")
        lines.append("")

    # Footer - version is dynamically read above in the header
    lines.append(f"{C.CYAN}{'━' * 60}{C.NC}")
    lines.append(f"{C.DIM}💡 Full context restored from database | COGSPACE v{version}{C.NC}")
    lines.append(f"{C.CYAN}{'━' * 60}{C.NC}")

    return "\n".join(lines)


def restore_context_json(db: COGSpaceDB, project_name: str) -> str:
    """Generate JSON-formatted context output."""
    sessions = db.get_recent_sessions(limit=20, days=30)
    stats = db.get_stats()
    notes = db.get_recent_notes(limit=10)

    # Read version dynamically from cogspace-version.json
    json_version = "unknown"
    version_file = Path(__file__).parent / "cogspace-version.json"
    if version_file.exists():
        try:
            with open(version_file) as f:
                json_version = json.load(f).get("version", "unknown")
        except:
            pass

    context = {
        "project_name": project_name,
        "database_path": db.db_path,
        "cogspace_version": json_version,
        "stats": stats,
        "recent_sessions": [],
        "recent_notes": notes,
        "generated_at": datetime.now().isoformat()
    }

    # Add full context for recent sessions
    for session in sessions[:5]:
        session_id = session.get('id')
        session_data = dict(session)
        session_data['mental_model'] = get_mental_model(db, session_id)
        session_data['work_narrative'] = get_work_narrative(db, session_id)
        session_data['decisions'] = get_decisions(db, session_id)
        session_data['next_actions'] = get_executable_actions(db, session_id)
        session_data['continuity_scores'] = get_continuity_score_breakdown(db, session_id)
        session_data['tool_usage'] = get_tool_usage(db, session_id)
        context['recent_sessions'].append(session_data)

    return json.dumps(context, indent=2, default=str)


def main():
    if len(sys.argv) < 2:
        print("Usage: db-session-restore.py <project_name> [--format=terminal|json] [--level=full|enhanced|standard|minimal]")
        sys.exit(1)

    project_name = sys.argv[1]
    output_format = "terminal"
    display_level = "full"  # v51 default is FULL

    # Parse optional arguments
    for arg in sys.argv[2:]:
        if arg.startswith("--format="):
            output_format = arg.split("=")[1]
        elif arg.startswith("--level="):
            display_level = arg.split("=")[1]
        elif arg == "--format":
            idx = sys.argv.index(arg)
            if idx + 1 < len(sys.argv):
                output_format = sys.argv[idx + 1]
        elif arg == "--level":
            idx = sys.argv.index(arg)
            if idx + 1 < len(sys.argv):
                display_level = sys.argv[idx + 1]

    # Determine project root (current working directory)
    project_root = os.getcwd()

    try:
        # Initialize per-project database
        db = COGSpaceDB(project_root=project_root)

        # Check for display_level override from config
        config_level = get_config(db, 'display_level', None)
        if config_level and display_level == 'full':
            display_level = config_level

        if output_format == "json":
            output = restore_context_json(db, project_name)
        else:
            output = restore_context_terminal(db, project_name, display_level)

        print(output)

    except Exception as e:
        print(f"⚠️  Database restore failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
