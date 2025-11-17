# Implementation Plan: Budget Tracking Fix & Progress Feedback Loop

**Date:** 2025-11-14  
**Status:** Pre-Implementation

---

## Part 1: Budget Tracking Fix

### Current Problem
- `free_minutes_used` calculated but not passed to `record_transcription()`
- Actual billed duration logged but not extracted/returned
- Free tier tracking shows 0.0 minutes used (should be ~24.1 minutes)

### Solution

**Step 1: Extract Billed Duration from Transcription Results**
- Location: `app/services/transcribe_v2.py` - `_parse_results()` and `_parse_batch_results()`
- Extract: `result.metadata.total_billed_duration` (currently only logged)
- Convert: Duration is in seconds, convert to minutes
- Include: Add `billed_duration_minutes` to returned metadata

**Step 2: Calculate Actual Cost & Free Minutes**
- Location: `app/main.py` - `check_job_status()` endpoint
- When job completes:
  1. Get `billed_duration_minutes` from `status_result["metadata"]`
  2. Get current `free_tier_remaining` from budget service
  3. Calculate `actual_free_minutes_used = min(billed_duration_minutes, free_tier_remaining)`
  4. Calculate `actual_billable_minutes = max(0, billed_duration_minutes - free_tier_remaining)`
  5. Get `cost_per_minute` from pricing service
  6. Calculate `actual_cost = actual_billable_minutes * cost_per_minute`

**Step 3: Pass Free Minutes to Budget Service**
- Update `record_transcription()` call to include `free_minutes_used=actual_free_minutes_used`

**Step 4: Update Job Record**
- Store `actual_cost` and `billed_duration_minutes` in job record
- Update `mark_complete()` to accept these values

### Testing Plan
1. Run a test transcription (should use free tier)
2. Verify `billed_duration_minutes` is extracted and returned
3. Verify `free_minutes_used` is calculated correctly
4. Verify budget tracking file shows updated free tier usage
5. Verify cost is $0.00 if free tier covers it

---

## Part 2: Progress Feedback Loop

### Current State
- Hardcoded estimates: Batch = 45s + 5s/min, Standard = 22s + 3s/min
- No learning from actual results
- Progress calculated as: `(elapsed / estimated) * 100`

### Solution: Learning System

**Step 1: Create Processing Time Tracking Service**
- New file: `app/services/processing_time.py`
- Purpose: Track and learn from actual processing times
- Data structure:
  ```python
  {
    "model": "long_standard",
    "audio_duration_minutes": 5.6,
    "processing_time_seconds": 45.2,
    "timestamp": "2025-11-14T..."
  }
  ```
- Storage: `data/processing_times.json`

**Step 2: Record Actual Processing Times**
- Location: `app/main.py` - `check_job_status()` when job completes
- Calculate: `processing_time_seconds = (completed_at - submitted_at).total_seconds()`
- Record: Call `processing_time_service.record_processing_time(model, duration_minutes, processing_time_seconds)`

**Step 3: Build Estimation Model**
- Method: Simple linear regression per model
- Formula: `estimated_seconds = base_time + (duration_minutes * rate_per_minute)`
- Learning: Calculate `base_time` and `rate_per_minute` from historical data
- Fallback: Use hardcoded estimates if insufficient data (< 3 samples)

**Step 4: Update Progress Calculation**
- Location: `app/static/index.html` and `app/static/jobs.html`
- Replace hardcoded `getEstimatedProcessingTime()` with API call
- New endpoint: `GET /api/estimate-processing-time?model=X&duration_minutes=Y`
- Backend: Use learning service to return learned estimate

**Step 5: Continuous Learning**
- After each completed job: update model with new data point
- Use weighted average or linear regression
- Older data points can be weighted less (optional)

### Learning Algorithm Options

**Option A: Simple Moving Average**
- Track: `(base_time, rate_per_minute)` per model
- Update: Average of all historical data points
- Pros: Simple, stable
- Cons: Doesn't account for model improvements over time

**Option B: Linear Regression**
- Fit: `processing_time = base + rate * duration`
- Update: Recalculate regression coefficients with each new data point
- Pros: More accurate, accounts for linear relationship
- Cons: Slightly more complex

**Option C: Weighted Average (Recent Data More Important)**
- Weight recent data points more heavily
- Pros: Adapts to changes in Google's processing speed
- Cons: More complex, may overfit to recent outliers

**Recommendation: Option B (Linear Regression)**
- Most accurate for this use case
- Simple enough to implement
- Can add exponential weighting later if needed

### Data Structure

**Storage File: `data/processing_times.json`**
```json
{
  "version": "1.0",
  "records": [
    {
      "model": "long_standard",
      "audio_duration_minutes": 5.6,
      "processing_time_seconds": 45.2,
      "timestamp": "2025-11-14T10:30:00",
      "job_id": "projects/.../operations/..."
    },
    ...
  ],
  "models": {
    "long_standard": {
      "base_time_seconds": 22.5,
      "rate_per_minute_seconds": 3.2,
      "sample_count": 15,
      "last_updated": "2025-11-14T10:30:00"
    },
    ...
  }
}
```

### API Endpoints

**New Endpoint: `GET /api/estimate-processing-time`**
- Query params: `model`, `duration_minutes`
- Returns: `{"estimated_seconds": 45, "confidence": "high|medium|low"}`
- Confidence: "high" if >= 5 samples, "medium" if 3-4, "low" if < 3

**New Endpoint: `GET /api/processing-time-stats`** (optional, for debugging)
- Returns: Statistics about learning data
- Shows: Sample counts, current estimates per model

### Implementation Steps

1. **Create ProcessingTimeService**
   - `record_processing_time()` - Store new data point
   - `get_estimate()` - Return learned estimate
   - `_calculate_model()` - Update regression coefficients
   - `_load_data()` / `_save_data()` - Persistence

2. **Integrate Recording**
   - In `check_job_status()` when job completes
   - Calculate processing time from timestamps
   - Call `record_processing_time()`

3. **Create API Endpoint**
   - `GET /api/estimate-processing-time`
   - Use service to get learned estimate
   - Return to frontend

4. **Update Frontend**
   - Replace hardcoded `getEstimatedProcessingTime()`
   - Call API endpoint instead
   - Handle loading states and fallback to hardcoded if API fails

5. **Test & Validate**
   - Run several transcriptions
   - Verify data is recorded
   - Verify estimates improve over time
   - Verify progress calculation uses learned estimates

### Testing Plan

1. **Initial State:**
   - No historical data → uses hardcoded estimates
   - Verify fallback works

2. **After 1 Job:**
   - Data recorded
   - Estimate may not be accurate yet (low confidence)
   - Still uses hardcoded or shows "learning..."

3. **After 3 Jobs:**
   - Enough data for basic estimate
   - Confidence: "medium"
   - Uses learned estimate

4. **After 10+ Jobs:**
   - Accurate estimates
   - Confidence: "high"
   - Progress indicator should be more accurate

---

## Implementation Order

1. **Budget Tracking Fix** (Critical, simpler)
   - Extract billed duration
   - Calculate free minutes
   - Pass to budget service
   - Test immediately

2. **Progress Feedback Loop** (Enhancement, more complex)
   - Create service
   - Record processing times
   - Build learning model
   - Update frontend
   - Test over time

---

## Questions to Resolve

1. **Billed Duration Format:**
   - What is the exact format of `total_billed_duration`?
   - Is it a `Duration` protobuf object or seconds as float?
   - Need to observe actual value

2. **Processing Time Accuracy:**
   - Should we track time from `submitted_at` to `completed_at`?
   - Or time from when Google actually starts processing?
   - Current: `submitted_at` to `completed_at` (includes queue time)

3. **Learning Model Complexity:**
   - Start with simple linear regression?
   - Or weighted average?
   - Can always enhance later

4. **Data Retention:**
   - Keep all historical data?
   - Or prune old data (> 90 days)?
   - Start with keeping all, prune later if needed

---

## Next Steps

1. **Observe Billed Duration Format**
   - Check logs or add debug output
   - Understand exact structure

2. **Implement Budget Fix**
   - Extract billed duration
   - Calculate free minutes
   - Test with real transcription

3. **Implement Progress Learning**
   - Create service
   - Record first data point
   - Verify learning works

4. **Iterate & Improve**
   - Monitor accuracy
   - Adjust model if needed
   - Add features (confidence, stats, etc.)

