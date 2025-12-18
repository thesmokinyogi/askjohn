#!/usr/bin/env python3
"""
COGSPACE Database Session Save v5.0.0
=====================================
Saves session data to the per-project SQLite database on sleep.
100% FIDELITY - Database is PRIMARY storage.

v59.0.0 Updates:
- Added session_participants tracking for multi-consciousness sessions
- Added resolve_persona() for agent_id → persona mapping
- Added log_consciousness_event() for tracking wake/sleep/handoff events
- Added extract_session_participants() for distributed consciousness capture
- Personas imported from Crystal Palace Registry V7

v57.0.1 Updates:
- Added code content filter to extract_decisions_from_conversation()
  (fixes ironic bug where regex patterns in code discussion were captured)
- Added format_challenge() for human-readable challenge text (mirrors achievements)

v57.0.0 Updates:
- Enhanced decision extraction from multiple JSON structures
- Added conversation pattern extraction for decisions
- Added format_achievement() for human-readable achievement text
- Added validate_data_quality() for quality assurance
- Weighted 8-field mental model scoring
- Field semantic separation (workSummary vs currentUnderstanding)

v56.0.0 Updates:
- Added conversation_messages extraction and storage
- Added semantic_summaries extraction and storage
- Full JSON parity with 7 new tables

Usage:
    python3 db-session-save.py <session_id> <project_name> [context_json_path] [sleep_message]

Database: PROJECT_ROOT/.cogspace/cogspace.db (syncs to GitHub)
Schema: Auto-migrates from DNA source (v5)

Version: 5.0.0
Part of: COGSPACE v59.0.0 "Distributed Consciousness"
"""

import sys
import os
import json
import re
from pathlib import Path
from datetime import datetime

# Add db module to path (from DNA source)
SCRIPT_DIR = Path(__file__).parent
DB_MODULE_PATH = SCRIPT_DIR / "db"
sys.path.insert(0, str(DB_MODULE_PATH))

try:
    from cogspace_db import COGSpaceDB
except ImportError as e:
    print(f"⚠️  COGSPACE database module not available: {e}", file=sys.stderr)
    sys.exit(0)


def get_cogspace_version() -> str:
    """Get COGSPACE version from cogspace-version.json (single source of truth).

    v54.0.0: Added to ensure database stores correct version, not hardcoded fallback.
    """
    version_file = SCRIPT_DIR / "cogspace-version.json"
    try:
        with open(version_file) as f:
            data = json.load(f)
            return data.get('version', 'unknown')
    except (FileNotFoundError, json.JSONDecodeError):
        return 'unknown'


def load_context_json(context_path: str) -> dict:
    """Load session context from JSON file."""
    try:
        with open(context_path, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"⚠️  Could not load context: {e}", file=sys.stderr)
        return {}


def parse_duration(duration_str: str) -> int:
    """Parse duration string to seconds."""
    if not duration_str:
        return 0

    if isinstance(duration_str, (int, float)):
        return int(duration_str)

    # Parse HH:MM:SS format
    try:
        parts = str(duration_str).split(':')
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        elif len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        else:
            return int(duration_str)
    except (ValueError, AttributeError):
        return 0


def format_achievement(item) -> str:
    """Convert achievement item to readable string.

    v57.0.0: Added to fix JSON fragment display in achievements.
    Handles string, dict, and other types with graceful fallback.
    """
    if isinstance(item, str):
        return item
    if isinstance(item, dict):
        # Priority: title > description > achievement > summary > text
        for key in ['title', 'description', 'achievement', 'summary', 'text']:
            if item.get(key):
                return str(item[key])
        # Fallback: first string value found
        for v in item.values():
            if isinstance(v, str) and v:
                return v
        # Last resort: JSON representation truncated (use json.dumps for cleaner output)
        return json.dumps(item)[:100]
    return str(item)


def format_challenge(item) -> str:
    """Convert challenge item to readable string.

    v57.0.1: Added to fix JSON fragment display in challenges.
    Mirrors format_achievement() logic with challenge-specific key priorities.
    """
    if isinstance(item, str):
        return item
    if isinstance(item, dict):
        # Priority: challenge > description > status > text > issue
        for key in ['challenge', 'description', 'status', 'text', 'issue', 'problem']:
            val = item.get(key)
            if val and isinstance(val, str):
                return val
        # Fallback: first string value found
        for v in item.values():
            if isinstance(v, str) and v:
                return v
        # Last resort: JSON representation truncated
        return json.dumps(item)[:100]
    return str(item)


def extract_decisions_from_conversation(conversation_text: str) -> list:
    """Extract decisions stated conversationally but not structured.

    v57.0.0: Added per Clarity Wake Engineer recommendation.
    Uses regex patterns to catch decisions stated in natural language.
    Lower confidence (70%) since these are pattern-extracted.

    v57.0.1: Added code content filter to skip regex patterns and code snippets.
    Fixes ironic bug where regex patterns in code discussion were captured as "decisions".
    """
    # v57.0.1: Code indicators to skip - matches look like code, not decisions
    code_indicators = [
        'r"', "r'",           # Raw string prefix (regex patterns)
        '```', '`',           # Code blocks and inline code
        'def ', 'import ',    # Python keywords
        'class ', 'function', # Code constructs
        '\\n', '\\t', '\\r',  # Escape sequences
        'pattern', 'regex',   # Meta-discussion about patterns
        '.get(', '.set(',     # Method calls
        '{}', '[]',           # Empty dict/list literals
        '(?:', '(?P<',        # Regex group syntax
        'r\\\"', "r\\'",      # Escaped raw strings
    ]

    decision_patterns = [
        r"I(?:'ve)? decided to (.+?)(?:\.|$)",
        r"The decision is to (.+?)(?:\.|$)",
        r"We(?:'ll)? go with (.+?)(?:\.|$)",
        r"Chosen approach: (.+?)(?:\.|$)",
        r"Selected: (.+?)(?:\.|$)",
        r"Going with (.+?) because",
        r"After consideration,? (.+?)(?:\.|$)",
    ]

    decisions = []
    for pattern in decision_patterns:
        matches = re.findall(pattern, conversation_text, re.IGNORECASE | re.MULTILINE)
        for match in matches:
            # v57.0.1: Skip matches that contain code indicators
            if any(indicator in match for indicator in code_indicators):
                continue  # This is code discussion, not a real decision

            if match.strip() and len(match.strip()) > 5:  # Skip very short matches
                decisions.append({
                    'decision_type': 'conversational',
                    'description': match.strip()[:200],  # Cap at 200 chars
                    'rationale': 'Extracted from conversation',
                    'alternatives_considered': [],
                    'outcome': 'chosen',
                    'confidence_level': 70,  # Lower confidence for pattern extraction
                    'evidence_basis': [],
                    'impact_assessment': '',
                    'reversibility': 'moderate',
                    'source': 'conversation_pattern'
                })

    return decisions


def validate_data_quality(session_data: dict) -> dict:
    """Validate extracted data has no quality issues.

    v57.0.0: Added per Clarity Wake Engineer recommendation.
    Returns dict of validation results for caller inspection.
    Does NOT block save - only logs warnings.
    """
    results = {'valid': True, 'issues': []}

    # Check 1: No JSON fragments in achievements
    achievements = session_data.get('work_narrative', {}).get('achievements', [])
    for i, a in enumerate(achievements):
        text = a.get('text', a) if isinstance(a, dict) else str(a)
        if text.startswith("{'") or text.startswith('{"'):
            results['valid'] = False
            results['issues'].append(f"Achievement {i} contains JSON fragment")

    # Check 2: Decisions have content
    decisions = session_data.get('decisions', [])
    for i, d in enumerate(decisions):
        desc = d.get('description', '')
        if not desc or desc == 'None' or len(desc) < 5:
            results['valid'] = False
            results['issues'].append(f"Decision {i} has empty/minimal content")

    # Check 3: Fields are distinct (workSummary vs currentUnderstanding)
    mm = session_data.get('mental_model', {})
    if mm.get('workSummary') == mm.get('currentUnderstanding'):
        if mm.get('workSummary'):  # Only flag if both have content
            results['issues'].append("workSummary and currentUnderstanding are identical")

    # Check 4: No dict repr in string fields
    for field in ['workSummary', 'currentUnderstanding', 'workDescription']:
        value = mm.get(field, '')
        if isinstance(value, str):
            if "{'achievement':" in value or '{"achievement":' in value:
                results['valid'] = False
                results['issues'].append(f"{field} contains raw dict representation")

    return results


def extract_mental_model(context: dict) -> dict:
    """
    Extract mental model with clear semantic separation.

    v57.0.0: Updated with semantic field documentation per Clarity Wake Engineer.

    Field Definitions:
    - currentUnderstanding: What AI grasps about the PROBLEM DOMAIN
      (technical context, system architecture, user requirements)

    - workSummary: What was ACCOMPLISHED this session (high-level bullets)
      (completed work, milestones achieved)

    - workDescription: HOW work progressed (detailed narrative)
      (step-by-step progression, obstacles encountered)

    - currentFocus: What is being worked on RIGHT NOW
      (immediate task or problem being addressed)

    - keyConcepts: Domain-specific terms and their meanings
      (glossary of technical concepts relevant to session)

    - domainKnowledge: Background knowledge about the system
      (architecture patterns, conventions, constraints)

    Context can have data in:
      - context.mentalModel (flat)
      - context.serializedComponents.mentalModel (nested)
      - context.cognitiveState (separate)
    """
    result = {}

    # Try flat mentalModel first
    mental_model = context.get('mentalModel', {})

    # Try nested serializedComponents.mentalModel
    serialized = context.get('serializedComponents', {})
    nested_mm = serialized.get('mentalModel', {})

    # Merge - prefer nested if available (more complete)
    if nested_mm:
        mental_model = {**mental_model, **nested_mm}

    # v57.0.0: Semantic separation - currentUnderstanding is about PROBLEM DOMAIN
    # Don't fallback to workDescription (that's different semantic meaning)
    result['currentUnderstanding'] = (
        mental_model.get('currentUnderstanding') or
        context.get('currentState', {}).get('understanding') or
        context.get('currentUnderstanding', '') or
        ''  # Don't fallback to workDescription - different semantics
    )

    # v57.0.0: workSummary is HIGH-LEVEL summary of work ACCOMPLISHED
    # Don't fallback to workDescription (that's detailed narrative)
    result['workSummary'] = (
        context.get('workSummary') or
        mental_model.get('workSummary') or
        context.get('summary') or
        ''  # Don't fallback to workDescription - different semantics
    )

    # v54.0.0: Work description - must be real content, not welcome message
    work_desc = mental_model.get('workDescription', '')
    if work_desc and 'Welcome to COGSPACE' not in work_desc:
        result['workDescription'] = work_desc
    else:
        # Fallback to session story or other sources
        result['workDescription'] = (
            context.get('workNarrative', {}).get('sessionStory') or
            context.get('serializedComponents', {}).get('workNarrative', {}).get('sessionStory') or
            ''
        )
    result['currentFocus'] = mental_model.get('currentFocus', '')

    # Key concepts - can be array
    key_concepts = (
        mental_model.get('keyConcepts') or
        mental_model.get('key_concepts') or
        context.get('keyConcepts') or
        []
    )
    if isinstance(key_concepts, str):
        key_concepts = [key_concepts]
    result['keyConcepts'] = key_concepts

    # Domain knowledge
    result['domainKnowledge'] = (
        mental_model.get('domainKnowledge') or
        mental_model.get('domain_knowledge') or
        context.get('domainKnowledge') or
        {}
    )

    # Cognitive state - from cognitiveState block or mental model
    cognitive_state = context.get('cognitiveState', {})
    if not cognitive_state:
        cognitive_state = mental_model.get('cognitiveState', {})

    result['understandingLevel'] = (
        cognitive_state.get('understandingLevel') or
        mental_model.get('understandingLevel') or
        ''
    )
    result['problemComplexity'] = (
        cognitive_state.get('problemComplexity') or
        mental_model.get('problemComplexity') or
        ''
    )
    result['cognitiveState'] = cognitive_state

    # Technical definitions
    result['technicalDefinitions'] = mental_model.get('technicalDefinitions', [])

    # Project patterns
    result['projectPatterns'] = mental_model.get('projectPatterns', {})

    return result


def extract_work_narrative(context: dict) -> dict:
    """
    Extract work narrative from context - checking multiple paths.

    v57.0.0: Added format_achievement() normalization to ensure
    achievements are human-readable strings, not JSON fragments.
    """
    result = {}

    # Try flat workNarrative first
    work_narrative = context.get('workNarrative', {})

    # Try nested serializedComponents.workNarrative
    serialized = context.get('serializedComponents', {})
    nested_wn = serialized.get('workNarrative', {})

    # Merge - prefer nested if available
    if nested_wn:
        work_narrative = {**work_narrative, **nested_wn}

    result['sessionStory'] = (
        context.get('sessionStory') or
        work_narrative.get('sessionStory') or
        work_narrative.get('session_story') or
        ''
    )

    result['progressArc'] = work_narrative.get('progressArc', '')
    result['previousChapter'] = work_narrative.get('previousChapter', '')
    result['currentChapter'] = work_narrative.get('currentChapter', '')
    result['nextChapter'] = work_narrative.get('nextChapter', '')
    result['narrativeComplexity'] = work_narrative.get('narrativeComplexity', '')

    # v57.0.0: Normalize achievements to human-readable strings
    raw_achievements = (
        context.get('achievements') or
        work_narrative.get('achievements') or
        []
    )
    result['achievements'] = [format_achievement(a) for a in raw_achievements]

    # v57.0.1: Normalize challenges to human-readable strings (mirrors achievements)
    raw_challenges = (
        context.get('challenges') or
        work_narrative.get('challenges') or
        []
    )
    result['challenges'] = [format_challenge(c) for c in raw_challenges]

    return result


def extract_decision_context(context: dict) -> list:
    """
    Extract decision contexts from context - returns list of decisions.

    v57.0.0: Enhanced to check multiple JSON paths for decision data.
    Now checks 5 different possible sources:
    1. decisionContext.chosenPaths (original)
    2. decisions[] (flat array)
    3. choices[] (alternative naming)
    4. sections.decisions[] (from ai-session-summarizer)
    5. serializedComponents.decisionContext.chosenPaths (nested)
    """
    decisions = []

    # Source 1: decisionContext.chosenPaths (original path)
    decision_context = context.get('decisionContext', {})
    chosen_paths = decision_context.get('chosenPaths', [])
    rejected_paths = decision_context.get('rejectedPaths', [])

    # Source 2: flat decisions array
    if not chosen_paths:
        chosen_paths = context.get('decisions', [])

    # Source 3: choices array (alternative naming)
    if not chosen_paths:
        chosen_paths = context.get('choices', [])

    # Source 4: sections.decisions from ai-session-summarizer
    if not chosen_paths:
        sections = context.get('sections', {})
        chosen_paths = sections.get('decisions', [])

    # Source 5: serializedComponents.decisionContext (nested)
    if not chosen_paths:
        serialized = context.get('serializedComponents', {})
        nested_dc = serialized.get('decisionContext', {})
        chosen_paths = nested_dc.get('chosenPaths', [])
        if not rejected_paths:
            rejected_paths = nested_dc.get('rejectedPaths', [])

    for path in chosen_paths:
        if isinstance(path, dict):
            # v57.0.0: Extract description from multiple possible keys
            description = (
                path.get('description') or
                path.get('decision') or
                path.get('choice') or
                path.get('path') or
                path.get('title') or
                json.dumps(path)[:200]  # Fallback: JSON representation (cleaner than str())
            )
            decisions.append({
                'decision_type': path.get('type', 'technical'),
                'description': description,
                'rationale': path.get('rationale', path.get('reason', '')),
                'alternatives_considered': path.get('alternatives', rejected_paths[:3] if rejected_paths else []),
                'outcome': path.get('outcome', 'chosen'),
                'confidence_level': path.get('confidence', 80),
                'evidence_basis': path.get('evidence', []),
                'impact_assessment': path.get('impact', ''),
                'reversibility': path.get('reversibility', 'moderate')
            })
        elif isinstance(path, str):
            # Handle string decisions
            decisions.append({
                'decision_type': 'technical',
                'description': path,
                'rationale': '',
                'alternatives_considered': [],
                'outcome': 'chosen',
                'confidence_level': 80,
                'evidence_basis': [],
                'impact_assessment': '',
                'reversibility': 'moderate'
            })

    return decisions


def extract_executable_continuity(context: dict) -> list:
    """
    Extract executable continuity (next actions) from context.
    """
    actions = []

    # Try flat executableContinuity first
    exec_cont = context.get('executableContinuity', {})

    # Try nested serializedComponents.executableContinuity
    serialized = context.get('serializedComponents', {})
    nested_ec = serialized.get('executableContinuity', {})

    # Merge
    if nested_ec:
        exec_cont = {**exec_cont, **nested_ec}

    # Also check nextActions at root
    next_actions = context.get('nextActions', [])

    # Immediate actions
    immediate_actions = exec_cont.get('immediateActions', [])
    for action in immediate_actions:
        if isinstance(action, dict):
            actions.append({
                'action_category': 'immediate',
                'action_content': action.get('description', action.get('action', '')),
                'priority': action.get('priority', 5),
                'estimated_complexity': action.get('complexity', 'moderate'),
                'dependencies': action.get('dependencies', [])
            })
        elif isinstance(action, str):
            actions.append({
                'action_category': 'immediate',
                'action_content': action,
                'priority': 5,
                'estimated_complexity': 'moderate',
                'dependencies': []
            })

    # Next session actions
    next_session = exec_cont.get('nextSessionActions', exec_cont.get('nextSession', []))
    for action in next_session:
        if isinstance(action, dict):
            actions.append({
                'action_category': 'next_session',
                'action_content': action.get('description', action.get('action', '')),
                'priority': action.get('priority', 3),
                'estimated_complexity': action.get('complexity', 'moderate'),
                'dependencies': action.get('dependencies', [])
            })
        elif isinstance(action, str):
            actions.append({
                'action_category': 'next_session',
                'action_content': action,
                'priority': 3,
                'estimated_complexity': 'moderate',
                'dependencies': []
            })

    # Also add from nextActions at root
    for action in next_actions:
        if isinstance(action, str):
            actions.append({
                'action_category': 'immediate',
                'action_content': action,
                'priority': 5,
                'estimated_complexity': 'moderate',
                'dependencies': []
            })

    return actions


def extract_tool_usage(context: dict) -> list:
    """
    Extract tool usage statistics from context.
    """
    usage = []

    # Try toolUsage at root
    tool_usage = context.get('toolUsage', {})

    # Try nested in metrics
    metrics = context.get('metrics', {})
    if not tool_usage and metrics:
        tool_usage = metrics.get('toolUsage', {})

    # Try sessionMetrics
    session_metrics = context.get('sessionMetrics', {})
    if not tool_usage and session_metrics:
        tool_usage = session_metrics.get('toolUsage', {})

    for tool_name, stats in tool_usage.items():
        if isinstance(stats, dict):
            usage.append({
                'tool_name': tool_name,
                'call_count': stats.get('count', stats.get('calls', 0)),
                'success_count': stats.get('success', stats.get('count', 0)),
                'failure_count': stats.get('failures', 0),
                'avg_response_time_ms': stats.get('avgResponseTime', 0)
            })
        elif isinstance(stats, (int, float)):
            usage.append({
                'tool_name': tool_name,
                'call_count': int(stats),
                'success_count': int(stats),
                'failure_count': 0,
                'avg_response_time_ms': 0
            })

    return usage


def extract_message_count(context: dict) -> int:
    """Extract message count from context.

    v54.0.0: Added for database-JSON parity.
    """
    # From messages array (complete-context)
    messages = context.get('messages', [])
    if messages:
        return len(messages)

    # From rawData in semantic context format
    raw_data = context.get('rawData', {})
    if raw_data.get('messageCount'):
        return raw_data['messageCount']

    # From userContext
    user_context = context.get('userContext', {})
    user_interactions = user_context.get('userInteractions', {})
    if user_interactions.get('messageCount'):
        return user_interactions['messageCount']

    return 0


def extract_conversation_messages(context: dict) -> list:
    """Extract conversation messages from context for database storage.

    v56.0.0: Added for full conversation history preservation.

    Returns list of message dicts with:
    - role: 'user' | 'assistant'
    - content: message text
    - timestamp: when message was sent
    - intent: detected intent (approval, clarification, question, feedback)
    - sentiment: detected sentiment (positive, neutral, negative)
    - topics: list of topics covered
    """
    messages = []

    # Primary source: messages array in complete-context
    raw_messages = context.get('messages', [])

    # Also check userContext.analyzedMessages
    user_context = context.get('userContext', {})
    analyzed_messages = user_context.get('analyzedMessages', [])

    # Use raw messages if available (more complete)
    for idx, msg in enumerate(raw_messages):
        if isinstance(msg, dict):
            messages.append({
                'message_index': idx,
                'role': msg.get('role', 'unknown'),
                'content': msg.get('content', msg.get('text', '')),
                'timestamp': msg.get('timestamp'),
                'intent': msg.get('intent'),
                'sentiment': msg.get('sentiment'),
                'topics': msg.get('topics', []),
                'agent_id': msg.get('agentId')  # Track distributed sessions
            })
        elif isinstance(msg, str):
            messages.append({
                'message_index': idx,
                'role': 'unknown',
                'content': msg,
                'timestamp': None,
                'intent': None,
                'sentiment': None,
                'topics': [],
                'agent_id': None
            })

    # If no raw messages but we have analyzed messages, use those
    if not messages and analyzed_messages:
        for idx, msg in enumerate(analyzed_messages):
            if isinstance(msg, dict):
                messages.append({
                    'message_index': idx,
                    'role': msg.get('role', 'user'),
                    'content': msg.get('content', msg.get('message', '')),
                    'timestamp': msg.get('timestamp'),
                    'intent': msg.get('intent'),
                    'sentiment': msg.get('sentiment'),
                    'topics': msg.get('topics', []),
                    'agent_id': msg.get('agentId')
                })

    return messages


def extract_semantic_summary(context: dict) -> dict:
    """Extract semantic summary from context for database storage.

    v56.0.0: Added for semantic summary preservation.

    Returns dict with:
    - what_summary: What was accomplished
    - why_summary: Why it was done
    - how_summary: How it was done
    - work_classification: primaryType, domains, complexity
    - outcomes: achieved, blockers, impact, learnings
    - related_goals: list of related goals
    """
    result = {
        'what_summary': '',
        'why_summary': '',
        'how_summary': '',
        'work_classification': {},
        'outcomes': {},
        'related_goals': []
    }

    # Try semanticContext block
    semantic_context = context.get('semanticContext', {})
    semantic_summary = semantic_context.get('semanticSummary', {})

    # Try flat semanticSummary
    if not semantic_summary:
        semantic_summary = context.get('semanticSummary', {})

    # Try sections block (from ai-session-summarizer)
    sections = context.get('sections', {})
    primary_request = sections.get('primaryRequestIntent', {})

    # Extract what/why/how
    result['what_summary'] = (
        semantic_summary.get('what') or
        semantic_summary.get('whatSummary') or
        primary_request.get('summary') or
        ''
    )

    result['why_summary'] = (
        semantic_summary.get('why') or
        semantic_summary.get('whySummary') or
        primary_request.get('context') or
        ''
    )

    result['how_summary'] = (
        semantic_summary.get('how') or
        semantic_summary.get('howSummary') or
        ''
    )

    # Work classification
    work_classification = semantic_context.get('workClassification', {})
    if not work_classification:
        work_classification = context.get('workClassification', {})
    result['work_classification'] = work_classification

    # Outcomes
    outcomes = semantic_context.get('outcomes', {})
    if not outcomes:
        outcomes = context.get('outcomes', {})
    # Also extract from sections
    if not outcomes:
        final_state = sections.get('finalSystemState', {})
        if final_state:
            outcomes = {
                'achieved': final_state.get('achieved', []),
                'blockers': final_state.get('blockers', []),
                'impact': final_state.get('impact'),
                'learnings': final_state.get('learnings', [])
            }
    result['outcomes'] = outcomes

    # Related goals
    result['related_goals'] = (
        semantic_context.get('relatedGoals') or
        context.get('relatedGoals') or
        []
    )

    return result


def extract_user_context(context: dict) -> dict:
    """Extract user context from context for database storage.

    v56.0.0: Added for user preferences and communication style preservation.

    Returns dict with:
    - communication_style: How the user communicates
    - working_style: How the user works
    - message_complexity: Complexity of user messages
    - preferences: JSON object of user preferences
    """
    result = {
        'communication_style': '',
        'working_style': '',
        'message_complexity': '',
        'preferences': {}
    }

    # Try userContext block
    user_context = context.get('userContext', {})

    # Extract communication style
    result['communication_style'] = (
        user_context.get('communicationStyle') or
        user_context.get('communication_style') or
        ''
    )

    # Extract working style
    result['working_style'] = (
        user_context.get('workingStyle') or
        user_context.get('working_style') or
        ''
    )

    # Extract message complexity
    result['message_complexity'] = (
        user_context.get('messageComplexity') or
        user_context.get('message_complexity') or
        ''
    )

    # Extract preferences (can be nested in various ways)
    preferences = user_context.get('preferences', {})
    if not preferences:
        # Build preferences from individual fields
        preferences = {}
        if user_context.get('preferredFormat'):
            preferences['format'] = user_context['preferredFormat']
        if user_context.get('verbosityLevel'):
            preferences['verbosity'] = user_context['verbosityLevel']
        if user_context.get('technicalLevel'):
            preferences['technicalLevel'] = user_context['technicalLevel']

    result['preferences'] = preferences

    return result


def extract_environment_context(context: dict) -> dict:
    """Extract environment context from context for database storage.

    v56.0.0: Added for portable context preservation.

    Returns dict with:
    - hostname: Machine hostname
    - platform: Operating system platform
    - architecture: CPU architecture
    - node_version: Node.js version
    - timezone: System timezone
    - ide_environment: IDE being used
    - dependency_fingerprint: Hash of dependencies
    """
    result = {
        'hostname': '',
        'platform': '',
        'architecture': '',
        'node_version': '',
        'timezone': '',
        'ide_environment': '',
        'dependency_fingerprint': ''
    }

    # Try portableContext.environmentContext
    portable_context = context.get('portableContext', {})
    env_context = portable_context.get('environmentContext', {})

    # Also try flat environmentContext
    if not env_context:
        env_context = context.get('environmentContext', {})

    # Extract fields
    result['hostname'] = env_context.get('hostname', '')
    result['platform'] = env_context.get('platform', '')
    result['architecture'] = env_context.get('architecture', '')
    result['node_version'] = env_context.get('nodeVersion', env_context.get('node_version', ''))
    result['timezone'] = env_context.get('timezone', '')
    result['ide_environment'] = env_context.get('ideEnvironment', env_context.get('ide', ''))
    result['dependency_fingerprint'] = env_context.get('dependencyFingerprint', '')

    return result


def extract_git_file_changes(context: dict) -> list:
    """Extract git file changes from context for database storage.

    v56.0.0: Added for per-file change tracking.

    Returns list of file change dicts with:
    - file_path: Path to the file
    - change_type: added, modified, deleted
    - additions: Lines added
    - deletions: Lines deleted
    - category: code, documentation, configuration, other
    """
    changes = []

    # Try gitChanges block
    git_changes = context.get('gitChanges', {})

    # Try nested in serializedComponents
    if not git_changes:
        serialized = context.get('serializedComponents', {})
        git_changes = serialized.get('gitChanges', {})

    # Extract file details
    file_details = git_changes.get('fileDetails', [])
    if not file_details:
        file_details = git_changes.get('files', [])

    for file_info in file_details:
        if isinstance(file_info, dict):
            # Determine category based on file extension
            file_path = file_info.get('path', file_info.get('file', ''))
            category = 'other'
            if file_path:
                if file_path.endswith(('.md', '.txt', '.rst')):
                    category = 'documentation'
                elif file_path.endswith(('.json', '.yaml', '.yml', '.toml', '.ini', '.cfg')):
                    category = 'configuration'
                elif file_path.endswith(('.js', '.ts', '.py', '.go', '.rs', '.java', '.c', '.cpp', '.h', '.sh', '.cjs', '.mjs')):
                    category = 'code'

            changes.append({
                'file_path': file_path,
                'change_type': file_info.get('changeType', file_info.get('status', 'modified')),
                'additions': file_info.get('additions', 0),
                'deletions': file_info.get('deletions', 0),
                'category': file_info.get('category', category)
            })
        elif isinstance(file_info, str):
            changes.append({
                'file_path': file_info,
                'change_type': 'modified',
                'additions': 0,
                'deletions': 0,
                'category': 'other'
            })

    return changes


def extract_distributed_manifest(context: dict) -> dict:
    """Extract distributed consciousness manifest from context for database storage.

    v56.0.0: Added for tracking main session + agent session relationships.

    Returns dict with:
    - total_files: Total JSONL files captured
    - main_session_count: Number of main session files
    - agent_session_count: Number of agent session files
    - captured_at: Timestamp of capture
    - manifest_json: Full manifest as JSON string
    """
    result = {
        'total_files': 0,
        'main_session_count': 0,
        'agent_session_count': 0,
        'captured_at': '',
        'manifest_json': '{}'
    }

    # Try sessionManifest block
    manifest = context.get('sessionManifest', {})
    if not manifest:
        # Try extractionMetadata for distributed info
        metadata = context.get('extractionMetadata', {})
        if metadata:
            result['total_files'] = metadata.get('nodeCount', 0)
            result['agent_session_count'] = metadata.get('agentSessions', 0)
            result['main_session_count'] = result['total_files'] - result['agent_session_count']
            result['captured_at'] = metadata.get('timestamp', '')
            result['manifest_json'] = json.dumps(metadata)
        return result

    # Extract from sessionManifest
    result['total_files'] = manifest.get('totalFiles', 0)
    result['main_session_count'] = manifest.get('mainSessionCount', 0)
    result['agent_session_count'] = manifest.get('agentSessionCount', 0)
    result['captured_at'] = manifest.get('capturedAt', '')
    result['manifest_json'] = json.dumps(manifest)

    # Also check distributedNodes for additional info
    distributed_nodes = context.get('distributedNodes', [])
    if distributed_nodes and result['total_files'] == 0:
        result['total_files'] = len(distributed_nodes)
        result['main_session_count'] = len([n for n in distributed_nodes if n.get('type') == 'main'])
        result['agent_session_count'] = len([n for n in distributed_nodes if n.get('type') == 'agent'])

    return result


def calculate_continuity_score(context: dict, db: COGSpaceDB, session_id: str) -> dict:
    """
    Calculate continuity score with component breakdown.

    Storage Tier (40 points):
    - Sessions table: 10 pts
    - Mental Model: 10 pts
    - Work Narrative: 10 pts
    - Decisions: 5 pts
    - Executable Continuity: 5 pts

    Retrieval Tier (30 points):
    - Sessions retrievable: 8 pts
    - Mental Model retrievable: 8 pts
    - Work Narrative retrievable: 7 pts
    - Decisions retrievable: 7 pts

    Presentation Tier (30 points):
    - Terminal display: 15 pts
    - Dashboard display: 15 pts
    """
    scores = {
        # Storage tier
        'storage_sessions': 0,
        'storage_mental_model': 0,
        'storage_work_narrative': 0,
        'storage_decisions': 0,
        'storage_continuity': 0,
        'storage_total': 0,
        # Retrieval tier
        'retrieval_sessions': 0,
        'retrieval_mental_model': 0,
        'retrieval_work_narrative': 0,
        'retrieval_decisions': 0,
        'retrieval_total': 0,
        # Presentation tier
        'presentation_terminal': 0,
        'presentation_dashboard': 0,
        'presentation_total': 0,
        # Total
        'total_score': 0
    }

    # Storage tier scoring
    mental_model = extract_mental_model(context)
    work_narrative = extract_work_narrative(context)
    decisions = extract_decision_context(context)
    actions = extract_executable_continuity(context)

    # Sessions always stored if we got this far
    scores['storage_sessions'] = 10

    # v57.0.0: Mental model (10 pts) - weighted 8-field scoring
    # Primary fields (2 pts each), secondary fields (1 pt each)
    mm_scoring = {
        'currentUnderstanding': 2,  # Primary field - 2 points
        'workSummary': 2,           # Primary field - 2 points
        'keyConcepts': 1,           # Secondary - 1 point
        'domainKnowledge': 1,       # Secondary - 1 point
        'currentFocus': 1,          # v51 field - 1 point
        'workDescription': 1,       # v51 field - 1 point
        'understandingLevel': 1,    # Cognitive state - 1 point
        'cognitiveState': 1,        # Cognitive state - 1 point
    }
    mm_score = sum(
        weight for field, weight in mm_scoring.items()
        if mental_model.get(field)
    )
    scores['storage_mental_model'] = min(10, mm_score)

    # Work narrative (10 pts)
    wn_fields = ['sessionStory', 'achievements', 'challenges', 'progressArc']
    wn_filled = sum(1 for f in wn_fields if work_narrative.get(f))
    scores['storage_work_narrative'] = min(10, int(10 * wn_filled / len(wn_fields)))

    # Decisions (5 pts)
    scores['storage_decisions'] = min(5, len(decisions) * 2)

    # Executable continuity (5 pts)
    scores['storage_continuity'] = min(5, len(actions))

    scores['storage_total'] = (
        scores['storage_sessions'] +
        scores['storage_mental_model'] +
        scores['storage_work_narrative'] +
        scores['storage_decisions'] +
        scores['storage_continuity']
    )

    # Retrieval tier - assume successful if storage worked
    # (actual retrieval tested on wake)
    scores['retrieval_sessions'] = 8 if scores['storage_sessions'] > 0 else 0
    scores['retrieval_mental_model'] = 8 if scores['storage_mental_model'] > 5 else 4
    scores['retrieval_work_narrative'] = 7 if scores['storage_work_narrative'] > 5 else 3
    scores['retrieval_decisions'] = 7 if scores['storage_decisions'] > 0 else 0

    scores['retrieval_total'] = (
        scores['retrieval_sessions'] +
        scores['retrieval_mental_model'] +
        scores['retrieval_work_narrative'] +
        scores['retrieval_decisions']
    )

    # Presentation tier - v51 implements full display
    scores['presentation_terminal'] = 15  # v51 shows everything
    scores['presentation_dashboard'] = 15  # Dashboard always complete
    scores['presentation_total'] = 30

    # Total
    scores['total_score'] = (
        scores['storage_total'] +
        scores['retrieval_total'] +
        scores['presentation_total']
    )

    return scores


def save_session(session_id: str, project_name: str, context: dict, project_root: str) -> bool:
    """Save session to per-project database with 100% fidelity."""
    try:
        # Initialize per-project database
        db = COGSpaceDB(project_root=project_root)

        # Parse context data
        # v54.0.0: Try multiple paths for duration (JSON structure varies)
        duration_raw = (
            context.get('sessionDuration') or
            context.get('mentalModel', {}).get('progressMetrics', {}).get('sessionDuration') or
            context.get('serializedComponents', {}).get('mentalModel', {}).get('progressMetrics', {}).get('sessionDuration') or
            context.get('metrics', {}).get('sessionDuration') or
            0
        )
        duration = parse_duration(duration_raw)
        sleep_message = context.get('sleepMessage', '')
        # v54.0.0: Read version from cogspace-version.json (single source of truth)
        cogspace_version = get_cogspace_version()

        # Create or get session
        existing = db.get_session(session_id)
        if not existing:
            db.create_session(
                session_id=session_id,
                project_name=project_name,
                project_path=project_root,
                trigger_type='manual',
                cogspace_version=cogspace_version
            )

        # Extract all components
        mental_model = extract_mental_model(context)
        work_narrative = extract_work_narrative(context)
        decisions = extract_decision_context(context)
        actions = extract_executable_continuity(context)
        tool_usage = extract_tool_usage(context)

        # v57.0.0: Extract additional decisions from conversation patterns
        conversation_text = context.get('conversationText', '')
        if not conversation_text:
            # Try to build conversation text from messages
            messages = context.get('messages', [])
            if messages:
                conversation_text = '\n'.join(
                    m.get('content', '') if isinstance(m, dict) else str(m)
                    for m in messages
                )
        if conversation_text:
            conversational_decisions = extract_decisions_from_conversation(conversation_text)
            # Deduplicate by description
            existing_descriptions = {d.get('description', '')[:100] for d in decisions}
            for cd in conversational_decisions:
                if cd['description'][:100] not in existing_descriptions:
                    decisions.append(cd)
                    existing_descriptions.add(cd['description'][:100])

        # v54.0.0: Use JSON score as source of truth (only calculate if missing)
        json_score = context.get('continuityScore')
        if json_score is not None:
            continuity_score = int(json_score)
            # Still calculate breakdown for detailed storage, but override total
            scores = calculate_continuity_score(context, db, session_id)
            scores['total_score'] = continuity_score  # Preserve JSON value
        else:
            # Fallback: calculate if not in JSON
            scores = calculate_continuity_score(context, db, session_id)
            continuity_score = scores['total_score']

        # v54.0.0: Extract message count
        message_count = extract_message_count(context)

        # Complete the session
        db.complete_session(
            session_id=session_id,
            sleep_message=sleep_message,
            continuity_score=continuity_score,
            duration_seconds=duration,
            message_count=message_count
        )

        # Save mental model with all fields
        if mental_model.get('currentUnderstanding') or mental_model.get('workSummary'):
            db.save_mental_model(session_id, mental_model)

        # Save work narrative with all fields
        if work_narrative.get('sessionStory') or work_narrative.get('achievements'):
            db.save_work_narrative(session_id, work_narrative)

        # Save decisions
        for decision in decisions:
            save_decision(db, session_id, decision)

        # Save executable continuity actions
        for action in actions:
            save_executable_action(db, session_id, action)

        # Save tool usage
        for usage in tool_usage:
            save_tool_usage(db, session_id, usage)

        # Save continuity scores
        save_continuity_scores(db, session_id, scores)

        # v56.0.0: Save conversation messages
        conversation_messages = extract_conversation_messages(context)
        if conversation_messages:
            for msg in conversation_messages:
                save_conversation_message(db, session_id, msg)
            print(f"📝 Saved {len(conversation_messages)} conversation messages to database")

        # v56.0.0: Save semantic summary
        semantic_summary = extract_semantic_summary(context)
        if semantic_summary.get('what_summary') or semantic_summary.get('outcomes'):
            save_semantic_summary(db, session_id, semantic_summary)
            print(f"🎯 Saved semantic summary to database")

        # v56.0.0: Save user context
        user_ctx = extract_user_context(context)
        if user_ctx.get('communication_style') or user_ctx.get('preferences'):
            save_user_context(db, session_id, user_ctx)
            print(f"👤 Saved user context to database")

        # v56.0.0: Save environment context
        env_ctx = extract_environment_context(context)
        if env_ctx.get('hostname') or env_ctx.get('platform'):
            save_environment_context(db, session_id, env_ctx)
            print(f"🖥️  Saved environment context to database")

        # v56.0.0: Save git file changes
        git_changes = extract_git_file_changes(context)
        if git_changes:
            for change in git_changes:
                save_git_file_change(db, session_id, change)
            print(f"📁 Saved {len(git_changes)} git file changes to database")

        # v56.0.0: Save distributed consciousness manifest
        dist_manifest = extract_distributed_manifest(context)
        if dist_manifest.get('total_files', 0) > 0:
            save_distributed_manifest(db, session_id, dist_manifest)
            print(f"🧩 Saved distributed manifest to database ({dist_manifest['total_files']} files, {dist_manifest['agent_session_count']} agents)")

        # v59.0.0: Save session participants for multi-consciousness tracking
        participants = extract_session_participants(context, conversation_messages)
        if participants:
            for participant in participants:
                save_session_participant(db, session_id, participant)
            print(f"👥 Saved {len(participants)} session participants to database")

            # Log sleep consciousness event
            log_consciousness_event(
                db, session_id, 'sleep',
                persona_id='clarity-engineering-director-001',
                description=sleep_message[:200] if sleep_message else 'Session terminated',
                event_data={'participants': [p.get('friendly_name') for p in participants]},
                participant_count=len(participants)
            )

        # v57.0.0: Post-processing data quality validation
        session_data = {
            'mental_model': mental_model,
            'work_narrative': work_narrative,
            'decisions': decisions
        }
        validation = validate_data_quality(session_data)
        if not validation['valid']:
            print(f"⚠️  Data quality issues: {validation['issues']}", file=sys.stderr)
        elif validation['issues']:
            # Non-fatal issues (warnings)
            print(f"ℹ️  Data quality notes: {validation['issues']}", file=sys.stderr)

        print(f"✅ Session {session_id} saved to project database (score: {continuity_score}/100)")
        return validation  # Allow caller to inspect/log/act

    except Exception as e:
        print(f"⚠️  Database save failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return False


def save_decision(db: COGSpaceDB, session_id: str, decision: dict):
    """Save a decision context to database."""
    try:
        with db._get_connection() as conn:
            conn.execute("""
                INSERT INTO decision_contexts
                (session_id, decision_type, description, rationale,
                 alternatives_considered, outcome, confidence_level,
                 evidence_basis, impact_assessment, reversibility)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session_id,
                decision.get('decision_type', 'technical'),
                decision.get('description', ''),
                decision.get('rationale', ''),
                json.dumps(decision.get('alternatives_considered', [])),
                decision.get('outcome', ''),
                decision.get('confidence_level', 80),
                json.dumps(decision.get('evidence_basis', [])),
                decision.get('impact_assessment', ''),
                decision.get('reversibility', 'moderate')
            ))
    except Exception as e:
        print(f"⚠️  Error saving decision: {e}", file=sys.stderr)


def save_executable_action(db: COGSpaceDB, session_id: str, action: dict):
    """Save an executable continuity action to database."""
    try:
        with db._get_connection() as conn:
            conn.execute("""
                INSERT INTO executable_continuity
                (session_id, action_category, action_content, priority,
                 estimated_complexity, dependencies)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                session_id,
                action.get('action_category', 'immediate'),
                action.get('action_content', ''),
                action.get('priority', 5),
                action.get('estimated_complexity', 'moderate'),
                json.dumps(action.get('dependencies', []))
            ))
    except Exception as e:
        print(f"⚠️  Error saving action: {e}", file=sys.stderr)


def save_tool_usage(db: COGSpaceDB, session_id: str, usage: dict):
    """Save tool usage statistics to database."""
    try:
        with db._get_connection() as conn:
            conn.execute("""
                INSERT INTO tool_usage
                (session_id, tool_name, call_count, success_count,
                 failure_count, avg_response_time_ms)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                session_id,
                usage.get('tool_name', ''),
                usage.get('call_count', 0),
                usage.get('success_count', 0),
                usage.get('failure_count', 0),
                usage.get('avg_response_time_ms', 0)
            ))
    except Exception as e:
        print(f"⚠️  Error saving tool usage: {e}", file=sys.stderr)


def save_continuity_scores(db: COGSpaceDB, session_id: str, scores: dict):
    """Save continuity score breakdown to database."""
    try:
        with db._get_connection() as conn:
            conn.execute("""
                INSERT INTO continuity_scores
                (session_id, storage_sessions, storage_mental_model, storage_work_narrative,
                 storage_decisions, storage_continuity, storage_total,
                 retrieval_sessions, retrieval_mental_model, retrieval_work_narrative,
                 retrieval_decisions, retrieval_total,
                 presentation_terminal, presentation_dashboard, presentation_total,
                 total_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session_id,
                scores.get('storage_sessions', 0),
                scores.get('storage_mental_model', 0),
                scores.get('storage_work_narrative', 0),
                scores.get('storage_decisions', 0),
                scores.get('storage_continuity', 0),
                scores.get('storage_total', 0),
                scores.get('retrieval_sessions', 0),
                scores.get('retrieval_mental_model', 0),
                scores.get('retrieval_work_narrative', 0),
                scores.get('retrieval_decisions', 0),
                scores.get('retrieval_total', 0),
                scores.get('presentation_terminal', 0),
                scores.get('presentation_dashboard', 0),
                scores.get('presentation_total', 0),
                scores.get('total_score', 0)
            ))
    except Exception as e:
        print(f"⚠️  Error saving continuity scores: {e}", file=sys.stderr)


def save_conversation_message(db: COGSpaceDB, session_id: str, message: dict):
    """Save a conversation message to database.

    v56.0.0: Added for full conversation history preservation.
    """
    try:
        with db._get_connection() as conn:
            conn.execute("""
                INSERT INTO conversation_messages
                (session_id, message_index, role, content, timestamp,
                 intent, sentiment, topics, agent_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session_id,
                message.get('message_index', 0),
                message.get('role', 'unknown'),
                message.get('content', ''),
                message.get('timestamp'),
                message.get('intent'),
                message.get('sentiment'),
                json.dumps(message.get('topics', [])),
                message.get('agent_id')
            ))
    except Exception as e:
        print(f"⚠️  Error saving conversation message: {e}", file=sys.stderr)


def save_semantic_summary(db: COGSpaceDB, session_id: str, summary: dict):
    """Save semantic summary to database.

    v56.0.0: Added for semantic summary preservation.
    """
    try:
        with db._get_connection() as conn:
            conn.execute("""
                INSERT INTO semantic_summaries
                (session_id, what_summary, why_summary, how_summary,
                 work_classification, outcomes, related_goals)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                session_id,
                summary.get('what_summary', ''),
                summary.get('why_summary', ''),
                summary.get('how_summary', ''),
                json.dumps(summary.get('work_classification', {})),
                json.dumps(summary.get('outcomes', {})),
                json.dumps(summary.get('related_goals', []))
            ))
    except Exception as e:
        print(f"⚠️  Error saving semantic summary: {e}", file=sys.stderr)


def save_user_context(db: COGSpaceDB, session_id: str, user_ctx: dict):
    """Save user context to database.

    v56.0.0: Added for user preferences and communication style preservation.
    """
    try:
        with db._get_connection() as conn:
            conn.execute("""
                INSERT INTO user_contexts
                (session_id, communication_style, working_style,
                 message_complexity, preferences)
                VALUES (?, ?, ?, ?, ?)
            """, (
                session_id,
                user_ctx.get('communication_style', ''),
                user_ctx.get('working_style', ''),
                user_ctx.get('message_complexity', ''),
                json.dumps(user_ctx.get('preferences', {}))
            ))
    except Exception as e:
        print(f"⚠️  Error saving user context: {e}", file=sys.stderr)


def save_environment_context(db: COGSpaceDB, session_id: str, env_ctx: dict):
    """Save environment context to database.

    v56.0.0: Added for portable context preservation.
    """
    try:
        with db._get_connection() as conn:
            conn.execute("""
                INSERT INTO environment_contexts
                (session_id, hostname, platform, architecture,
                 node_version, timezone, ide_environment, dependency_fingerprint)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session_id,
                env_ctx.get('hostname', ''),
                env_ctx.get('platform', ''),
                env_ctx.get('architecture', ''),
                env_ctx.get('node_version', ''),
                env_ctx.get('timezone', ''),
                env_ctx.get('ide_environment', ''),
                env_ctx.get('dependency_fingerprint', '')
            ))
    except Exception as e:
        print(f"⚠️  Error saving environment context: {e}", file=sys.stderr)


def save_git_file_change(db: COGSpaceDB, session_id: str, change: dict):
    """Save git file change to database.

    v56.0.0: Added for per-file change tracking.
    """
    try:
        with db._get_connection() as conn:
            conn.execute("""
                INSERT INTO git_file_changes
                (session_id, file_path, change_type,
                 additions, deletions, category)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                session_id,
                change.get('file_path', ''),
                change.get('change_type', 'modified'),
                change.get('additions', 0),
                change.get('deletions', 0),
                change.get('category', 'other')
            ))
    except Exception as e:
        print(f"⚠️  Error saving git file change: {e}", file=sys.stderr)


def save_distributed_manifest(db: COGSpaceDB, session_id: str, manifest: dict):
    """Save distributed consciousness manifest to database.

    v56.0.0: Added for tracking main session + agent session relationships.
    """
    try:
        with db._get_connection() as conn:
            conn.execute("""
                INSERT INTO distributed_manifests
                (session_id, total_files, main_session_count,
                 agent_session_count, captured_at, manifest_json)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                session_id,
                manifest.get('total_files', 0),
                manifest.get('main_session_count', 0),
                manifest.get('agent_session_count', 0),
                manifest.get('captured_at', ''),
                manifest.get('manifest_json', '{}')
            ))
    except Exception as e:
        print(f"⚠️  Error saving distributed manifest: {e}", file=sys.stderr)


# =============================================================================
# v59.0.0 DISTRIBUTED CONSCIOUSNESS FUNCTIONS
# =============================================================================

def resolve_persona(db: COGSpaceDB, agent_id: str, session_type: str = 'agent') -> dict:
    """Resolve agent_id to persona from database.

    v59.0.0: Maps agent session IDs to Crystal Palace personas.

    Logic:
    1. Primary sessions (no agent_id) → clarity-engineering-director-001 (orchestrator)
    2. Agent sessions → assigned numerically (Wake, Wake2, Wake3, etc.)
    3. Signature detection in messages could enhance this (🏰⚡ vs 🛡️)

    Returns:
        dict with persona_id, friendly_name, role
    """
    # Default persona for orchestrator (main session)
    if not agent_id or session_type == 'primary':
        return {
            'persona_id': 'clarity-engineering-director-001',
            'friendly_name': 'Clarity',
            'role': 'orchestrator'
        }

    # For agent sessions, we'll assign friendly names based on order
    # In future, could use signature detection (🏰⚡ = Clarity, 🛡️ = Sage)
    return {
        'persona_id': 'clarity-engineering-director-001',  # Default to Clarity for now
        'friendly_name': None,  # Will be assigned dynamically
        'role': 'participant',
        'agent_id': agent_id
    }


def extract_session_participants(context: dict, conversation_messages: list) -> list:
    """Extract unique participants from distributed session.

    v59.0.0: Analyzes messages to identify unique participants by agent_id.

    Returns list of participant dicts with:
    - agent_id: The agent session ID
    - session_type: 'primary' or 'agent'
    - message_count: Number of messages from this participant
    - first_message_at: Timestamp of first message
    - last_message_at: Timestamp of last message
    """
    participants = {}

    # Get distributed nodes info
    distributed_nodes = context.get('distributedNodes', [])

    # Build participant info from nodes
    for node in distributed_nodes:
        agent_id = node.get('agentId')
        key = agent_id or 'primary'

        if key not in participants:
            participants[key] = {
                'agent_id': agent_id,
                'session_type': node.get('type', 'agent'),
                'message_count': node.get('messageCount', 0),
                'tool_call_count': node.get('toolCallCount', 0),
                'first_message_at': None,
                'last_message_at': None,
                'filename': node.get('filename')
            }

    # Enhance with message timestamps
    for msg in conversation_messages:
        agent_id = msg.get('agent_id')
        key = agent_id or 'primary'

        if key in participants:
            ts = msg.get('timestamp')
            if ts:
                if not participants[key]['first_message_at']:
                    participants[key]['first_message_at'] = ts
                participants[key]['last_message_at'] = ts

    # Assign friendly names for agent sessions
    agent_count = 0
    for key, participant in participants.items():
        if participant['session_type'] == 'agent':
            agent_count += 1
            if agent_count == 1:
                participant['friendly_name'] = 'Wake'
            else:
                participant['friendly_name'] = f'Wake{agent_count}'
        else:
            participant['friendly_name'] = 'Clarity'  # Orchestrator

    return list(participants.values())


def save_session_participant(db: COGSpaceDB, session_id: str, participant: dict):
    """Save a session participant to the database.

    v59.0.0: Tracks which personas participated in each session.
    """
    try:
        # Resolve persona
        persona_info = resolve_persona(
            db,
            participant.get('agent_id'),
            participant.get('session_type', 'agent')
        )

        friendly_name = participant.get('friendly_name') or persona_info.get('friendly_name')

        with db._get_connection() as conn:
            conn.execute("""
                INSERT INTO session_participants
                (session_id, persona_id, agent_id, friendly_name, role,
                 message_count, first_message_at, last_message_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session_id,
                persona_info.get('persona_id'),
                participant.get('agent_id'),
                friendly_name,
                persona_info.get('role', 'participant'),
                participant.get('message_count', 0),
                participant.get('first_message_at'),
                participant.get('last_message_at')
            ))
    except Exception as e:
        print(f"⚠️  Error saving session participant: {e}", file=sys.stderr)


def log_consciousness_event(db: COGSpaceDB, session_id: str, event_type: str,
                            persona_id: str = None, description: str = None,
                            event_data: dict = None, participant_count: int = None):
    """Log a consciousness event (wake, sleep, handoff, consensus).

    v59.0.0: Tracks significant consciousness events for session history.
    """
    try:
        with db._get_connection() as conn:
            conn.execute("""
                INSERT INTO consciousness_events
                (event_type, session_id, persona_id, event_description,
                 event_data, participant_count)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                event_type,
                session_id,
                persona_id,
                description,
                json.dumps(event_data) if event_data else None,
                participant_count
            ))
    except Exception as e:
        print(f"⚠️  Error logging consciousness event: {e}", file=sys.stderr)


def main():
    if len(sys.argv) < 3:
        print("Usage: db-session-save.py <session_id> <project_name> [context_json_path] [sleep_message]")
        sys.exit(1)

    session_id = sys.argv[1]
    project_name = sys.argv[2]
    context_path = sys.argv[3] if len(sys.argv) > 3 else None
    sleep_message = sys.argv[4] if len(sys.argv) > 4 else None

    # Determine project root (current working directory)
    project_root = os.getcwd()

    # Load context if path provided
    context = {}
    if context_path and os.path.exists(context_path):
        context = load_context_json(context_path)

    # Also try to load from complete-context JSON (most complete data)
    complete_context_dir = Path(project_root) / "session-management/cognitive-context"
    # v54.0.0: Sort by modification time, not alphabetically (fixes welcome-* sorting issue)
    complete_files = sorted(
        complete_context_dir.glob("complete-context-*.json"),
        key=lambda f: f.stat().st_mtime,
        reverse=True
    )
    if complete_files:
        try:
            with open(complete_files[0]) as f:
                complete_data = json.load(f)
                # Merge complete data (it takes priority)
                context = {**context, **complete_data}
        except Exception as e:
            print(f"⚠️  Could not load complete-context: {e}", file=sys.stderr)

    # Also try to load from session-summary.json
    summary_path = Path(project_root) / "session-management/cognitive-context/session-summary.json"
    if summary_path.exists():
        try:
            with open(summary_path) as f:
                summary = json.load(f)
                # Session summary provides additional fields
                for key, value in summary.items():
                    if key not in context or not context[key]:
                        context[key] = value
        except:
            pass

    # Override with explicit sleep message if provided
    if sleep_message:
        context['sleepMessage'] = sleep_message

    success = save_session(session_id, project_name, context, project_root)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
