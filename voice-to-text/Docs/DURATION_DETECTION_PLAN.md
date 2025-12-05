# Duration Detection Optimization Plan

**Date:** 2025-11-19  
**Following:** Working Agreement - Observe Before Implement

---

## Step 1: Observe Current System

### Current Flow

1. **Frontend (`index.html`):**
   - User drops file → `detectDuration(file)` called
   - Creates `FormData`, uploads to `/api/detect-duration` (separate HTTP request)
   - Later, user clicks "Transcribe" → creates NEW `FormData`, uploads to `/transcribe` (separate HTTP request)
   - **Key:** These are TWO SEPARATE file uploads of the same file

2. **Backend `/api/detect-duration`:**
   - Receives `UploadFile` (stream)
   - Currently: Streams entire file to temp file on disk
   - Calls `analyze_file(temp_path)` which uses:
     - `ffprobe` for video files (reads headers only)
     - `mutagen` for audio files (can read headers efficiently)

3. **Backend `/transcribe`:**
   - Receives `UploadFile` (separate stream, separate request)
   - Streams entire file to temp file
   - Uploads to GCS, processes, transcribes

### Key Observations

✅ **Good news:** `/api/detect-duration` and `/transcribe` are separate requests, so:
- Reading from one doesn't affect the other
- We can optimize `/api/detect-duration` independently
- No need to "reset" or "seek" - each request gets a fresh stream

❌ **Problem:** We're writing entire file to disk in `/api/detect-duration` when we only need:
- Video: First ~1KB (headers)
- MP3: First ~64KB (ID3v2) + last 128 bytes (ID3v1)
- Other audio: First ~64KB (headers)

---

## Step 2: Research Questions

### Q1: Can FastAPI UploadFile be read partially?

**Hypothesis:** Yes, `await file.read(chunk_size)` reads only that chunk.

**Need to verify:**
- Can we read first chunk, then continue reading?
- Can we track file size while reading?
- What happens if we don't read the entire file?

**Answer needed:** ✅ YES - `file.read()` reads incrementally, we can read first chunk, track size, read last chunk for MP3.

### Q2: Can mutagen work with partial MP3 files?

**Hypothesis:** 
- Mutagen can read ID3v2 tags from beginning (first ~64KB)
- Mutagen can read ID3v1 tags from end (last 128 bytes)
- But mutagen may need to parse MP3 frame headers to calculate duration accurately

**Need to verify:**
- Does mutagen need full file for duration calculation?
- Can we create a minimal file (first chunk + last chunk) that mutagen can parse?
- What happens if we pass a partial file to `MutagenFile()`?

**Research needed:** Test with actual MP3 files - try reading first 64KB + last 128 bytes, create temp file, see if mutagen can extract duration.

### Q3: Can ffprobe work with partial video files?

**Hypothesis:** ✅ YES - ffprobe reads headers only, doesn't need full file.

**Confidence:** HIGH - ffprobe is designed to read metadata without processing entire file.

**Verification needed:** Test with partial video file (first 64KB).

### Q4: What about other audio formats?

**Formats to consider:**
- **WAV:** Header at beginning (~44 bytes), should work with first chunk
- **FLAC:** Metadata block at beginning, should work with first chunk
- **M4A:** Similar to MP4, headers at beginning, should work with first chunk
- **OGG:** Headers at beginning, should work with first chunk

**Hypothesis:** All should work with first 64KB chunk.

---

## Step 3: System-Wide Consequences

### Impact Analysis

#### ✅ Safe Changes (No Breaking Changes)

1. **Video files (MOV, MP4):**
   - Read only first 64KB
   - Use `ffprobe` on partial file
   - **Impact:** ✅ None - ffprobe works with headers only
   - **Risk:** 🟢 LOW

2. **Audio files (WAV, FLAC, M4A, OGG):**
   - Read only first 64KB
   - Use `mutagen` on partial file
   - **Impact:** ✅ None - headers are at beginning
   - **Risk:** 🟢 LOW

#### ⚠️ Needs Testing (Potential Issues)

3. **MP3 files:**
   - Read first 64KB (ID3v2) + last 128 bytes (ID3v1)
   - Create minimal temp file
   - Use `mutagen` on partial file
   - **Impact:** ⚠️ UNKNOWN - need to test if mutagen can calculate duration from partial file
   - **Risk:** 🟡 MEDIUM - mutagen may need full file for accurate duration

### Fallback Strategy

**If partial file doesn't work:**
- Try partial file first (optimized path)
- If metadata extraction fails, fall back to full file
- Log which path was used for monitoring

**Implementation:**
```python
try:
    # Try optimized path (partial file)
    metadata = extract_from_partial_file(file, filename)
except Exception as e:
    logger.warning(f"Partial file extraction failed, falling back to full file: {e}")
    # Fall back to current approach (full file)
    metadata = extract_from_full_file(file, filename)
```

---

## Step 4: Implementation Plan

### Phase 1: Research & Validation (DO THIS FIRST)

1. **Test mutagen with partial MP3 files:**
   - Create test script that:
     - Reads first 64KB of MP3
     - Reads last 128 bytes of MP3
     - Creates temp file with just these chunks
     - Tries `mutagen.MP3()` on partial file
     - Compares duration with full file
   - **Goal:** Verify if mutagen can extract duration from partial file

2. **Test ffprobe with partial video files:**
   - Create test script that:
     - Reads first 64KB of video file
     - Creates temp file with just this chunk
     - Tries `ffprobe` on partial file
     - Compares metadata with full file
   - **Goal:** Verify ffprobe works with partial files (should work, but verify)

3. **Test other audio formats:**
   - Test WAV, FLAC, M4A, OGG with first 64KB
   - **Goal:** Verify all formats work with partial files

### Phase 2: Implementation (AFTER VALIDATION)

**Only proceed if Phase 1 validates the approach.**

1. **Create helper function for partial file extraction:**
   ```python
   async def extract_metadata_partial(file: UploadFile, filename: str) -> Dict:
       """Extract metadata using only necessary file chunks."""
       # Detect file type
       # Read appropriate chunks
       # Create minimal temp file
       # Extract metadata
       # Return metadata
   ```

2. **Update `/api/detect-duration` endpoints:**
   - Try partial file extraction first
   - Fall back to full file if needed
   - Log which path was used

3. **Update `/api/v1/transcription.py` endpoint:**
   - Same approach

### Phase 3: Testing

1. **Test with various file types:**
   - Video: MOV, MP4
   - Audio: MP3, WAV, FLAC, M4A, OGG
   - Large files (500MB+)
   - Small files (<1MB)

2. **Verify accuracy:**
   - Compare duration from partial vs full file
   - Ensure no regressions

3. **Monitor performance:**
   - Measure disk I/O reduction
   - Measure time savings

---

## Step 5: Risk Assessment

### Risks

1. **Mutagen may not work with partial MP3 files:**
   - **Probability:** 🟡 MEDIUM
   - **Impact:** 🟡 MEDIUM (fallback to full file)
   - **Mitigation:** Fallback strategy, extensive testing

2. **Edge cases in file formats:**
   - Some MP3s may have unusual structure
   - Some video files may have metadata at end
   - **Probability:** 🟢 LOW
   - **Impact:** 🟡 MEDIUM (fallback handles it)
   - **Mitigation:** Fallback strategy, test with various files

3. **File size tracking complexity:**
   - Need to track total size while reading chunks
   - **Probability:** 🟢 LOW
   - **Impact:** 🟢 LOW (simple counter)
   - **Mitigation:** Simple implementation

### Benefits

1. **Massive disk I/O reduction:**
   - 500MB video → 64KB (99.987% reduction)
   - 100MB MP3 → ~64KB (99.936% reduction)

2. **Faster metadata extraction:**
   - Less disk I/O = faster processing
   - Especially for large files

3. **Lower memory pressure:**
   - Less data written to disk
   - Less temp file cleanup needed

---

## Step 6: Decision Points

### Decision 1: Proceed with optimization?

**Criteria:**
- ✅ Phase 1 validation passes
- ✅ Fallback strategy works
- ✅ No breaking changes

**Decision:** Proceed if all criteria met.

### Decision 2: Which formats to optimize?

**Options:**
- **A:** All formats (video + all audio)
- **B:** Video only (safest, biggest win)
- **C:** Video + non-MP3 audio (MP3 is tricky)

**Recommendation:** Start with **Option B** (video only), then expand if successful.

**Rationale:**
- Video files are largest (biggest win)
- ffprobe definitely works with headers
- Lowest risk
- Can optimize audio later

---

## Step 7: Next Steps

### Immediate Actions

1. ✅ **Create test script** to validate mutagen with partial MP3 files
2. ✅ **Create test script** to validate ffprobe with partial video files
3. ✅ **Run tests** with various file types
4. ✅ **Document results** in test results file

### After Validation

5. ⏸️ **Implement optimization** (only if validation passes)
6. ⏸️ **Add fallback strategy**
7. ⏸️ **Update both endpoints**
8. ⏸️ **Test thoroughly**
9. ⏸️ **Monitor in production**

---

## Summary

**Current State:** Writing entire file to disk for metadata extraction (wasteful)

**Goal:** Read only necessary chunks (headers) for metadata extraction

**Approach:**
1. Research first (validate approach)
2. Implement with fallback
3. Test thoroughly
4. Monitor results

**Risk Level:** 🟡 MEDIUM (with fallback strategy)

**Benefit:** 🟢 HIGH (massive disk I/O reduction)

**Recommendation:** Proceed with research/validation first, then implement if validated.

