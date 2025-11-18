# Manual Testing Guide

**Date:** 2025-11-18  
**Purpose:** Complete testing of refactored system with real files and UI

---

## Prerequisites

- ✅ Server running on `http://localhost:8000`
- ✅ Audio file ready for testing (MP3, WAV, M4A, OGG, or FLAC)
- ✅ Browser open to `http://localhost:8000`

---

## Test 1: Transcription Endpoint - File Upload

### Step 1.1: Test `/api/v1/transcribe` with File

**What to do:**
1. Open Terminal
2. Navigate to directory with your audio file
3. Run this command (replace `test_audio.mp3` with your file):

```bash
curl -X POST http://localhost:8000/api/v1/transcribe \
  -F "file=@test_audio.mp3" \
  -F "model=chirp_batch" \
  -v
```

**What to check:**
- [ ] Returns HTTP 200 status
- [ ] Response contains `job_id` field
- [ ] Response contains `status: "queued"`
- [ ] Response contains `model: "chirp_batch"`
- [ ] Response contains `estimated_cost` field
- [ ] Response contains `check_status_url` field

**Expected Response:**
```json
{
  "job_id": "projects/.../operations/...",
  "status": "queued",
  "filename": "test_audio.mp3",
  "model": "chirp_batch",
  "duration_minutes": 5.0,
  "estimated_cost": 0.02,
  "submitted_at": "2025-11-18T...",
  "check_status_url": "/api/v1/jobs/.../status"
}
```

**Report back:**
- Did it work? (Yes/No)
- What was the `job_id`? (copy it for next test)
- Any errors?

---

### Step 1.2: Test `/api/v1/detect-duration`

**What to do:**
Run this command:

```bash
curl -X POST http://localhost:8000/api/v1/detect-duration \
  -F "file=@test_audio.mp3" \
  -v
```

**What to check:**
- [ ] Returns HTTP 200 status
- [ ] Response contains `duration` (in seconds)
- [ ] Response contains `duration_minutes`
- [ ] Response contains `format` (e.g., "mp3")
- [ ] Response contains `sample_rate`
- [ ] Response contains `channels`

**Expected Response:**
```json
{
  "duration": 300.0,
  "duration_minutes": 5.0,
  "format": "mp3",
  "codec": "mp3",
  "sample_rate": 44100,
  "channels": 2,
  "bit_rate": "128k",
  "file_size": 5000000,
  "filename": "test_audio.mp3"
}
```

**Report back:**
- Did it work? (Yes/No)
- What duration was detected?
- Any errors?

---

## Test 2: End-to-End Workflow

### Step 2.1: Submit Transcription Job

**What to do:**
1. Use the same file from Test 1
2. Submit via UI or API (your choice)
3. **If using UI:** Go to `http://localhost:8000`, upload file, select model, click "Transcribe Audio"
4. **If using API:** Use the command from Test 1.1

**What to check:**
- [ ] Job submitted successfully
- [ ] Job ID returned
- [ ] Status is "queued" or "processing"

**Report back:**
- Job ID: `_________________`
- Initial status: `_________________`

---

### Step 2.2: Check Job Status (Polling)

**What to do:**
1. Take the `job_id` from Step 2.1
2. Replace `JOB_ID` in this command and run it:

```bash
curl http://localhost:8000/api/v1/jobs/JOB_ID/status | python3 -m json.tool
```

**What to check:**
- [ ] Status transitions: `queued` → `processing` → `complete`
- [ ] When status becomes "processing", check if `processing_started_at` is set
- [ ] When status is "complete", check:
  - [ ] `transcript` field present
  - [ ] `confidence` field present (or null for Chirp)
  - [ ] `actual_cost` field present
  - [ ] `completed_at` field present
  - [ ] `tier` field present (should be "batch" or "standard")

**Run this multiple times** (every 10-30 seconds) until job completes.

**Report back:**
- Final status: `_________________`
- Was `processing_started_at` set? (Yes/No)
- Was `tier` field present? (Yes/No, what value?)
- What was the `actual_cost`?
- What was the `confidence`? (or null?)

---

### Step 2.3: Verify Job in Jobs List

**What to do:**
Run this command:

```bash
curl http://localhost:8000/api/v1/jobs | python3 -m json.tool | grep -A 20 "YOUR_JOB_ID"
```

Or check the UI at `http://localhost:8000/jobs`

**What to check:**
- [ ] Job appears in list
- [ ] `tier` field is present
- [ ] `status` is "complete"
- [ ] `actual_cost` matches what you saw in status check
- [ ] `confidence` matches (or shows "N/A" for Chirp)

**Report back:**
- Job appears in list? (Yes/No)
- All fields correct? (Yes/No)
- Any issues?

---

### Step 2.4: Verify Job in Library

**What to do:**
Run this command:

```bash
curl http://localhost:8000/api/v1/library | python3 -m json.tool | grep -A 20 "YOUR_FILENAME"
```

Or check the UI at `http://localhost:8000/library`

**What to check:**
- [ ] Entry appears in library
- [ ] `transcript` field present
- [ ] `words` field present (if word timings enabled)
- [ ] `metadata` field present
- [ ] `cost` field matches `actual_cost`

**Report back:**
- Entry appears in library? (Yes/No)
- Transcript present? (Yes/No)
- Words/timings present? (Yes/No)
- Any issues?

---

## Test 3: UI Integration Testing

### Step 3.1: Main Transcription Page (`/`)

**What to do:**
1. Open `http://localhost:8000` in browser
2. Upload an audio file
3. Select a model (try `chirp_batch` and `long_batch`)
4. Click "Transcribe Audio"

**What to check:**
- [ ] File upload works
- [ ] Model selection works
- [ ] Cost estimate displays correctly
- [ ] Processing time estimate displays
- [ ] Progress indicator shows status
- [ ] When complete, transcript displays
- [ ] Confidence displays (or "N/A" for Chirp)
- [ ] Budget display updates correctly

**Report back:**
- All UI elements work? (Yes/No)
- Any visual issues?
- Any JavaScript errors in console? (F12 → Console)

---

### Step 3.2: Jobs Page (`/jobs`)

**What to do:**
1. Navigate to `http://localhost:8000/jobs`
2. Review the jobs list

**What to check:**
- [ ] Jobs list displays
- [ ] All jobs show confidence (or "N/A")
- [ ] Status indicators work
- [ ] Cost displays correctly
- [ ] Tier information visible (if displayed)
- [ ] Sorting/filtering works (if implemented)

**Report back:**
- Page loads correctly? (Yes/No)
- All jobs visible? (Yes/No)
- Any issues?

---

### Step 3.3: Library Page (`/library`)

**What to do:**
1. Navigate to `http://localhost:8000/library`
2. Review the library entries

**What to check:**
- [ ] Library entries display
- [ ] Filenames wrap correctly (not truncated)
- [ ] Transcript preview works
- [ ] Download buttons work
- [ ] Refresh button works
- [ ] All columns visible (no truncation)

**Report back:**
- Page loads correctly? (Yes/No)
- Filenames wrap correctly? (Yes/No)
- All columns visible? (Yes/No)
- Any issues?

---

## Test 4: Error Handling

### Step 4.1: Invalid File Type

**What to do:**
Try uploading a PDF or text file:

```bash
curl -X POST http://localhost:8000/api/v1/transcribe \
  -F "file=@test.pdf" \
  -F "model=chirp_batch" \
  -v
```

**What to check:**
- [ ] Returns HTTP 400 or 422
- [ ] Error message is clear
- [ ] Error format matches `ErrorResponse` model

**Report back:**
- Error returned? (Yes/No)
- Error message clear? (Yes/No)
- What was the error?

---

### Step 4.2: File Too Large

**What to do:**
Try uploading a file larger than 500MB (if you have one), or test the limit:

**What to check:**
- [ ] Returns HTTP 400
- [ ] Error message indicates file size limit

**Report back:**
- Error returned? (Yes/No)
- Error message clear? (Yes/No)

---

### Step 4.3: Invalid Job ID

**What to do:**
Try checking status of non-existent job:

```bash
curl http://localhost:8000/api/v1/jobs/invalid_job_id/status | python3 -m json.tool
```

**What to check:**
- [ ] Returns HTTP 404
- [ ] Error message is clear

**Report back:**
- Error returned? (Yes/No)
- Error message clear? (Yes/No)

---

## Test 5: Tier Tracking Verification

### Step 5.1: Submit Job with Different Tiers

**What to do:**
Submit two jobs:
1. One with `chirp_batch` model
2. One with `chirp_standard` model

**What to check:**
- [ ] Both jobs have `tier` field
- [ ] First job has `tier: "batch"`
- [ ] Second job has `tier: "standard"`

**Report back:**
- Both jobs have tier field? (Yes/No)
- Values correct? (Yes/No)

---

## Summary Report Template

After completing all tests, provide:

```
=== Manual Testing Summary ===

Test 1: Transcription Endpoints
- File upload: [PASS/FAIL]
- Duration detection: [PASS/FAIL]
- Issues: [list any]

Test 2: End-to-End Workflow
- Job submission: [PASS/FAIL]
- Status polling: [PASS/FAIL]
- Jobs list: [PASS/FAIL]
- Library integration: [PASS/FAIL]
- Issues: [list any]

Test 3: UI Integration
- Main page: [PASS/FAIL]
- Jobs page: [PASS/FAIL]
- Library page: [PASS/FAIL]
- Issues: [list any]

Test 4: Error Handling
- Invalid file type: [PASS/FAIL]
- File too large: [PASS/FAIL]
- Invalid job ID: [PASS/FAIL]
- Issues: [list any]

Test 5: Tier Tracking
- Batch tier: [PASS/FAIL]
- Standard tier: [PASS/FAIL]
- Issues: [list any]

Overall: [PASS/FAIL]
Critical Issues: [list any]
```

---

## Quick Start Commands

**If you just want to test quickly:**

1. **Submit a job:**
```bash
curl -X POST http://localhost:8000/api/v1/transcribe \
  -F "file=@your_audio.mp3" \
  -F "model=chirp_batch"
```

2. **Check status (replace JOB_ID):**
```bash
curl http://localhost:8000/api/v1/jobs/JOB_ID/status | python3 -m json.tool
```

3. **Check jobs list:**
```bash
curl http://localhost:8000/api/v1/jobs | python3 -m json.tool
```

4. **Check library:**
```bash
curl http://localhost:8000/api/v1/library | python3 -m json.tool
```

---

**Ready to start?** Begin with Test 1.1 and work through systematically. Report back after each test or when you encounter issues!

