# Investigation: Stuck Jobs and Library Addition Failures

## Problem Summary

1. **Stuck Job:** Job `v2-6f84f379` was stuck in "processing" status
2. **Library Missing:** Job `v2-6f595188` completed successfully but wasn't added to library

## Root Cause Analysis

### Issue 1: Stuck Jobs

**Symptoms:**
- Job status remains "processing" indefinitely
- `updated_at` timestamp doesn't change
- No error recorded

**Possible Causes:**
1. Status check endpoint not called (UI stopped polling)
2. Status check failed silently
3. Google operation actually stuck (rare)
4. Server restart during processing (job state lost)

**Current Detection:**
- No automatic detection
- Manual inspection required

### Issue 2: Library Addition Failures

**Symptoms:**
- Job marked `complete` with `actual_cost` set
- `library_id` is `None` or missing
- Transcript file exists
- Not in `library.json`

**Root Cause Analysis:**

Looking at `_handle_job_completion` (orchestrator.py:546-680):

1. **Line 575:** Guard checks if `actual_cost` AND `library_id` are both set → skip
2. **Line 594-595:** If `actual_cost` set but `library_id` missing → should re-add
3. **Line 665-673:** Calls `library_service.add_entry()`
4. **Line 676-680:** Only updates job if `library_id` is returned

**Failure Scenarios:**

**Scenario A: `add_entry()` returns `None`**
- `library_service.add_entry()` can return `None` on failure (line 171 in library.py)
- If it returns `None`, job record is NOT updated with `library_id`
- Job remains complete but not in library
- **Fix:** The re-add logic (line 594-595) should catch this, but only if status is checked again

**Scenario B: Exception during library addition**
- If exception occurs after `mark_complete()` but before library update
- Job is marked complete, but library addition fails
- **Fix:** Need try/except around library addition

**Scenario C: Status check never happens after completion**
- Job completes on Google's side
- Status check endpoint never called (or called before completion)
- Job never goes through `_handle_job_completion`
- **Fix:** Need periodic status check for old processing jobs

## Current Code Flow

```
Job Completes on Google
  ↓
Status Check Endpoint Called
  ↓
orchestrator.check_job_status()
  ↓
Google API returns "done: true"
  ↓
_handle_job_completion()
  ↓
mark_complete() → Sets actual_cost
  ↓
library_service.add_entry() → Returns library_id or None
  ↓
If library_id: Update job with in_library=True
```

**Problem:** If `add_entry()` fails or returns `None`, job is still marked complete but not in library.

## Proposed Solutions

### Solution 1: Healthy Cleanup Script

**Purpose:** Detect and fix stuck/missing jobs

**Detects:**
1. **Stuck Processing Jobs:**
   - Status = "processing" for > 1 hour
   - Check actual status with Google API
   - Update if complete/failed

2. **Complete Jobs Missing Library:**
   - Status = "complete"
   - `actual_cost` is set
   - `library_id` is None or missing
   - Transcript file exists
   - Re-add to library

3. **Duplicate Jobs:**
   - Same filename, multiple jobs
   - Keep most recent complete, mark others as failed/duplicate

4. **Orphaned Jobs:**
   - Status = "complete" but no transcript file
   - Mark as failed or delete

### Solution 2: Improve Error Handling

**In `_handle_job_completion`:**
- Wrap library addition in try/except
- Log errors but don't fail the entire completion
- Set a flag if library addition fails for retry

**In `library_service.add_entry`:**
- Better error logging
- Return error details, not just None

### Solution 3: Periodic Status Check

**Background Task:**
- Check all "processing" jobs older than 1 hour
- Call status check endpoint
- Update status if changed

## Implementation Plan

1. **Create cleanup script** (immediate)
2. **Improve error handling** (prevent future issues)
3. **Add periodic status check** (prevent stuck jobs)

