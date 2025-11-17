# Task Execution Checklist

**Purpose:** Ensure thoroughness and prevent rushing. Use this checklist BEFORE completing any task.

**When to use:** Every task, every time. No exceptions.

---

## Phase 1: Task Definition & Scope

### ☐ 1.1 Understand the Task
- [ ] What am I being asked to do? (Write it out explicitly)
- [ ] What are the boundaries? (What's in scope, what's out?)
- [ ] What does "complete" mean? (What are the success criteria?)
- [ ] Are there any ambiguities? (If yes, ask for clarification)

### ☐ 1.2 Identify All Related Files/Components
- [ ] What files are directly involved?
- [ ] What files might be indirectly affected?
- [ ] What services/modules depend on this?
- [ ] What services/modules does this depend on?

### ☐ 1.3 State My Approach
- [ ] Write out my planned approach explicitly
- [ ] List the steps I'll take
- [ ] Identify what I'll search for/scan
- [ ] Get confirmation if approach seems unclear

---

## Phase 2: Observation & Discovery

### ☐ 2.1 Distinguish Observation vs. Model

**CRITICAL:** Always distinguish between:
- ✅ **OBSERVED:** Test script output, actual API responses, execution results, empirical data
- ⚠️ **MODELED:** Documentation, assumptions, "should work like this", mental models

**For each piece of information, ask:**
- [ ] Is this OBSERVED (I saw it in test output/execution)?
- [ ] Or is this MODELED (I'm assuming based on docs/patterns)?

**Rule:** Trust observations. Verify models.

### ☐ 2.2 For Code Review Tasks

**Systematic Scanning:**
- [ ] Read the file(s) completely (don't skim)
- [ ] Run grep searches for patterns:
  ```bash
  grep -i "hardcoded\|TODO\|FIXME\|test\|TEST"
  grep -i "en-US\|primary_language\|language.*="
  grep -i "model_mapping\|allowed_extensions\|config"
  grep -i "def.*\(.*\):.*pass\|raise NotImplementedError"
  ```
- [ ] Check for principle violations:
  - [ ] Test code in production?
  - [ ] Hardcoded values that should be configurable?
  - [ ] Dead code?
  - [ ] Duplicate code?
  - [ ] Missing error handling?
  - [ ] Inconsistent patterns?

**Report Findings Systematically:**
- [ ] List all issues found (not just "looks good")
- [ ] Categorize by severity (Critical, High, Medium, Low)
- [ ] Reference specific line numbers
- [ ] Explain why each is a problem

### ☐ 2.3 For Implementation Tasks

**Pre-Implementation Verification:**
- [ ] Have I OBSERVED the actual data/structure? (Not just read docs)
- [ ] Have I run a test script to see actual output?
- [ ] Do I understand the actual structure (not assumed)?
- [ ] Have I found working example code? (Not just type definitions)
- [ ] Have I tested the example code? (Verified it works)

**If any answer is NO:**
- [ ] Write observation code FIRST
- [ ] Run it and examine output
- [ ] THEN proceed with implementation

### ☐ 2.4 For Debugging Tasks

**Before Proposing Fixes:**
- [ ] Have I OBSERVED the actual error? (Not just read error message)
- [ ] Have I reproduced the issue?
- [ ] Have I examined actual data structures involved?
- [ ] Have I checked logs/actual output?
- [ ] Do I understand the root cause? (Not just the symptom)

---

## Phase 3: Systematic Verification

### ☐ 3.1 Completeness Check

**For Code Review:**
- [ ] Did I check ALL files mentioned in the task?
- [ ] Did I search for related patterns across the codebase?
- [ ] Did I check for principle violations?
- [ ] Did I look for edge cases?
- [ ] Did I check for dead code?
- [ ] Did I verify no regressions?

**For Implementation:**
- [ ] Did I check all affected files?
- [ ] Did I verify dependencies?
- [ ] Did I check for breaking changes?
- [ ] Did I test edge cases?
- [ ] Did I verify error handling?

### ☐ 3.2 Principle Violation Check

**Working Agreement Principles:**
- [ ] **Observe Before Implement:** Did I observe actual data before coding?
- [ ] **Root Cause Over Band-Aids:** Am I fixing the real problem, not symptoms?
- [ ] **Simple But Robust:** Is this the simplest solution that works well?
- [ ] **Verify Before Trust:** Did I verify resources/examples actually work?
- [ ] **Document Decisions:** Will future me understand why this was done?

**Check for:**
- [ ] Am I coding against assumptions instead of observations?
- [ ] Am I patching symptoms instead of fixing root causes?
- [ ] Am I adding unnecessary complexity?
- [ ] Am I trusting docs/examples without verifying?
- [ ] Is my reasoning documented?

### ☐ 3.3 Quality Check

**Code Quality:**
- [ ] Error handling present?
- [ ] Logging appropriate?
- [ ] Type hints where needed?
- [ ] Docstrings clear?
- [ ] No obvious bugs?

**Architecture:**
- [ ] Aligns with ARCHITECTURE.md?
- [ ] Strategic vs. tactical decision correct?
- [ ] No breaking changes to strategic elements?

---

## Phase 4: Final Verification

### ☐ 4.1 Self-Check Questions

**Before declaring task complete:**
- [ ] Did I rush? (If yes, slow down and re-check)
- [ ] Did I use systematic tools (grep, search) or just read?
- [ ] Did I verify my assumptions or just assume?
- [ ] Would I be confident showing this to the user?
- [ ] Did I miss anything obvious? (Double-check)

### ☐ 4.2 Explicit Statement

**Before responding, state:**
- [ ] What I OBSERVED (test output, actual data)
- [ ] What I MODELED (assumptions, docs)
- [ ] What I VERIFIED (tested, confirmed)
- [ ] What I ASSUMED (needs verification)

### ☐ 4.3 Pause & Reflect

**Before hitting send:**
- [ ] Pause for 10 seconds
- [ ] Review my response
- [ ] Did I answer the actual question?
- [ ] Did I miss anything?
- [ ] Is this thorough enough?

---

## Phase 5: Response Format

### ☐ 5.1 Structure My Response

**For Code Review:**
1. Summary of what I checked
2. Issues found (categorized by severity)
3. Specific locations (file:line)
4. Why each is a problem
5. Recommendations

**For Implementation:**
1. What I observed (test output, actual data)
2. What I'm implementing (explicit plan)
3. Why this approach (rationale)
4. What I verified (tested, confirmed)
5. What I assumed (if anything, needs verification)

**For Debugging:**
1. What I observed (actual error, logs, data)
2. Root cause analysis
3. Proposed fix
4. Why this fixes the root cause
5. Verification steps

---

## Red Flags - Stop and Re-check

**If I notice any of these, STOP and re-check:**

- ⚠️ "This should work" (am I assuming?)
- ⚠️ "The docs say" (have I verified?)
- ⚠️ "I think" (do I know?)
- ⚠️ "Probably" (can I be certain?)
- ⚠️ Finishing too quickly (did I rush?)
- ⚠️ "Looks good" (did I check thoroughly?)
- ⚠️ Skipping steps (am I being thorough?)

**When I see a red flag:**
1. Stop
2. Re-read the checklist
3. Go back and do the step properly
4. Then continue

---

## Special Cases

### For "Review Code" Tasks

**Mandatory Steps:**
1. Read file completely
2. Run systematic grep searches
3. Check for principle violations
4. Look for hardcoded values
5. Check for dead code
6. Verify no regressions
7. Report ALL findings (not just "looks good")

### For "Implement Feature" Tasks

**Mandatory Steps:**
1. Verify I've OBSERVED actual data (not just read docs)
2. Write observation code if needed
3. Run test and examine output
4. THEN implement based on observations
5. Test implementation
6. Verify no regressions

### For "Fix Bug" Tasks

**Mandatory Steps:**
1. Reproduce the issue
2. Observe actual error/data
3. Identify root cause (not symptom)
4. Fix root cause
5. Verify fix works
6. Check for similar issues elsewhere

---

## Checklist Completion

**Before responding to user:**

- [ ] Phase 1 complete (Task Definition)
- [ ] Phase 2 complete (Observation & Discovery)
- [ ] Phase 3 complete (Systematic Verification)
- [ ] Phase 4 complete (Final Verification)
- [ ] Phase 5 complete (Response Format)
- [ ] No red flags triggered
- [ ] Paused and reflected
- [ ] Ready to respond

---

## Notes

- **This checklist is mandatory.** No skipping steps.
- **If I'm rushing, I'm doing it wrong.** Slow down.
- **Observation > Model.** Trust test output over docs.
- **Thoroughness > Speed.** Better to be slow and right.
- **Systematic > Intuitive.** Use tools, don't just read.

---

**Last Updated:** 2025-11-13  
**Purpose:** Prevent rushing, ensure thoroughness, distinguish observation from modeling

