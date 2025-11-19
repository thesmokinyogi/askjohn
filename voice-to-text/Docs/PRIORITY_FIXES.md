# Priority Fixes - Current Status

**Date:** 2025-11-18  
**Last Updated:** After temp file cleanup implementation

---

## ✅ COMPLETED

1. **Temp File Cleanup on Startup** ✅
   - **Status:** Implemented
   - **Location:** `app/main.py:cleanup_orphaned_temp_files()`
   - **Impact:** Prevents disk space leaks from interrupted uploads
   - **Next:** Test on next server restart

2. **Progress Monitoring for GCS Uploads** ✅
   - **Status:** Implemented
   - **Location:** `app/services/storage.py:upload_audio_from_file()`
   - **Impact:** Will show upload speed and progress every 5 seconds
   - **Next:** Test with actual upload to verify it works

---

## 🔴 CRITICAL - Blocking Core Functionality

### 1. Long File Transcription - Empty Transcripts
- **Status:** 🔴 **BROKEN**
- **Evidence:** All 3 long file jobs (94.32 min) have empty transcripts
- **Root Cause:** ASR Starvation (MP3 + background music + Chirp model)
- **Documentation:** 
  - `docs/TRANSCRIPT_EMPTY_ROOT_CAUSE.md`
  - `COGNITIVE_CHECKPOINT_20251118.md`
- **Next Steps:**
  1. Test with lossless WAV format (re-encode MP3 to LINEAR16 WAV @ 16000 Hz)
  2. Use "long" model instead of Chirp (better for speech+music)
  3. Verify audio file actually contains speech
- **Priority:** **P0 - BLOCKING**

---

## 🟡 HIGH PRIORITY - User-Facing Issues

### 2. Slow Upload Speeds
- **Status:** 🟡 **INVESTIGATING**
- **Evidence:** 1.33 Mbps observed vs 50+ Mbps expected
- **Impact:** 80.6 MB file takes 8+ minutes instead of ~13 seconds
- **Progress:** Added progress monitoring (needs testing)
- **Next Steps:**
  1. Test progress monitoring with actual upload
  2. Verify actual upload speed from logs
  3. If still slow, investigate GCS client configuration
  4. Consider using resumable upload API directly
- **Priority:** **P1 - HIGH**

### 3. Server Restart During Upload = Lost Job
- **Status:** 🟡 **ARCHITECTURAL ISSUE**
- **Impact:** Code is NOT re-entrant. Restart during upload = lost job, no error message
- **Documentation:** `docs/SERVER_RESTART_IMPACT_ANALYSIS.md`
- **Fixes Applied:**
  - ✅ Temp file cleanup on startup
- **Remaining Issues:**
  1. No way to resume interrupted uploads
  2. No health check endpoint to prevent restart during uploads
  3. No graceful shutdown
  4. Orphaned GCS files possible
- **Next Steps:**
  1. Add health check endpoint (`/health`) to show active uploads
  2. Implement graceful shutdown (wait for active requests)
  3. Consider resumable uploads (longer-term)
- **Priority:** **P1 - HIGH**

### 4. "file is not defined" Error
- **Status:** 🟡 **PARTIALLY FIXED**
- **Location:** `app/api/v1/transcription.py`, `app/main.py`
- **Fix Applied:** Captured filename early to avoid scoping issues
- **Status:** May still occur - needs verification
- **Next Steps:**
  1. Monitor for recurrence
  2. If it occurs, get full traceback
  3. Verify fix is complete
- **Priority:** **P1 - HIGH**

### 5. Estimate Processing Time Endpoint Errors
- **Status:** 🟡 **INVESTIGATING**
- **Issue:** `/api/estimate-processing-time` returning 500 errors with empty messages
- **Location:** Both `app/main.py` (old) and `app/api/v1/budget.py` (new) endpoints exist
- **Fix Applied:** Added `exc_info=True` for full traceback
- **Next Steps:**
  1. Wait for next error to see full traceback
  2. Fix root cause
  3. Remove duplicate endpoint
- **Priority:** **P1 - HIGH**

---

## 🟢 MEDIUM PRIORITY - Code Quality

### 6. Duplicate Endpoints
- **Status:** 🟢 **CLEANUP NEEDED**
- **Issue:** Two endpoints for same functionality:
  - `/api/estimate-processing-time` (old, in `app/main.py`)
  - `/api/v1/estimate-processing-time` (new, in `app/api/v1/budget.py`)
- **Impact:** Confusion, potential conflicts
- **Next Steps:**
  1. Update frontend to use `/api/v1/estimate-processing-time`
  2. Remove old endpoint from `app/main.py`
  3. Test thoroughly
- **Priority:** **P2 - MEDIUM**

### 7. `billed_duration` Not Being Stored
- **Status:** 🟢 **INVESTIGATION NEEDED**
- **Issue:** `billed_duration` extracted from API but not stored in job records
- **Impact:** Using estimated duration instead of actual billed duration
- **Documentation:** `docs/BILLED_DURATION_ANALYSIS.md`
- **Next Steps:**
  1. Investigate why it's not being stored
  2. Fix storage logic
  3. Verify it's stored in future jobs
- **Priority:** **P2 - MEDIUM**

### 8. Duplicate Budget Entries (Historical)
- **Status:** 🟢 **CLEANUP NEEDED**
- **Issue:** Budget shows $9.15 instead of actual ~$1.14 (24 entries for 3 jobs)
- **Fix Applied:** ✅ Guards prevent future duplicates
- **Remaining:** Historical data cleanup
- **Next Steps:**
  1. Create script to deduplicate `budget_tracking.json`
  2. Verify cleanup doesn't break anything
- **Priority:** **P3 - LOW** (fix prevents future, cleanup is cosmetic)

---

## 🔵 DEFERRED - Future Improvements

### 9. Billing Source of Truth
- **Status:** 🔵 **DEFERRED**
- **Issue:** We calculate costs internally instead of using Google's actual billing data
- **Documentation:** `docs/BILLING_SOURCE_OF_TRUTH.md`
- **Priority:** **P4 - DEFERRED**

### 10. Resumable Uploads
- **Status:** 🔵 **DEFERRED**
- **Issue:** Uploads can't resume after server restart
- **Priority:** **P4 - DEFERRED** (longer-term architectural improvement)

---

## Summary

### Immediate Actions Needed (This Session)
1. **Test progress monitoring** - Verify upload speed logging works
2. **Test long file transcription** - Try with WAV format and "long" model
3. **Monitor for errors** - Watch for "file is not defined" and estimate-processing-time errors

### Short-term (Next Session)
1. Fix long file transcription (if WAV doesn't work, investigate further)
2. Investigate slow upload speeds (if progress monitoring shows it's still slow)
3. Add health check endpoint
4. Remove duplicate endpoints

### Medium-term
1. Fix `billed_duration` storage
2. Implement graceful shutdown
3. Clean up duplicate budget entries

### Long-term
1. Resumable uploads
2. Billing API integration
3. Async job queue

---

## Testing Checklist

- [ ] Test progress monitoring with actual upload (verify logs show speed)
- [ ] Test long file transcription with WAV format
- [ ] Test long file transcription with "long" model
- [ ] Monitor for "file is not defined" error recurrence
- [ ] Monitor for estimate-processing-time error with full traceback
- [ ] Verify temp file cleanup on server restart

