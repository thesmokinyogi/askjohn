# Status Update: Critical Issues Complete

**Date:** 2025-11-13  
**Session:** Critical fixes + error handling + Probe List Strategy

---

## ✅ Completed (All Critical Issues)

### Critical Issues - All Fixed
1. ✅ **Bug fix:** `jobs.py:443` - `self.data_dir` → `self.TRANSCRIPTS_DIR`
2. ✅ **Broken discovery:** Replaced `discover_speech_metadata()` with REST API approach
3. ✅ **Dead code:** Removed `initialize_feature_cache()` and `_query_locations_api()`
4. ✅ **Duplicate function:** Removed duplicate `get_supported_features()`, fixed call site
5. ✅ **Bug fix:** Fixed `_get_fallback_features()` call (removed extra parameter)

### Error Handling - All Critical Fixes
6. ✅ **Auth exceptions:** Added handling for `DefaultCredentialsError` and `RefreshError`
7. ✅ **JSON parsing:** Added handling for `JSONDecodeError`
8. ✅ **Discovery validation:** Added validation for `success` and `available_locations`

### Architecture Improvements
9. ✅ **Probe List Strategy:** Refactored to official Google Cloud pattern with documentation
10. ✅ **Dependencies:** Added `requests` to requirements.txt

---

## 📋 Remaining High Priority Issues

### From CODEBASE_REVIEW_REPORT.md:

**Issue #6: Hardcoded `MODEL_REGION_CONFIG` dict**
- **File:** `app/services/transcribe_v2.py:612-631`
- **Issue:** Hardcoded model → region mappings
- **Impact:** Must manually update when Google adds regions/models
- **Fix:** Discover dynamically from REST API metadata

**Issue #7: Hardcoded `REGION_PROXIMITY_MAP` dict**
- **File:** `app/services/transcribe_v2.py:635-654`
- **Issue:** Hardcoded geographic proximity mappings
- **Impact:** Doesn't work for new regions Google adds
- **Fix:** Calculate dynamically based on discovered locations

**Issue #8: Hardcoded `primary_languages = ['en-US']`**
- **File:** `app/main.py:141`
- **Issue:** Hardcoded language list
- **Impact:** Can't easily support other languages
- **Fix:** Make configurable via env var

**Issue #9: Hardcoded Multiple `'en-US'` strings**
- **File:** `app/main.py:162, 166` and throughout
- **Issue:** Hardcoded language code in multiple places
- **Impact:** Inconsistent, hard to change
- **Fix:** Use variable from config

**Issue #10: Test Code in Production**
- **File:** `app/main.py:36-47, 307-310, 392`
- **Issue:** TEST MODE configuration in production file
- **Impact:** Principle violation, confusion
- **Fix:** Move to separate test config or remove if not needed

**Issue #11: Hardcoded `model_mapping` dict**
- **File:** `app/main.py:256-267`
- **Issue:** Hardcoded UI model names → API model names mapping
- **Impact:** Must manually update when new models discovered
- **Fix:** Build dynamically from discovered models

**Issue #12: Hardcoded `allowed_extensions` list**
- **File:** `app/main.py:273`
- **Issue:** Hardcoded file extension list
- **Impact:** May not match what service actually supports
- **Fix:** Query service for supported formats or document why hardcoded

**Issue #13: Missing Language Parameter**
- **File:** `app/main.py:349`
- **Issue:** `submit_job()` called without `language_code` parameter
- **Impact:** Relies on service default, not explicit
- **Fix:** Pass language from request/config

---

## 🎯 Recommended Next Steps

### Option A: Continue with High Priority Issues
**Focus:** Issues #6 and #7 (MODEL_REGION_CONFIG, REGION_PROXIMITY_MAP)
- These relate directly to the metadata discovery work we just completed
- Can leverage the discovered metadata to make these dynamic
- Natural continuation of the work we've done

### Option B: Test Current Implementation
**Focus:** Verify all critical fixes work correctly
- Test metadata discovery with real API calls
- Verify error handling works
- Ensure no regressions

### Option C: Address Principle Violations
**Focus:** Issue #10 (Test code in production)
- Clean up TEST MODE configuration
- Move to proper test infrastructure or remove

---

## 💭 Decision Point

**What should we tackle next?**

1. **High Priority Issues #6-7** (Make MODEL_REGION_CONFIG and REGION_PROXIMITY_MAP dynamic)
   - Natural continuation of metadata discovery work
   - Leverages what we just built

2. **Test Current Implementation**
   - Verify everything works before moving on
   - Good practice after major refactoring

3. **Clean Up (Issue #10)**
   - Remove test code from production
   - Quick win, principle violation

4. **Something else?**

---

## 📊 Progress Summary

- **Critical Issues:** 5/5 complete (100%)
- **Error Handling:** 3/3 critical fixes complete (100%)
- **High Priority Issues:** 0/8 complete (0%)
- **Medium Priority Issues:** 0/7 complete (0%)
- **Low Priority Issues:** 0/5 complete (0%)

**Overall:** Critical work complete, ready for next phase.

