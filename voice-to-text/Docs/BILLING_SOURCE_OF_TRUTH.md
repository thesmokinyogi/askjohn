# Billing Source of Truth: Google Cloud Billing API

**Date:** 2025-11-18  
**Issue:** We're calculating costs ourselves instead of using Google's actual billing data.

---

## Current Problem

**What We're Doing:**
1. ✅ Get `billed_duration` from Google Speech-to-Text API response (actual usage)
2. ❌ Calculate cost ourselves using our pricing table
3. ❌ Track costs in our own `budget_tracking.json`

**What We Should Do:**
1. ✅ Get `billed_duration` from API (actual usage) - KEEP THIS
2. ✅ Query Google Cloud Billing API for actual charges
3. ✅ Use Google's charges as source of truth
4. ✅ Reconcile our calculations with actual charges

---

## Google Cloud Billing API Options

### Option 1: Cloud Billing API (`cloudbilling.googleapis.com`)
- **What it provides:** Billing account info, cost data, budget alerts
- **Limitation:** May have delays (billing data can lag by hours/days)
- **Use case:** Get actual charges for reconciliation

### Option 2: BigQuery Billing Export
- **What it provides:** Detailed billing data exported to BigQuery
- **Advantage:** Most detailed, queryable data
- **Requirement:** Must enable BigQuery export in billing console
- **Use case:** Historical analysis, detailed reconciliation

### Option 3: Cloud Monitoring API (Usage Metrics)
- **What it provides:** Service usage metrics in near real-time
- **Limitation:** Usage metrics, not actual charges
- **Use case:** Real-time usage tracking

---

## Recommended Approach: Hybrid

**Immediate (Real-time):**
1. Use `billed_duration` from API response (actual usage)
2. Calculate estimated cost using our pricing table
3. Store as "estimated_cost" until actual charge is available

**Periodic Reconciliation (Daily/Hourly):**
1. Query Google Cloud Billing API for actual charges
2. Match charges to jobs by:
   - Timestamp window
   - Service (Speech-to-Text)
   - Project
3. Update `actual_cost` with Google's charge
4. Flag discrepancies for review

**Source of Truth:**
- **For display:** Use `actual_cost` from Google when available, fall back to calculated
- **For tracking:** Always use Google's actual charges when available
- **For estimates:** Use our calculations (needed before billing data is available)

---

## Implementation Plan

### Phase 1: Add Billing API Client
1. Install `google-cloud-billing` library
2. Create `BillingService` class
3. Query charges for Speech-to-Text service
4. Match charges to jobs

### Phase 2: Reconciliation Service
1. Create `BillingReconciliationService`
2. Match Google charges to our job records
3. Update `actual_cost` with Google's data
4. Flag discrepancies

### Phase 3: Update Budget Tracking
1. Use Google's actual charges when available
2. Show "estimated" vs "actual" in UI
3. Reconcile daily/hourly

---

## Google Cloud Billing API Details

**Required Permissions:**
- `billing.accounts.get`
- `billing.accounts.list`
- `billing.budgets.get`
- `billing.budgets.list`

**API Endpoints:**
- `GET /v1/billingAccounts/{billingAccountId}` - Get billing account
- `GET /v1/billingAccounts/{billingAccountId}/services/{serviceId}` - Get service costs
- BigQuery export: Query billing export table

**Challenges:**
- Billing data can lag by hours/days
- Need to match charges to specific jobs (by timestamp/service)
- Free tier credits are applied automatically (not separate line items)

---

## Next Steps

1. **Research:** Check if we can query charges per-operation or only aggregate
2. **Design:** Create BillingService interface
3. **Implement:** Add billing API client
4. **Test:** Query actual charges and match to jobs
5. **Reconcile:** Update budget tracking to use actual charges

---

## Questions to Answer

1. Can we get charges per-transcription-job, or only aggregate?
2. How long does billing data lag? (hours? days?)
3. How do we match Google charges to our job IDs?
4. Should we keep our calculations as estimates until actual charges arrive?

