# Billing API Analysis: Getting Actual Usage from Google Cloud

**Date:** 2025-11-17  
**Question:** Should we query Google Cloud Billing API for actual usage instead of calculating it?

---

## Current Situation

**What We're Doing:**
- Calculating free tier usage based on estimated/actual duration
- Tracking usage in our own `budget_tracking.json` file
- Manually calculating what portion was covered by free tier

**What User Wants:**
- Get actual usage from Google Cloud's billing system
- Use Google's actual data, not our calculations

---

## Google Cloud Billing API Options

### Option 1: Cloud Billing API
- **Endpoint:** `cloudbilling.googleapis.com`
- **What it provides:** Billing account info, cost data, budget alerts
- **Limitation:** Doesn't provide real-time usage for free tier
- **Free tier tracking:** Not directly available via API

### Option 2: Cloud Monitoring API (Usage Metrics)
- **Endpoint:** `monitoring.googleapis.com`
- **What it provides:** Service usage metrics
- **Limitation:** May have delays, not specifically for free tier

### Option 3: Use `total_billed_duration` from API Response
- **Source:** Speech-to-Text API response metadata
- **What it provides:** Actual billed duration for each transcription
- **Advantage:** Real-time, accurate, comes directly from Google
- **This is what we should use!**

---

## Recommendation

**Use `total_billed_duration` from API Response**

**Why:**
1. ✅ It's the actual billed duration from Google
2. ✅ Available immediately after transcription completes
3. ✅ More accurate than our estimates
4. ✅ No need for separate billing API calls
5. ✅ Works for both free tier and paid usage

**What We Need to Do:**
1. Extract `total_billed_duration` from `result.metadata` in `_parse_results()`
2. Convert from Duration protobuf to minutes
3. Include in returned metadata
4. Use it for budget tracking instead of estimated duration

**Free Tier Calculation:**
- Get `total_billed_duration` from Google (actual usage)
- Check current free tier remaining
- Calculate: `free_minutes_used = min(billed_duration, free_tier_remaining)`
- This is still our calculation, but based on Google's actual billed duration

---

## Google Cloud Billing API - Can We Query It?

**For Free Tier Usage:**
- ❌ Google doesn't expose free tier usage via API
- ❌ Free tier is a billing credit, not a separate metric
- ✅ We can query actual usage amounts
- ✅ We can query costs
- ⚠️ But free tier application is automatic in billing, not queryable

**What We CAN Query:**
- Actual usage amounts (minutes transcribed)
- Costs incurred
- Service usage metrics

**What We CANNOT Query:**
- How much free tier was used (it's a credit applied automatically)
- Real-time free tier remaining (we need to track this ourselves)

---

## Conclusion

**Best Approach:**
1. Extract `total_billed_duration` from Google's API response (actual usage)
2. Use that for all calculations (not estimated duration)
3. Track free tier usage ourselves (Google doesn't expose this via API)
4. Calculate free tier based on actual billed duration

**This gives us:**
- ✅ Actual usage from Google (not estimates)
- ✅ Accurate billing calculations
- ✅ Proper free tier tracking

**We cannot:**
- ❌ Query free tier usage from Google's API (it's not exposed)
- ❌ Get real-time free tier status from Google (we track it ourselves)

---

## Implementation

1. Extract `total_billed_duration` from `result.metadata.total_billed_duration`
2. Convert Duration protobuf to seconds/minutes
3. Include in metadata: `billed_duration_minutes`
4. Use for budget tracking instead of `duration_minutes`

