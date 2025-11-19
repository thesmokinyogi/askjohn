# Server Restart Impact Analysis

## Problem Statement

**The code is NOT re-entrant.** If the server restarts during a job submission, the following occurs:

## Consequences of Server Restart During Job Submission

### 1. **File Upload to Temp File** (Lines 332-344 in `app/main.py`)
- **Status**: Request is lost
- **Impact**: 
  - Client (browser) gets connection error
  - Temp file may be left behind (if `finally` block doesn't execute)
  - No cleanup occurs if server is killed forcefully

### 2. **GCS Upload** (Line 367 in `app/main.py`)
- **Status**: Upload is interrupted mid-stream
- **Impact**:
  - Connection to GCS is lost
  - **No partial upload saved** (we're not using resumable uploads with resume capability)
  - GCS may have a partial blob, but it's incomplete and unusable
  - Client gets connection error
  - No job record created

### 3. **Job Submission to Google** (Lines 402-411)
- **Status**: Request is lost
- **Impact**:
  - No job submitted to Google
  - No job_id returned to client
  - Client gets connection error

### 4. **Job Record Creation** (Lines 417-425)
- **Status**: Request is lost
- **Impact**:
  - No job record in `jobs.json`
  - No way to track the job
  - Client gets connection error

### 5. **Temp File Cleanup** (Lines 456-463)
- **Status**: `finally` block may not execute if server is killed
- **Impact**:
  - Temp files accumulate in `/tmp`
  - Disk space leak
  - Manual cleanup required

## Current Evidence

From logs:
- Server started: 16:56:39
- Upload started: 17:06:15
- **No job record created** (confirmed by checking `jobs.json`)
- **Upload was interrupted** (no completion log)

## Architectural Issues

### 1. **Synchronous Blocking Operations**
- GCS upload is synchronous and blocking
- If it takes 2+ minutes, server restart kills it
- No way to resume

### 2. **No Transactional Guarantees**
- Job submission is not atomic
- If server dies between GCS upload and job record creation, we have:
  - File in GCS (orphaned)
  - No job record
  - No way to clean up

### 3. **No Idempotency**
- Retrying the same file creates a new job
- No deduplication
- Could lead to duplicate charges

### 4. **Temp File Cleanup Not Guaranteed**
- `finally` block only executes if Python process exits normally
- Force kill (`kill -9`) bypasses `finally`
- Temp files accumulate

## Recommendations

### Short-term (Immediate)
1. **Don't restart server during active uploads**
   - Check for active requests before restarting
   - Wait for uploads to complete

2. **Add temp file cleanup on startup**
   - Scan `/tmp` for orphaned temp files
   - Clean up files older than 1 hour

### Medium-term (Architectural)
1. **Make uploads resumable**
   - Use GCS resumable upload API
   - Store upload session ID
   - Can resume after server restart

2. **Add job submission idempotency**
   - Check if file already uploaded (hash-based)
   - Return existing job_id if found
   - Prevent duplicate submissions

3. **Make job submission atomic**
   - Create job record BEFORE uploading to GCS
   - Mark as "uploading" status
   - Update to "queued" after successful upload
   - Clean up on failure

4. **Add health check endpoint**
   - Check for active uploads
   - Prevent restart if uploads in progress
   - Graceful shutdown with timeout

### Long-term (Production-Ready)
1. **Use async job queue** (Cloud Tasks, Celery, etc.)
   - Upload happens in background worker
   - Server restart doesn't affect upload
   - Automatic retry on failure

2. **Use database transactions**
   - Atomic job creation
   - Rollback on failure
   - No orphaned records

3. **Implement proper cleanup**
   - Periodic cleanup job
   - Remove orphaned GCS files
   - Remove old temp files

## Current State Assessment

**Is the code re-entrant?** **NO**

**Can we safely restart during uploads?** **NO**

**What happens if we do?**
- Client gets connection error
- Upload is lost
- No job created
- Temp files may accumulate
- Orphaned GCS files possible

## Action Items

1. ✅ Document the issue (this document)
2. ⏳ Add temp file cleanup on startup
3. ⏳ Add health check endpoint
4. ⏳ Implement graceful shutdown
5. ⏳ Make uploads resumable (longer-term)

