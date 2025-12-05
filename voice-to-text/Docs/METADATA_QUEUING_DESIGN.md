# Design: Request Queuing for Metadata Discovery

## Problem
User wants transcription requests to be queued (not use fallback) until metadata discovery completes. Library and job pages should work immediately.

## Requirements
1. **Transcription requests**: Queue until metadata ready, return graceful message
2. **Library page**: Works immediately (doesn't need metadata)
3. **Jobs page**: Works immediately (doesn't need metadata)
4. **Transcribe page**: Accepts job, shows message that it's queued
5. **No fallback configs**: Wait for real metadata

## Architecture

### Components Needed
1. **Metadata Readiness Flag**: Track when discovery completes
2. **Request Queue**: Store pending transcription requests
3. **Queue Processor**: Process queue once metadata ready
4. **Status Messages**: Return appropriate messages to users

### Request Flow

**Before Metadata Ready:**
```
User submits transcription
  → Check metadata_ready flag (False)
  → Queue request (file + metadata)
  → Return: {"status": "queued", "message": "System initializing, your job will start shortly"}
  → User sees message on transcribe page
```

**After Metadata Ready:**
```
Metadata discovery completes
  → Set metadata_ready = True
  → Process queued requests
  → Submit each transcription normally
```

**During Processing:**
```
User submits transcription
  → Check metadata_ready flag (True)
  → Process immediately (normal flow)
```

### Implementation Plan

1. **Create Metadata Readiness Service**
   - Module-level flag: `_METADATA_READY = False`
   - Function: `is_metadata_ready() -> bool`
   - Function: `set_metadata_ready()`

2. **Create Request Queue**
   - `asyncio.Queue` for pending requests
   - Store: (file_path, filename, model, request_id)
   - Thread-safe queue

3. **Modify Transcription Endpoint**
   - Check `is_metadata_ready()` before processing
   - If not ready: queue request, return queued status
   - If ready: process normally

4. **Modify Discovery Completion**
   - When discovery completes: `set_metadata_ready(True)`
   - Start background task to process queue

5. **Queue Processor**
   - Background task that processes queue
   - Submits each transcription normally
   - Handles errors gracefully

### Edge Cases
- Discovery fails: Need timeout/retry mechanism
- Queue grows large: Should have max size
- Server restarts: Queue is lost (acceptable - user can resubmit)
- File cleanup: Queued files need to persist until processed

### User Experience
- **Transcribe page**: Shows "System initializing, your job will start shortly"
- **Jobs page**: Shows queued jobs with status "queued"
- **Library page**: Works normally (no dependency on metadata)

