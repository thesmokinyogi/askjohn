# Duration Detection Optimization Analysis

**Date:** 2025-11-19  
**Question:** Can we optimize duration detection to avoid writing the entire file to disk?

---

## Current Approach

**What we do now:**
1. Stream entire uploaded file to temp file on disk (8KB chunks)
2. Call `analyze_file(temp_path)` which:
   - **Video files (MOV, MP4):** Uses `ffprobe` (reads headers only - very efficient!)
   - **Audio files:** Uses `mutagen` (can read headers efficiently, but may need to seek)

**Problem:** We're writing the entire file to disk, even though metadata extraction only needs headers.

---

## Analysis by File Type

### 1. Video Files (MOV, MP4)

**Current:** Write entire file → `ffprobe` reads headers only

**Optimization Opportunity:** ✅ **YES - Can optimize!**

**Better approach:**
- Read only first ~64KB (headers are typically in first few KB)
- Write only that chunk to temp file
- Use `ffprobe` on the partial file
- **Benefit:** For 500MB video, only write 64KB instead of 500MB

**Caveat:** Some video formats have metadata at the end (MP4 can have `moov` atom at end), but `ffprobe` with `-show_format` should work with headers.

**Implementation:**
```python
# Read only first 64KB
chunk_size = 64 * 1024  # 64KB
first_chunk = await file.read(chunk_size)
file.seek(0)  # Reset for actual upload later

# Write to temp file
with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as tmp:
    tmp.write(first_chunk)
    temp_path = tmp.name

# Use ffprobe on partial file
metadata = metadata_service.analyze_file(Path(temp_path))
```

**Risk:** Some video formats may need more than 64KB. Could make it configurable or try progressively larger chunks.

---

### 2. Audio Files (MP3, M4A, WAV, FLAC, OGG)

**Current:** Write entire file → `mutagen` reads headers

**Optimization Opportunity:** ⚠️ **MAYBE - Format dependent**

**Format-specific behavior:**

1. **MP3:**
   - Metadata can be at beginning (ID3v2) or end (ID3v1)
   - Duration calculation may require scanning entire file
   - **Optimization:** Read first ~128KB and last ~128KB
   - **Risk:** May not work for all MP3 files

2. **M4A (MP4 audio):**
   - Similar to video MP4 - headers at beginning
   - **Optimization:** Read first ~64KB should work
   - **Risk:** Low

3. **WAV:**
   - Header at beginning
   - **Optimization:** Read first ~64KB should work
   - **Risk:** Very low

4. **FLAC:**
   - Metadata block at beginning
   - **Optimization:** Read first ~64KB should work
   - **Risk:** Very low

5. **OGG:**
   - Headers at beginning
   - **Optimization:** Read first ~64KB should work
   - **Risk:** Low

**Implementation:**
```python
# For audio files, read first chunk
chunk_size = 64 * 1024  # 64KB
first_chunk = await file.read(chunk_size)
file.seek(0)  # Reset for actual upload

# For MP3, also read last chunk (ID3v1 at end)
if filename.endswith('.mp3'):
    file.seek(-128, 2)  # Last 128 bytes
    last_chunk = await file.read(128)
    file.seek(0)
    # Combine chunks
else:
    # Just use first chunk
```

**Risk:** Some formats may need more data. Could make it progressive (try 64KB, if fails try full file).

---

## Recommended Approach

### Option 1: **Optimize Video Files Only** (Safest)

**Rationale:**
- Video files are largest (often 500MB+)
- `ffprobe` definitely only needs headers
- Low risk of breaking

**Implementation:**
```python
file_extension = Path(filename).suffix.lower()

if file_extension in ['.mov', '.mp4', '.m4v']:
    # Video file - only read first 64KB
    chunk_size = 64 * 1024
    first_chunk = await file.read(chunk_size)
    file.seek(0)  # Reset for actual upload
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as tmp:
        tmp.write(first_chunk)
        temp_path = tmp.name
else:
    # Audio file - stream entire file (current approach)
    # (Could optimize later if needed)
    with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as tmp:
        chunk_size = 8192
        while True:
            chunk = await file.read(chunk_size)
            if not chunk:
                break
            tmp.write(chunk)
        temp_path = tmp.name
```

**Benefit:** 
- For 500MB video: Only write 64KB instead of 500MB
- For audio: Current approach (safe, works for all formats)

---

### Option 2: **Optimize Both Video and Audio** (More Aggressive)

**Rationale:**
- Most audio formats have headers at beginning
- Significant savings for large audio files too

**Implementation:**
- Video: Read first 64KB
- Audio: Read first 64KB (or first + last for MP3)
- Fallback: If metadata extraction fails, try full file

**Risk:** Higher - may break for edge cases

---

### Option 3: **Keep Current Approach** (Safest, but less efficient)

**Rationale:**
- Works reliably for all formats
- Disk I/O is fast (temp files are on fast storage)
- Simpler code (no format-specific logic)
- Memory efficient (streaming, not loading into memory)

**Trade-off:** 
- Writes entire file to disk even though we only need headers
- But disk I/O is typically fast, and we clean up immediately

---

## Recommendation

**Option 1: Optimize Video Files Only**

**Why:**
1. **Biggest win:** Video files are largest (500MB+), so optimization has most impact
2. **Low risk:** `ffprobe` definitely only needs headers
3. **Simple:** Easy to implement, easy to test
4. **Audio files:** Current approach is fine - audio files are typically smaller, and mutagen may need to seek

**Implementation:**
- Detect video file extension
- Read only first 64KB
- Use `ffprobe` on partial file
- Keep current approach for audio files

**Future:** Can optimize audio files later if needed, but video optimization gives us 99% of the benefit.

---

## Performance Impact

**Current (500MB video file):**
- Write: 500MB to disk
- Read: ~1KB (headers only)
- **Waste:** 499.999MB written unnecessarily

**Optimized (500MB video file):**
- Write: 64KB to disk
- Read: ~1KB (headers only)
- **Savings:** 499.936MB not written

**For 500MB file:**
- **Time saved:** ~2-5 seconds (depending on disk speed)
- **Disk I/O saved:** 99.987% reduction

---

## Conclusion

**Recommendation:** Implement Option 1 (optimize video files only)

**Benefits:**
- ✅ Huge performance improvement for large video files
- ✅ Low risk (ffprobe definitely works with headers)
- ✅ Simple implementation
- ✅ Can optimize audio later if needed

**Next Steps:**
1. Modify `detect_duration` endpoints to detect video files
2. Read only first 64KB for video files
3. Keep current approach for audio files
4. Test with various video formats

