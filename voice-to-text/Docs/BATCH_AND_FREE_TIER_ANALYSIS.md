# Batch Transcription & Free Tier Transition Analysis

## Summary

Analysis of two critical areas:
1. **Batch vs Standard Tier Differentiation** - How the system handles `chirp_batch` vs `chirp_standard` and `long_batch` vs `long_standard`
2. **Free Tier to Paid Transition** - How the system calculates costs when free minutes are exhausted

---

## 1. Batch vs Standard Tier Analysis

### Current Implementation

**Issue Found:** The system does NOT differentiate between batch and standard tiers.

**Flow:**
1. UI sends model name: `chirp_batch` or `chirp_standard`
2. `TranscriptionOrchestrator.map_model_name()` normalizes both to `chirp`
3. `GoogleSpeechV2Service` receives only `chirp` (tier information lost)
4. `_build_config()` creates `RecognitionConfig` without `recognition_tier` field
5. All requests use `batch_recognize` API, but tier defaults to... **unknown**

### What's Missing

In Google Speech-to-Text V2, the `RecognitionConfig` should include:
```python
config = cloud_speech.RecognitionConfig(
    ...
    recognition_tier=cloud_speech.RecognitionTier.BATCH,  # or STANDARD
    ...
)
```

**Current Code Location:** `app/services/transcribe_v2.py:1248-1257`
- `config_kwargs` is built but does NOT include `recognition_tier`
- The tier information from the UI model name (`_batch` vs `_standard`) is lost during normalization

### Impact

1. **Cost Accuracy:** Pricing calculations assume batch tier (75% savings), but if the API defaults to standard tier, actual costs will be 4x higher than estimated
2. **User Expectation:** Users select "batch" expecting slower processing but lower cost, but may get standard tier pricing
3. **Processing Time:** Batch tier can take up to 24 hours, standard tier is 1-3 minutes - users may not get expected behavior

### Recommended Fix

**Option A: Preserve Tier Information**
1. Modify `map_model_name()` to return both model and tier:
   ```python
   def map_model_name(self, ui_model: Optional[str]) -> Tuple[str, str]:
       # Returns: (google_api_model, tier)
       # e.g., ('chirp', 'batch') or ('chirp', 'standard')
   ```

2. Pass tier to `GoogleSpeechV2Service`:
   ```python
   class GoogleSpeechV2Service:
       def __init__(self, ..., tier: str = 'batch'):
           self.tier = tier
   ```

3. Set `recognition_tier` in `_build_config()`:
   ```python
   if self.tier == 'batch':
       config_kwargs['recognition_tier'] = cloud_speech.RecognitionTier.BATCH
   else:
       config_kwargs['recognition_tier'] = cloud_speech.RecognitionTier.STANDARD
   ```

**Option B: Always Use Batch Tier**
- If batch tier is always desired, explicitly set it in `_build_config()`
- Update UI to remove standard tier options
- Update pricing to always use batch tier rates

### Testing Required

1. **Verify Current Behavior:**
   - Check Google Cloud billing logs to see what tier is actually being used
   - Compare estimated costs vs actual costs for recent jobs

2. **Test After Fix:**
   - Submit job with `chirp_batch` → verify `RecognitionTier.BATCH` in config
   - Submit job with `chirp_standard` → verify `RecognitionTier.STANDARD` in config
   - Verify costs match expectations for each tier

---

## 2. Free Tier to Paid Transition Analysis

### Current Implementation

**Status:** ✅ **CORRECTLY IMPLEMENTED**

The free tier transition logic is properly handled in `CostCalculationService.calculate_actual_cost()`:

**Location:** `app/services/cost_calculation.py:34-107`

**Logic Flow:**
1. Get `free_tier_remaining` from `BudgetService`
2. Calculate free minutes used: `min(billed_duration_minutes, free_tier_remaining)`
3. Calculate billable minutes: `max(0, billed_duration_minutes - free_tier_remaining)`
4. Calculate cost: `actual_billable_minutes * cost_per_minute`

**Example Scenarios:**

**Scenario 1: All Free (60 min remaining, 30 min job)**
- `actual_free_minutes_used = min(30, 60) = 30`
- `actual_billable_minutes = max(0, 30 - 60) = 0`
- `actual_cost = 0 * $0.016 = $0.00` ✅

**Scenario 2: Partial Free (10 min remaining, 30 min job)**
- `actual_free_minutes_used = min(30, 10) = 10`
- `actual_billable_minutes = max(0, 30 - 10) = 20`
- `actual_cost = 20 * $0.016 = $0.32` ✅

**Scenario 3: All Paid (0 min remaining, 30 min job)**
- `actual_free_minutes_used = min(30, 0) = 0`
- `actual_billable_minutes = max(0, 30 - 0) = 30`
- `actual_cost = 30 * $0.016 = $0.48` ✅

### Integration Points

**Job Completion Flow:** `app/services/orchestrator.py:344-407`
1. Extracts `billed_duration_minutes` from transcription metadata
2. Calls `cost_calculation_service.calculate_actual_cost()`
3. Gets `actual_free_minutes_used` and `actual_cost`
4. Records to budget with both values
5. Updates job record with actual cost

**Budget Tracking:** `app/services/budget.py:215-274`
- `record_transcription()` accepts `free_minutes_used` parameter
- Updates `free_tier_used` for Google provider
- Tracks total cost separately from free tier usage

### Verification

✅ **Correct Calculation:** The math is sound
✅ **Proper Integration:** Values flow correctly from API → calculation → budget
✅ **Edge Cases Handled:** 
   - Negative free tier remaining (handled by `max(0, ...)`)
   - Jobs larger than free tier (handled by `min()` and `max()`)
   - Zero free tier remaining (correctly calculates all as billable)

### Potential Edge Case

**Question:** What if `billed_duration_minutes` is `None`?

**Current Handling:** `app/services/cost_calculation.py:64-70`
- Falls back to `estimated_duration_minutes`
- Logs warning
- Proceeds with calculation

**Risk:** If both are `None`, raises `ValueError` - this is appropriate.

---

## Recommendations

### Priority 1: Fix Batch/Standard Tier Differentiation

**Impact:** High - affects cost accuracy and user expectations
**Effort:** Medium - requires changes to orchestrator, service, and config building
**Risk:** Low - well-defined API, straightforward implementation

**Steps:**
1. Preserve tier information through model name normalization
2. Pass tier to `GoogleSpeechV2Service`
3. Set `recognition_tier` in `RecognitionConfig`
4. Update pricing service to use correct tier rates
5. Test with both tiers and verify billing

### Priority 2: Verify Current Tier Behavior

**Impact:** Medium - need to understand current state before fixing
**Effort:** Low - check billing logs and recent job costs
**Risk:** None - read-only investigation

**Steps:**
1. Check Google Cloud billing for recent transcription jobs
2. Compare estimated vs actual costs
3. Determine if current default is batch or standard tier
4. Document findings

### Priority 3: Add Tier to Job Records

**Impact:** Low - nice to have for debugging and transparency
**Effort:** Low - add field to job record
**Risk:** None - additive change

**Steps:**
1. Add `tier` field to `JobRecord` model
2. Store tier when job is created
3. Display tier in UI (jobs page, library page)

---

## Testing Checklist

### Batch/Standard Tier
- [ ] Submit job with `chirp_batch` → verify `RecognitionTier.BATCH` in logs
- [ ] Submit job with `chirp_standard` → verify `RecognitionTier.STANDARD` in logs
- [ ] Verify costs match tier pricing (batch = 75% of standard)
- [ ] Verify processing time matches tier expectations (batch slower, standard faster)

### Free Tier Transition
- [ ] Job with 60 min free remaining, 30 min audio → $0.00 cost
- [ ] Job with 10 min free remaining, 30 min audio → 20 min billable
- [ ] Job with 0 min free remaining, 30 min audio → 30 min billable
- [ ] Verify free tier usage decrements correctly in UI
- [ ] Verify budget tracking shows correct free tier remaining

---

## Files to Modify

### For Batch/Standard Tier Fix:
1. `app/services/orchestrator.py` - Preserve tier in `map_model_name()`
2. `app/services/transcribe_v2.py` - Accept tier, set `recognition_tier` in config
3. `app/services/pricing.py` - Use tier for cost calculation (if different rates)
4. `app/models/job.py` - Add `tier` field to `JobRecord` (optional)
5. `app/services/jobs.py` - Store tier in job record (optional)

### For Free Tier (No Changes Needed):
- ✅ Already correctly implemented

