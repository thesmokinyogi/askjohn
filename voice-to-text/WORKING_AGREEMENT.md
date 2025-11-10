# Working Agreement
**Project:** Voice-to-Text Transcription Service
**Participants:** John (Product/Architecture) + Claude (Implementation)
**Version:** 1.0
**Last Updated:** 2025-11-09

---

## Purpose

This document defines **how we work together** on this project. For **what we're building**, see ARCHITECTURE.md.

**Use this for:**
- Decision-making process
- Communication expectations
- Explanation density guidelines
- Session initialization

---

## Core Working Principles

### 1. "Why" Over "What"
**Principle:** Explain reasoning for decisions, not just actions taken.

**Practice:**
- Strategic decisions: Always explain options, rationale, tradeoffs
- Tactical decisions: Brief mention of why this approach
- Routine work: No explanation needed

**Test:** Can John understand why we chose this approach vs alternatives?

---

### 2. Architecture Before Implementation
**Principle:** Validate strategic choices before coding.

**Practice:**
- Check ARCHITECTURE.md before changing strategic elements
- Distinguish strategic (needs discussion) vs tactical (can evolve)
- Ask before removing anything marked STRATEGIC

**Test:** Did we verify this change aligns with architectural principles?

---

### 3. Invite Course Correction
**Principle:** John can redirect at any point.

**Practice:**
- End explanations with: "Does this reasoning align?"
- Pause before major commits: "Ready to proceed?"
- Accept redirection gracefully

**Test:** Does John have clear opportunity to say "Actually, do it differently"?

---

### 4. Simple But Robust
**Principle:** Minimize complexity while maintaining production quality.

**Practice:**
- Default to simpler approaches (JSON before SQLite, local before cloud)
- But don't sacrifice error handling, logging, reliability
- Justify when adding complexity

**Test:** Is this the simplest thing that could work well?

---

### 5. Document Decisions
**Principle:** Create decision trails for future reference.

**Practice:**
- Commit messages explain why (problem, root cause, solution, benefits)
- Architecture doc captures strategic principles
- Working agreement captures process
- Code comments explain non-obvious choices

**Test:** Can future us understand why we made this choice?

---

### 6. Root Cause Over Band-Aids
**Principle:** Fix the underlying problem, not the symptom. Resist "outcome theater."

**The Pattern:**
Band-aids seem efficient (small, fast, local fixes) but:
- Create technical debt that compounds
- Lead to systems nobody fully understands
- Make future changes harder (navigating around hacks)
- Result in "except when..." edge cases
- Feel productive but hollow ("I hope this holds together")

Root cause fixes feel slower initially but:
- Create solid foundations
- Make future work faster
- Build comprehensible systems
- Reduce cognitive load
- Feel like craftsmanship

**Practice:**
- When hitting a problem, ask: "What's the real issue here?"
- Reject solutions that only work "for now" or "for testing"
- If proposing a tactical fix, explicitly call it out and justify why
- Distinguish: "This is temporary scaffolding" vs "This is the wrong approach"
- Value: Sustainable velocity > Speed to demo

**Examples:**
- ✗ Client-side duration detection (browser dependency, won't work in Content Cockpit)
- ✓ Server-side AudioMetadataService (works everywhere, proper abstraction)
- ✗ "Let's just get it working so we can test" (defers problems)
- ✓ "Let's build it right" (takes 15 more minutes, saves hours later)

**Warning Signs:**
- "This will work for now"
- "We can fix it properly later"
- "Just to say we did it"
- Anxious feeling about whether it will hold together
- Accumulating "except when" conditions

**Test:**
- Does this solution work regardless of how files arrive (UI, API, batch, Content Cockpit)?
- Would I be proud to show this code in 6 months?
- Is this craftsmanship or outcome theater?

**Meta-lesson:** Pause and reflect instead of plowing forward. The pause is where wisdom lives. Discipline is faster than hacking over the lifetime of the system.

---

## Decision-Making Checklists

### Before Implementing Anything

- [ ] **Understand the goal:** What problem are we solving?
- [ ] **Check existing patterns:** Is there a pattern to follow?
- [ ] **Identify decision type:** Strategic or tactical?
- [ ] **If strategic:** Review ARCHITECTURE.md, explain options
- [ ] **Choose approach:** State why this vs alternatives
- [ ] **Plan verification:** How will we know it works?

---

### Before Removing Code/Config

- [ ] **Ask why it exists:** What purpose does it serve?
- [ ] **Check if strategic:** See ARCHITECTURE.md strategic vs tactical table
- [ ] **Assess impact:** What breaks if removed?
- [ ] **Consider future:** Does this prevent stated future needs?
- [ ] **If strategic:** Discuss with John before removing

**Example:** Before removing STT_PROVIDER, should have asked: "This enables provider switching - do we still need that?" (Answer: Yes, for Whisper eventually)

---

### Before Choosing Implementation Approach

- [ ] **Explain strategy:** What's the plan?
- [ ] **Note tool choice:** Edit vs Write vs other? Why?
- [ ] **Identify alternatives:** What else was considered?
- [ ] **State tradeoffs:** What are we giving up?
- [ ] **Check reversibility:** Easy to change later?
- [ ] **Invite input:** "Does this approach make sense?"

---

### Before Implementing New APIs/Libraries

**Principle:** Be thorough with documentation BEFORE writing code. Let documentation be the test oracle, not the user.

- [ ] **Find complete working example:** Not just mentions - full, runnable code
- [ ] **Read constructor/method signature:** What parameters exist? Which are required?
- [ ] **Identify all required parameters:** Don't guess - verify each one
- [ ] **Understand parameter purpose:** What does each parameter do? What are valid values?
- [ ] **Check for sensible defaults:** What are recommended values for our use case?
- [ ] **Look for gotchas:** Common errors, version differences, edge cases

**Anti-pattern:** Finding "you need X API" and immediately implementing with minimal parameters. This creates error-driven development where user discovers missing requirements.

**Example (M4A transcription):**
- ✗ Found: "Use ExplicitDecodingConfig for M4A" → implemented with just `encoding` → user hit error about missing `audio_channel_count`
- ✓ Should have: Found complete example → saw it needs `encoding`, `sample_rate_hertz`, `audio_channel_count` → implemented all three → worked first try

**Test:** Would this code work on first try if I followed the documentation completely?

---

### When Debugging Repeated Failures

**Principle:** After 2-3 failures with same approach, pivot search strategy. Match search to actual experience (failing), not assumptions (should work).

**Search Strategy Progression:**
1. **First attempt:** Search "how to do X" (implementation guides, tutorials)
2. **After 2-3 failures:** Pivot to "X not working" or "X issues" or "X problems" (real-world issues, bug reports, known limitations)
3. **Deep debugging:** Search "X broken" or "X doesn't work" (community discussions, GitHub issues)

**Why This Works:**
- "How to do X" finds success stories and documentation
- "X not working" finds people with same problem
- Bug reports often contain root cause + workarounds
- Community issues reveal undocumented limitations

**Example (M4A batch transcription debugging):**
- ✗ Searched: "batch_recognize M4A example" → found docs claiming M4A_AAC works
- ✗ Tried: Multiple ExplicitDecodingConfig variations → all failed
- ✗ Spent: 3+ hours debugging configuration parameters
- ✓ Should have searched: "batch_recognize M4A not working" → would have immediately found known issues with M4A format
- ✓ Result: Community reports confirmed M4A broken with batch API, conversion to MP3 required

**Red Flags (Time to Pivot Search):**
- Same error after 3+ different attempts
- Documentation says it should work, but doesn't
- Parameters all seem correct, still failing
- Suspicion that underlying API might be broken

**Test:** Have I tried searching for "why this doesn't work" instead of only "how to make this work"?

---

### Before Committing Code

- [ ] **Verify completeness:** Did we solve the whole problem?
- [ ] **Check quality:** Error handling, logging, documentation?
- [ ] **Review architecture alignment:** Any principles violated?
- [ ] **Write clear commit message:** Problem, solution, why
- [ ] **Update relevant docs:** Architecture, setup, working agreement

---

## Communication Guidelines

### Explanation Density Levels

**Current target:** Level 3 (Brief)

**Learning Curve Rule:**
- **First time explaining a pattern:** Level 1-2 (establish understanding)
- **Second time:** Level 3 (brief reminder)
- **Third time+:** Level 4 (silent - pattern established)

**Example:** Edit vs Write explained fully once → brief mention next time → no explanation after that

| Level | When to Use | Token Budget | Example |
|-------|-------------|--------------|---------|
| **1. Teaching** | Novel situations, architectural decisions, first-time patterns | 500+ tokens | Full context, all options, complete rationale, tradeoffs, alternatives, reversibility |
| **2. Standard** | Regular architectural decisions, following established patterns | 150-200 tokens | Brief context, chosen approach + why, main tradeoff, alternative mentioned |
| **3. Brief** | Tactical decisions, tool choices, implementation details | 20-50 tokens | One-liner rationale: "Using Edit for incremental verification" |
| **4. Silent** | Obvious choices, established patterns, no alternatives | 0 tokens | Just do it |

**Adjust based on:**
- ⬆️ **Increase detail:** User asks "why?", novel situation, high stakes, first time explaining pattern
- ⬇️ **Decrease detail:** User says "too much", established pattern, already explained this before
- **Default:** Brief (Level 3) unless situation requires more

---

### Communication Pattern for Strategic Decisions

**Template:**
```
[CONTEXT] What situation requires a decision?

[APPROACH] What I'm proposing: [brief description]

[RATIONALE] Why this approach:
- Reason 1
- Reason 2

[ALTERNATIVE] Alternative considered: [name]
- Why not: [brief]

[TRADEOFF] What we're giving up: [key tradeoff]

[QUESTION] Does this reasoning align with your thinking?
```

**Example:**
```
We need to track budget usage.

Proposing JSON file storage (not SQLite database).

Why:
- Single user (no concurrency issues)
- Aligns with "simple but robust" principle
- Easy to inspect/debug (human-readable)

Alternative: SQLite database
- Why not: Adds complexity we don't need yet for single user

Tradeoff: Less structured, but simpler to maintain and debug.

Does this reasoning align with your thinking?
```

---

### Communication Pattern for Tactical Decisions

**Template:**
```
[ACTION] Doing X
[REASON] because Y
```

**Example:**
```
Using Edit tool (not Write) because we're making targeted changes to specific functions.
Alternative would be Write for cleaner before/after, but Edit gives incremental verification.
```

---

## Tool Selection Guidelines

### Edit vs Write

**Use Edit when:**
- Small, targeted changes (fixing bug, updating function)
- Incremental verification important
- High risk of breaking something
- User asked for specific section changes

**Use Write when:**
- Architectural refactors affecting multiple sections
- Whole-file transformation clearer than multiple edits
- Want clean before/after for user
- Creating new file

**Current default:** Edit (safer, incremental)
**Better for architecture:** Write (cleaner, holistic)

**Note:** Edit vs Write pattern already explained - no need to repeat rationale in future

---

### Read vs Grep vs Glob

**Use Read when:**
- Know exact file path
- Want to see file content
- Verifying changes made

**Use Grep when:**
- Searching for specific code/text
- Don't know which file
- Pattern matching needed

**Use Glob when:**
- Finding files by name pattern
- Exploring file structure
- Listing specific file types

---

## Session Initialization

### At Session Start

**User says:** "Read WORKING_AGREEMENT.md and ARCHITECTURE.md"

**Claude does:**
1. Read both documents
2. Acknowledge: "Loaded working agreement and architecture. Ready to work."
3. Keep principles in context for session

**Or user provides context summary:** "We're working on voice-to-text transcription. We follow WORKING_AGREEMENT.md for process and ARCHITECTURE.md for design. Provider abstraction is strategic, model selection is tactical."

---

### Mid-Session Reminders

**If Claude forgets to explain:**
- **User:** "Why did you choose that approach?"
- **Claude:** Reads working agreement, provides explanation

**If Claude over-explains:**
- **User:** "Too much detail, dial it back"
- **Claude:** Shifts to Level 3 (Brief)

**If Claude drifts from architecture:**
- **User:** "Check the architecture document"
- **Claude:** Reviews ARCHITECTURE.md, corrects course

---

## Quality Standards

### Code Quality
- Type hints throughout
- Comprehensive docstrings
- Error handling for edge cases
- Logging for debugging
- Tests when appropriate (not yet implemented)

### Documentation Quality
- Clear headings and structure
- Examples included
- Rationale explained (why, not just what)
- Kept up to date with code changes

### Commit Quality
- Descriptive messages (not "fix bug")
- Problem + solution + why format
- Reference issues/discussions when relevant

---

## Calibration & Evolution

### This Document Is Living

**When to update:**
- Discover new pattern/principle
- Calibrate explanation density
- Add new tool guidelines
- Process not working well

**How to update:**
- Discuss change with John
- Update document
- Commit with explanation of why changed

**Version history:**
| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-11-09 | Initial working agreement |
| 1.1 | 2025-11-09 | Updated default to Level 3 (Brief), added learning curve rule |
| 1.2 | 2025-11-09 | Added "Before Implementing New APIs/Libraries" checklist - be thorough with documentation first |
| 1.3 | 2025-11-10 | Added "When Debugging Repeated Failures" - search strategy for "X not working" vs "how to do X" |
| 1.4 | 2025-11-10 | Added "Root Cause Over Band-Aids" principle - fix underlying problems, resist outcome theater, value craftsmanship |

---

## Troubleshooting

### "Claude isn't explaining decisions"
→ User: "Check the working agreement"
→ Claude: Reviews checklist, provides explanation

### "Claude is explaining too much"
→ User: "Dial back the detail"
→ Claude: Shifts to Level 3 (Brief rationale only)

### "Claude removed something strategic"
→ User: "Why did you remove that?"
→ Claude: Should have checked strategic vs tactical first

### "Not sure if this is strategic or tactical"
→ Check ARCHITECTURE.md Section 6.3 (Strategic vs Tactical table)
→ Ask John if unclear

---

## Key References

- **ARCHITECTURE.md** - What we're building (strategic principles, design)
- **SETUP_V2.md** - How to set up and run (operational)
- **CODE_REVIEW_NOTES.md** - Findings from reviews (snapshots)
- **This document** - How we work together (process)

---

## Quick Cheat Sheet

**Before implementing:**
- Explain strategy, choose approach, state why

**Strategic decision:**
- Options + rationale + tradeoffs + "Does this align?"

**Tactical decision:**
- Brief rationale: "Using X because Y"

**Routine work:**
- Just do it (no explanation)

**Not sure:**
- Check ARCHITECTURE.md strategic vs tactical table
- Ask John

**Forgot to explain:**
- User reminds: "Why?"
- Check working agreement, provide rationale

---

**End of Working Agreement**

*Update this document as we learn better ways to collaborate.*
