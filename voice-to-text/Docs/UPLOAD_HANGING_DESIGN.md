# Design: Fix Upload Hanging Issue

## Design Phase

### Problem Statement
Upload hangs when using `ProgressFile` wrapper with `upload_from_file()`. No progress logs, no completion, no errors. Upload has been stuck for 6+ minutes.

### Root Cause
`ProgressFile` wrapper doesn't properly implement all methods that `upload_from_file()` needs (likely `seek()`, `tell()`, or other file-like object methods).

### Solution Design

**Approach:** Remove `ProgressFile` wrapper, use `upload_from_filename()` with `chunk_size` parameter

**Why This Works:**
1. `upload_from_filename()` is proven reliable (we used it before)
2. SDK handles all file operations internally (no wrapper needed)
3. `chunk_size` parameter enables resumable uploads for large files
4. Simpler code = fewer bugs

**Implementation:**
```python
# For files > 5MB, use resumable uploads with explicit chunk_size
if file_size > 5 * 1024 * 1024:  # > 5MB
    chunk_size = 8 * 1024 * 1024  # 8MB chunks
    blob.upload_from_filename(
        upload_file_path,
        content_type=content_type,
        timeout=timeout_seconds,
        chunk_size=chunk_size
    )
else:
    # Small files: use default
    blob.upload_from_filename(
        upload_file_path,
        content_type=content_type,
        timeout=timeout_seconds
    )
```

**What We Lose:**
- Real-time progress tracking (logs every 5 seconds)
- Upload speed monitoring during upload

**What We Keep:**
- Upload start/end logging
- Upload duration calculation
- Upload speed calculation (after completion)
- Reliability

**Future Enhancement:**
- Can add progress tracking later using GCS callbacks or separate monitoring thread
- For now, reliability > progress tracking

### Code Changes

**File:** `app/services/storage.py`
**Method:** `upload_audio_from_file()`
**Lines:** ~285-352

**Changes:**
1. Remove `ProgressFile` class definition (~30 lines)
2. Remove `upload_from_file()` call with wrapper
3. Replace with `upload_from_filename()` with `chunk_size` for large files
4. Keep upload timing and speed calculation (after completion)

**Lines Removed:** ~35 lines (ProgressFile class + wrapper usage)
**Lines Added:** ~15 lines (upload_from_filename with chunk_size)
**Net Change:** ~20 lines removed (simpler code)

### Testing Plan

1. **Test with current stuck upload:**
   - Cancel current upload (refresh page)
   - Wait for server reload
   - Submit same file again
   - Verify upload completes quickly (< 2 minutes for 33.7 MB)

2. **Test with different file sizes:**
   - Small file (< 5MB): Should use default chunk size
   - Large file (> 5MB): Should use 8MB chunks
   - Verify both complete successfully

3. **Verify logging:**
   - Upload start log
   - Upload completion log
   - Upload duration and speed (after completion)

### Risk Assessment

**Low Risk:**
- ✅ Using proven method (`upload_from_filename()`)
- ✅ Simple change (remove wrapper, use direct method)
- ✅ Easy to revert if needed
- ✅ No breaking changes to API

**Potential Issues:**
- ⚠️ No real-time progress (but we can add later)
- ⚠️ If upload still hangs, root cause is elsewhere (network/GCS)

### Alignment with Working Agreement

✅ **Observe Before Implement:** Documented observation
✅ **Research:** Investigated root cause, checked previous implementation
✅ **Design:** Created solution plan
⏳ **Review:** Need user approval before implementing
⏳ **Implement:** Only after approval

---

**Status:** Design complete, ready for review and approval

