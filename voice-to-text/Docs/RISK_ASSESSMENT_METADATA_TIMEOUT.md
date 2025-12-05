# Risk Assessment: Submitting Job While Metadata Detection May Be Processing

**Date:** 2025-11-19  
**Scenario:** User submits transcription job while `/api/detect-duration` request may still be processing on server after client timeout

---

## Risk Analysis

### ✅ **LOW RISK: Queue/Job Submission**

**Why it's safe:**
1. **Separate endpoints**: `/api/detect-duration` and `/transcribe` are completely independent
2. **No shared state**: No shared variables, locks, or resources between endpoints
3. **Async isolation**: FastAPI handles each request in its own async context
4. **No queue dependency**: `/transcribe` doesn't depend on metadata detection completing

**Conclusion:** Job submission will work normally, regardless of metadata detection status.

---

### ⚠️ **MEDIUM RISK: Resource Contention**

**Potential issues:**
1. **Memory usage**: `/api/detect-duration` reads entire file into memory (`audio_bytes = await file.read()`)
   - Large video file (500MB+) = 500MB+ in memory
   - If client disconnects but server continues, memory is held until processing completes
   
2. **CPU usage**: Metadata extraction (mutagen) can be CPU-intensive for large files
   - May slow down other requests if server is resource-constrained
   
3. **No explicit disconnect handling**: FastAPI/Uvicorn should detect client disconnects, but:
   - `await file.read()` may continue even after client disconnect
   - No explicit `ClientDisconnect` exception handling

**Impact:**
- **Low impact** if server has sufficient resources
- **Medium impact** if server is resource-constrained
- **No functional impact** - jobs will still process, just potentially slower

---

### 🔍 **Current Behavior**

**What happens when client aborts:**
1. Client: `AbortController.abort()` → fetch request cancelled
2. Browser: Stops waiting for response
3. Server: May continue processing (no explicit disconnect detection)
4. Server: Will complete metadata extraction, but response won't be sent (client disconnected)

**What happens when new job submitted:**
1. New request arrives at `/transcribe` endpoint
2. Completely independent from any ongoing `/api/detect-duration` processing
3. Processes normally, no interference

---

## Recommendations

### ✅ **Safe to Proceed**
- Job submission will work correctly
- No queue issues
- No functional problems

### ⚠️ **Potential Improvements** (Future)
1. **Add client disconnect detection** to `/api/detect-duration`:
   ```python
   from fastapi import Request
   
   async def detect_duration(request: Request, file: UploadFile = File(...)):
       # Check if client disconnected
       if await request.is_disconnected():
           return  # Early exit
   ```

2. **Stream file reading** instead of loading entire file into memory:
   - For very large files, process in chunks
   - Allows early exit if client disconnects

3. **Add timeout to server-side** metadata extraction:
   - Prevent runaway processing
   - Match client-side timeout

---

## Verdict

**✅ SAFE TO SUBMIT ANOTHER JOB**

- No queue issues
- No functional problems
- Only potential impact is resource usage (memory/CPU), which is acceptable for development
- Job will process normally

**Action:** Proceed with job submission. The metadata detection timeout is non-blocking and won't affect job processing.

