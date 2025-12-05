# Cleanup and Library Addition Fixes

## Summary

Fixed issues with stuck jobs and library addition failures.

## Issues Fixed

### 1. Library Addition Error Handling ✅

**Problem:** Library addition failures were silent - if `add_entry()` returned `None` or threw an exception, the job was still marked complete but not added to library.

**Root Cause:**
- `library_service.add_entry()` can return `None` if save fails (line 198 in library.py)
- `_handle_job_completion()` only updates job if `library_id` is returned (line 676)
- No error logging or retry mechanism

**Fix Applied:**
- Wrapped library addition in try/except in `_handle_job_completion()`
- Added detailed error logging
- Set `library_add_failed` flag on job record for cleanup script to detect
- Improved error logging in `library_service.add_entry()`

**Files Changed:**
- `app/services/orchestrator.py` - Added try/except and error handling
- `app/services/library.py` - Improved error logging

### 2. Cleanup Script ✅

**Created:** `scripts/cleanup_jobs.py`

**Detects:**
1. **Stuck Processing Jobs:** Status = "processing" for > 1 hour
2. **Complete Jobs Missing Library:** Status = "complete", `actual_cost` set, but `library_id` missing
3. **Duplicate Jobs:** Multiple jobs with same filename
4. **Orphaned Jobs:** Status = "complete" but transcript file missing

**Features:**
- `--dry-run` mode to preview changes
- `--fix-stuck` - Check and update stuck processing jobs
- `--fix-library` - Add complete jobs to library
- `--fix-duplicates` - Mark duplicate jobs as failed
- `--fix-orphans` - Mark orphaned jobs as failed
- `--all` - Fix all issues

**Results:**
- Fixed 4 jobs missing from library
- Fixed 4 duplicate job groups (marked duplicates as failed)
- Fixed 4 orphaned jobs (marked as failed)
- 1 stuck job found (needs status check with Google API)

## Root Cause Analysis

### Why Library Addition Failed

**Scenario 1: Save Failure**
- `_save_library()` can fail (permissions, disk full, etc.)
- Returns `False` → `add_entry()` returns `None`
- Job marked complete but not in library

**Scenario 2: Exception During Addition**
- Exception in `add_entry()` (e.g., metadata conversion)
- Returns `None` → job not in library

**Scenario 3: Status Check Never Happens**
- Job completes on Google's side
- Status check endpoint never called (or called before completion)
- Job never goes through `_handle_job_completion()`
- Remains in "processing" status

### Why Jobs Get Stuck

1. **UI Stops Polling:** User closes browser, network issue
2. **Server Restart:** Job state lost, never checked again
3. **Status Check Fails:** Google API error, but job actually completed
4. **Race Condition:** Multiple status checks, one fails

## Prevention Measures

### 1. Improved Error Handling ✅
- Library addition wrapped in try/except
- Errors logged with full traceback
- `library_add_failed` flag set for cleanup detection

### 2. Cleanup Script ✅
- Can be run periodically to detect and fix issues
- Can check stuck jobs with Google API
- Can re-add jobs to library

### 3. Future: Periodic Status Check (Not Implemented)
- Background task to check all "processing" jobs > 1 hour old
- Would prevent jobs from getting stuck
- Could be added as a scheduled task or startup check

## Recommendations

### Immediate Actions
1. ✅ Run cleanup script periodically (weekly/monthly)
2. ✅ Monitor logs for library addition failures
3. ✅ Check for `library_add_failed` flag in jobs

### Future Improvements
1. **Periodic Status Check:** Background task to check old processing jobs
2. **Retry Logic:** Automatic retry of failed library additions
3. **Health Check Endpoint:** API endpoint to check system health
4. **Alerting:** Notify when jobs are stuck or library additions fail

## Usage

```bash
# Report issues only
python scripts/cleanup_jobs.py

# Fix all issues
python scripts/cleanup_jobs.py --all

# Fix specific issues
python scripts/cleanup_jobs.py --fix-library --fix-duplicates

# Dry run (preview changes)
python scripts/cleanup_jobs.py --all --dry-run
```

