# Trouble Report

**Report ID:** larry-llama-20251212-141750-5847
**Date Submitted:** 2025-12-12T22:17:50Z
**Project:** larry-llama (affects all COGSPACE projects)
**Folder:** /Users/wizard/projects/larry-llama
**Reporter:** Bob PM / Wizard
**Priority:** HIGH
**Category:** BUG

## Issue Description

### What's happening?

The `claude-code-context-extractor.cjs` explicitly **excludes agent JSONL files** from conversation extraction. This means any work done via Claude Code's Task tool (which spawns agents) is **completely lost** from COGSPACE memory.

**The problematic code (line 67-68 in `claude-code-context-extractor.cjs`):**
```javascript
.filter(f => f.endsWith('.jsonl') && !f.startsWith('agent-'))
```

This filter removes all `agent-*.jsonl` files from consideration, even though these files contain complete conversation transcripts of substantial development work.

### What should be happening?

Agent JSONL files should be **included** in context extraction, either:
1. Merged with their parent session context, OR
2. Extracted as separate but linked conversation threads

### When did this start?

**Unknown origin** - the filter may have been intentional at one point but is now causing data loss. The issue was discovered on 2025-12-12 when investigating why a development session (Dec 11, 2025) that created 800+ lines of code was not captured in COGSPACE memory.

### Evidence of Data Loss

**December 11, 2025 Development Session:**
- `agent-5676e36f.jsonl` - 412KB, modified Dec 11 17:23
- Contains 181 mentions of "larry" and 20 mentions of "DevRadio"
- This session created: `larry-chat/`, `mcp-ollama-server/`, `persona/` directories
- **None of this work was captured** because it was an agent session

**Current session extractor output (excludes agent files):**
```
✅ Found Claude Code session: 59c182c4-57f7-42b7-b428-d210fa5aff74.jsonl
✅ Parsed 36 messages, 46 tool calls
```

## Technical Details

### Environment
- **Project:** All COGSPACE-enabled projects
- **Folder:** DNA source at `~/.cogspace/dna/` and all deployed projects
- **System:** Darwin arm64 (macOS)
- **COGSPACE Version:** v40.0.0+
- **Claude Code Environment:** VS Code extension / Cursor IDE
- **Relevant File:** `cogspace/claude-code-context-extractor.cjs`

### Root Cause

The `findLatestSession()` method filters out agent files:

```javascript
findLatestSession(projectDir) {
    const sessions = fs.readdirSync(projectDir)
        .filter(f => f.endsWith('.jsonl') && !f.startsWith('agent-'))  // <-- BUG HERE
        .map(f => ({
            path: path.join(projectDir, f),
            mtime: fs.statSync(path.join(projectDir, f)).mtimeMs
        }))
        .sort((a, b) => b.mtime - a.mtime);

    return sessions.length > 0 ? sessions[0].path : null;
}
```

### Steps to Reproduce

1. Open a COGSPACE-enabled project in Claude Code (VS Code or Cursor)
2. Use the Task tool to spawn an agent for development work
3. Complete substantial work via the agent
4. Run `bye "session complete"` to save context
5. Run `hi` to restore context
6. **Observe:** The agent's work is NOT in the restored context

### What I've tried

- [x] Verified agent JSONL files exist and contain conversation data
- [x] Confirmed the filter explicitly excludes `agent-*` files
- [x] Tested extractor manually - it only reads non-agent sessions
- [x] Verified the Dec 11 agent session contains the missing work (181 mentions of "larry")

## Impact Assessment

### Severity
- **User Impact:** All COGSPACE users who use Task tool / agents
- **Business Impact:** MAJOR - Complete loss of development context for agent-based work
- **Timeline:** Needs attention - blocking accurate context preservation

### Affected Components
- [x] Backend (context extraction)
- [x] Other: COGSPACE DNA / Memory System

### Data Loss Scope

Any project where work was done via:
- Claude Code Task tool
- Agent spawning
- Background agents
- Cursor IDE agent features

## Proposed Fix

### Option A: Include Agent Files (Simple)
```javascript
.filter(f => f.endsWith('.jsonl'))  // Remove agent exclusion
```

### Option B: Merge Agent Context with Parent (Better)
Parse agent files and link them to their parent session for a complete conversation thread.

### Option C: Configurable Extraction (Most Flexible)
Add environment variable or config option:
```javascript
const INCLUDE_AGENTS = process.env.COGSPACE_INCLUDE_AGENTS !== 'false';
.filter(f => f.endsWith('.jsonl') && (INCLUDE_AGENTS || !f.startsWith('agent-')))
```

## Additional Context

This bug was discovered during a session where we:
1. Investigated why previous session context was minimal
2. Found 800+ lines of code that had been written but not captured
3. Traced the issue to the agent file exclusion filter

The irony: The very session that discovered this bug is being properly captured because it's NOT an agent session.

---

**Tags:** bug, critical, memory-loss, context-extraction, agent-sessions, COGSPACE-DNA
