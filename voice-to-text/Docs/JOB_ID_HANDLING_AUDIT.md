# Job ID Handling Audit

**Date:** 2025-11-19  
**Purpose:** Verify job ID handling is clean and consistent, especially for early submissions

---

## ID Handling Flow

### Normal Flow (Main Endpoint: `/transcribe`)

1. **Job Submission:**
   - Upload to GCS → get `gcs_uri` ✅
   - Submit to Google → get `operation.operation.name` = Google operation ID ✅
   - **At this point we HAVE the Google operation ID** (unlike queued jobs)
   - `job_id = google_operation_id` (same value)
   - `job_storage.create_job(job_id=job_id, ...)` creates record (with `google_operation_id=None` initially)
   - `job_storage.update_job(job_id, {"google_operation_id": google_operation_id})` sets it explicitly
   - **Result:** `job_id` = Google operation ID, `google_operation_id` = same value

2. **Status Check:**
   - User calls `/api/jobs/{job_id}/status` with Google operation ID
   - `job_storage.get_job(job_id)` finds it directly
   - **Fallback:** If not found, searches by `google_operation_id` (added for safety)

### Queued Flow (API v1 Endpoint: `/api/v1/transcribe`)

1. **Initial Queue (Metadata Not Ready):**
   - Creates temporary `job_id = f"job-{uuid.uuid4()}"`
   - `job_storage.create_job(job_id=job_id, ...)` with `google_operation_id=None`
   - Request queued with `job_id` reference

2. **Processing (When Metadata Ready):**
   - `orchestrator.submit_transcription_from_file(existing_job_id=job_id, ...)`
   - Gets Google operation ID from submission
   - `job_storage.update_job(existing_job_id, {"google_operation_id": google_operation_id, ...})`
   - **Result:** `job_id` = temporary UUID, `google_operation_id` = Google operation ID

3. **Status Check:**
   - User might call with temporary `job_id` or Google operation ID
   - `orchestrator.check_job_status(job_id)` has fallback logic:
     - First tries `get_job(job_id)`
     - If not found, searches by `google_operation_id`
     - Uses internal `job_id` for consistency

---

## ID Consistency Rules

### Rule 1: Main Endpoint (Direct Submission)
- **job_id** = Google operation ID (e.g., `"projects/.../operations/123"`)
- **google_operation_id** = Same as job_id (explicitly set)
- **Status:** ✅ Consistent

### Rule 2: Queued Endpoint (Metadata Not Ready)
- **job_id** = Temporary UUID (e.g., `"job-abc-123"`)
- **google_operation_id** = Google operation ID (set when processed)
- **Status:** ✅ Consistent (different IDs, but linked)

### Rule 3: Status Lookup
- **Primary:** Look up by `job_id`
- **Fallback:** If not found, search by `google_operation_id`
- **Status:** ✅ Both endpoints have fallback logic

---

## Potential Issues & Fixes

### Issue 1: Main Endpoint Not Setting `google_operation_id`
**Status:** ✅ FIXED
- **Problem:** `create_job()` sets `google_operation_id=None`, but main endpoint uses Google operation ID as `job_id`
- **Context:** Main endpoint ALWAYS has Google operation ID immediately (submits synchronously), unlike queued jobs
- **Fix:** Added explicit `update_job()` call to set `google_operation_id` after creation (we have it at this point)
- **Impact:** Ensures consistency and enables fallback lookups
- **Note:** This is safe because we only set it AFTER we've successfully submitted to Google and received the operation ID

### Issue 2: Status Check Missing Fallback
**Status:** ✅ FIXED
- **Problem:** Main endpoint's `check_job_status()` didn't have fallback to search by `google_operation_id`
- **Fix:** Added same fallback logic as orchestrator
- **Impact:** Handles edge cases where job might be looked up by Google operation ID

### Issue 3: ID Mismatch Between Endpoints
**Status:** ✅ ACCEPTABLE
- **Observation:** Main endpoint uses Google operation ID as `job_id`, queued endpoint uses temporary UUID
- **Assessment:** This is intentional - queued jobs need temporary IDs before Google operation exists
- **Mitigation:** Fallback lookup by `google_operation_id` handles both cases

---

## Verification Checklist

- [x] Main endpoint sets `google_operation_id` explicitly
- [x] Main endpoint has fallback lookup by `google_operation_id`
- [x] Orchestrator has fallback lookup by `google_operation_id`
- [x] Queued jobs update `google_operation_id` when processed
- [x] Both endpoints can find jobs by either ID (with fallback)
- [x] Job records always have both `job_id` and `google_operation_id` set (eventually)

---

## Edge Cases Handled

1. **Early Submission (Before Metadata Ready):**
   - Main endpoint: Processes immediately (no queue)
   - API v1 endpoint: Queues with temporary ID, updates later
   - ✅ Both paths work correctly

2. **Status Check with Google Operation ID:**
   - If job was created with temporary ID, fallback finds it
   - ✅ Fallback logic handles this

3. **Status Check with Temporary ID:**
   - Direct lookup works for queued jobs
   - ✅ No issue

4. **ID Consistency:**
   - Main endpoint: `job_id == google_operation_id`
   - Queued endpoint: `job_id != google_operation_id` (until processed)
   - ✅ Both patterns supported with fallback

---

## Summary

**Status:** ✅ Clean and Tidy

All ID handling is now consistent:
- Main endpoint explicitly sets `google_operation_id`
- Both endpoints have fallback lookup logic
- Queued jobs properly update `google_operation_id` when processed
- Status checks work with either ID format

The system handles both direct submissions and queued submissions correctly, with proper ID tracking and fallback mechanisms.

