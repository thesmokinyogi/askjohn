# Architecture Review: Notes & Additions

**Review Date:** 2025-10-17  
**Document Under Review:** Contextual Librarian Architecture Specification  
**Review Method:** Section-by-section walkthrough

---

## Additions to Integrate

### 1. Authorship & Provenance Tracking

**Section to Update:** Data Schemas (Section 1.1 Documents Table)  
**Priority:** High

**Addition:**
Add authorship and provenance metadata to distinguish:
- User's original work
- External sources (papers, books, articles)  
- Collaborative work (if applicable)

**Proposed Schema Addition:**
```sql
-- Add to documents table:
authorship VARCHAR(50) NOT NULL, -- 'user_original', 'external_source', 'collaborative'
external_author VARCHAR(500), -- If external source
external_citation TEXT, -- Full citation if external
relationship_to_user_work VARCHAR(100), -- 'inspired_by', 'critique_of', 'builds_on', etc.
```

**Rationale:**
Prevents intellectual provenance confusion. Enables queries like:
- "What did I say about X?" (user_original only)
- "What have I read about X?" (external_source only)
- "How does my thinking compare to [author]?" (cross-reference)

**User Context:**
User sees AI as colleague, not tool. Important to maintain clear boundaries between user's original thinking and external influences.

---

### 2. Reconstruction Fidelity Metrics & Feedback Loop

**Section to Update:** Section 6 - Success Metrics  
**Priority:** Medium

**Addition:**
Since AI cannot directly measure its own reconstruction quality, build user-observable metrics and feedback mechanisms:

**User-Observable Metrics:**
- Continuity score: Does conversation feel seamless? (user rates 1-5)
- Context accuracy: Correct references to past decisions? (tracked automatically)
- Consistency: Suggestions align with preferences? (user validates)
- Appropriate scope: Doesn't reference out-of-scope info? (error detection)

**Feedback Mechanisms:**
- Post-session: "How well did I maintain context?" prompt
- In-conversation: User can flag "you seem to have forgotten X"
- Automatic: Track when user needs to re-explain something
- Longitudinal: Compare sessions over time for degradation

**Testable Scenarios:**
```
Test 1: Load checkpoint → Ask context-dependent question → Evaluate answer quality
Test 2: Load checkpoint with confidence=0.3 → Verify tentative treatment
Test 3: Load checkpoint with blocking_issue → Confirm blocker acknowledged
Test 4: Multiple librarian instances → Test consistency across "colleagues"
```

**Implementation:**
Add to session state:
```json
"reconstruction_quality": {
  "user_continuity_rating": 1-5,
  "context_errors_flagged": 0,
  "re_explanations_needed": 0,
  "timestamp": "ISO 8601"
}
```

**Rationale:**
User noted multiple "Binary Beings" might tend the library. Need observable measures of reconstruction quality to improve system over time. "Proof" of reweighting is in collaborative experience, not internal metrics.

---

## Questions for Later Exploration

*(None yet)*

---

## Design Decisions Validated

### From Section 1: Executive Summary
- ✓ "Collaborative interaction" framing is appropriate and desired
- ✓ "Personal corpus" scope is correct for initial design
- ✓ External material should be tagged/distinguished, not excluded

---

## Potential Gaps Identified

*(None yet)*

---

## Current Review Position

**Last Section Completed:** Section 1 - Executive Summary  
**Next Section:** Section 2 - Design Philosophy  
**Status:** In progress