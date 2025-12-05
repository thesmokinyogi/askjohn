# Design: Fix Upload Timeout Issue

## Problem Statement

Large file uploads (>5MB) to Google Cloud Storage hang indefinitely using `blob.upload_from_filename()` in `google-cloud-storage==2.10.0`. The `timeout` parameter is not being respected for resumable uploads, causing the process to block indefinitely without raising an exception.

**Impact:** Transcription service is non-functional for files larger than ~5MB.

**Root Cause:** Confirmed via controlled test - `timeout` parameter is ignored for resumable uploads (used automatically for large files).

---

## Solution Design

### Approach: Thread-Based Timeout Wrapper

Wrap `blob.upload_from_filename()` in a thread with a real timeout that we control, since the library's timeout parameter doesn't work for resumable uploads.

### Why This Approach

1. **Addresses Root Cause:** Enforces actual timeout (the core issue)
2. **No Library Changes:** Works with existing `google-cloud-storage==2.10.0`
3. **Immediate Fix:** Can be implemented without waiting for library updates
4. **Maintains API:** Doesn't change the method signature or behavior from caller's perspective
5. **Proper Error Handling:** Raises `TimeoutError` when timeout is exceeded

### Implementation Details

**Location:** `app/services/storage.py`, method `upload_audio_from_file()`

**Changes:**
1. Create helper method `_upload_with_enforced_timeout()` that wraps upload in thread
2. Replace direct `blob.upload_from_filename()` call with thread-based wrapper
3. Add proper exception handling and logging
4. Maintain existing timeout calculation logic

**Code Structure:**
```python
def _upload_with_enforced_timeout(
    self,
    blob,
    file_path: str,
    content_type: str,
    timeout_seconds: int
) -> None:
    """
    Upload file with thread-based timeout enforcement.
    
    The library's timeout parameter doesn't work for resumable uploads,
    so we enforce our own timeout using threading.
    """
    import threading
    import time
    
    upload_complete = threading.Event()
    upload_exception = [None]
    
    def upload_worker():
        try:
            # Still set library timeout (may help with initial connection)
            blob.upload_from_filename(
                file_path,
                content_type=content_type,
                timeout=timeout_seconds
            )
        except Exception as e:
            upload_exception[0] = e
        finally:
            upload_complete.set()
    
    # Start upload in daemon thread
    upload_thread = threading.Thread(target=upload_worker, daemon=True)
    upload_thread.start()
    
    # Wait with our enforced timeout
    if not upload_complete.wait(timeout=timeout_seconds):
        # Timeout occurred - raise exception
        raise TimeoutError(
            f"GCS upload timed out after {timeout_seconds}s "
            f"(file={file_path})"
        )
    
    # Check for exceptions from upload thread
    if upload_exception[0]:
        raise upload_exception[0]
```

**Integration:**
Replace lines 297-301 in `storage.py`:
```python
# OLD:
blob.upload_from_filename(
    upload_file_path,
    content_type=content_type,
    timeout=timeout_seconds
)

# NEW:
self._upload_with_enforced_timeout(
    blob,
    upload_file_path,
    content_type,
    timeout_seconds
)
```

---

## Alternatives Considered

### Option A: Chunked Upload with Manual Control
Read file in chunks and upload using `upload_from_string()` with explicit timeout per chunk.

**Why Not:**
- More complex implementation
- May load chunks into memory (defeats streaming benefit)
- Need to handle resumable upload manually
- More code to maintain

### Option B: Use gsutil Subprocess (Fallback)
If Python client fails, fall back to `gsutil cp` command.

**Why Not:**
- Requires gsutil installation (not guaranteed)
- Less integrated with application
- Harder to get progress/errors in Python
- Adds external dependency

### Option C: Upgrade/Downgrade Library Version
Try different versions of `google-cloud-storage` library.

**Why Not:**
- Doesn't address root cause (may be issue in multiple versions)
- May introduce other breaking changes
- May break other functionality
- Unclear which version would fix it

### Option D: Accept Hanging and Add External Monitoring
Keep current code, add external process to kill hanging uploads.

**Why Not:**
- Doesn't fix the problem, just works around it
- Adds complexity
- Poor user experience
- Not a real solution

---

## Tradeoffs

### What We Gain
- ✅ Actual timeout enforcement (fixes the bug)
- ✅ Proper error handling (raises TimeoutError)
- ✅ No library changes required
- ✅ Maintains existing API
- ✅ Can be implemented immediately

### What We Give Up
- ⚠️ Small thread overhead (negligible for file uploads)
- ⚠️ Slightly more complex code (but isolated in helper method)
- ⚠️ Still relies on library for actual upload (but we control timeout)

### Risks
- **Low Risk:** Thread-based timeout is standard pattern
- **Low Risk:** Daemon thread ensures cleanup if main thread exits
- **Low Risk:** Exception handling ensures errors propagate correctly

---

## Testing Plan

1. **Test Small Files (<1MB):**
   - Should work as before (no regression)
   - Verify timeout wrapper doesn't interfere

2. **Test Large Files (>5MB):**
   - Should complete successfully if network is good
   - Should raise TimeoutError if actually times out
   - Verify timeout is actually enforced

3. **Test Timeout Behavior:**
   - Use artificially short timeout (10 seconds) on large file
   - Verify TimeoutError is raised after 10 seconds
   - Verify process doesn't hang

4. **Test Error Handling:**
   - Verify other exceptions (network errors, auth errors) still propagate
   - Verify logging still works correctly

---

## Alignment with Working Agreement

✅ **Observe Before Implement:** 
  - Confirmed issue with controlled test (`test_gcs_python_client.py`)
  - Verified solution approach with observation script (`verify_timeout_wrapper.py`)
  - Solution verified to work before implementation

✅ **Research:** Investigated root cause, tested alternatives  
✅ **Design:** Created solution plan (this document)  
✅ **Verify Before Trust:** Tested timeout wrapper concept and actual GCS upload  
✅ **Root Cause Over Band-Aids:** Fixes actual timeout issue, not just symptoms  
✅ **Simple But Robust:** Minimal code change, proper error handling

## Verification Results

**Test Script:** `scripts/verify_timeout_wrapper.py`

**Results:**
- ✅ Timeout wrapper enforces timeout correctly (tested with simulated hangs)
- ✅ Exception propagation works correctly (tested with failing functions)
- ✅ Catches hanging GCS uploads (tested with actual 5MB upload - timed out after 10s)

**Conclusion:** Solution verified to work before implementation. Ready to proceed.  

---

## Implementation Estimate

- **Helper Method:** ~30 lines (thread wrapper)
- **Integration:** ~5 lines (replace existing call)
- **Testing:** Use existing test script
- **Total:** ~35 lines, low complexity

**Time:** ~30 minutes implementation + testing

---

## Questions for Review

1. Does this approach align with your expectations?
2. Any concerns about thread-based timeout?
3. Should we add progress monitoring in the thread wrapper?
4. Ready to proceed with implementation?

---

**Status:** Design complete, ready for review and approval before implementation.

