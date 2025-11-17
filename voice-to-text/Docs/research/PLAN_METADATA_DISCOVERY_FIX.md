# Plan: Fix Metadata Discovery & Code Cleanup

**Date:** 2025-11-13  
**Status:** Planning Phase  
**Goal:** Replace broken SDK-based discovery with working REST API approach, remove dead code, eliminate hardcoded configs

---

## Pre-Coding Gate Checklist

### ✅ 1. Have I SEEN actual data/responses? (OBSERVED, not modeled)
**YES** - We have **observed** (not assumed) from `debug_metadata_discovery.py` output:
- REST API (G.2) **actually ran** and returned JSON structure
- Path **observed in output**: `metadata.languages.models[lang_code]['modelFeatures'][model_id]['modelFeature']`
- Structure **confirmed empirically** across multiple languages (en-US, es-US, pt-BR, es-MX)
- **Test script feedback is real** - this is observed reality, not a mental model

### ✅ 2. Do I understand the architecture?
**YES** - From cognitive checkpoint:
- SDK doesn't expose `LocationsMetadata` type
- `MessageToDict` fails with descriptor error
- REST API bypasses SDK entirely, returns JSON we can parse
- Structure: `metadata.languages.models[lang_code]['modelFeatures'][model_id]['modelFeature']`

### ✅ 3. Have I found working example code?
**YES** - `debug_metadata_discovery.py` lines 545-690 contain working REST API implementation:
- Auth with explicit scopes: `['https://www.googleapis.com/auth/cloud-platform']`
- GET request to: `https://{region}-speech.googleapis.com/v2/projects/{project_id}/locations/{region}`
- JSON parsing of the response structure

### ✅ 4. Am I coding based on observation or assumption?
**OBSERVATION** - We've **observed** the actual REST API response structure from test script output. This is empirical data, not a mental model.

### ✅ 5. Is my mental model validated by reality?
**YES** - Test script **execution** proves REST API works. Structure is **observed in output**, not assumed from documentation. Auth pattern is **validated by actual test results**.

**Critical Distinction:**
- ❌ **Model/Assumption:** "The docs say it should work like this"
- ✅ **Observation:** "I ran the test script and saw this output"
- ❌ **Model/Assumption:** "This code pattern should work"
- ✅ **Observation:** "I tested this pattern and it produced this result"

---

## Issues to Fix

### Critical Priority

1. **Replace `discover_speech_metadata()` with REST API approach**
   - Current: Uses `MessageToDict(loc)` which fails
   - Fix: Implement REST API call (from debug script G.2)
   - Impact: Enables dynamic metadata discovery

2. **Fix structure path in discovery code**
   - Current: `metadata_dict.get('languages', {}).get(language)` then `.get('models')`
   - Actual: `metadata['languages']['models'][lang_code]['modelFeatures']`
   - Fix: Update path to match observed structure

3. **Remove dead code**
   - `initialize_feature_cache()` (old version, replaced)
   - `_query_locations_api()` (uses broken MessageToDict)
   - Duplicate `get_supported_features()` definition

### High Priority

4. **Replace hardcoded `MODEL_REGION_CONFIG`**
   - Current: Hardcoded dict of model → region mappings
   - Fix: Discover from REST API metadata
   - Impact: Auto-updates when Google adds new regions/models

5. **Replace hardcoded `REGION_PROXIMITY_MAP`**
   - Current: Hardcoded geographic proximity mappings
   - Fix: Use discovered locations, calculate proximity dynamically
   - Impact: Works for any region Google adds

6. **Fix cache key inconsistency**
   - Current: `get_supported_features()` has two different signatures
   - Fix: Standardize on `(location, language, model)` tuple
   - Impact: Prevents cache misses

### Medium Priority

7. **Replace `REGION_MAPPING` fallback in `storage.py`**
   - Current: Hardcoded bucket → Speech region mapping
   - Fix: Use discovered locations from metadata cache
   - Impact: Consistent with dynamic discovery

---

## Implementation Plan

### Phase 1: Create REST API Discovery Function

**File:** `app/services/transcribe_v2.py`

**Action:**
1. Create new function `_discover_metadata_via_rest_api(project_id: str, region: str) -> dict`
2. Copy working pattern from `debug_metadata_discovery.py` lines 545-690
3. Extract auth logic (explicit scopes)
4. Extract GET request logic
5. Extract JSON parsing logic for structure: `metadata.languages.models[lang_code]['modelFeatures'][model_id]['modelFeature']`

**Dependencies:**
- `google.auth` for credentials
- `google.auth.transport.requests` for auth request
- `requests` for HTTP GET

**Validation:**
- Test with `us-west1` region (known to work)
- Verify structure matches debug script output
- Confirm feature extraction works

**Principle:** "Observe Before Implement" - We're using the observed working pattern

---

### Phase 2: Replace `discover_speech_metadata()`

**File:** `app/services/transcribe_v2.py`

**Action:**
1. Replace `discover_speech_metadata()` implementation
2. Remove `MessageToDict(loc)` approach (lines 140-152)
3. Use REST API for each discovered location
4. Fix structure path to: `metadata['languages']['models'][lang_code]['modelFeatures']`
5. Extract features from `modelFeature` array correctly

**Changes:**
```python
# OLD (broken):
location_dict = MessageToDict(loc)
metadata_dict = location_dict.get('metadata', {})
languages_map = metadata_dict.get('languages', {})

# NEW (REST API):
# For each location, call REST API
rest_data = _discover_metadata_via_rest_api(project_id, location_id)
metadata = rest_data.get('metadata', {})
languages_obj = metadata.get('languages', {})
models_by_lang = languages_obj.get('models', {})  # This is the correct path
```

**Validation:**
- Run `initialize_metadata_cache()` at startup
- Verify it discovers locations, models, and features
- Compare with debug script output

**Principle:** "Root Cause Over Band-Aids" - Fixing the broken approach, not patching it

---

### Phase 3: Remove Dead Code

**File:** `app/services/transcribe_v2.py`

**Action:**
1. Delete `initialize_feature_cache()` (lines 349-406) - replaced by `initialize_metadata_cache()`
2. Delete `_query_locations_api()` (lines 409-507) - uses broken MessageToDict
3. Remove duplicate `get_supported_features()` definition (lines 510-543)
4. Keep only the version that uses `(location, language, model)` tuple (lines 310-346)

**Validation:**
- Search codebase for references to deleted functions
- Verify no imports/calls remain
- Run tests to ensure nothing breaks

**Principle:** "Simple But Robust" - Remove complexity that doesn't work

---

### Phase 4: Replace Hardcoded `MODEL_REGION_CONFIG`

**File:** `app/services/transcribe_v2.py`

**Action:**
1. Create function `_discover_model_regions(project_id: str) -> dict`
2. Query REST API for each discovered location
3. Extract which models are available in which regions
4. Build dynamic mapping: `{model: {supported_regions: [...], default_region: ...}}`
5. Replace `MODEL_REGION_CONFIG` usage in `_select_optimal_location()` with dynamic lookup

**Changes:**
```python
# OLD (hardcoded):
model_config = self.MODEL_REGION_CONFIG.get(model, {})

# NEW (dynamic):
model_config = _get_discovered_model_config(model)  # From cache
```

**Fallback:**
- If discovery fails, use minimal safe defaults
- Log warning about degraded mode

**Validation:**
- Verify model selection works for all discovered models
- Test fallback when discovery unavailable

**Principle:** "Root Cause Over Band-Aids" - Dynamic discovery vs hardcoded config

---

### Phase 5: Replace Hardcoded `REGION_PROXIMITY_MAP`

**File:** `app/services/transcribe_v2.py`

**Action:**
1. Create function `_calculate_region_proximity(requested: str, available: list) -> Optional[str]`
2. Use geographic prefixes (us-, europe-, asia-) for matching
3. Prefer same prefix, then fallback to defaults
4. Remove hardcoded `REGION_PROXIMITY_MAP` dict

**Changes:**
```python
# OLD (hardcoded):
nearby_regions = self.REGION_PROXIMITY_MAP.get(requested, [])

# NEW (calculated):
nearest = _calculate_region_proximity(requested, available_regions)
```

**Validation:**
- Test with various region combinations
- Verify fallback logic works

**Principle:** "Simple But Robust" - Calculate instead of hardcode

---

### Phase 6: Fix Cache Key Consistency

**File:** `app/services/transcribe_v2.py`

**Action:**
1. Standardize all cache keys to `(location, language, model)` tuple
2. Update `get_supported_features()` signature to require `location` parameter
3. Update all call sites to pass location
4. Fix cache lookup in `_build_config()` to use correct key

**Changes:**
```python
# OLD (inconsistent):
get_supported_features(model, language)  # Uses (model, language) key
get_supported_features(model, language, location)  # Uses (location, language, model) key

# NEW (consistent):
get_supported_features(model, language, location)  # Always uses (location, language, model)
```

**Validation:**
- Search for all `get_supported_features()` calls
- Update each to include location parameter
- Verify feature detection works correctly

**Principle:** "Root Cause Over Band-Aids" - Fix inconsistency, not work around it

---

### Phase 7: Update `storage.py` Region Mapping

**File:** `app/services/storage.py`

**Action:**
1. Enhance `detect_speech_location()` to use discovered locations
2. Remove hardcoded `REGION_MAPPING` fallback (lines 304-325)
3. Use `get_available_locations()` from metadata cache
4. Calculate proximity dynamically instead of hardcoded table

**Changes:**
```python
# OLD (hardcoded fallback):
REGION_MAPPING = {'us-west1': 'us-central1', ...}

# NEW (dynamic):
speech_v2_regions = get_available_locations()  # From cache
# Calculate best match from discovered regions
```

**Validation:**
- Test with various bucket locations
- Verify it finds correct Speech V2 region

**Principle:** "Root Cause Over Band-Aids" - Use discovered data, not assumptions

---

### Phase 8: Fix Hardcoded Values in `main.py`

**File:** `app/main.py`

**Issues Found:**
1. Hardcoded `primary_languages = ['en-US']` (line 141)
2. Hardcoded `'en-US'` in multiple places (lines 162, 166)
3. TEST MODE configuration in production code (lines 36-47)
4. Hardcoded `model_mapping` dict (lines 256-267)
5. Hardcoded `allowed_extensions` (line 273)
6. Missing language parameter in `submit_job()` call
7. Duplicate service initialization

**Action:**
1. **Make languages configurable:**
   - Add `PRIMARY_LANGUAGES` env var (defaults to `['en-US']`)
   - Use variable instead of hardcoded string

2. **Make model mapping dynamic:**
   - Discover available models from metadata cache
   - Build mapping from discovered models instead of hardcoding
   - Support both UI names (chirp_batch) and API names (chirp)

3. **Make file extensions dynamic:**
   - Query service for supported formats
   - Or at least document why these are hardcoded

4. **Remove/refactor TEST MODE:**
   - Move to separate test config file, or
   - Document it's for development only, or
   - Remove if not actively used

5. **Fix language parameter:**
   - Pass `language_code` to `submit_job()` from request or config
   - Don't rely on service default

6. **Fix duplicate service initialization:**
   - Reuse `transcription_service` from module level
   - Or create service factory that caches instances

**Changes:**
```python
# OLD (hardcoded):
primary_languages = ['en-US']
available_models = get_available_models(SPEECH_LOCATION, 'en-US')

# NEW (configurable):
PRIMARY_LANGUAGES = os.getenv("PRIMARY_LANGUAGES", "en-US").split(",")
available_models = get_available_models(SPEECH_LOCATION, PRIMARY_LANGUAGES[0])
```

```python
# OLD (hardcoded):
model_mapping = {
    'chirp_batch': 'chirp',
    'long_batch': 'long',
    ...
}

# NEW (dynamic):
def _build_model_mapping(location: str, language: str) -> dict:
    """Build model mapping from discovered models."""
    available = get_available_models(location, language)
    mapping = {}
    for model in available:
        mapping[f'{model}_batch'] = model
        mapping[f'{model}_standard'] = model
        mapping[model] = model  # Direct API name
    return mapping
```

**Validation:**
- Test with different language configurations
- Verify model mapping works for all discovered models
- Confirm no regressions in transcription flow

**Principle:** "Simple But Robust" - Make configurable what should be, remove test code from production

---

## Testing Strategy

### Unit Tests (Manual for now)

1. **Test REST API discovery:**
   - Call `_discover_metadata_via_rest_api()` with known region
   - Verify structure matches debug script output
   - Confirm features extracted correctly

2. **Test metadata cache initialization:**
   - Call `initialize_metadata_cache()` at startup
   - Verify locations, models, features discovered
   - Check cache populated correctly

3. **Test feature detection:**
   - Call `get_supported_features('long', 'en-US', 'us-west1')`
   - Verify returns correct feature set
   - Test with different models/locations

4. **Test region selection:**
   - Call `_select_optimal_location()` with various inputs
   - Verify uses discovered regions
   - Test fallback when discovery unavailable

### Integration Tests

1. **End-to-end transcription:**
   - Submit transcription job
   - Verify feature detection works
   - Confirm no errors from hardcoded configs

2. **Startup sequence:**
   - Start server
   - Verify metadata discovery completes
   - Check logs for successful discovery

---

## Risk Assessment

### High Risk
- **Breaking existing functionality** if REST API approach has edge cases
  - **Mitigation:** Keep fallback logic, test thoroughly
  - **Rollback:** Can revert to hardcoded configs if needed

### Medium Risk
- **REST API rate limits** if querying many locations
  - **Mitigation:** Cache results, query only needed locations
  - **Rollback:** Fallback to hardcoded configs

### Low Risk
- **Dead code removal** - low impact, easy to verify
- **Cache key changes** - straightforward refactor

---

## Implementation Order

1. **Phase 1** - Create REST API function (foundation)
2. **Phase 2** - Replace discovery function (core fix)
3. **Phase 3** - Remove dead code (cleanup)
4. **Phase 4** - Replace MODEL_REGION_CONFIG (dynamic config)
5. **Phase 5** - Replace REGION_PROXIMITY_MAP (dynamic config)
6. **Phase 6** - Fix cache keys (consistency)
7. **Phase 7** - Update storage.py (consistency)

**Rationale:** Build foundation first, then replace broken code, then clean up, then make configs dynamic, finally ensure consistency.

---

## Success Criteria

✅ **Metadata discovery works:**
- `initialize_metadata_cache()` succeeds at startup
- Discovers locations, models, features from REST API
- No errors about missing descriptors

✅ **No hardcoded configs:**
- `MODEL_REGION_CONFIG` replaced with dynamic discovery
- `REGION_PROXIMITY_MAP` replaced with calculation
- `REGION_MAPPING` in storage.py uses discovered locations

✅ **No dead code:**
- Old functions removed
- No duplicate definitions
- Codebase is clean

✅ **Feature detection works:**
- `get_supported_features()` returns correct features
- Cache keys are consistent
- No cache misses from key mismatches

✅ **Transcription works:**
- End-to-end transcription succeeds
- Feature detection prevents API errors
- No regressions

---

## Notes

- **Follow "Observe Before Implement":** We're using the observed working REST API pattern
- **Follow "Root Cause Over Band-Aids":** Replacing broken SDK approach, not patching it
- **Follow "Simple But Robust":** Removing complexity, using discovered data
- **Test incrementally:** Each phase should be testable independently
- **Keep fallbacks:** Maintain graceful degradation if discovery fails

---

**Ready to proceed?** This plan follows working agreement principles:
- ✅ Based on observed reality (REST API works)
- ✅ Fixes root causes (broken SDK approach)
- ✅ Removes complexity (dead code)
- ✅ Makes system dynamic (no hardcoded configs)
- ✅ Ensures consistency (cache keys)

