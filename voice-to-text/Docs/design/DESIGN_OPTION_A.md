# Design: Dynamic MODEL_REGION_CONFIG and REGION_PROXIMITY_MAP

**Date:** 2025-11-13  
**Based on:** OBSERVATION_RESULTS.md  
**Status:** Ready for Implementation

---

## Observed Facts

1. ✅ Cache inversion works: `model_id -> Set[locations]`
2. ✅ Hardcoded config is incomplete (missing 8+ regions)
3. ✅ `requires_regional` flag is not used (just metadata)
4. ✅ Proximity has fallback logic (prefix matching) that works
5. ⚠️ Model name normalization needed (chirp vs chirp_2 vs chirp_3)
6. ⚠️ Default region selection needs logic (prefer us-central1)

---

## Design Decisions

### 1. MODEL_REGION_CONFIG Replacement

**Approach:** Build from discovered metadata cache

**Function:**
```python
def _build_model_region_config() -> Dict[str, Dict]:
    """
    Build model → region config dynamically from discovered metadata.
    
    Returns:
        Dict with structure matching MODEL_REGION_CONFIG
    """
    global _AVAILABLE_MODELS
    
    # Invert cache: (location, language) -> model_ids
    # To: model_id -> Set[locations]
    model_to_locations = {}
    for (location, language), model_ids in _AVAILABLE_MODELS.items():
        for model_id in model_ids:
            if model_id not in model_to_locations:
                model_to_locations[model_id] = set()
            model_to_locations[model_id].add(location)
    
    # Build config - handle model name normalization
    config = {}
    
    # Group model variants (chirp, chirp_2, chirp_3 -> 'chirp')
    base_models = {
        'chirp': ['chirp', 'chirp_2', 'chirp_3', 'chirp_telephony'],
        'long': ['long'],
        'short': ['short'],
        'telephony': ['telephony', 'telephony_short']
    }
    
    for base_name, variants in base_models.items():
        # Collect all locations for all variants
        all_locations = set()
        for variant in variants:
            if variant in model_to_locations:
                all_locations.update(model_to_locations[variant])
        
        if all_locations:
            locations_list = sorted(all_locations)
            config[base_name] = {
                'requires_regional': len(locations_list) > 0,
                'supported_regions': locations_list,
                'default_region': _choose_default_region(locations_list)
            }
    
    return config
```

**Default Region Selection:**
```python
def _choose_default_region(locations: list[str]) -> str:
    """
    Choose default region with preference for us-central1.
    
    Strategy:
    1. Prefer us-central1 if available
    2. Prefer us-* regions if available
    3. Otherwise first in sorted list
    """
    if 'us-central1' in locations:
        return 'us-central1'
    
    # Prefer US regions
    us_regions = [loc for loc in locations if loc.startswith('us')]
    if us_regions:
        return sorted(us_regions)[0]
    
    # Fallback to first
    return locations[0] if locations else 'us-central1'
```

---

### 2. REGION_PROXIMITY_MAP Replacement

**Approach:** Use prefix matching (already exists as fallback!)

**Observation:** Current code already has fallback logic (lines 685-689):
```python
if '-' in requested:
    region_prefix = requested.split('-')[0]  # "us", "europe", "asia"
    for region in available:
        if region.startswith(region_prefix):
            return region
```

**Design:** Make prefix matching the PRIMARY approach, eliminate hardcoded map

**Function:**
```python
def _find_nearby_region(requested: str, available: list[str]) -> Optional[str]:
    """
    Find nearby region using prefix matching.
    
    Strategy:
    1. Extract continent prefix (us, europe, asia, etc.)
    2. Find first available region with same prefix
    3. If no match, return None (let caller handle fallback)
    
    Args:
        requested: Requested region (e.g., 'us-west1')
        available: List of available regions for the model
    
    Returns:
        Nearby region with same prefix, or None
    """
    if '-' not in requested:
        # Multi-region endpoints (us, eu) - no prefix matching
        return None
    
    region_prefix = requested.split('-')[0]  # "us", "europe", "asia"
    
    # Find first available region with same prefix
    for region in available:
        if region.startswith(region_prefix):
            return region
    
    return None
```

**Simplification:** We can eliminate REGION_PROXIMITY_MAP entirely and use prefix matching!

---

## Implementation Plan

### Step 1: Build MODEL_REGION_CONFIG Function
1. Create `_build_model_region_config()` function
2. Handle model name normalization (base names + variants)
3. Implement `_choose_default_region()` with us-central1 preference
4. Cache the result (build once at startup, rebuild if cache updates)

### Step 2: Simplify Proximity Logic
1. Update `_map_to_nearest_region()` to use prefix matching as primary
2. Remove dependency on REGION_PROXIMITY_MAP
3. Keep fallback to default region if prefix matching fails

### Step 3: Update _select_optimal_location()
1. Replace `self.MODEL_REGION_CONFIG` with dynamic config
2. Build config on-demand or cache it
3. Handle cache not loaded case

### Step 4: Testing
1. Test with discovered metadata
2. Test location selection for various models
3. Test proximity matching
4. Verify no regressions

---

## Edge Cases

### 1. Cache Not Loaded
**Handling:** Fallback to minimal hardcoded config or raise error
```python
if not _CACHE_LOADED:
    logger.warning("Cache not loaded, using minimal fallback")
    return _get_minimal_fallback_config()
```

### 2. Unknown Model
**Handling:** Return empty config, let `_select_optimal_location()` handle with warning

### 3. No Regions for Model
**Handling:** Return empty supported_regions, use default fallback

### 4. Multi-region Endpoints (us, eu)
**Handling:** Prefix matching won't work (no '-'), but these are usually in available list directly

---

## Model Name Normalization Strategy

**Problem:** User says `'chirp'`, but metadata has `'chirp'`, `'chirp_2'`, `'chirp_3'`, `'chirp_telephony'`

**Solution:** Group variants under base name
- `'chirp'` → includes locations from all: `chirp`, `chirp_2`, `chirp_3`, `chirp_telephony`
- `'long'` → just `long`
- `'short'` → just `short`
- `'telephony'` → includes: `telephony`, `telephony_short`

**Rationale:** User wants to use "chirp" - they don't care which variant, they want any chirp model available in their region.

---

## Benefits

1. ✅ **Eliminates hardcoded MODEL_REGION_CONFIG** - Built from discovered metadata
2. ✅ **Eliminates hardcoded REGION_PROXIMITY_MAP** - Uses prefix matching
3. ✅ **More complete** - Discovers all regions, not just hardcoded subset
4. ✅ **Auto-updates** - New regions automatically included
5. ✅ **Simpler** - Less code, less maintenance

---

## Questions Resolved

1. ✅ Can we build MODEL_REGION_CONFIG? **YES** - Cache inversion works
2. ✅ Model name normalization? **Group variants under base name**
3. ✅ requires_regional flag? **Not used, derive from has_locations**
4. ✅ Default region? **Prefer us-central1, then us-*, then first**
5. ✅ Proximity calculation? **Prefix matching (already exists!)**
6. ✅ Proximity logic? **Naming-based prefix matching**

---

## Ready to Implement

All observations complete. Design decisions made. Ready to code.

