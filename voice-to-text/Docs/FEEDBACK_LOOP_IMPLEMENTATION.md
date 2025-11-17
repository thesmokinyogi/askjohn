# Processing Time Feedback Loop - Implementation Summary

**Date:** 2025-11-14  
**Status:** Implemented & Ready for Testing

---

## What Was Implemented

### 1. ProcessingTimeService (`app/services/processing_time.py`)
- Tracks actual processing times (submitted_at to completed_at)
- Uses linear regression to learn from historical data
- Formula: `processing_time = base_time + rate * audio_duration`
- Calculates R² for quality assessment
- Provides confidence levels (high/medium/low/fallback)

### 2. Seed Data Loading
- Loaded 10 completed jobs from existing data:
  - `chirp_standard`: 6 samples, R² = 0.810, formula: `8.0s + 4.24s/min`
  - `long_standard`: 4 samples, R² = 0.529, formula: `345.1s + 32.18s/min`
- Data stored in `data/processing_times.json`

### 3. API Endpoint
- `GET /api/estimate-processing-time?model=X&duration_minutes=Y`
- Returns learned estimate with confidence level
- Falls back to hardcoded estimates if no data available

### 4. Automatic Recording
- When jobs complete, processing time is automatically recorded
- Calculates: `processing_time_seconds = completed_at - submitted_at`
- Includes queue time (since we can't differentiate queued vs processing)

### 5. Frontend Integration
- Updated `index.html` and `jobs.html` to use API endpoint
- Falls back to hardcoded estimates if API fails
- Progress indicator now uses learned estimates

---

## Current Learned Estimates

### chirp_standard
- **Samples:** 6
- **Confidence:** Medium
- **Formula:** `8.0s + 4.24s/min * duration`
- **R²:** 0.810 (good fit)
- **Examples:**
  - 1.0 min → 12.2s
  - 5.0 min → 29.2s
  - 10.0 min → 50.4s
  - 30.0 min → 135.2s

### long_standard
- **Samples:** 4
- **Confidence:** Low (needs more data)
- **Formula:** `345.1s + 32.18s/min * duration`
- **R²:** 0.529 (moderate fit - high variance)
- **Examples:**
  - 1.0 min → 377.3s
  - 5.0 min → 506.0s
  - 10.0 min → 666.9s
  - 30.0 min → 1310.5s

---

## How It Works

### Learning Process
1. Job completes → Calculate `processing_time_seconds = completed_at - submitted_at`
2. Record data point: `(model, audio_duration_minutes, processing_time_seconds)`
3. Recalculate linear regression for that model
4. Update confidence level based on sample count and R²

### Estimation Process
1. Frontend calls `/api/estimate-processing-time?model=X&duration_minutes=Y`
2. Service checks if model has learned data
3. If yes: Calculate `base_time + rate * duration`
4. If no: Use hardcoded fallback
5. Return estimate with confidence level

### Confidence Levels
- **High:** ≥10 samples AND R² ≥ 0.7
- **Medium:** ≥5 samples AND R² ≥ 0.5
- **Low:** <5 samples OR R² < 0.5
- **Fallback:** No data available

---

## Queue Time Handling

**Decision:** Include queue time in estimates

**Rationale:**
- Google's operation API only provides `operation.done` (True/False)
- Cannot differentiate "queued" vs "processing" states
- User experience: Total time from submission to completion is what matters
- Our estimates include queue time, which is realistic for users

**Future Enhancement:**
- If Google adds detailed status (queued/processing), we can:
  1. Track queue time separately
  2. Show "Queued" status in UI
  3. Only start progress indicator when processing begins
  4. Use processing-only time for learning

---

## Testing

### Test the API
```bash
# Test chirp_standard estimate
curl "http://localhost:8000/api/estimate-processing-time?model=chirp_standard&duration_minutes=5.0"

# Expected response:
{
  "estimated_seconds": 29.2,
  "confidence": "medium",
  "sample_count": 6,
  "base_time_seconds": 8.0,
  "rate_per_minute_seconds": 4.24
}
```

### Test the Feedback Loop
1. Submit a transcription job
2. Wait for it to complete
3. Check `data/processing_times.json` - should have new record
4. Check model estimates - should be updated
5. Submit another job - should use updated estimate

### Verify Frontend
1. Upload a file
2. Check progress indicator - should show learned estimate
3. Check browser console - should see API call
4. If API fails, should fall back to hardcoded estimate

---

## Next Steps

### Immediate
- ✅ Seed data loaded
- ✅ Service implemented
- ✅ API endpoint created
- ✅ Frontend integrated
- ✅ Automatic recording on job completion

### Future Enhancements
1. **Better Queue Detection:** If Google adds status details, differentiate queue vs processing
2. **Weighted Learning:** Give more weight to recent data points
3. **Outlier Detection:** Ignore unusually slow/fast jobs (may indicate issues)
4. **Model-Specific Learning:** Track different patterns for different models
5. **UI Improvements:** Show confidence level in progress indicator
6. **Stats Dashboard:** Show learning progress and model accuracy

---

## Files Modified

1. **New:** `app/services/processing_time.py` - Core service
2. **Modified:** `app/main.py` - Added endpoint and recording integration
3. **Modified:** `app/static/index.html` - Updated to use API
4. **Modified:** `app/static/jobs.html` - Updated to use API
5. **New:** `data/processing_times.json` - Data storage

---

## Notes

- **Queue Time:** Currently included in estimates (realistic for users)
- **R² Quality:** `chirp_standard` has good fit (0.810), `long_standard` has moderate fit (0.529) due to high variance
- **Confidence:** Will improve as more jobs complete
- **Fallback:** Always available if API fails or no data exists

