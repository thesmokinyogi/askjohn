# Refactored System Test Plan

**Purpose:** Verify the Pydantic model refactoring works end-to-end with actual transcription jobs.

**Date:** 2025-11-18

---

## Test Objectives

1. Verify job submission works with new model-based flow
2. Verify metadata extraction and storage works correctly
3. Verify library integration works with new models
4. Verify cost calculation and budget tracking still work
5. Verify event publishing (stub) works
6. Verify backward compatibility with existing data

---

## Test Models to Use

Based on available models in `us-central1`:
- `chirp` (Chirp Batch) - Standard model, no confidence scores
- `long` (Long Audio) - For longer files, supports confidence
- `short` (Short Audio) - For shorter files, supports confidence

**Note:** Test with models that have different capabilities (confidence vs no confidence) to ensure metadata handling works correctly.

---

## Test Cases

### Test 1: Chirp Batch (No Confidence)
**Model:** `chirp_batch` (maps to `chirp`)  
**File:** Short audio file (1-2 minutes)  
**Expected:**
- ✅ Job submits successfully
- ✅ Status checking works
- ✅ Transcript extracted correctly
- ✅ Metadata created as `TranscriptMetadata` model
- ✅ `confidence` field is `None` in metadata
- ✅ Library entry created with model
- ✅ Cost calculated and recorded
- ✅ Budget updated
- ✅ Event published (check logs for "EVENT: Job completed")
- ✅ Transcript file saved with correct structure
- ✅ No "words" field in metadata (should be filtered if present)

**Validation:**
- Check `data/jobs.json` - job record should have `billed_duration` fields
- Check `data/library.json` - entry should have `metadata` as dict (converted from model)
- Check `data/transcripts/*.json` - should have `metadata` dict with no "words" field
- Check server logs for event publishing messages
- Check budget tracking updated

---

### Test 2: Long Audio (With Confidence)
**Model:** `long`  
**File:** Medium audio file (5-10 minutes)  
**Expected:**
- ✅ Job submits successfully
- ✅ Status checking works
- ✅ Transcript extracted correctly
- ✅ Metadata created as `TranscriptMetadata` model
- ✅ `confidence` field is present (float 0-1)
- ✅ Word timestamps extracted correctly
- ✅ Library entry created with model
- ✅ Cost calculated and recorded
- ✅ Budget updated
- ✅ Event published
- ✅ Transcript file saved with correct structure

**Validation:**
- Check transcript file has `words` array in content (not metadata)
- Check metadata has `total_words` count
- Check confidence score is present and valid
- Check word timestamps are present

---

### Test 3: Short Audio (With Confidence)
**Model:** `short`  
**File:** Short audio file (30 seconds - 1 minute)  
**Expected:**
- ✅ Job submits successfully
- ✅ Status checking works
- ✅ Transcript extracted correctly
- ✅ Metadata created as `TranscriptMetadata` model
- ✅ `confidence` field is present
- ✅ Library entry created
- ✅ Cost calculated and recorded
- ✅ Budget updated

**Validation:**
- Verify all same checks as Test 2
- Verify processing time is reasonable for short file

---

## What to Check in Each Test

### 1. Server Logs
Look for:
- ✅ No errors or warnings about `TranscriptMetadata`
- ✅ No "words" field filtering warnings (unless data has it)
- ✅ Event publishing messages: "EVENT: Job started", "EVENT: Job completed"
- ✅ No import errors
- ✅ No type conversion errors

### 2. Job Record (`data/jobs.json`)
- ✅ Job has `status: "completed"`
- ✅ Job has `actual_cost` field
- ✅ Job has `billed_duration_minutes` and `billed_duration_seconds` (if available)
- ✅ Job has `transcript_file` reference

### 3. Library Entry (`data/library.json`)
- ✅ Entry has `metadata` dict (converted from model)
- ✅ Metadata has required fields: `total_words`, `model`, `language`, `api_version`
- ✅ Metadata does NOT have `words` field (should be filtered)
- ✅ Entry has `library_id`, `filename`, `cost`, etc.

### 4. Transcript File (`data/transcripts/*.json`)
- ✅ File has `transcript` field (string)
- ✅ File has `words` array (if word timestamps available)
- ✅ File has `metadata` dict (converted from model)
- ✅ Metadata does NOT have `words` field
- ✅ Metadata has required fields: `total_words`, `model`, `language`, `api_version`
- ✅ File has `confidence` field (float or null)
- ✅ File has `saved_at` timestamp

### 5. Budget Tracking (`data/budget_tracking.json`)
- ✅ New entry created for each job
- ✅ Cost matches job's `actual_cost`
- ✅ No duplicate entries

### 6. Event Publishing (Logs)
- ✅ "EVENT: Job started" message when job submitted
- ✅ "EVENT: Job completed" message when job completes
- ✅ Event includes correct metadata (check log details)

---

## Test Execution Checklist

For each test:
- [ ] Submit job via UI
- [ ] Monitor server logs for errors
- [ ] Wait for job completion
- [ ] Verify job record in `jobs.json`
- [ ] Verify library entry in `library.json`
- [ ] Verify transcript file structure
- [ ] Verify budget tracking updated
- [ ] Verify event publishing (check logs)
- [ ] Verify UI displays correctly (transcript, confidence, cost)

---

## Success Criteria

All tests pass if:
1. ✅ All jobs complete successfully
2. ✅ No errors in server logs related to models
3. ✅ All data structures are correct (models converted to dicts at storage boundary)
4. ✅ No "words" field in metadata (filtered correctly)
5. ✅ Event publishing works (stub logs events)
6. ✅ Cost calculation and budget tracking work
7. ✅ UI displays all information correctly

---

## Issues to Watch For

1. **Type Errors:** If `TranscriptMetadata` model is not properly converted to dict before JSON storage
2. **Missing Fields:** If required metadata fields are missing
3. **Words in Metadata:** If "words" field appears in metadata (should be filtered)
4. **Event Publishing:** If events don't publish (check logs)
5. **Cost Calculation:** If costs don't match expected values
6. **Budget Tracking:** If budget entries are duplicated or missing

---

## Post-Test Validation

After all tests complete, run validation script again:
```bash
python scripts/validate_transcript_data.py
```

Should still report: ✅ All data is valid!

---

## Notes

- Use different audio files for each test to avoid confusion
- Keep server logs visible to monitor in real-time
- Check both UI and data files to verify end-to-end correctness
- If any test fails, document the issue and fix before proceeding

