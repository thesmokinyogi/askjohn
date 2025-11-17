# Error Handling Priority Matrix

**Date:** 2025-11-13  
**Analysis:** Likelihood vs. Complexity for error handling fixes

---

## Priority Matrix

| Issue | Likelihood | Complexity | Priority | Action |
|-------|-----------|------------|----------|--------|
| **1. Auth Exceptions** | Medium | **Simple** | **HIGH** | ✅ Fix now |
| **2. JSON Parsing** | Low | **Simple** | Medium | ✅ Fix now |
| **3. Discovery Validation** | Medium | **Simple** | **HIGH** | ✅ Fix now |
| **4. Partial Failure Logging** | Medium | Medium | Medium | Consider |
| **5. Structure Validation** | Very Low | Medium | Low | Skip |
| **6. Runtime Lookup** | Low | **Simple** | Low | Optional |
| **7. Hardcoded Locations** | Low | Complex | Low | Skip |
| **8. Timeout Optimization** | Low | Complex | Low | Skip |

---

## Detailed Analysis

### 🔴 HIGH PRIORITY - Fix Now

#### 1. Authentication Exceptions (Simple Fix)

**Likelihood:** Medium
- Happens if credentials misconfigured
- Happens if service account key expired
- Happens if GOOGLE_APPLICATION_CREDENTIALS path wrong
- **Real-world frequency:** Once per misconfiguration (not rare during setup)

**Complexity:** **Simple** (5 minutes)
- Add 2 try/except blocks
- Import exception types
- Return None on failure
- ~10 lines of code

**Impact if not fixed:**
- Service won't start at all
- No graceful degradation
- Hard to diagnose (cryptic exception)

**Fix:**
```python
try:
    credentials, _ = default(scopes=['https://www.googleapis.com/auth/cloud-platform'])
    auth_request = AuthRequest()
    credentials.refresh(auth_request)
    token = credentials.token
    if not token:
        return None
except (google.auth.exceptions.DefaultCredentialsError, 
        google.auth.exceptions.RefreshError) as e:
    logger.error(f"Auth failed for {location}: {e}")
    return None
```

**Verdict:** ✅ **Fix immediately** - High impact, simple fix

---

#### 2. JSON Parsing Exceptions (Simple Fix)

**Likelihood:** Low
- Google API is stable, unlikely to return invalid JSON
- Could happen with network corruption
- Could happen if API returns error page (HTML instead of JSON)
- **Real-world frequency:** Very rare, but possible

**Complexity:** **Simple** (2 minutes)
- Wrap `response.json()` in try/except
- ~3 lines of code

**Impact if not fixed:**
- Crashes discovery for that location
- Other locations still work (graceful degradation exists)
- But error is cryptic

**Fix:**
```python
try:
    return response.json()
except json.JSONDecodeError as e:
    logger.warning(f"Invalid JSON from {location}: {e}")
    return None
```

**Verdict:** ✅ **Fix now** - Simple, prevents rare but possible crash

---

#### 3. Discovery Success Validation (Simple Fix)

**Likelihood:** Medium
- If all locations fail (network issues, auth problems)
- If discovery returns `success: False`
- **Real-world frequency:** Happens when there are systemic issues

**Complexity:** **Simple** (5 minutes)
- Add 2 if statements to check `metadata['success']` and `available_locations`
- Raise exception if validation fails
- ~5 lines of code

**Impact if not fixed:**
- Service starts with empty cache
- Runtime failures when trying to use features
- Misleading - service "starts" but doesn't work

**Fix:**
```python
metadata = discover_speech_metadata(project_id, languages)

if not metadata.get('success', False):
    raise ValueError("Metadata discovery failed")

if not metadata.get('available_locations'):
    raise ValueError("No locations discovered")
```

**Verdict:** ✅ **Fix now** - Prevents silent failures, simple fix

---

### 🟡 MEDIUM PRIORITY - Consider

#### 4. Partial Failure Logging (Medium Complexity)

**Likelihood:** Medium
- Some locations succeed, some fail (common in real world)
- Network issues, regional outages, etc.

**Complexity:** Medium (15 minutes)
- Track which locations succeeded/failed
- Log summary at end
- Distinguish failure types
- ~20 lines of code

**Impact if not fixed:**
- Hard to diagnose which locations failed
- But service still works with partial data

**Verdict:** ⚠️ **Consider** - Helpful for debugging, but not critical

---

### 🟢 LOW PRIORITY - Skip or Optional

#### 5. Structure Validation Edge Cases (Medium Complexity)

**Likelihood:** Very Low
- Google API structure is stable
- We already check `isinstance()` for most things
- Edge cases are theoretical

**Complexity:** Medium
- Add more validation checks
- Add debug logging
- ~15 lines of code

**Verdict:** ❌ **Skip** - Very unlikely, already mostly handled

---

#### 6. Runtime Lookup Improvements (Simple)

**Likelihood:** Low
- Cache misses are already handled
- Fallback works
- Just could be more informative

**Complexity:** Simple (5 minutes)
- Add better logging messages
- ~5 lines of code

**Verdict:** ⚠️ **Optional** - Nice to have, not critical

---

#### 7. Hardcoded Location List (Complex)

**Likelihood:** Low
- Google rarely adds new regions
- When they do, we can update manually
- Current list covers all major regions

**Complexity:** Complex
- Would need to query "list locations" endpoint (if it exists)
- Or maintain dynamic discovery
- Significant refactoring

**Verdict:** ❌ **Skip** - Low value, high effort

---

#### 8. Timeout Optimization (Complex)

**Likelihood:** Low
- Current 10s timeout per location is reasonable
- Sequential queries are slow but safe
- Parallel would be faster but more complex

**Complexity:** Complex
- Add concurrent.futures
- Handle thread safety
- More error handling complexity
- ~50+ lines of code

**Verdict:** ❌ **Skip** - Optimization, not a bug fix

---

## Recommended Action Plan

### Phase 1: Critical Fixes (15 minutes total)
1. ✅ Add auth exception handling (5 min)
2. ✅ Add JSON parsing exception handling (2 min)
3. ✅ Add discovery validation (5 min)
4. ✅ Test fixes (3 min)

**Total:** ~15 minutes for all critical fixes

### Phase 2: Optional Improvements (if time permits)
- Add partial failure logging (15 min)
- Improve runtime lookup messages (5 min)

### Phase 3: Skip
- Structure validation edge cases
- Hardcoded location list
- Timeout optimization

---

## Summary

**Fix Now (High Priority):**
- Auth exceptions (Simple, Medium likelihood, High impact)
- JSON parsing (Simple, Low likelihood, Medium impact)
- Discovery validation (Simple, Medium likelihood, High impact)

**Total Effort:** ~15 minutes for all critical fixes

**Skip:**
- Everything else is either very unlikely, already handled, or too complex for the value

---

## Decision Framework

**Fix if:**
- Likelihood: Medium+ AND Complexity: Simple
- OR Impact: High AND Complexity: Simple

**Skip if:**
- Likelihood: Very Low
- OR Complexity: Complex (unless impact is critical)
- OR Already mostly handled

