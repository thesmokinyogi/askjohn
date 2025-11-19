# Billed Duration Analysis

**Date:** 2025-11-18  
**Question:** What is `billed_duration`? Per-job or cumulative? Are we using it correctly?

---

## What is `billed_duration`?

**Answer: PER-JOB, not cumulative**

`total_billed_duration` from Google Speech-to-Text API is:
- The actual billed duration for **that specific transcription job**
- Rounded up to nearest 15-second increment
- Example: 4 seconds of audio = 15 seconds billed
- Each job has its own `billed_duration` value

**Source:** `file_result.metadata.total_billed_duration` in BatchRecognizeResponse

---

## Current Situation

### What We're Doing:
1. ✅ Extract `billed_duration` from Google API response
2. ✅ Convert to minutes and include in metadata
3. ❌ **NOT storing it in job records** (missing from jobs.json)
4. ❌ Falling back to estimated duration when `billed_duration` is missing
5. ❌ Recording same job multiple times in budget (24 entries for 3 jobs)

### Evidence:
- **3 jobs** with 94.32 minutes in `jobs.json`
- **24 budget entries** for 94.32 minutes
- **0 jobs** have `billed_duration_minutes` in metadata
- Logs show: "missing billed_duration_minutes in metadata, using estimated duration"

---

## The Problem

### Issue 1: `billed_duration` Not Being Stored
- We extract it from API response
- We include it in metadata returned from `check_job_status()`
- But when we call `mark_complete()`, the metadata might not include it
- Or Google isn't providing it for these specific jobs

### Issue 2: Duplicate Recording
- Same job being recorded 24 times in budget
- Each recording uses estimated duration (94.32 min) instead of actual `billed_duration`
- Cost calculation: 94.32 min × $0.004/min = $0.38 per entry
- 24 entries × $0.38 = $9.12 (matches total)

---

## Root Cause Analysis

### Why `billed_duration` is Missing:

**Possibility 1: Google Not Providing It**
- Some jobs might not have `total_billed_duration` in metadata
- Could be due to API version, job type, or Google's internal processing

**Possibility 2: We're Not Storing It**
- We extract it in `_parse_batch_results()`
- We add it to metadata
- But `mark_complete()` might not be receiving it, or it's not being saved

**Possibility 3: Parsing Issue**
- We're parsing from GCS JSON (not Protobuf)
- The JSON structure might not include `total_billed_duration`
- Or it's in a different location in the JSON

---

## What We Need to Check

1. **Is Google providing `billed_duration`?**
   - Check raw API response for `total_billed_duration`
   - Check GCS JSON files for this field
   - Add debug logging to see what we're actually receiving

2. **Are we storing it correctly?**
   - Verify `mark_complete()` receives metadata with `billed_duration`
   - Check if it's being saved to transcript files but not jobs.json
   - Verify metadata structure when saving

3. **Why duplicate recording?**
   - Already fixed with guards, but need to verify
   - Check if old endpoint is still being called

---

## Next Steps

1. **Add debug logging** to see if Google provides `billed_duration`
2. **Check GCS JSON files** for `totalBilledDuration` field
3. **Verify metadata flow** from API → parsing → storage
4. **Fix storage** if `billed_duration` is being lost
5. **Clean up duplicate entries** in budget_tracking.json

---

## Summary

- `billed_duration` = **PER-JOB** (not cumulative)
- We're extracting it but **not storing it** in job records
- We're using **estimated duration** instead of actual `billed_duration`
- Same job recorded **24 times** in budget (already fixed with guards)
- Need to investigate why `billed_duration` isn't in job metadata

