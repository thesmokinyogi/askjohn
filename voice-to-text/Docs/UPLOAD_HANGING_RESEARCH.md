# Research: Upload Hanging Issue

## Research Phase

### 1. What Changed

**Before ProgressFile (Working):**
- Used `upload_from_filename()` directly
- Simple, reliable, streams from disk
- No progress tracking

**After ProgressFile (Current - Hanging):**
- Added `ProgressFile` wrapper class
- Switched to `upload_from_file()` with wrapper
- Wrapper only implements `read()` and `__getattr__`
- **Result:** Upload hangs, no progress logs, no completion

### 2. Root Cause Hypothesis

**The Problem:**
`upload_from_file()` likely calls methods on the file object that `ProgressFile` doesn't properly handle:
- `seek()` - to check file size or reset position
- `tell()` - to get current position  
- `readable()` - to check if file is readable
- File size checks via `os.path.getsize()` or similar
- Other file-like object protocol methods

**Why `__getattr__` Might Not Work:**
- Python's `__getattr__` is only called when attribute is NOT found
- If `upload_from_file()` checks for methods before calling them (e.g., `hasattr(file, 'seek')`), `__getattr__` might not be invoked correctly
- Some methods might need to be explicitly implemented for proper delegation

### 3. Google Cloud Storage SDK Behavior

**From Documentation:**
- `upload_from_filename()` - Opens file internally, handles all file operations
- `upload_from_file()` - Expects a file-like object with specific methods
- For resumable uploads, SDK may need to `seek()` to check file size or resume from position

**Key Insight:**
`upload_from_filename()` is simpler and more reliable because:
- SDK handles all file operations internally
- No need to wrap or delegate methods
- Automatically uses resumable uploads for large files
- Less prone to compatibility issues

### 4. Previous Working Implementation

**What We Know:**
- Before ProgressFile, we used `upload_from_filename()` directly
- It worked reliably
- ProgressFile was added to track upload speed/progress

**The Trade-off:**
- Progress tracking (nice-to-have) vs. Reliability (must-have)
- Current implementation: Progress tracking breaks reliability

### 5. Solution Options

**Option A: Remove ProgressFile, Use `upload_from_filename()`**
- ✅ Most reliable (proven to work)
- ✅ Simpler code
- ❌ No progress tracking
- ✅ Can add progress tracking later with different approach

**Option B: Fix ProgressFile to Implement All Required Methods**
- Implement `seek()`, `tell()`, `readable()`, etc. explicitly
- More complex, but keeps progress tracking
- ⚠️ Risk: May still have compatibility issues

**Option C: Use `upload_from_filename()` with `chunk_size` Parameter**
- ✅ Reliable (uses proven method)
- ✅ Can enable resumable uploads with `chunk_size` parameter
- ❌ No progress tracking (but can log start/end times)
- ✅ Best balance of reliability and features

### 6. Recommendation

**Option C: Use `upload_from_filename()` with `chunk_size`**
- Most reliable approach
- Enables resumable uploads for large files (>5MB)
- Can log start/end times for upload duration
- Can add progress tracking later with a different approach (e.g., GCS callbacks or separate monitoring)

**Why Not Option B:**
- Too risky - we don't know all methods `upload_from_file()` needs
- Could introduce more bugs
- Progress tracking is nice-to-have, reliability is must-have

---

**Status:** Research complete, ready for design phase

