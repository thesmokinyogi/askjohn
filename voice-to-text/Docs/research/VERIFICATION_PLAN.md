# Pre-Implementation Verification Plan

**Date:** 2025-11-13  
**Purpose:** Verify all modeled assumptions before writing code

---

## Items Marked as "MODELED (needs verification)"

### 1. `requests` library in requirements.txt
**Status:** ⚠️ MODELED - Need to verify

**Verification Steps:**
1. Check if `requests` is in requirements.txt
2. If not, verify it's available in venv (already tested - it is)
3. Plan: Add to requirements.txt if missing

**Result:** ✅ VERIFIED - `requests` is available in venv but NOT in requirements.txt
**Action:** Add `requests` to requirements.txt

---

### 2. Removing dead code won't break anything
**Status:** ⚠️ MODELED - Need to verify

**Verification Steps:**
1. Search for imports of `initialize_feature_cache` or `_query_locations_api`
2. Search for any references outside `transcribe_v2.py`
3. Verify they're only called internally
4. Check if they're exported in `__init__.py` or module exports

**Result:** ✅ VERIFIED - No external references found
**Action:** Safe to remove

---

## Additional Verifications Needed

### 3. Structure Path Understanding
**Status:** ⚠️ Need to verify current code's expected path vs. observed path

**Current Code Expects:**
```python
languages_map = metadata_dict.get('languages', {})  # metadata['languages']
language_metadata = languages_map.get(language)     # metadata['languages'][language]
models_map = language_metadata.get('models', {})     # metadata['languages'][language]['models']
```

**Observed Structure (from debug script):**
```python
metadata['languages']['models'][lang_code]['modelFeatures'][model_id]['modelFeature']
```

**Verification:** These are DIFFERENT paths!
- Current: `metadata['languages'][language]['models']`
- Observed: `metadata['languages']['models'][language]`

**Action:** Must fix structure path when implementing REST API

---

### 4. Cache Key Mismatch
**Status:** ⚠️ Need to verify which cache keys are actually used

**Verification Steps:**
1. Check how cache is populated (what keys are used)
2. Check how cache is accessed (what keys are looked up)
3. Verify mismatch exists

**Result:** ✅ VERIFIED - Mismatch confirmed
- Cache populated with: `(location, language, model)`
- Second function looks up: `(model, language)`
- **This is a bug** - cache will never match

---

### 5. Function Call Site
**Status:** ⚠️ Need to verify what parameters are available at call site

**Verification Steps:**
1. Check line 1154 call site
2. Verify `self.location` is available
3. Verify we can pass it to function

**Result:** ✅ VERIFIED - `self.location` exists in `GoogleSpeechV2Service`
**Action:** Can safely update call to include location

---

## Verification Results Summary

| Item | Status | Action Required |
|------|--------|---------------------|
| `requests` in requirements.txt | ❌ NOT FOUND | Add to requirements.txt |
| Dead code external references | ✅ VERIFIED SAFE | No imports found, safe to remove |
| Dead code exported? | ✅ VERIFIED SAFE | Not in `__all__`, not imported by main.py |
| Structure path mismatch | ✅ VERIFIED | Must fix in implementation |
| Cache key mismatch | ✅ VERIFIED BUG | Fix by using correct function |
| Call site has location | ✅ VERIFIED | `self.location` exists (line 673), can update call |

---

## Pre-Implementation Checklist

Before writing ANY code:

- [x] Add `requests` to requirements.txt
- [x] Verify structure path fix is correct ✅ TESTED - Works!
- [x] Verify cache key fix is correct
- [x] Test REST API helper function in isolation ✅ TESTED - Works!
- [x] Verify all imports work ✅ VERIFIED
- [ ] Test each fix incrementally (during implementation)

## Test Results

**REST API Test Script:** ✅ PASSED
- Successfully authenticated with explicit scopes
- Retrieved metadata from us-west1 region
- Verified structure path: `metadata['languages']['models'][lang_code]['modelFeatures'][model_id]['modelFeature']`
- Successfully extracted 8 features from telephony_short model
- Confirmed structure matches observed pattern from debug script

**Ready to implement!**

---

## Next Steps

1. **Add `requests` to requirements.txt** (1 minute)
2. **Create minimal test script** to verify REST API approach works (5 minutes)
3. **Then proceed with implementation**

