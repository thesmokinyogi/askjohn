# Design Discussion: Request Queuing Implementation

## Current System Analysis

### Job ID Usage
**Where job_id is used:**
1. **Display (UI):** Shows truncated job_id (last part after `/`) - e.g., "Job ID: v2-abc123"
2. **Internal storage:** Key in `jobs.json` dictionary
3. **API endpoints:** 
   - `/api/v1/jobs/{job_id}/status` - Status check
   - `/api/v1/jobs/{job_id}` - Delete job
4. **Google API:** Real job_id is Google operation name (e.g., `projects/123/locations/us-central1/operations/v2-abc123`)

**Current pattern:** Job ID = Google operation name (created when job is submitted to Google)

### Metadata Discovery Fallback
**Current behavior:**
- If discovery fails after retries: `_CACHE_LOADED = False`
- `_get_model_region_config()` falls back to hardcoded minimal config
- System continues operating with fallback

**User requirement:** "When fallback handling is invoked, that's when the job can leave the queue"
- So: If metadata discovery fails → fallback is used → process queued jobs
- If metadata discovery succeeds → process queued jobs with real metadata

## Design Questions & Implications

### 2. Job ID Design Choice

**Option A: Stable Internal ID (Recommended)**
- Create UUID when job is queued: `job_id = f"job-{uuid4()}"`
- Store Google operation ID separately: `google_operation_id` (set when processed)
- **Pros:**
  - Stable ID from creation to completion
  - No ID changes needed
  - Simple to implement
- **Cons:**
  - Two IDs to track (internal + Google)
  - UI needs to handle display (show "Job Pending" or filename for queued)

**Option B: Update Job ID When Processed**
- Create temp ID when queued: `job_id = f"queued-{uuid4()}"`
- Update to real Google operation ID when processed
- **Pros:**
  - Single ID (eventually becomes real Google ID)
- **Cons:**
  - Need to update key in `jobs.json` (delete old, create new)
  - More complex (atomic update required)
  - Risk of race conditions

**Recommendation: Option A** - Stable internal ID with separate Google operation ID field

### 4. Job Linking Design Choice

**Option A: Update Existing Job Record (Recommended)**
- Create job record immediately when queued (status="queued")
- When processed, update same record:
  - Set `google_operation_id` field
  - Update `status` to "processing"
  - Keep same `job_id`
- **Pros:**
  - Single job record throughout lifecycle
  - Clean, simple
  - Jobs page shows job from creation
- **Cons:**
  - Need to handle fields that aren't available yet (duration, cost, etc.)
  - Need to distinguish "queued" vs "processing" states

**Option B: Create New Job Record, Link Old**
- Create queued job record with temp ID
- When processed, create new job record with real Google ID
- Link them: `queued_job_id` field in new record
- **Pros:**
  - Clear separation of queued vs processed
- **Cons:**
  - Two records for same logical job
  - Jobs page might show duplicates
  - More complex queries

**Option C: Replace Queued Job**
- Create queued job record
- When processed, delete queued record, create new with real ID
- **Pros:**
  - Only one record at a time
- **Cons:**
  - Job disappears from jobs page during transition
  - Risk of losing queued job if processing fails
  - Complex atomic operation

**Recommendation: Option A** - Update existing job record

### Implications for Services/UI

**What services need to handle:**
1. **Jobs API (`/api/v1/jobs`):**
   - Must return queued jobs (status="queued")
   - Must handle missing fields gracefully (duration=0, cost=0, etc.)

2. **Status Check (`/api/v1/jobs/{job_id}/status`):**
   - Must handle queued jobs (return status="queued", message)
   - Must NOT call Google API for queued jobs (no google_operation_id yet)

3. **UI (Jobs Page):**
   - Display queued jobs with minimal info:
     - Status: "Queued" or "Pending"
     - Filename
     - Submitted time
     - Message: "Waiting for system initialization"
   - Hide/disable fields that don't exist yet:
     - Duration (show "—" or "Pending")
     - Cost (show "—" or "Pending")
     - Model (can show if provided, or "Pending")

4. **UI (Transcribe Page):**
   - Show job_id as "Job Pending" or filename
   - Display message from response
   - Poll status endpoint (which will return queued status)

5. **Orchestrator:**
   - When processing queued job, must:
     - Find existing job record by job_id
     - Update it with google_operation_id
     - Update status to "processing"
     - NOT create new job record

### 5. Status Check Endpoint Implications

**Current behavior:**
- `/api/v1/jobs/{job_id}/status` calls `orchestrator.check_job_status()`
- Which calls Google API using `job_id` as operation name

**For queued jobs:**
- No `google_operation_id` yet
- Cannot call Google API
- Must return queued status directly from job record

**Design:**
```python
# In check_job_status endpoint:
job = job_storage.get_job(job_id)
if job["status"] == "queued":
    # Return queued status directly - don't call Google API
    return {
        "job_id": job_id,
        "status": "queued",
        "message": "System is initializing. Your job will start automatically once ready.",
        ...
    }
else:
    # Normal flow - call Google API
    ...
```

### 6. Metadata Discovery Failure Handling

**Current fallback:**
- If discovery fails: `_CACHE_LOADED = False`
- `_get_model_region_config()` returns hardcoded fallback
- System continues operating

**User requirement:** "When fallback handling is invoked, that's when the job can leave the queue"

**Design:**
```python
# In discover_metadata_background():
if cache_loaded:
    _METADATA_READY = True
    # Process queue
else:
    # Discovery failed - use fallback
    _METADATA_READY = True  # Still ready, just using fallback
    # Process queue (will use fallback config)
```

**Implication:** `_METADATA_READY` means "ready to process" (either with real metadata or fallback), not "has real metadata"

## Recommended Design

1. **Job ID:** Stable UUID (`job-{uuid4()}`) created immediately when queued
2. **Job Record:** Create immediately when queued, update when processed
3. **Google Operation ID:** Separate field `google_operation_id` (set when processed)
4. **Status Check:** Handle queued jobs specially (don't call Google API)
5. **UI:** Show minimal info for queued jobs, handle missing fields gracefully
6. **Metadata Ready:** `True` when either real metadata loaded OR fallback is active

## Open Questions

1. **Job ID Display:** For queued jobs, show "Job Pending" or the UUID? (User said "job pending" with filename)
2. **Queue Reference:** Should we store `queue_request_id` in job record to link back to queue?
3. **Error Handling:** If queue processor fails to process a queued job, should it:
   - Retry automatically?
   - Mark job as failed?
   - Keep in queue for manual retry?

