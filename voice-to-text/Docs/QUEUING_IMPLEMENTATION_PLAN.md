# Implementation Plan: Request Queuing

## Design Decisions Confirmed

1. **Job ID:** Stable UUID (`job-{uuid4()}`) created immediately when queued
2. **Job Record:** Create immediately when queued, update when processed
3. **Google Operation ID:** Separate field `google_operation_id` (set when processed)
4. **Status Check:** Handle queued jobs specially (don't call Google API)
5. **UI Display:** "Job Pending - {filename}" for queued jobs
6. **Queue Reference:** Store `queue_request_id` for future batch/retry support
7. **Error Handling:** Keep failed jobs in queue for manual retry
8. **Metadata Ready:** `True` when either real metadata loaded OR fallback is active

## Implementation Steps

### Step 1: Update Job Storage
- Add `google_operation_id` field (optional, set when processed)
- Add `queue_request_id` field (optional, set when queued)
- Ensure `create_job()` can handle missing fields (duration=0, cost=0, etc.)

### Step 2: Update Transcription Endpoint
- Create job record immediately when queued (status="queued")
- Use stable UUID: `job_id = f"job-{uuid4()}"`
- Store `queue_request_id` in job record
- Return job_id (not temp ID)
- Don't delete temp file (queue processor will handle)

### Step 3: Update Queue Service
- Store `job_id` in `QueuedRequest` (link back to job record)
- Update `enqueue()` to accept `job_id`

### Step 4: Update Queue Processor
- Find existing job record by `job_id` (from queued request)
- Update job record with `google_operation_id` when processed
- Update status from "queued" → "processing"
- If processing fails, keep job in queue (don't mark as failed)

### Step 5: Update Orchestrator
- Modify `submit_transcription_from_file()` to accept optional `job_id`
- If `job_id` provided, update existing job record instead of creating new
- Set `google_operation_id` field

### Step 6: Update Status Check Endpoint
- Check if job status is "queued"
- If queued, return status directly (don't call Google API)
- Return appropriate message

### Step 7: Update Metadata Discovery
- Set `_METADATA_READY = True` when either:
  - Real metadata loaded, OR
  - Fallback is active (discovery failed but fallback available)

### Step 8: Update UI (if needed)
- Jobs page: Handle queued jobs with minimal fields
- Transcribe page: Show "Job Pending - {filename}"

## Edge Cases

1. **Queue processor fails:** Job stays in queue, can be retried
2. **Server restart:** Queue is lost (in-memory), but job records persist
3. **Metadata discovery fails:** Fallback activates, queue processes
4. **Job record not found:** Queue processor should handle gracefully

