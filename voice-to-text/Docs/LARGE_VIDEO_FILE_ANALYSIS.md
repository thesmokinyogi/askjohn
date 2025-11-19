# Large Video File Handling Analysis

**Date:** 2025-11-18  
**Problem:** Need to handle ~10GB video files for transcription

---

## Current File Size Limit

### 500MB Limit - What It's Based On

**Current Configuration:**
- **Limit:** 500MB (configured in `app/config.py`)
- **Applied to:** All file uploads
- **Enforced in:** `app/services/orchestrator.py` → `validate_file()`

**Why 500MB?**
- **Not from Google API** - Google Speech-to-Text V2 batch recognition supports much larger files
- **Practical limit** - Based on:
  - HTTP upload timeouts
  - Memory constraints (loading entire file into memory)
  - GCS upload timeouts (currently 15 minutes = ~900 seconds)
  - User experience (large uploads can be slow/unreliable)

**Current GCS Upload:**
- Timeout: 900 seconds (15 minutes)
- At ~5 Mbps: 500MB = ~13 minutes ✅ (fits in timeout)
- At ~5 Mbps: 10GB = ~4.4 hours ❌ (exceeds timeout)

---

## Google Speech-to-Text V2 Actual Limits

### Batch Recognition Limits
- **Duration:** Up to 8 hours of audio
- **File Size:** No explicit limit documented (practical limits based on GCS)
- **Storage:** Files must be in GCS (not direct upload)

### GCS Limits
- **Object size:** Up to 5 TB per object
- **Upload methods:**
  - Simple upload: Up to 5 GB
  - Resumable upload: Up to 5 TB (recommended for large files)

---

## The Problem: 10GB Video Files

### Current System Limitations

1. **File Size Validation**
   - ❌ 10GB > 500MB limit → Rejected before processing

2. **HTTP Upload**
   - ❌ 10GB upload via HTTP form → Timeout likely
   - ❌ Browser may timeout or fail

3. **Memory Usage**
   - ❌ Loading 10GB into memory → Server may crash
   - ❌ Current code: `audio_bytes = await file.read()` loads entire file

4. **GCS Upload Timeout**
   - ❌ 15-minute timeout insufficient for 10GB
   - ❌ Would need resumable upload for large files

5. **Video File Processing**
   - ✅ System supports MP4/MOV (in allowed extensions)
   - ✅ `pydub` can extract audio from video
   - ⚠️ But extraction happens AFTER upload (wasteful)

---

## Solution Options

### Option 1: Extract Audio Before Upload (Recommended) ✅

**Approach:**
1. Client-side or server-side audio extraction
2. Upload only extracted audio (much smaller)
3. Transcribe audio

**Benefits:**
- ✅ Dramatically reduces file size (10GB video → ~100-500MB audio)
- ✅ Faster uploads
- ✅ Less storage cost
- ✅ No video processing needed

**Implementation:**
- **Client-side:** Use browser APIs (MediaRecorder, Web Audio API) to extract audio
- **Server-side:** Extract audio during upload processing (before GCS)

**Audio Size Estimates:**
- **90 min video → audio:**
  - MP3 @ 128kbps: ~86MB ✅
  - MP3 @ 192kbps: ~129MB ✅
  - MP3 @ 320kbps: ~216MB ✅
  - WAV uncompressed: ~950MB ⚠️ (may exceed limit)

**Challenges:**
- Client-side extraction requires browser support
- Server-side extraction requires processing large video files
- Need to handle extraction errors gracefully

---

### Option 2: Increase File Size Limit + Resumable Upload

**Approach:**
1. Increase limit to 10GB (or remove limit)
2. Implement resumable GCS upload
3. Stream file processing (don't load entire file into memory)
4. Extract audio during upload

**Benefits:**
- ✅ Supports large files directly
- ✅ No client-side processing needed
- ✅ Handles any file size

**Challenges:**
- ⚠️ Complex implementation (resumable upload, streaming)
- ⚠️ Still uploads entire video (wasteful)
- ⚠️ Higher storage costs
- ⚠️ Longer upload times

---

### Option 3: Two-Stage Upload (Hybrid)

**Approach:**
1. **Stage 1:** Upload video to GCS (resumable, async)
2. **Stage 2:** Server extracts audio from GCS video
3. **Stage 3:** Transcribe extracted audio

**Benefits:**
- ✅ Handles large files
- ✅ Extracts audio server-side (no client processing)
- ✅ Can process extraction asynchronously

**Challenges:**
- ⚠️ Most complex implementation
- ⚠️ Requires video processing infrastructure
- ⚠️ Still stores full video in GCS

---

### Option 4: Client-Side Audio Extraction (Best UX)

**Approach:**
1. User uploads video
2. Browser extracts audio using Web Audio API or MediaRecorder
3. Upload only audio file
4. Transcribe audio

**Benefits:**
- ✅ Fastest upload (only audio)
- ✅ No server processing needed
- ✅ Best user experience
- ✅ Works with current 500MB limit

**Challenges:**
- ⚠️ Requires browser support
- ⚠️ Client-side processing (may be slow for large videos)
- ⚠️ Need fallback for unsupported browsers

---

## Recommended Solution

### Phase 1: Server-Side Audio Extraction (Immediate)

**What to do:**
1. **Remove file size limit for video files** (or increase significantly)
2. **Extract audio from video during upload** (before GCS)
3. **Upload only audio to GCS** (much smaller)
4. **Keep 500MB limit for audio files** (prevents abuse)

**Implementation:**
```python
# In storage.py upload_audio()
if file_extension in ['.mp4', '.mov']:
    # Extract audio from video
    audio = AudioSegment.from_file(temp_path, format=file_extension[1:])
    # Export as MP3
    mp3_buffer = BytesIO()
    audio.export(mp3_buffer, format="mp3", bitrate="128k")
    audio_bytes = mp3_buffer.getvalue()
    filename = filename.rsplit('.', 1)[0] + '.mp3'
```

**Benefits:**
- ✅ Works immediately
- ✅ No client-side changes needed
- ✅ Handles large video files
- ✅ Reduces storage costs
- ✅ Faster transcription (smaller files)

**Limitations:**
- ⚠️ Server must process large video files (memory/CPU)
- ⚠️ Extraction may be slow for very large videos

---

### Phase 2: Streaming/Chunked Processing (Future)

**For very large files (>5GB):**
- Stream video processing (don't load entire file)
- Use resumable GCS upload
- Process in chunks if needed

---

## Implementation Plan

### Step 1: Video File Detection & Audio Extraction

**Modify `app/services/storage.py`:**
- Detect video files (MP4, MOV)
- Extract audio using `pydub` (already installed)
- Export as MP3 (compressed, compatible)
- Upload audio only

### Step 2: Update File Size Validation

**Modify `app/services/orchestrator.py`:**
- Different limits for video vs audio
- Video files: Higher limit (e.g., 10GB) or no limit
- Audio files: Keep 500MB limit

### Step 3: Update Configuration

**Modify `app/config.py`:**
- Add `max_video_file_size_mb` setting
- Default: 10GB (10240 MB) for video files
- Keep 500MB for audio files

---

## File Size Estimates

### Video Files (10GB)
- **Typical:** 1080p video, 90 minutes
- **Audio track:** Usually 1-2% of video size
- **Extracted audio (MP3 @ 128kbps):** ~86MB for 90 min
- **Extracted audio (MP3 @ 192kbps):** ~129MB for 90 min

### Audio Files
- **MP3 (128kbps, 90 min):** ~86MB ✅
- **MP3 (192kbps, 90 min):** ~129MB ✅
- **MP3 (320kbps, 90 min):** ~216MB ✅
- **WAV (uncompressed, 90 min):** ~950MB ❌ (exceeds 500MB)

---

## Recommendations

### Immediate (For 90-Minute MP3 Test)
- ✅ Current system should handle it (MP3 @ 128kbps = ~86MB < 500MB)
- ✅ No changes needed for this test

### Short-Term (For 10GB Video Files)
- ✅ **Implement server-side audio extraction**
- ✅ **Increase limit for video files** (or remove limit)
- ✅ **Extract audio before GCS upload**
- ✅ **Upload only audio** (saves storage, faster)

### Long-Term (For Very Large Files)
- Consider client-side extraction (better UX)
- Consider streaming processing (for >5GB files)
- Consider async processing pipeline

---

## Questions to Answer

1. **What's the typical video file size?** (10GB seems large - is this 4K video?)
2. **What's the audio bitrate in your videos?** (affects extracted audio size)
3. **Do you need the video file stored?** (or just audio for transcription)
4. **What's the typical video duration?** (affects processing time)

---

## Next Steps

1. **For 90-minute MP3 test:** Proceed as-is (should work)
2. **For 10GB video files:** Implement audio extraction
3. **Test with actual video file:** Verify extraction works correctly

**Ready to implement audio extraction?** I can add it to the storage service.

