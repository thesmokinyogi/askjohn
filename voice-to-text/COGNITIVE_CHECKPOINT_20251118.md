# Cognitive Checkpoint: Budget Tracking & Error Debugging Session

**Date:** 2025-11-18  
**Session Focus:** Budget tracking bugs, error debugging, source of truth issues

---

## ⚠️ CRITICAL: Core Functionality Issue

### Long File Transcription NOT Working
- **Status:** 🔴 **BROKEN** - All 3 long file jobs (94.32 min) have **EMPTY transcripts**
- **Evidence:** 
  - Jobs marked "complete" ✅
  - Transcript files exist ✅
  - But transcript text is **0 characters** ❌
  - Word count: **0** ❌
- **Root Cause:** ASR Starvation (per Gemini diagnosis)
  - MP3 (lossy codec) + background music + Chirp model = empty transcripts
  - Google segments audio but can't extract speech
- **Documentation:** 
  - `docs/TRANSCRIPT_EMPTY_ROOT_CAUSE.md`
  - `docs/GEMINI_RESPONSE_ANALYSIS.md`
  - `docs/ROOT_CAUSE_SUMMARY.md`
- **Status:** 🔄 **BLOCKING** - Core functionality not working

### What We've Tried
1. ✅ Added `processing_strategy=DYNAMIC_BATCHING`
2. ✅ Always enable `enable_word_time_offsets` (for debugging)
3. ✅ Added detailed config logging
4. ✅ Direct JSON parsing (bypassing Protobuf)
5. ⏸️ User testing with different audio (no background music) - results pending

### Next Steps (CRITICAL)
1. **Test with lossless WAV** (per Gemini recommendation)
   - Re-encode MP3 to LINEAR16 WAV @ 16000 Hz
   - Use "long" model (not Chirp) for speech+music content
   - Minimal config for debugging
2. **Verify audio file quality**
   - Does the file actually contain speech?
   - Is the audio intelligible?
3. **Model selection strategy**
   - Use "long" model for speech+music
   - Use Chirp for clean speech-only
   - Make this configurable

---

## Session Summary

### What We Accomplished

1. **✅ Fixed Duplicate Budget Recording Bug**
   - **Problem:** Same job recorded 24 times in budget (3 jobs → 24 entries = $9.12 instead of $1.14)
   - **Root Cause:** Status polling was recording cost on every check, even for completed jobs
   - **Fix Applied:**
     - Added race condition check in `app/main.py` status endpoint
     - Added `actual_cost` guard (only record if not already set)
     - Added early return in `orchestrator._handle_job_completion` if already recorded
   - **Status:** ✅ Fixed - prevents duplicate recording going forward

2. **✅ Identified Billing Source of Truth Issue**
   - **Problem:** We calculate costs ourselves instead of using Google's actual billing data
   - **Current Approach:** Calculate from `billed_duration` + pricing table
   - **Should Be:** Query Google Cloud Billing API for actual charges
   - **Documentation:** Created `docs/BILLING_SOURCE_OF_TRUTH.md`
   - **Status:** ⏸️ Deferred - needs implementation

3. **✅ Identified `billed_duration` Storage Issue**
   - **Problem:** `billed_duration` extracted from API but not stored in job records
   - **Evidence:** 3 jobs with 94.32 min, none have `billed_duration_minutes` in metadata
   - **Impact:** Falling back to estimated duration instead of actual billed duration
   - **Documentation:** Created `docs/BILLED_DURATION_ANALYSIS.md`
   - **Status:** ⏸️ Deferred - needs investigation

4. **⚠️ Attempted to Fix Error Logging**
   - **Problem:** "Error estimating processing time:" with empty error message
   - **Attempted Fix:** Added `exc_info=True` for full traceback
   - **Status:** 🔄 In Progress - waiting for next error to see traceback

5. **⚠️ Attempted to Fix "file is not defined" Error**
   - **Problem:** NameError: file is not defined in `detect_duration` endpoint
   - **Attempted Fix:** Added safe access check in exception handler
   - **Status:** 🔄 Still occurring - needs deeper investigation

---

## Hanging Threads

### 1. Estimate Processing Time Endpoint Errors
- **Issue:** `/api/estimate-processing-time` returning 500 errors with empty messages
- **Location:** Both `app/main.py` (old) and `app/api/v1/budget.py` (new) endpoints exist
- **Impact:** Frontend can't get processing time estimates
- **Next Steps:**
  - Wait for improved error logging to show actual exception
  - Check if Pydantic validation is failing
  - Verify `ProcessingTimeEstimateResponse` model matches return value
  - Consider removing old endpoint and updating frontend

### 2. "file is not defined" Error
- **Issue:** NameError in `detect_duration` endpoint
- **Location:** `app/main.py:1004` (exception handler)
- **Attempted Fix:** Added safe access, but error persists
- **Next Steps:**
  - Check if error occurs before `file` parameter is available
  - Verify FastAPI parameter handling
  - Check for syntax errors or indentation issues
  - Review full traceback when it occurs again

### 3. Duplicate Endpoint Confusion
- **Issue:** Two endpoints for same functionality:
  - `/api/estimate-processing-time` (old, in `app/main.py`)
  - `/api/v1/estimate-processing-time` (new, in `app/api/v1/budget.py`)
- **Impact:** Confusion about which is being called, potential conflicts
- **Next Steps:**
  - Update frontend to use `/api/v1/estimate-processing-time`
  - Remove old endpoint from `app/main.py`
  - Test thoroughly

---

## Deferred Items

### High Priority

1. **Billing Source of Truth Implementation**
   - **Why Deferred:** Complex implementation, requires Google Billing API integration
   - **Impact:** Cost tracking may not match actual Google charges
   - **Documentation:** `docs/BILLING_SOURCE_OF_TRUTH.md`
   - **Estimated Effort:** 2-3 hours (research + implementation)

2. **`billed_duration` Storage Fix**
   - **Why Deferred:** Need to understand why it's not being stored
   - **Impact:** Using estimated duration instead of actual billed duration
   - **Documentation:** `docs/BILLED_DURATION_ANALYSIS.md`
   - **Estimated Effort:** 1-2 hours (investigation + fix)

3. **Clean Up Duplicate Budget Entries**
   - **Why Deferred:** Not urgent, fix prevents future duplicates
   - **Impact:** Budget shows $9.15 instead of actual ~$1.14
   - **Estimated Effort:** 30 minutes (script to deduplicate)

### Medium Priority

4. **Endpoint Consolidation**
   - Remove old endpoints from `app/main.py`
   - Update frontend to use `/api/v1/` endpoints
   - **Estimated Effort:** 1 hour

5. **Error Handling Improvements**
   - Standardize error logging across all endpoints
   - Add `exc_info=True` to all exception handlers
   - **Estimated Effort:** 30 minutes

---

## Key Learnings

1. **Duplicate Recording Pattern**
   - Status polling can trigger completion logic multiple times
   - Need guards to prevent duplicate operations (cost recording, library entries)
   - Pattern: Check if already processed before processing

2. **Source of Truth Principle**
   - We should use Google's actual billing data, not our calculations
   - `billed_duration` from API is per-job, not cumulative
   - Need to reconcile our tracking with Google's actual charges

3. **Error Debugging Challenges**
   - Empty error messages make debugging difficult
   - Need full tracebacks (`exc_info=True`) to diagnose issues
   - Multiple endpoints for same functionality creates confusion

---

## Immediate Next Steps

### Priority 1: CRITICAL - Fix Long File Transcription
1. **Test with lossless WAV format**
   - Re-encode MP3 to LINEAR16 WAV @ 16000 Hz
   - Use "long" model instead of Chirp
   - Minimal config for debugging
2. **Verify audio file contains speech**
   - Listen to the file
   - Confirm it's not just music/silence
3. **Test with different model**
   - Try "long" model (better for speech+music)
   - Compare results with Chirp

### Priority 2: Fix Current Errors
1. Get full traceback for "file is not defined" error
2. Get full traceback for estimate-processing-time error
3. Fix root causes

### Priority 3: Clean Up Code
1. Remove duplicate endpoints
2. Update frontend to use new API structure
3. Standardize error handling

### Priority 4: Implement Deferred Items
1. Fix `billed_duration` storage
2. Implement billing source of truth
3. Clean up duplicate budget entries

---

## Files Modified This Session

- `app/main.py` - Added duplicate recording guards, improved error logging
- `app/services/orchestrator.py` - Added duplicate recording guard
- `app/api/v1/budget.py` - Improved error logging
- `docs/BILLING_SOURCE_OF_TRUTH.md` - New documentation
- `docs/BILLED_DURATION_ANALYSIS.md` - New documentation

---

## Questions for Next Session

### Critical Questions
1. **Why are long file transcripts empty?** (ASR Starvation - MP3+music+Chirp?)
2. **Does the audio file actually contain speech?** (Need to verify)
3. **Will lossless WAV format fix it?** (Per Gemini recommendation)
4. **Should we use "long" model instead of Chirp?** (Better for speech+music)

### Secondary Questions
5. What is the actual error causing "file is not defined"? (Need full traceback)
6. What is the actual error in estimate-processing-time? (Need full traceback)
7. Why isn't `billed_duration` being stored in job metadata?
8. Should we implement Google Billing API integration now or later?
9. Should we clean up duplicate budget entries now or later?

---

## Session Metrics

- **Time Spent:** ~2 hours
- **Issues Fixed:** 1 (duplicate recording)
- **Issues Identified:** 4 (billing source, billed_duration, endpoint errors)
- **Issues Deferred:** 3
- **Documentation Created:** 2 files

---

## Reflection

We made good progress on identifying the duplicate recording bug and fixing it. However, we got sidetracked trying to debug errors without full tracebacks, which made diagnosis difficult. The improved error logging should help in the next session.

**Key Takeaway:** Always get full tracebacks before attempting fixes. Empty error messages are a red flag that we need better logging.

