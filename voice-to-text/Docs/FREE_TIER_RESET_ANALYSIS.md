# Free Tier Reset Analysis

**Date:** 2025-11-17  
**Question:** Can we query Google Cloud to get actual free tier credit availability and reset date?

---

## Current Implementation

**What We're Doing:**
- Tracking free tier usage in `budget_tracking.json`
- Resetting on calendar month change (YYYY-MM format)
- Hardcoded limit: 60 minutes/month
- Reset detection: Compares current month string to stored month

**Reset Logic:**
```python
current_month = datetime.now().strftime("%Y-%m")  # "2025-11"
if data.get("month") != current_month:
    # Reset free tier usage
```

**Limitation:**
- Resets at midnight on the 1st of each month (calendar month)
- But Google's billing cycle might be different (billing account start date)

---

## Google Cloud Free Tier Details

**From Documentation:**
- ✅ 60 minutes of audio processing per billing account per month
- ✅ Resets at the beginning of each calendar month
- ❌ No API to query remaining free tier credit
- ❌ No API to query reset date

**Billing Cycle:**
- Free tier resets on calendar month (not billing account anniversary)
- Example: Resets on Nov 1, Dec 1, Jan 1, etc.
- Not tied to when you created the billing account

---

## Can We Query Google Cloud?

### Option 1: Cloud Billing API
- **What it provides:** Billing account info, costs, budgets
- **Free tier info:** ❌ Not available
- **Reset date:** ❌ Not exposed

### Option 2: Cloud Monitoring API
- **What it provides:** Usage metrics, quotas
- **Free tier info:** ❌ Not specifically for free tier
- **Reset date:** ❌ Not available

### Option 3: Service Usage API
- **What it provides:** Service quotas, limits
- **Free tier info:** ❌ Not available
- **Reset date:** ❌ Not available

**Conclusion:** Google doesn't expose free tier credit/remaining via API.

---

## What We Can Do

### Current Approach (Best Available)
1. **Track usage ourselves** in `budget_tracking.json`
2. **Reset on calendar month** (matches Google's reset)
3. **Calculate remaining:** `60 - free_tier_used`

### Enhancements We Could Add
1. **Show reset date in UI:** "Resets on Dec 1, 2025"
2. **Add reset countdown:** "Resets in 14 days"
3. **Store reset history:** Track when resets happened
4. **Validate against billing console:** Manual verification option

---

## Implementation Recommendation

**Keep current approach but enhance:**
1. ✅ Continue tracking usage ourselves (Google doesn't provide API)
2. ✅ Continue resetting on calendar month (matches Google)
3. ➕ Add reset date calculation and display
4. ➕ Add days until reset countdown

**Reset Date Calculation:**
```python
from datetime import datetime
from calendar import monthrange

now = datetime.now()
# Next reset is first day of next month
if now.month == 12:
    next_reset = datetime(now.year + 1, 1, 1)
else:
    next_reset = datetime(now.year, now.month + 1, 1)

days_until_reset = (next_reset - now).days
```

---

## Summary

**Can we query Google Cloud for free tier info?**
- ❌ No API available for free tier credit/remaining
- ❌ No API for reset date
- ✅ We must track it ourselves

**Is our reset logic correct?**
- ✅ Yes - Google resets on calendar month (1st of each month)
- ✅ Our logic matches this

**What we should add:**
- Display reset date in UI
- Show days until reset
- Maybe add manual sync option (user can verify in console)

