# Tier Tracking Testing Plan

## Overview

This document outlines how to test the tier tracking feature that was just added. The tier field stores whether a job used 'batch' or 'standard' recognition tier, extracted from model names like `chirp_batch` or `chirp_standard`.

## Testing Approach

### 1. Unit Tests (Automated)

**File:** `tests/test_tier_extraction.py`

**Purpose:** Verify tier extraction logic works correctly for all model name patterns.

**Run:**
```bash
cd /Users/johncarosella/Documents/GitHub/askjohn/voice-to-text
python -m pytest tests/test_tier_extraction.py -v
```

**What it tests:**
- ✅ `chirp_batch` → extracts `batch`
- ✅ `chirp_standard` → extracts `standard`
- ✅ `long_batch` → extracts `batch`
- ✅ `long_standard` → extracts `standard`
- ✅ `short_batch` → extracts `batch`
- ✅ `short_standard` → extracts `standard`
- ✅ Legacy models (no suffix) → defaults to `batch`
- ✅ Unknown models → defaults to `batch`

**Expected Result:** All tests pass

---

### 2. Verification Script (Existing Jobs)

**File:** `tests/verify_tier_tracking.py`

**Purpose:** Check current state of tier tracking in existing job records.

**Run:**
```bash
cd /Users/johncarosella/Documents/GitHub/askjohn/voice-to-text
python tests/verify_tier_tracking.py
```

**What it reports:**
- Total number of jobs
- How many have tier information
- How many are missing tier (legacy jobs)
- Breakdown by tier (batch vs standard)
- Examples of jobs with/without tier
- Model name analysis

**Expected Result:**
- New jobs (created after this change) should have tier
- Old jobs (created before) will have `tier: null` (this is OK)

---

### 3. Manual Testing (End-to-End)

#### Test 1: Submit Job with Batch Tier

**Steps:**
1. Start the server: `uvicorn app.main:app --reload`
2. Open UI: `http://localhost:8000`
3. Select model: **"Chirp (Dynamic Batch)"** (should be `chirp_batch`)
4. Upload a small test audio file
5. Submit transcription
6. Note the job ID from the response

**Verify:**
1. Check server logs - should see: `Model selection: UI=chirp_batch, API=chirp, Tier=batch`
2. Check job record via API:
   ```bash
   curl http://localhost:8000/api/jobs | jq '.jobs[] | select(.job_id == "YOUR_JOB_ID") | {model, tier}'
   ```
3. Should see: `{"model": "chirp_batch", "tier": "batch"}`

#### Test 2: Submit Job with Standard Tier

**Steps:**
1. In the UI, select model: **"Chirp (Standard)"** (should be `chirp_standard`)
2. Upload a small test audio file
3. Submit transcription
4. Note the job ID

**Verify:**
1. Check server logs - should see: `Model selection: UI=chirp_standard, API=chirp, Tier=standard`
2. Check job record:
   ```bash
   curl http://localhost:8000/api/jobs | jq '.jobs[] | select(.job_id == "YOUR_JOB_ID") | {model, tier}'
   ```
3. Should see: `{"model": "chirp_standard", "tier": "standard"}`

#### Test 3: Check Jobs Page

**Steps:**
1. Navigate to: `http://localhost:8000/static/jobs.html`
2. View the jobs list

**Verify:**
- Jobs should display correctly (even if tier isn't shown in UI yet)
- No errors in browser console
- Jobs page loads successfully

#### Test 4: Check API Response

**Steps:**
```bash
# Get all jobs
curl http://localhost:8000/api/v1/jobs | jq '.jobs[0] | {job_id, model, tier, status}'
```

**Verify:**
- Response includes `tier` field
- `tier` is either `"batch"`, `"standard"`, or `null` (for legacy jobs)
- No errors in API response

---

### 4. Database/Storage Verification

**Check job storage file directly:**

```bash
# View job storage file
cat data/jobs.json | jq '.[] | {job_id, model, tier}' | head -20
```

**Verify:**
- New jobs have `"tier": "batch"` or `"tier": "standard"`
- Old jobs may have `"tier": null` (this is expected)

---

## Success Criteria

✅ **Unit tests pass** - All tier extraction logic works correctly

✅ **Verification script runs** - Can analyze existing jobs

✅ **New jobs have tier** - Jobs submitted after this change include tier field

✅ **API includes tier** - `/api/v1/jobs` endpoint returns tier in response

✅ **No regressions** - Existing functionality still works (jobs page, status checks, etc.)

✅ **Backward compatible** - Old jobs without tier don't break anything

---

## Known Limitations

1. **UI doesn't display tier yet** - The tier field is stored but not shown in the UI. This is fine for now - it's for debugging and future use.

2. **Legacy jobs** - Jobs created before this change won't have tier information. This is expected and OK.

3. **Tier not used in API calls yet** - The tier is extracted and stored, but not yet used to set `recognition_tier` in the `RecognitionConfig`. That's Priority 1 (the actual fix).

---

## Next Steps After Testing

Once tier tracking is verified:

1. **Priority 1:** Implement actual tier differentiation in `RecognitionConfig` (set `recognition_tier` field)
2. **Optional:** Add tier display to UI (jobs page, library page)
3. **Optional:** Add tier filtering to jobs API

---

## Troubleshooting

### Issue: Tier is always `null`

**Check:**
- Is the model name ending with `_batch` or `_standard`?
- Check server logs for tier extraction messages
- Verify `map_model_name()` is being called

### Issue: Unit tests fail

**Check:**
- Are all dependencies installed? `pip install pytest`
- Is the orchestrator being initialized correctly in tests?

### Issue: Verification script errors

**Check:**
- Does `data/jobs.json` exist?
- Are there any jobs in storage?
- Check file permissions

---

## Quick Test Commands

```bash
# Run unit tests
pytest tests/test_tier_extraction.py -v

# Check existing jobs
python tests/verify_tier_tracking.py

# Submit test job and check tier
curl -X POST http://localhost:8000/api/v1/transcribe \
  -F "file=@test_audio.mp3" \
  -F "model=chirp_batch" | jq '.job_id'

# Then check the job
curl http://localhost:8000/api/v1/jobs | jq '.jobs[] | select(.job_id == "YOUR_JOB_ID") | {model, tier}'
```

