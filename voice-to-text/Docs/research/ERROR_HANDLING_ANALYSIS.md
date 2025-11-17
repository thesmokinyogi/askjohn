# Error Handling Analysis

**Date:** 2025-11-13  
**Scope:** Critical fixes implementation - REST API metadata discovery  
**Purpose:** Identify failure modes, edge cases, and error handling gaps

---

## Current Error Handling State

### ✅ What's Handled

1. **REST API Helper (`_discover_location_metadata_via_rest_api`)**
   - ✅ Catches `requests.exceptions.RequestException` (network errors, HTTP errors)
   - ✅ Catches generic `Exception` (unexpected errors)
   - ✅ Returns `None` on failure (graceful degradation)
   - ✅ Logs warnings for failures

2. **Discovery Function (`discover_speech_metadata`)**
   - ✅ Handles missing metadata gracefully (skips location)
   - ✅ Handles missing structure keys (skips location/language)
   - ✅ Handles type mismatches (checks `isinstance`)
   - ✅ Returns `success: False` if no locations succeed
   - ✅ Continues processing other locations if one fails

3. **Cache Initialization (`initialize_metadata_cache`)**
   - ✅ Retry logic with exponential backoff (3 attempts)
   - ✅ Handles exceptions from `discover_speech_metadata`
   - ✅ Sets `_CACHE_LOADED = False` on failure
   - ✅ Logs degradation warnings

4. **Feature Lookup (`get_supported_features`)**
   - ✅ Handles missing cache entries (searches all locations)
   - ✅ Falls back to `_get_fallback_features()` if cache not loaded
   - ✅ Logs warnings for cache misses

---

## 🐛 Bugs Found During Analysis

### Bug: Function Call Mismatch

**Location:** `get_supported_features()` line 401

**Issue:**
```python
return _get_fallback_features(model, language)  # ❌ Called with 2 args
```

But function signature:
```python
def _get_fallback_features(model: str) -> Set[str]:  # Only accepts 1 arg
```

**Impact:** Would raise `TypeError: _get_fallback_features() takes 1 positional argument but 2 were given`

**Status:** ✅ Fixed - Removed `language` parameter from call

---

## ⚠️ Error Handling Gaps

### 1. **Authentication Failures**

**Location:** `_discover_location_metadata_via_rest_api()` lines 58-61

**Current Behavior:**
```python
credentials, _ = default(scopes=['https://www.googleapis.com/auth/cloud-platform'])
auth_request = AuthRequest()
credentials.refresh(auth_request)
```

**Potential Failures:**
- `default()` could raise `google.auth.exceptions.DefaultCredentialsError`
- `credentials.refresh()` could raise `google.auth.exceptions.RefreshError`
- Token could be `None` or invalid

**Current Handling:** ❌ Not caught - would bubble up as unhandled exception

**Impact:** 
- High - Would crash discovery on startup
- Would prevent service from starting

**Recommendation:**
```python
try:
    credentials, _ = default(scopes=['https://www.googleapis.com/auth/cloud-platform'])
    auth_request = AuthRequest()
    credentials.refresh(auth_request)
    token = credentials.token
    if not token:
        logger.error(f"Failed to get auth token for {location}")
        return None
except google.auth.exceptions.DefaultCredentialsError as e:
    logger.error(f"Authentication failed: {e}")
    return None
except google.auth.exceptions.RefreshError as e:
    logger.error(f"Token refresh failed: {e}")
    return None
```

---

### 2. **JSON Parsing Failures**

**Location:** `_discover_location_metadata_via_rest_api()` line 76

**Current Behavior:**
```python
return response.json()
```

**Potential Failures:**
- Invalid JSON in response
- Empty response body
- Response encoding issues

**Current Handling:** ❌ Not caught - would raise `json.JSONDecodeError`

**Impact:**
- Medium - Would crash discovery for that location
- Other locations would still be processed

**Recommendation:**
```python
try:
    return response.json()
except json.JSONDecodeError as e:
    logger.warning(f"Invalid JSON response from {location}: {e}")
    return None
```

---

### 3. **Partial Discovery Failures**

**Location:** `discover_speech_metadata()` lines 179-267

**Current Behavior:**
- If all locations fail, returns `success: False` but still returns empty dicts
- If some locations fail, continues with successful ones

**Potential Issues:**
- What if 0 locations succeed but we need at least one?
- What if critical locations (like `us-central1`) all fail?
- What if requested language not found in any location?

**Current Handling:** ⚠️ Partial - Returns `success: False` but doesn't distinguish between:
- "No locations available" vs "Language not found" vs "Network failure"

**Impact:**
- Medium - Service might start with incomplete metadata
- Could lead to runtime failures when using unsupported models/regions

**Recommendation:**
- Add more granular success indicators
- Log specific failure reasons
- Consider minimum threshold (e.g., require at least 3 locations)

---

### 4. **Structure Validation**

**Location:** `discover_speech_metadata()` lines 189-221

**Current Behavior:**
- Checks for key existence
- Checks `isinstance()` for types
- Skips invalid entries

**Potential Issues:**
- What if `models_by_lang[language]` is not a dict but code expects dict?
- What if `modelFeature` array contains unexpected structure?
- What if feature objects missing `'feature'` key?

**Current Handling:** ✅ Mostly handled - checks `isinstance()` and skips invalid entries

**Edge Cases:**
- ⚠️ What if `modelFeature` is a dict instead of list? (Currently checks `isinstance(feature_list, list)` but what if it's a dict?)
- ⚠️ What if feature object has `'feature'` key but value is `None`? (Currently checks `if feature_name:` which handles this)

**Recommendation:**
- Add explicit validation for `modelFeature` being a list
- Add logging for unexpected structures (debug level)

---

### 5. **Cache Initialization Edge Cases**

**Location:** `initialize_metadata_cache()` lines 292-338

**Current Behavior:**
- Retries 3 times with exponential backoff
- Sets `_CACHE_LOADED = False` on failure
- Returns `False` to indicate failure

**Potential Issues:**
- What if `discover_speech_metadata()` returns `success: False` but no exception?
- What if metadata dict missing expected keys?
- What if cache partially populated (some locations succeed, some fail)?

**Current Handling:** ⚠️ Partial
- If `discover_speech_metadata()` raises exception, retries
- If it returns `success: False`, still populates cache with empty data
- Doesn't check `metadata['success']` before using data

**Impact:**
- Medium - Could populate cache with empty/incomplete data
- Service would start but feature detection wouldn't work

**Recommendation:**
```python
metadata = discover_speech_metadata(project_id, languages)

# Check if discovery actually succeeded
if not metadata.get('success', False):
    raise ValueError("Metadata discovery returned success=False")

# Verify we got some data
if not metadata.get('available_locations'):
    raise ValueError("No locations discovered")

# Then populate caches...
```

---

### 6. **Runtime Feature Lookup Failures**

**Location:** `get_supported_features()` lines 372-408

**Current Behavior:**
- If location specified, tries direct lookup
- If not found, searches all locations
- Falls back to `_get_fallback_features()` if cache not loaded

**Potential Issues:**
- What if cache loaded but model/language not found in any location?
- What if location specified but doesn't exist in cache?
- What if cache has stale/incomplete data?

**Current Handling:** ✅ Mostly handled
- Logs warning for cache misses
- Falls back to minimal feature set
- Returns empty set if not found

**Edge Cases:**
- ⚠️ What if `location` parameter is invalid (e.g., typo like `'us-cental1'`)?
- Currently searches all locations, which is fine, but could log more clearly

**Recommendation:**
- Add explicit check: "Location X not in cache, searching all locations..."
- Consider returning more informative error messages

---

### 7. **Hardcoded Location List**

**Location:** `discover_speech_metadata()` lines 167-172

**Current Behavior:**
- Hardcoded list of 20 known locations
- Queries each one sequentially

**Potential Issues:**
- What if Google adds new regions? (Won't be discovered)
- What if a region is deprecated? (Will fail silently)
- What if `'us'` is not a valid location? (Will fail for that one)

**Current Handling:** ⚠️ Partial
- Individual location failures are handled (skipped)
- But hardcoded list is a limitation

**Impact:**
- Low-Medium - New regions won't be discovered automatically
- But existing regions will work

**Recommendation:**
- Consider querying a "list locations" endpoint first (if available)
- Or document that new regions need to be added manually
- Add comment explaining why list is hardcoded

---

### 8. **Timeout Handling**

**Location:** `_discover_location_metadata_via_rest_api()` line 72

**Current Behavior:**
```python
response = requests.get(rest_url, headers=headers, timeout=10)
```

**Potential Issues:**
- 10 second timeout per location
- 20 locations × 10 seconds = up to 200 seconds if all timeout
- No overall timeout for entire discovery process

**Current Handling:** ✅ Handled
- Individual requests have timeout
- But entire discovery could take a long time

**Impact:**
- Low - Individual timeouts are handled
- But startup could be slow if many locations timeout

**Recommendation:**
- Consider parallel requests (with `concurrent.futures`)
- Or reduce timeout for faster failure
- Or add overall timeout for discovery process

---

## Error Scenarios & Expected Behavior

### Scenario 1: Network Failure During Discovery

**What Happens:**
- `_discover_location_metadata_via_rest_api()` catches `RequestException`
- Returns `None` for that location
- `discover_speech_metadata()` skips location, continues
- If all locations fail, returns `success: False`

**Expected:** ✅ Handled correctly

---

### Scenario 2: Authentication Failure

**What Happens:**
- `default()` or `refresh()` raises exception
- Currently NOT caught - would crash discovery

**Expected:** ❌ Should catch and handle gracefully

**Fix Needed:** Add auth exception handling

---

### Scenario 3: Invalid JSON Response

**What Happens:**
- `response.json()` raises `JSONDecodeError`
- Currently NOT caught - would crash discovery for that location

**Expected:** ❌ Should catch and skip location

**Fix Needed:** Add JSON parsing exception handling

---

### Scenario 4: Partial Discovery Success

**What Happens:**
- Some locations succeed, some fail
- Returns `success: True` if any location succeeds
- Cache populated with partial data

**Expected:** ⚠️ Works but could be more informative

**Enhancement:** Log which locations succeeded/failed

---

### Scenario 5: Language Not Found

**What Happens:**
- Requested language not in any location's metadata
- `models_by_location` and `features_by_model` remain empty
- Returns `success: True` (if locations succeeded)

**Expected:** ⚠️ Works but misleading - `success: True` but no data for language

**Enhancement:** Check if requested languages were found

---

### Scenario 6: Cache Not Loaded at Runtime

**What Happens:**
- `get_supported_features()` called but `_CACHE_LOADED = False`
- Falls back to `_get_fallback_features()`
- Returns minimal safe feature set

**Expected:** ✅ Handled correctly

---

## Recommendations Summary

### Critical (Must Fix)

1. **Add authentication exception handling** in `_discover_location_metadata_via_rest_api()`
   - Catch `DefaultCredentialsError` and `RefreshError`
   - Return `None` instead of crashing

2. **Add JSON parsing exception handling** in `_discover_location_metadata_via_rest_api()`
   - Catch `JSONDecodeError`
   - Return `None` instead of crashing

### Important (Should Fix)

3. **Validate discovery success** in `initialize_metadata_cache()`
   - Check `metadata['success']` before using data
   - Verify at least some locations were discovered
   - Raise exception if discovery completely failed

4. **Improve partial failure reporting** in `discover_speech_metadata()`
   - Log which locations succeeded/failed
   - Distinguish between "no locations" vs "no language data"
   - Return more granular success indicators

### Nice to Have (Enhancements)

5. **Add structure validation logging** (debug level)
   - Log when unexpected structures encountered
   - Help diagnose API changes

6. **Consider parallel requests** for location discovery
   - Speed up startup
   - Reduce overall timeout risk

7. **Document hardcoded location list**
   - Explain why it's hardcoded
   - Note that new regions need manual addition

---

## Testing Recommendations

### Test Cases to Add

1. **Authentication failure test**
   - Mock `default()` to raise `DefaultCredentialsError`
   - Verify graceful handling

2. **JSON parsing failure test**
   - Mock response with invalid JSON
   - Verify location is skipped

3. **Partial discovery test**
   - Mock some locations succeed, some fail
   - Verify cache populated with partial data

4. **Empty discovery test**
   - Mock all locations fail
   - Verify `success: False` returned
   - Verify cache initialization handles it

5. **Language not found test**
   - Mock language not in any location
   - Verify graceful handling

---

## Risk Assessment

| Issue | Severity | Likelihood | Impact | Priority |
|------|----------|------------|--------|----------|
| Auth exception not caught | High | Medium | Service won't start | Critical |
| JSON parsing not caught | Medium | Low | Location discovery fails | Important |
| Partial discovery not validated | Medium | Medium | Incomplete cache | Important |
| Hardcoded location list | Low | Low | New regions not discovered | Nice to have |

---

## Next Steps

1. **Fix critical issues** (auth + JSON exceptions)
2. **Add validation** in cache initialization
3. **Improve logging** for partial failures
4. **Test error scenarios**
5. **Document edge cases**

---

## Questions for Discussion

1. **Should we fail fast if discovery completely fails?**
   - Current: Service starts with fallback
   - Alternative: Fail startup if no locations discovered

2. **Should we require minimum number of locations?**
   - Current: Any success = OK
   - Alternative: Require at least 3-5 locations

3. **How should we handle new regions?**
   - Current: Must manually add to hardcoded list
   - Alternative: Try to discover dynamically (if API supports)

4. **Should we parallelize location queries?**
   - Current: Sequential (slow but safe)
   - Alternative: Parallel with thread pool (faster but more complex)

