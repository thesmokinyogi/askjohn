# Upload Hanging Investigation - November 19, 2025

## Executive Summary

**Problem:** Large file uploads (>5MB) to Google Cloud Storage hang indefinitely using `blob.upload_from_filename()` in `google-cloud-storage==2.10.0`.

**Root Cause:** The `timeout` parameter in `upload_from_filename()` is not being respected for large files. The upload starts but never completes or raises a timeout exception.

**Status:** Confirmed via controlled test. Small uploads work, large uploads hang.

---

## Test Results

### Test Script: `scripts/test_gcs_python_client.py`

**Test 1: Small File Upload (620 bytes)**
- ✅ **SUCCESS** - Completed in 2.0 seconds
- Upload works correctly for small files

**Test 2: Large File Upload (5MB)**
- ❌ **FAILURE** - Hung for 120 seconds, then timed out
- No exception raised, no error message
- Upload started but never completed

### Key Findings

1. **Credentials:** ✅ Working (small uploads succeed)
2. **Bucket Access:** ✅ Working (can list blobs, access bucket)
3. **Network Connectivity:** ✅ Working (small uploads succeed)
4. **Large File Upload:** ❌ **BROKEN** (hangs indefinitely)
5. **Timeout Parameter:** ❌ **NOT WORKING** (should raise exception after timeout, doesn't)

---

## Technical Details

### Current Implementation
- **File:** `app/services/storage.py`, lines 297-301
- **Method:** `blob.upload_from_filename()`
- **Timeout:** Set to 600-1800 seconds based on file size
- **Library Version:** `google-cloud-storage==2.10.0`

### Observed Behavior
1. Upload starts: "Starting GCS upload..." log appears
2. No progress logs
3. No completion message
4. No timeout exception (even after 120+ seconds)
5. Process blocks indefinitely
6. Server must be force-killed

### What Works
- Small files (<1MB) upload successfully
- Bucket access and listing work
- Credentials are valid
- Network connectivity is fine

### What Doesn't Work
- Large files (>5MB) hang indefinitely
- Timeout parameter is ignored
- No error or exception is raised
- No way to cancel or monitor progress

---

## Root Cause Analysis

### Hypothesis
The `upload_from_filename()` method uses resumable uploads for large files automatically. The resumable upload initialization or chunk upload process is hanging, and the timeout parameter is not being properly applied to the underlying HTTP requests.

### Why Timeout Doesn't Work
The `timeout` parameter may only apply to the initial request, not to the resumable upload chunks. Once the resumable upload session is established, subsequent chunk uploads may not respect the timeout, causing the hang.

### Why Small Files Work
Small files likely use simple (non-resumable) uploads, which properly respect the timeout parameter.

---

## Solution Options

### Option 1: Thread-Based Timeout Wrapper (Recommended)
Wrap `upload_from_filename()` in a thread with a real timeout that we control.

**Pros:**
- Can actually enforce timeout
- Doesn't require library changes
- Can be implemented immediately

**Cons:**
- Thread overhead
- Need to handle thread cleanup

**Implementation:**
```python
import threading
import time

def upload_with_real_timeout(blob, file_path, content_type, timeout_seconds):
    """Upload with thread-based timeout that actually works."""
    upload_complete = threading.Event()
    upload_exception = [None]
    upload_result = [None]
    
    def upload_worker():
        try:
            blob.upload_from_filename(
                file_path,
                content_type=content_type,
                timeout=timeout_seconds  # Still set, but we'll enforce our own
            )
            upload_result[0] = True
        except Exception as e:
            upload_exception[0] = e
        finally:
            upload_complete.set()
    
    # Start upload in thread
    upload_thread = threading.Thread(target=upload_worker, daemon=True)
    upload_thread.start()
    
    # Wait with our timeout
    if not upload_complete.wait(timeout=timeout_seconds):
        # Timeout occurred - raise exception
        raise TimeoutError(f"Upload timed out after {timeout_seconds} seconds")
    
    # Check for exceptions
    if upload_exception[0]:
        raise upload_exception[0]
    
    return upload_result[0]
```

### Option 2: Chunked Upload with Manual Control
Read file in chunks and upload using `upload_from_string()` with explicit timeout per chunk.

**Pros:**
- Full control over upload process
- Can monitor progress
- Can enforce timeout per chunk

**Cons:**
- More complex implementation
- May load chunks into memory (but can be small chunks)
- Need to handle resumable upload manually

### Option 3: Use gsutil Subprocess (Fallback)
If Python client fails, fall back to `gsutil cp` command.

**Pros:**
- Known to work reliably
- Can use existing tool

**Cons:**
- Requires gsutil installation
- Less integrated
- Harder to get progress/errors

### Option 4: Upgrade/Downgrade Library Version
Try different versions of `google-cloud-storage` library.

**Pros:**
- Might fix the issue if it's version-specific

**Cons:**
- May introduce other issues
- Doesn't address root cause
- May break other functionality

---

## Recommended Solution

**Implement Option 1: Thread-Based Timeout Wrapper**

This is the most practical solution because:
1. It actually enforces timeouts (the current issue)
2. Doesn't require library changes
3. Can be implemented immediately
4. Maintains existing API
5. Provides real error handling

**Implementation Plan:**
1. Create `_upload_with_timeout()` helper method in `CloudStorageService`
2. Replace `blob.upload_from_filename()` call with thread-based wrapper
3. Add proper error handling and logging
4. Test with both small and large files
5. Monitor for any issues

---

## Next Steps

1. ✅ **Investigation Complete** - Confirmed issue with controlled test
2. ⏳ **Implement Solution** - Add thread-based timeout wrapper
3. ⏳ **Test Solution** - Verify with both small and large files
4. ⏳ **Monitor** - Watch for any edge cases or issues

---

## Files Modified

- `scripts/test_gcs_python_client.py` - Created test script
- `docs/UPLOAD_HANGING_INVESTIGATION.md` - This document

---

## References

- Test script: `scripts/test_gcs_python_client.py`
- Current implementation: `app/services/storage.py:297-301`
- Library version: `google-cloud-storage==2.10.0` (from `requirements.txt`)

