# Codebase Review Report

**Date:** 2025-11-13  
**Method:** Systematic scanning using TASK_CHECKLIST.md  
**Scope:** All Python files in `app/` directory

---

## Summary

**Total Issues Found:** 25  
**Critical:** 5  
**High Priority:** 8  
**Medium Priority:** 7  
**Low Priority:** 5

---

## Critical Issues (Must Fix)

### 1. **Bug: `self.data_dir` doesn't exist in `jobs.py`**
**File:** `app/services/jobs.py:443`  
**Issue:** References `self.data_dir` which doesn't exist  
**Should be:** `self.TRANSCRIPTS_DIR`  
**Impact:** Will crash when deleting jobs with transcript files  
**Fix:**
```python
# Line 443 - WRONG:
transcript_path = self.data_dir / job["transcript_file"]

# Should be:
transcript_path = self.TRANSCRIPTS_DIR / job["transcript_file"]
```

### 2. **Broken: `discover_speech_metadata()` uses `MessageToDict()` which fails**
**File:** `app/services/transcribe_v2.py:141`  
**Issue:** Uses `MessageToDict(loc)` which fails with "Can not find message descriptor"  
**Observed:** From debug script - this approach doesn't work  
**Impact:** Metadata discovery fails, falls back to hardcoded configs  
**Fix:** Replace with REST API approach (from debug script G.2)

### 3. **Dead Code: `initialize_feature_cache()` not called**
**File:** `app/services/transcribe_v2.py:349-406`  
**Issue:** Function exists but is never called (replaced by `initialize_metadata_cache()`)  
**Impact:** Dead code, confusion, maintenance burden  
**Fix:** Delete function

### 4. **Dead Code: `_query_locations_api()` not called**
**File:** `app/services/transcribe_v2.py:409-507`  
**Issue:** Function exists but is never called, also uses broken `MessageToDict`  
**Impact:** Dead code, uses broken approach  
**Fix:** Delete function

### 5. **Duplicate Function: `get_supported_features()` defined twice**
**File:** `app/services/transcribe_v2.py:310-346` and `510-543`  
**Issue:** Same function name, different signatures  
**Impact:** Second definition shadows first, causes confusion  
**Fix:** Remove duplicate (line 510-543), keep the one with location parameter

---

## High Priority Issues

### 6. **Hardcoded: `MODEL_REGION_CONFIG` dict**
**File:** `app/services/transcribe_v2.py:612-631`  
**Issue:** Hardcoded model → region mappings  
**Impact:** Must manually update when Google adds regions/models  
**Fix:** Discover dynamically from REST API metadata

### 7. **Hardcoded: `REGION_PROXIMITY_MAP` dict**
**File:** `app/services/transcribe_v2.py:635-654`  
**Issue:** Hardcoded geographic proximity mappings  
**Impact:** Doesn't work for new regions Google adds  
**Fix:** Calculate dynamically based on discovered locations

### 8. **Hardcoded: `primary_languages = ['en-US']`**
**File:** `app/main.py:141`  
**Issue:** Hardcoded language list  
**Impact:** Can't easily support other languages  
**Fix:** Make configurable via env var

### 9. **Hardcoded: Multiple `'en-US'` strings**
**File:** `app/main.py:162, 166` and throughout codebase  
**Issue:** Hardcoded language code in multiple places  
**Impact:** Inconsistent, hard to change  
**Fix:** Use variable from config

### 10. **Test Code in Production: TEST MODE configuration**
**File:** `app/main.py:36-47, 307-310, 392`  
**Issue:** Test/debug code in production file  
**Impact:** Principle violation, confusion  
**Fix:** Move to separate test config or remove if not needed

### 11. **Hardcoded: `model_mapping` dict**
**File:** `app/main.py:256-267`  
**Issue:** Hardcoded UI model names → API model names mapping  
**Impact:** Must manually update when new models discovered  
**Fix:** Build dynamically from discovered models

### 12. **Hardcoded: `allowed_extensions` list**
**File:** `app/main.py:273`  
**Issue:** Hardcoded file extension list  
**Impact:** May not match what service actually supports  
**Fix:** Query service for supported formats or document why hardcoded

### 13. **Missing: Language parameter not passed to `submit_job()`**
**File:** `app/main.py:349`  
**Issue:** `submit_job()` called without `language_code` parameter  
**Impact:** Relies on service default, not explicit  
**Fix:** Pass language from request/config

---

## Medium Priority Issues

### 14. **Hardcoded: `REGION_MAPPING` fallback in `storage.py`**
**File:** `app/services/storage.py:304-325`  
**Issue:** Hardcoded bucket → Speech region mapping  
**Impact:** Fallback may not match discovered locations  
**Fix:** Use discovered locations from metadata cache

### 15. **Hardcoded: Default language `'en-US'` in function signatures**
**File:** Multiple files - `transcribe_v2.py` functions default to `'en-US'`  
**Issue:** Hardcoded default language throughout  
**Impact:** Inconsistent, hard to change  
**Fix:** Use configurable default

### 16. **Inconsistent: Cache key format**
**File:** `app/services/transcribe_v2.py`  
**Issue:** Some functions use `(location, language, model)`, others use `(model, language)`  
**Impact:** Cache misses, confusion  
**Fix:** Standardize on `(location, language, model)`

### 17. **Debug Code: DEBUG logging statements**
**File:** `app/services/transcribe_v2.py:1285-1297`  
**Issue:** Extensive DEBUG logging left in production code  
**Impact:** Verbose logs, should be debug level or removed  
**Fix:** Change to logger.debug() or remove

### 18. **TODO: Phrase hints disabled**
**File:** `app/services/transcribe_v2.py:1182, 1194`  
**Issue:** Phrase hints commented out with TODO  
**Impact:** Feature disabled, needs implementation  
**Fix:** Implement V2 phrase hints syntax or remove TODO

### 19. **TODO: Library validation not implemented**
**File:** `app/services/library.py:310`  
**Issue:** `validate_library()` is a stub  
**Impact:** Can't detect orphaned data  
**Fix:** Implement validation logic or remove stub

### 20. **Duplicate Service Initialization**
**File:** `app/main.py:104` and `341`  
**Issue:** `transcription_service` initialized at module level, then new instance created in endpoint  
**Impact:** Wasted resources, potential confusion  
**Fix:** Reuse module-level instance or create factory

---

## Low Priority Issues

### 21. **Unused Import: `struct_pb2`**
**File:** `app/services/transcribe_v2.py:26`  
**Issue:** Imported but not used  
**Impact:** Minor, cleanup  
**Fix:** Remove unused import

### 22. **Unused Import: `Parse` from protobuf**
**File:** `app/services/transcribe_v2.py:25`  
**Issue:** `Parse` imported but not used  
**Impact:** Minor, cleanup  
**Fix:** Remove unused import

### 23. **Unused Import: `monthrange` from calendar**
**File:** `app/services/budget.py:12`  
**Issue:** Imported but not used  
**Impact:** Minor, cleanup  
**Fix:** Remove unused import

### 24. **Hardcoded: Free tier limits**
**File:** `app/services/budget.py:62, 68`  
**Issue:** Hardcoded `60.0` minutes and `5.0` credit limits  
**Impact:** Should be configurable if limits change  
**Fix:** Make configurable or document why hardcoded

### 25. **Hardcoded: Yoga vocabulary in `transcribe_v1.py`**
**File:** `app/services/transcribe_v1.py:53-63`  
**Issue:** Hardcoded yoga vocabulary list  
**Impact:** Should be configurable or shared with V2  
**Fix:** Extract to shared config or make configurable

---

## Principle Violations

### "Observe Before Implement" Violations
- ❌ `discover_speech_metadata()` uses `MessageToDict()` without observing it fails
- ❌ `_query_locations_api()` uses broken approach without verification

### "Root Cause Over Band-Aids" Violations
- ❌ Hardcoded configs instead of dynamic discovery
- ❌ Test code in production instead of proper test infrastructure

### "Simple But Robust" Violations
- ❌ Dead code increases complexity
- ❌ Duplicate functions create confusion

### "Verify Before Trust" Violations
- ❌ Using `MessageToDict()` without verifying it works
- ❌ Hardcoded values without verifying they're correct

---

## Files Requiring Changes

1. **`app/services/transcribe_v2.py`** - Major refactor needed
   - Replace broken discovery
   - Remove dead code
   - Fix duplicate functions
   - Replace hardcoded configs

2. **`app/main.py`** - Multiple fixes needed
   - Remove test code
   - Make languages configurable
   - Make model mapping dynamic
   - Fix duplicate service init

3. **`app/services/storage.py`** - Minor fix
   - Use discovered locations

4. **`app/services/jobs.py`** - Bug fix
   - Fix `self.data_dir` → `self.TRANSCRIPTS_DIR`

5. **`app/services/library.py`** - TODO
   - Implement validation or remove stub

6. **`app/services/budget.py`** - Minor cleanup
   - Remove unused import

7. **`app/services/transcribe_v1.py`** - Minor
   - Consider extracting yoga vocabulary

---

## Recommended Fix Order

1. **Fix bug first** (`jobs.py` line 443) - prevents crashes
2. **Replace broken discovery** (`transcribe_v2.py`) - enables dynamic config
3. **Remove dead code** (`transcribe_v2.py`) - reduces complexity
4. **Fix duplicate function** (`transcribe_v2.py`) - prevents confusion
5. **Remove test code** (`main.py`) - principle violation
6. **Make configs dynamic** (`transcribe_v2.py`, `main.py`) - root cause fixes
7. **Cleanup** (unused imports, TODOs) - polish

---

## Notes

- All issues found through systematic scanning (grep, codebase search, file reading)
- Issues categorized by severity and principle violations
- Each issue includes file location, description, impact, and fix direction
- This report should be used with PLAN_METADATA_DISCOVERY_FIX.md for implementation

