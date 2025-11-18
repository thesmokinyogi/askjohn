# Pre-Transition Checklist: Free Tier → Paid

## Current Status
- **Free tier remaining:** 3.82 minutes
- **Free tier used:** 56.18 / 60.0 minutes
- **Next job will likely transition to paid**

## Critical Pre-Flight Checks

### ✅ 1. Logic Verification (Run First!)

```bash
python tests/test_free_tier_transition.py
```

**Expected:** All scenarios pass, including:
- Small job (all free)
- Exact remaining (all free)
- **Transition job (part free, part paid)** ← Critical
- Large job (all paid)
- Edge cases

---

### ✅ 2. Verify Current Budget State

**Check free tier status:**
```bash
curl http://localhost:8000/api/v1/budget | jq '.providers.google.free_tier'
```

**Verify:**
- `remaining` matches expected (3.82 minutes)
- `used` + `remaining` = 60.0
- `reset_date` is correct (December 1, 2025)

---

### ✅ 3. Test Cost Estimation (Before Job)

**Before submitting the transition job, check the estimate:**

1. Upload a test file (or use existing file duration)
2. Select model (e.g., `chirp_batch`)
3. Check the cost estimate in UI

**Verify:**
- Estimate shows correct breakdown
- If job is > 3.82 min, should show partial free + partial paid
- Cost calculation looks correct

**Or test via API:**
```bash
curl -X POST http://localhost:8000/api/v1/budget/estimate-cost \
  -H "Content-Type: application/json" \
  -d '{"provider": "google", "model": "chirp_batch", "duration_minutes": 5.0}' | jq
```

**Expected for 5.0 min job:**
- `free_minutes_used`: 3.82
- `billable_minutes`: 1.18
- `total_cost`: ~$0.019 (1.18 * $0.016)

---

### ✅ 4. Monitor During Job Execution

**Watch server logs for:**
```
INFO: Using actual billed duration: X.XX minutes
INFO: Free tier remaining: 3.82 minutes
INFO: Calculated actual cost: $X.XX
INFO: Recorded transcription: google/chirp_batch - X.X min - $X.XX
```

**Key things to verify:**
- `actual_free_minutes_used` is correct (≤ 3.82)
- `actual_billable_minutes` is correct (duration - free_used)
- `actual_cost` matches expected (billable * rate)

---

### ✅ 5. Verify After Job Completes

**A. Check Job Record:**
```bash
curl http://localhost:8000/api/v1/jobs | jq '.jobs[0] | {model, actual_cost, duration_minutes}'
```

**B. Check Budget Updated:**
```bash
curl http://localhost:8000/api/v1/budget | jq '.providers.google'
```

**Verify:**
- `free_tier.used` increased by correct amount (≤ 3.82)
- `free_tier.remaining` is now 0.0 (or very close)
- `total_cost` increased by correct amount
- `transcription_count` increased by 1

**C. Check Budget File:**
```bash
cat data/budget_tracking.json | jq '.providers.google | {free_tier_used, total_cost, transcriptions: (.transcriptions | length)}'
```

**Verify:**
- Latest transcription record has correct `free_minutes_used`
- Latest transcription record has correct `cost`
- `free_tier_used` matches API response

---

### ✅ 6. Test Next Job (All Paid)

**After transition, submit another job (should be all paid):**

**Verify:**
- `free_minutes_used` = 0.0 (free tier exhausted)
- `billable_minutes` = full duration
- `actual_cost` = duration * rate
- Budget shows `free_tier.remaining` = 0.0

---

## Critical Edge Cases to Verify

### Edge Case 1: Job Exactly Uses Remaining Free
- **Duration:** 3.82 minutes
- **Expected:** All free, $0.00 cost
- **Verify:** `actual_cost` = 0.0, `free_tier.remaining` = 0.0

### Edge Case 2: Job Spans Boundary
- **Duration:** 5.0 minutes (3.82 free + 1.18 paid)
- **Expected:** 3.82 free, 1.18 paid, cost = 1.18 * rate
- **Verify:** Both free and paid portions calculated correctly

### Edge Case 3: Job Larger Than Remaining
- **Duration:** 10.0 minutes
- **Expected:** 3.82 free, 6.18 paid
- **Verify:** Correct split, correct cost

### Edge Case 4: Very Small Job
- **Duration:** 0.5 minutes
- **Expected:** All free, $0.00 cost
- **Verify:** No rounding errors

---

## What to Watch For (Red Flags)

### ❌ **Red Flag 1: Free Tier Not Decrementing**
- **Symptom:** `free_tier.used` doesn't increase after job
- **Check:** `record_transcription()` is being called with `free_minutes_used`
- **Fix:** Verify orchestrator passes `actual_free_minutes_used` to budget service

### ❌ **Red Flag 2: Cost Calculation Wrong**
- **Symptom:** `actual_cost` doesn't match expected
- **Check:** `billed_duration_minutes` vs `estimated_duration_minutes`
- **Check:** `cost_per_minute` is correct for model/tier
- **Fix:** Verify `CostCalculationService.calculate_actual_cost()` logic

### ❌ **Red Flag 3: Free Tier Goes Negative**
- **Symptom:** `free_tier.remaining` becomes negative
- **Check:** `min(billed_duration, free_remaining)` logic
- **Fix:** Should never happen, but verify `max(0, ...)` guards

### ❌ **Red Flag 4: Billable Minutes Wrong**
- **Symptom:** `billable_minutes` doesn't match `duration - free_used`
- **Check:** `max(0, billed_duration - free_remaining)` logic
- **Fix:** Verify calculation in `CostCalculationService`

---

## Recommended Test Sequence

1. **Run logic test:** `python tests/test_free_tier_transition.py`
2. **Check current state:** Verify free tier remaining (3.82 min)
3. **Submit transition job:** Use a file that will span the boundary (e.g., 5 min)
4. **Monitor logs:** Watch for correct calculations
5. **Verify results:** Check job record, budget, and file
6. **Submit paid job:** Test that next job is all paid
7. **Final verification:** Confirm free tier exhausted, all future jobs are paid

---

## Success Criteria

✅ Logic test passes all scenarios  
✅ Cost estimate shows correct breakdown before job  
✅ Job completes with correct `actual_cost`  
✅ Budget shows correct `free_tier.used` and `remaining`  
✅ Next job (all paid) calculates correctly  
✅ No red flags in logs or data  

---

## If Something Goes Wrong

1. **Stop submitting jobs** until fixed
2. **Check logs** for calculation details
3. **Verify budget file** hasn't been corrupted
4. **Compare** actual vs expected values
5. **Review** `CostCalculationService` and `BudgetService` logic
6. **Test** with logic verification script

---

## Post-Transition Verification

After the transition job completes successfully:

```bash
# Verify free tier exhausted
curl http://localhost:8000/api/v1/budget | jq '.providers.google.free_tier.remaining'
# Should be: 0.0

# Verify next job will be all paid
curl -X POST http://localhost:8000/api/v1/budget/estimate-cost \
  -H "Content-Type: application/json" \
  -d '{"provider": "google", "model": "chirp_batch", "duration_minutes": 5.0}' | jq '.billable_minutes'
# Should be: 5.0 (all billable)
```

---

**Good luck! You've got this! 🚀**

