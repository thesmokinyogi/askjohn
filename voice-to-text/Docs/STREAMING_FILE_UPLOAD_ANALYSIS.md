# Streaming File Upload Analysis

**Date:** 2025-11-18  
**Question:** Why do we load the entire file into memory? Is that necessary?

---

## Current Implementation

### How Files Are Currently Loaded

**Step 1: FastAPI Upload**
```python
# app/api/v1/transcription.py
audio_bytes = await file.read()  # ❌ Loads ENTIRE file into memory
```

**Step 2: Pass to Services**
```python
# app/services/orchestrator.py
gcs_uri, audio_metadata = self.storage_service.upload_audio(
    audio_bytes, filename  # ❌ Entire file in memory
)
```

**Step 3: Write to Temp File**
```python
# app/services/storage.py
with tempfile.NamedTemporaryFile(...) as temp_file:
    temp_file.write(audio_bytes)  # ❌ Writes from memory to disk
    temp_path = temp_file.name
```

**Step 4: Process & Upload**
```python
# Extract metadata, convert formats, etc.
# Then upload to GCS
blob.upload_from_string(audio_bytes, ...)  # ❌ Entire file in memory again
```

**Problem:** File is loaded into memory **twice**:
1. Once when reading from FastAPI (`file.read()`)
2. Once when uploading to GCS (`upload_from_string()`)

For a **10GB file**, this means:
- **20GB of memory usage** (10GB read + 10GB upload)
- **Server will likely crash** (out of memory)

---

## Is Loading Into Memory Necessary?

### Short Answer: **NO!**

We can stream the file directly to disk, then stream from disk to GCS, **never loading the entire file into memory**.

---

## Streaming Solution

### Option 1: Stream to Temp File, Then Stream to GCS ✅ (Recommended)

**How it works:**
1. **Stream upload to temp file** (FastAPI → disk, chunk by chunk)
2. **Extract audio from temp file** (pydub reads from disk, doesn't need full file in memory)
3. **Stream extracted audio to GCS** (disk → GCS, chunk by chunk)

**Benefits:**
- ✅ No memory loading (except small chunks)
- ✅ Works with any file size
- ✅ Server won't crash on large files
- ✅ Uses disk as buffer (plenty of space)

**Implementation:**
```python
# FastAPI endpoint
async def transcribe_audio(file: UploadFile, ...):
    # Stream to temp file (chunk by chunk)
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        async for chunk in file.stream():
            temp_file.write(chunk)
        temp_path = temp_file.name
    
    # Process from disk (pydub reads from file, not memory)
    result = orchestrator.submit_transcription_from_file(
        temp_path, filename, model
    )
    
    # Clean up
    os.unlink(temp_path)
```

```python
# Storage service
def upload_audio_from_file(self, file_path: str, filename: str):
    # Extract audio from video if needed (pydub reads from disk)
    if is_video_file(filename):
        audio = AudioSegment.from_file(file_path, format=...)
        # Export to temp MP3 file
        audio.export(mp3_path, format="mp3")
        file_path = mp3_path
    
    # Stream to GCS (from disk, not memory)
    blob.upload_from_filename(file_path)  # ✅ Streams from disk
```

---

### Option 2: Direct Stream to GCS (Advanced)

**How it works:**
1. Stream upload directly to GCS (FastAPI → GCS, no temp file)
2. Download from GCS for processing (if needed)

**Benefits:**
- ✅ No temp files
- ✅ Fastest upload

**Challenges:**
- ⚠️ Can't extract audio before upload (need video in GCS first)
- ⚠️ More complex (resumable upload, error handling)
- ⚠️ Need to download from GCS for audio extraction

**Not recommended** for video files (we want to extract audio first).

---

## FastAPI UploadFile Capabilities

### Current Usage (Memory Loading)
```python
audio_bytes = await file.read()  # ❌ Loads entire file
```

### Streaming Capability (Available)
```python
# FastAPI UploadFile has streaming support!
async for chunk in file.stream():
    # Process chunk by chunk
    temp_file.write(chunk)
```

**FastAPI `UploadFile` provides:**
- `.read()` - Loads entire file into memory ❌
- `.stream()` - Streams file chunk by chunk ✅
- `.file` - File-like object (can be used with streaming) ✅

---

## GCS Upload Methods

### Current (Memory Loading)
```python
blob.upload_from_string(audio_bytes, ...)  # ❌ Requires bytes in memory
```

### Streaming (Available)
```python
blob.upload_from_filename(file_path)  # ✅ Streams from disk
blob.upload_from_file(file_handle)   # ✅ Streams from file handle
```

**Google Cloud Storage supports:**
- `upload_from_string()` - Requires bytes in memory ❌
- `upload_from_filename()` - Streams from disk ✅
- `upload_from_file()` - Streams from file handle ✅
- Resumable upload - For very large files ✅

---

## pydub/AudioSegment Capabilities

### Current Usage
```python
# We write to temp file, then read it
temp_file.write(audio_bytes)  # Write from memory
audio = AudioSegment.from_file(temp_path)  # Read from disk
```

### Better Approach
```python
# Stream directly to temp file, then read
async for chunk in file.stream():
    temp_file.write(chunk)
audio = AudioSegment.from_file(temp_path)  # ✅ Reads from disk
```

**pydub can:**
- ✅ Read from file path (doesn't need full file in memory)
- ✅ Read from file handle (streaming)
- ✅ Process large files efficiently (uses ffmpeg, which streams)

---

## Recommended Implementation

### For Video Files (10GB)

**Step 1: Stream Upload to Temp File**
```python
# In FastAPI endpoint
with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
    async for chunk in file.stream(chunk_size=8192):  # 8KB chunks
        temp_file.write(chunk)
    temp_path = temp_file.name
```

**Step 2: Extract Audio from Temp File**
```python
# In storage service
if is_video_file(filename):
    # pydub reads from disk, doesn't load into memory
    audio = AudioSegment.from_file(temp_path, format="mp4")
    
    # Export to new temp file (streaming)
    mp3_path = temp_path + ".mp3"
    audio.export(mp3_path, format="mp3", bitrate="128k")
    
    # Use extracted audio file
    file_path = mp3_path
```

**Step 3: Stream to GCS**
```python
# Stream from disk to GCS (no memory loading)
blob.upload_from_filename(file_path, timeout=3600)  # 1 hour timeout for large files
```

**Memory Usage:**
- Upload: ~8KB chunks (minimal)
- Audio extraction: pydub/ffmpeg streams (minimal)
- GCS upload: Streams from disk (minimal)
- **Total: ~8-16KB in memory** (vs 20GB currently!)

---

## File Size Limits After Streaming

### With Streaming Implementation

**Current Limits (Memory-Based):**
- ❌ 500MB limit (practical)
- ❌ 10GB would crash server

**With Streaming:**
- ✅ **No practical limit** (disk space is the constraint)
- ✅ 10GB video files: Extract audio → ~100-500MB → Upload
- ✅ 50GB video files: Same process (just longer)
- ✅ Only limit: Disk space for temp files

**Recommended Limits:**
- **Video files:** 50GB (or no limit, just disk space)
- **Audio files:** 500MB (reasonable, audio is already extracted)

---

## Implementation Plan

### Phase 1: Stream Upload to Temp File

**Modify `app/api/v1/transcription.py`:**
```python
async def transcribe_audio(file: UploadFile, ...):
    # Stream to temp file instead of loading into memory
    with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as temp_file:
        async for chunk in file.stream(chunk_size=8192):
            temp_file.write(chunk)
        temp_path = temp_file.name
    
    try:
        # Process from file path instead of bytes
        result = orchestrator.submit_transcription_from_file(
            temp_path, file.filename, model
        )
    finally:
        # Clean up temp file
        if os.path.exists(temp_path):
            os.unlink(temp_path)
```

### Phase 2: Update Orchestrator

**Add new method:**
```python
def submit_transcription_from_file(
    self,
    file_path: str,
    filename: str,
    model: Optional[str] = None
) -> Dict[str, Any]:
    """Submit transcription from file path (streaming)."""
    # Get file size from disk
    file_size = Path(file_path).stat().st_size
    self.validate_file(filename, file_size)
    
    # Upload from file (streaming)
    gcs_uri, audio_metadata = self.storage_service.upload_audio_from_file(
        file_path, filename
    )
    # ... rest of workflow
```

### Phase 3: Update Storage Service

**Add new method:**
```python
def upload_audio_from_file(self, file_path: str, filename: str) -> Tuple[str, Dict]:
    """Upload audio from file path (streaming, no memory loading)."""
    # Extract audio if video
    if is_video_file(filename):
        audio = AudioSegment.from_file(file_path, format=...)
        mp3_path = file_path + ".mp3"
        audio.export(mp3_path, format="mp3", bitrate="128k")
        file_path = mp3_path
    
    # Stream to GCS from disk
    blob.upload_from_filename(file_path, timeout=3600)
    # ...
```

---

## Benefits of Streaming

### Memory Usage
- **Current:** 20GB for 10GB file (read + upload)
- **With streaming:** ~16KB (chunk buffer)
- **Savings:** 99.999% reduction

### Server Stability
- **Current:** Crashes on large files
- **With streaming:** Handles any file size (limited by disk)

### Performance
- **Current:** Must wait for entire upload before processing
- **With streaming:** Can start processing while uploading

### Scalability
- **Current:** Limited by server RAM
- **With streaming:** Limited by disk space (much larger)

---

## Questions

1. **Do you want me to implement streaming now?** (Before the 90-minute MP3 test)
2. **Or after the test?** (Test current system first, then improve)

**My recommendation:** Implement streaming **after** the 90-minute MP3 test, because:
- Current system should handle 90-min MP3 (~86MB)
- Streaming is a bigger change (needs testing)
- Better to test one thing at a time

But I can implement it now if you prefer!

---

## Summary

**Current Problem:**
- ❌ Loads entire file into memory (`file.read()`)
- ❌ Then loads again for GCS upload (`upload_from_string()`)
- ❌ 10GB file = 20GB memory usage = crash

**Solution:**
- ✅ Stream file to temp file (chunk by chunk)
- ✅ Extract audio from temp file (pydub reads from disk)
- ✅ Stream extracted audio to GCS (from disk)
- ✅ Never load entire file into memory

**Result:**
- ✅ Handles files of any size (limited by disk, not RAM)
- ✅ Server won't crash
- ✅ Much more efficient

**Is it necessary to load into memory?** **NO!** We can stream everything.

