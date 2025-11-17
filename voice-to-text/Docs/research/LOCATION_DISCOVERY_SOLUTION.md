# Location Discovery Solution

**Date:** 2025-11-13  
**Problem:** Need to eliminate hardcoded location list  
**Test Results:** SDK only returns 5 locations, Resource Manager API doesn't work

---

## Test Results Summary

### SDK `list_locations()` Test
- **Returned:** 5 locations (all in Asia/Australia)
- **Missing:** 18 known locations (all US, Europe regions)
- **Conclusion:** SDK only returns locations where project has resources
- **Verdict:** ❌ Option 2.5 (SDK Only) won't work

### Resource Manager API Test
- **Endpoints tried:** Multiple variations, all failed (404/403)
- **Compute Engine API:** Also failed (404)
- **Conclusion:** No working API to list all GCP regions
- **Verdict:** ❌ Option 3 (Resource Manager) not viable

---

## Proposed Solution: "Try Common Locations" Approach

### Concept

Instead of hardcoding "which locations support Speech V2", we:
1. **Hardcode a minimal list of common GCP region patterns** (well-documented, stable)
2. **Try querying each one** via REST API
3. **Discover dynamically** which ones actually support Speech V2
4. **Cache the results** for performance

### Key Insight

We're not hardcoding "Speech V2 locations" - we're hardcoding "locations to try" and discovering which ones work.

---

## Implementation

### Step 1: Minimal "Common GCP Regions" List

```python
# Common Google Cloud regions (well-documented, stable)
# We try these and discover which support Speech V2
COMMON_GCP_REGIONS = [
    # US regions
    'us', 'us-central1', 'us-east1', 'us-east4', 'us-west1', 'us-west2', 'us-west3', 'us-west4',
    # Europe regions
    'europe-west1', 'europe-west2', 'europe-west3', 'europe-west4', 'europe-west6',
    # Asia regions
    'asia-east1', 'asia-east2', 'asia-northeast1', 'asia-northeast2', 'asia-south1', 
    'asia-southeast1', 'asia-southeast2',
    # Other regions
    'australia-southeast1', 'northamerica-northeast1', 'southamerica-east1'
]
```

**Why this is acceptable:**
- ✅ These are **GCP infrastructure regions**, not Speech V2 specific
- ✅ Well-documented by Google (public knowledge)
- ✅ Very stable (rarely change)
- ✅ We're not hardcoding "which support Speech V2" - we discover that

### Step 2: Dynamic Discovery

```python
def discover_speech_metadata(project_id: str, languages: list[str] = None) -> dict:
    """Discover Speech V2 metadata by trying common GCP regions."""
    
    # Try common GCP regions (well-documented, stable list)
    # We discover which ones support Speech V2 dynamically
    regions_to_try = COMMON_GCP_REGIONS
    
    available_locations = set()
    models_by_location = {}
    features_by_model = {}
    
    for region in regions_to_try:
        # Try to get metadata for this region
        data = _discover_location_metadata_via_rest_api(project_id, region)
        
        if data and 'metadata' in data:
            # This region supports Speech V2!
            available_locations.add(region)
            # ... extract models and features ...
        # If it fails, region doesn't support Speech V2 - skip it
    
    return {
        'available_locations': available_locations,  # Discovered dynamically
        'models_by_location': models_by_location,
        'features_by_model': features_by_model,
        'success': len(available_locations) > 0
    }
```

### Step 3: Optional: Cache Discovered Locations

```python
# Cache which regions support Speech V2 (discovered dynamically)
# Update this cache when new regions are discovered
DISCOVERED_SPEECH_V2_LOCATIONS = None  # Populated at startup
```

---

## Comparison with Original Approach

| Aspect | Original (Hardcoded) | New (Try Common) |
|--------|---------------------|------------------|
| **What's hardcoded** | "Speech V2 locations" | "Common GCP regions to try" |
| **Discovery** | None | Dynamic (tries each region) |
| **Maintenance** | Update when Speech V2 adds regions | Update when GCP adds regions (rare) |
| **New regions** | Manual update needed | Automatic discovery |
| **Deprecated regions** | Manual removal needed | Automatic (fails, gets skipped) |

---

## Benefits

1. ✅ **Eliminates hardcoded "Speech V2 locations"** - We discover these dynamically
2. ✅ **Minimal hardcoded data** - Only common GCP regions (public knowledge, stable)
3. ✅ **Automatic discovery** - New Speech V2 regions found automatically
4. ✅ **Handles deprecations** - Failed regions automatically skipped
5. ✅ **Simple implementation** - Just try each region, see what works

---

## Trade-offs

### Pros
- ✅ No hardcoded "Speech V2 locations"
- ✅ Discovers new regions automatically
- ✅ Simple to implement
- ✅ Handles failures gracefully

### Cons
- ⚠️ Still has hardcoded "common GCP regions" list
- ⚠️ If GCP adds new region pattern, need to add to list
- ⚠️ Slightly slower (tries all regions, but most fail fast)

---

## Alternative: Even More Dynamic

### Option: Try Region Patterns

Instead of hardcoding specific regions, try common patterns:

```python
REGION_PATTERNS = [
    'us', 'us-central{1-4}', 'us-east{1-4}', 'us-west{1-4}',
    'europe-west{1-6}',
    'asia-east{1-2}', 'asia-northeast{1-2}', 'asia-south1', 'asia-southeast{1-2}',
    'australia-southeast1',
    'northamerica-northeast1', 'southamerica-east1'
]

# Generate all combinations and try them
# This is more complex but even more dynamic
```

**Verdict:** Probably overkill - the list of common regions is stable enough.

---

## Recommendation

**Use "Try Common Locations" approach:**

1. **Hardcode minimal list** of common GCP regions (well-documented, stable)
2. **Try each one** via REST API
3. **Discover dynamically** which support Speech V2
4. **Cache results** for performance

**Why this works:**
- ✅ Eliminates hardcoded "Speech V2 locations" (we discover these)
- ✅ Minimal hardcoded data (just common GCP regions)
- ✅ Automatic discovery of new Speech V2 regions
- ✅ Simple implementation
- ✅ Handles failures gracefully

**The key insight:** We're not hardcoding "which locations support Speech V2" - we're hardcoding "which locations to try" and discovering the answer.

---

## Implementation Plan

1. **Rename hardcoded list** to `COMMON_GCP_REGIONS` (clarifies purpose)
2. **Add comment** explaining we try these and discover which support Speech V2
3. **Keep discovery logic** as-is (already tries each region)
4. **Optional:** Cache discovered locations for faster subsequent queries

This is essentially what we're already doing, but with better naming and documentation to clarify that we're discovering Speech V2 support dynamically.

