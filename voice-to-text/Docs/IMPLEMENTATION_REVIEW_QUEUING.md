# Implementation Review: Request Queuing

## Your Requirements
1. Queue "premature" requests (when metadata not ready)
2. Return graceful message
3. Don't use fallback configs - wait for real metadata
4. Library page should refresh (works - doesn't need metadata)
5. Jobs page should refresh (needs to show queued jobs)
6. Transcribe page should accept job and show message

## What I Implemented

### ✅ What Works
1. ✅ Requests are queued when metadata not ready
2. ✅ Graceful message returned: "System is initializing. Your job will start automatically once the system is ready."
3. ✅ No fallback configs used - waits for real metadata
4. ✅ Library page works (no dependency on metadata)
5. ✅ Queue processor processes requests when metadata ready

### ❌ Issues Found

#### Issue 1: Queued Jobs Don't Appear on Jobs Page
**Problem:** When a request is queued, I return `temp_job_id = f"queued-{request_id}"` but never create a job record in `jobs.json`. So:
- Job doesn't appear on jobs page
- Status check endpoint can't find it
- User can't see their queued job

**What Should Happen:**
- Create job record immediately when queued (status="queued")
- Store the request_id or queue reference
- Jobs page shows queued jobs
- When processed, update the job record with real job_id

#### Issue 2: Job ID Mismatch
**Problem:** Queued job gets temp_job_id "queued-{uuid}", but when processed, it gets a real Google operation ID. These don't match.

**What Should Happen:**
- Either: Keep the temp_job_id and update it when processed
- Or: Create job record with temp_job_id, then update with real job_id when processed

#### Issue 3: Queue Processor Doesn't Update Job Record
**Problem:** Queue processor calls `orchestrator.submit_transcription_from_file()` which creates a NEW job record, but doesn't update the existing queued job record.

**What Should Happen:**
- Link the queued job record to the new job record
- Or: Update the queued job record with the real job_id

#### Issue 4: Temp File Cleanup Logic
**Problem:** In transcription endpoint, I check `is_metadata_ready()` in the finally block to decide whether to clean up temp file. But this check happens AFTER the response is returned, so the logic might be wrong.

**What Should Happen:**
- Track whether request was queued (flag or check queue)
- Only clean up if NOT queued

## Questions I Should Have Asked

1. **Job Records:** Should queued jobs appear in jobs.json immediately, or only after processing starts?
2. **Job ID:** Should queued jobs have a temporary ID that gets replaced, or should we create a real job record immediately?
3. **Status Updates:** How should the job status transition from "queued" → "processing" → "complete"?
4. **Job Linking:** When a queued request is processed, should it:
   - Update the existing queued job record?
   - Create a new job record and link them?
   - Replace the queued job record?
5. **UI Display:** How should the jobs page display queued jobs? Same format as other jobs?
6. **Status Check:** Should `/api/v1/jobs/{queued-job-id}/status` work and return queued status?
7. **Error Handling:** What happens if metadata discovery fails? Keep queuing indefinitely?
8. **Queue Persistence:** Should the queue survive server restarts? (Currently it doesn't)

## Recommended Fixes

1. **Create job record when queued:**
   - Call `job_storage.create_job()` immediately with status="queued"
   - Store queue reference (request_id) in job record
   - Return real job_id (not temp)

2. **Update job record when processed:**
   - Queue processor should update existing job record
   - Link queued job to processed job
   - Update status from "queued" → "processing"

3. **Fix temp file cleanup:**
   - Track queued status explicitly
   - Only clean up if not queued

4. **Handle status checks:**
   - Status endpoint should handle queued jobs
   - Return appropriate message for queued status

