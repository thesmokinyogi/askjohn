# Plan: Make MODEL_REGION_CONFIG and REGION_PROXIMITY_MAP Dynamic

**Date:** 2025-11-13  
**Following:** WORKING_AGREEMENT.md + TASK_CHECKLIST.md  
**Status:** Pre-Implementation Planning

---

## Phase 1: Task Definition & Scope

### 1.1 Understand the Task

**What:** Replace hardcoded `MODEL_REGION_CONFIG` and `REGION_PROXIMITY_MAP` with dynamic discovery

**Current State:**
- `MODEL_REGION_CONFIG`: Hardcoded dict mapping models → supported regions
- `REGION_PROXIMITY_MAP`: Hardcoded dict mapping regions → nearby regions
- Both used in `_select_optimal_location()` to choose best region for a model

**Goal:**
- Discover model → region mappings from metadata cache
- Calculate region proximity dynamically
- Eliminate hardcoded configs

**Boundaries:**
- **In scope:** `MODEL_REGION_CONFIG` and `REGION_PROXIMITY_MAP` in `transcribe_v2.py`
- **Out of scope:** Other hardcoded configs (for now)

**Success Criteria:**
- ✅ No hardcoded model → region mappings
- ✅ No hardcoded proximity mappings
- ✅ All data comes from discovered metadata
- ✅ Works with any new regions Google adds
- ✅ No regressions in location selection logic

---

### 1.2 Identify All Related Files/Components

**Files directly involved:**
- `app/services/transcribe_v2.py` - Contains both configs and usage

**Functions that use these:**
- `_select_optimal_location()` - Uses `MODEL_REGION_CONFIG`
- `_map_to_nearest_region()` - Uses `REGION_PROXIMITY_MAP`

**Dependencies:**
- `_AVAILABLE_MODELS` cache (from metadata discovery)
- `_FEATURE_CACHE` (from metadata discovery)
- `_AVAILABLE_LOCATIONS` (from metadata discovery)

**What depends on this:**
- `GoogleSpeechV2Service.__init__()` - Calls `_select_optimal_location()`
- Location selection for transcription requests

---

### 1.3 State My Approach

**Approach:**
1. **OBSERVE first** - Understand current usage and what data we have
2. **Analyze** - What can we derive from discovered metadata?
3. **Design** - How to build these configs dynamically
4. **Implement** - Replace hardcoded with dynamic generation
5. **Test** - Verify location selection still works

**Steps:**
1. Read and understand current `MODEL_REGION_CONFIG` structure
2. Read and understand current `REGION_PROXIMITY_MAP` structure
3. Trace how they're used in `_select_optimal_location()` and `_map_to_nearest_region()`
4. Examine discovered metadata structure - what data do we have?
5. Determine what we can derive from metadata vs. what needs calculation
6. Design dynamic generation functions
7. Implement and test

---

## Phase 2: Observation & Discovery

### 2.1 Current Implementation Analysis

**Need to observe:**
- [ ] What is the structure of `MODEL_REGION_CONFIG`?
- [ ] What is the structure of `REGION_PROXIMITY_MAP`?
- [ ] How is `_select_optimal_location()` called?
- [ ] What does it return?
- [ ] How is `_map_to_nearest_region()` used?
- [ ] What data do we have in `_AVAILABLE_MODELS` cache?
- [ ] What data do we have in `_FEATURE_CACHE`?
- [ ] Can we derive model → region mappings from discovered metadata?
- [ ] Can we calculate proximity dynamically?

**Observation tasks:**
1. Read `MODEL_REGION_CONFIG` definition (lines 517-536)
2. Read `REGION_PROXIMITY_MAP` definition (lines 540-560)
3. Read `_select_optimal_location()` implementation (lines 618-660)
4. Read `_map_to_nearest_region()` implementation (lines 662-690)
5. Examine `_AVAILABLE_MODELS` cache structure (from metadata discovery)
6. Test what data we actually have in the cache

---

### 2.2 What We Need to Discover

**For MODEL_REGION_CONFIG:**
- **Question:** Can we build `model → supported_regions` from `_AVAILABLE_MODELS`?
- **Hypothesis:** `_AVAILABLE_MODELS` has `(location, language) → Set[model_ids]`
- **Need to verify:** Can we invert this to get `model → Set[locations]`?
- **Observation needed:** Run discovery, examine actual cache structure

**For REGION_PROXIMITY_MAP:**
- **Question:** Can we calculate proximity dynamically?
- **Hypothesis:** We can use geographic coordinates or region naming patterns
- **Need to verify:** What's the actual proximity logic? Is it geographic or just "nearby in list"?
- **Observation needed:** Understand what "proximity" means in current implementation

---

### 2.3 Pre-Implementation Verification Checklist

**Before writing ANY code:**
- [ ] Have I OBSERVED the actual `MODEL_REGION_CONFIG` structure?
- [ ] Have I OBSERVED the actual `REGION_PROXIMITY_MAP` structure?
- [ ] Have I OBSERVED how `_select_optimal_location()` works?
- [ ] Have I OBSERVED the actual `_AVAILABLE_MODELS` cache structure?
- [ ] Have I run metadata discovery and examined the cache?
- [ ] Do I understand what data we can derive from metadata?
- [ ] Have I tested inverting the cache structure?

**If any answer is NO:**
- [ ] Write observation code FIRST
- [ ] Run metadata discovery
- [ ] Examine cache structure
- [ ] Test cache inversion
- [ ] THEN proceed with implementation

---

## Phase 3: Design & Architecture

### 3.1 MODEL_REGION_CONFIG Replacement

**Current structure:**
```python
MODEL_REGION_CONFIG = {
    'chirp': {
        'requires_regional': True,
        'supported_regions': ['us-central1', 'europe-west4', 'asia-southeast1'],
        'default_region': 'us-central1'
    },
    # ...
}
```

**Available data from metadata:**
- `_AVAILABLE_MODELS`: `Dict[(location, language)] -> Set[model_ids]`
- We can invert: `model_id -> Set[locations]` where model is available

**Design:**
```python
def _build_model_region_config() -> Dict[str, Dict]:
    """
    Build model → region config dynamically from discovered metadata.
    
    Returns:
        Dict with same structure as MODEL_REGION_CONFIG but built from cache
    """
    global _AVAILABLE_MODELS
    
    config = {}
    
    # Invert _AVAILABLE_MODELS: (location, language) -> model_ids
    # To: model_id -> Set[locations]
    model_to_locations = {}
    for (location, language), model_ids in _AVAILABLE_MODELS.items():
        for model_id in model_ids:
            if model_id not in model_to_locations:
                model_to_locations[model_id] = set()
            model_to_locations[model_id].add(location)
    
    # Build config structure
    for model_id, locations in model_to_locations.items():
        locations_list = sorted(locations)
        config[model_id] = {
            'requires_regional': len(locations_list) > 0,  # If has locations, it's regional
            'supported_regions': locations_list,
            'default_region': locations_list[0] if locations_list else 'us-central1'
        }
    
    return config
```

**Questions to answer:**
- Do we need `requires_regional` flag? What does it control?
- How do we determine default_region? (Currently first in list, but should it be smarter?)
- What about model name normalization? (e.g., 'chirp' vs 'chirp_2' vs 'chirp_batch')

---

### 3.2 REGION_PROXIMITY_MAP Replacement

**Current structure:**
```python
REGION_PROXIMITY_MAP = {
    'us-west1': ['us-central1', 'us-west2', 'us-east1'],
    'us-west2': ['us-central1', 'us-west1', 'us-east1'],
    # ...
}
```

**Design options:**

**Option A: Geographic calculation**
- Use region coordinates (if available)
- Calculate distance between regions
- Return nearest N regions

**Option B: Region naming patterns**
- Parse region names (e.g., 'us-west1' → continent='us', area='west', number=1)
- Find regions with same continent, nearby areas
- Simpler but less accurate

**Option C: Use discovered locations**
- Get all discovered locations
- Group by continent/area
- Return nearby regions from same group

**Need to observe:**
- What does current proximity map actually do?
- Is it geographic or just "nearby in list"?
- How many regions does it return?
- What's the fallback logic?

---

## Phase 4: Implementation Plan

### Step 1: Observation (REQUIRED - No coding yet)
1. Run metadata discovery
2. Examine `_AVAILABLE_MODELS` cache structure
3. Test inverting cache: `model_id -> Set[locations]`
4. Understand current proximity logic
5. Document what we observed

### Step 2: Design Dynamic Functions
1. Design `_build_model_region_config()` function
2. Design `_calculate_region_proximity()` function
3. Determine when to build/rebuild (startup? on-demand?)
4. Handle edge cases (no cache, empty cache, etc.)

### Step 3: Implementation
1. Implement `_build_model_region_config()`
2. Implement `_calculate_region_proximity()` or `_get_nearby_regions()`
3. Replace hardcoded configs with dynamic generation
4. Update `_select_optimal_location()` to use dynamic config
5. Update `_map_to_nearest_region()` to use dynamic proximity

### Step 4: Testing
1. Test with discovered metadata
2. Test location selection logic
3. Test edge cases (unknown model, unknown region)
4. Verify no regressions

---

## Phase 5: Risk Assessment

### Risks
1. **Cache not loaded** - What if `_AVAILABLE_MODELS` is empty?
   - **Mitigation:** Fallback to hardcoded config or raise error
   
2. **Model name mismatch** - What if model names don't match?
   - **Mitigation:** Normalize model names, handle aliases
   
3. **Performance** - Building config on every call?
   - **Mitigation:** Cache built config, rebuild when metadata cache updates
   
4. **Proximity calculation** - What if calculation is wrong?
   - **Mitigation:** Test thoroughly, compare with current hardcoded map

---

## Questions to Answer Before Implementation

1. **What does `requires_regional` flag actually control?**
   - Need to understand its purpose before removing

2. **How is default_region chosen?**
   - Currently first in list - is this correct?

3. **What is proximity logic actually doing?**
   - Geographic? Naming-based? Just "nearby in list"?

4. **When should we build these configs?**
   - At startup? On-demand? When cache updates?

5. **What about model name normalization?**
   - 'chirp' vs 'chirp_2' vs 'chirp_batch' - how do we map?

---

## Next Steps

1. **OBSERVE** - Read current implementation, understand usage
2. **OBSERVE** - Run metadata discovery, examine cache structure
3. **OBSERVE** - Test cache inversion, verify we can build configs
4. **DESIGN** - Create dynamic generation functions
5. **IMPLEMENT** - Replace hardcoded with dynamic
6. **TEST** - Verify everything works

**Status:** Ready to begin Phase 2 (Observation & Discovery)

