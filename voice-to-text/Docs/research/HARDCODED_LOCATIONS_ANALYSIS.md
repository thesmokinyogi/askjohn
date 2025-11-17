# Hardcoded Location List - Detailed Analysis

**Date:** 2025-11-13  
**Issue:** `discover_speech_metadata()` uses hardcoded list of 20 locations  
**Location:** `app/services/transcribe_v2.py` lines 177-182

---

## Current Implementation

```python
known_locations = [
    'us', 'us-central1', 'us-east1', 'us-east4', 'us-west1', 'us-west2', 'us-west3', 'us-west4',
    'europe-west1', 'europe-west2', 'europe-west3', 'europe-west4', 'europe-west6',
    'asia-east1', 'asia-east2', 'asia-northeast1', 'asia-northeast2', 'asia-south1', 'asia-southeast1',
    'australia-southeast1', 'northamerica-northeast1', 'southamerica-east1'
]
```

**Problem:** If Google adds new regions, we won't discover them automatically.

---

## Why This Is a Problem

### Real-World Scenarios

1. **Google Adds New Region**
   - Example: `europe-west8` (hypothetical)
   - Our code: Won't query it, won't discover it
   - Impact: Users in that region can't use optimal endpoint
   - Frequency: Rare (maybe 1-2 new regions per year)

2. **Google Deprecates Region**
   - Example: `us-west3` gets deprecated
   - Our code: Still queries it, gets 404 or error
   - Impact: Wasted API calls, slower startup
   - Frequency: Very rare (maybe once every few years)

3. **Regional Outage**
   - Example: `us-central1` has issues
   - Our code: Still queries it, gets timeout/error
   - Impact: Slower startup, but handled gracefully
   - Frequency: Occasional (maybe a few times per year)

---

## Options for Dynamic Discovery

### Option 1: Use Google Cloud Locations API

**Approach:** Query `https://cloudresourcemanager.googleapis.com/v1/projects/{project_id}/locations`

**Pros:**
- ✅ Truly dynamic - discovers all available locations
- ✅ No maintenance - automatically picks up new regions
- ✅ Handles deprecations - won't query unavailable regions

**Cons:**
- ❌ **Problem:** This API lists ALL Google Cloud locations (Compute, Storage, etc.)
- ❌ **Problem:** Not all locations support Speech V2 API
- ❌ **Problem:** Would need to filter by service availability
- ❌ **Complexity:** Medium - need to filter results

**Feasibility:** ⚠️ **Partial** - Would discover locations but not which ones support Speech V2

---

### Option 2: Use Speech API's ListLocations Endpoint

**Approach:** Use the SDK's `list_locations()` method we already have access to

**Current Code (from old implementation):**
```python
client = SpeechClient()
request = locations_pb2.ListLocationsRequest(name=f"projects/{project_id}")
response = client.list_locations(request=request)
# response.locations contains Location objects
```

**Pros:**
- ✅ Returns only Speech V2 supported locations
- ✅ Already have the code (from old implementation)
- ✅ No hardcoded list needed
- ✅ Automatically handles new/deprecated regions

**Cons:**
- ❌ **Problem:** We tried this before - `MessageToDict()` fails
- ❌ **Problem:** Can't extract metadata from protobuf Location objects
- ❌ **Problem:** That's why we switched to REST API

**Feasibility:** ⚠️ **Blocked** - Can get location IDs but not metadata

**Hybrid Approach:**
1. Use SDK `list_locations()` to get location IDs dynamically
2. Then query each location via REST API for metadata
3. Best of both worlds!

**Code:**
```python
# Get location IDs dynamically
client = SpeechClient()
request = locations_pb2.ListLocationsRequest(name=f"projects/{project_id}")
response = client.list_locations(request=request)
location_ids = [loc.location_id for loc in response.locations]

# Then query each via REST API for metadata
for location_id in location_ids:
    data = _discover_location_metadata_via_rest_api(project_id, location_id)
    # ... process metadata ...
```

**Feasibility:** ✅ **Viable** - Combines dynamic discovery with working metadata extraction

---

### Option 3: Query a "Global" Endpoint First

**Approach:** Try querying a global endpoint that lists all Speech V2 locations

**Hypothesis:** Maybe there's an endpoint like:
- `https://speech.googleapis.com/v2/projects/{project_id}/locations` (global)
- Or `https://us-central1-speech.googleapis.com/v2/projects/{project_id}/locations` (lists all)

**Pros:**
- ✅ Single API call to get all locations
- ✅ No hardcoded list

**Cons:**
- ❌ **Problem:** Need to verify this endpoint exists
- ❌ **Problem:** May not exist (hypothetical)

**Feasibility:** ❓ **Unknown** - Need to test if endpoint exists

---

### Option 4: Keep Hardcoded List + Add Discovery Fallback

**Approach:** Try SDK `list_locations()` first, fall back to hardcoded list if it fails

**Pros:**
- ✅ Best of both worlds
- ✅ Works even if SDK has issues
- ✅ Can discover new regions when SDK works

**Cons:**
- ⚠️ Still maintains hardcoded list (but as fallback only)
- ⚠️ Slightly more complex logic

**Feasibility:** ✅ **Viable** - Safe fallback approach

---

## Recommended Solution: Hybrid Approach

### Implementation Plan

**Step 1:** Use SDK to get location IDs dynamically
```python
def _get_speech_locations_dynamically(project_id: str) -> list[str]:
    """Get list of Speech V2 locations from API."""
    try:
        client = SpeechClient()
        request = locations_pb2.ListLocationsRequest(name=f"projects/{project_id}")
        response = client.list_locations(request=request)
        location_ids = [loc.location_id for loc in response.locations]
        logger.info(f"Discovered {len(location_ids)} locations from API")
        return location_ids
    except Exception as e:
        logger.warning(f"Failed to get locations dynamically: {e}, using fallback list")
        return None
```

**Step 2:** Fall back to hardcoded list if SDK fails
```python
def discover_speech_metadata(project_id: str, languages: list[str] = None) -> dict:
    # Try to get locations dynamically
    location_ids = _get_speech_locations_dynamically(project_id)
    
    if not location_ids:
        # Fallback to hardcoded list
        logger.warning("Using hardcoded location list as fallback")
        location_ids = [
            'us', 'us-central1', 'us-east1', 'us-east4', 'us-west1', 
            'us-west2', 'us-west3', 'us-west4',
            # ... rest of list
        ]
    
    # Query each location via REST API for metadata
    for location in location_ids:
        data = _discover_location_metadata_via_rest_api(project_id, location)
        # ... rest of discovery logic ...
```

**Benefits:**
- ✅ Discovers new regions automatically (when SDK works)
- ✅ Has safe fallback (when SDK fails)
- ✅ No breaking changes
- ✅ Best of both worlds

**Complexity:** Low-Medium (~20 lines of code)

---

## Testing the Hybrid Approach

### Test Case 1: SDK Works
- Call `list_locations()`
- Get location IDs
- Use those for discovery
- **Expected:** Discovers all current + new regions

### Test Case 2: SDK Fails
- Mock SDK to raise exception
- Fall back to hardcoded list
- Use those for discovery
- **Expected:** Works with known locations

### Test Case 3: SDK Returns Empty
- Mock SDK to return empty list
- Fall back to hardcoded list
- **Expected:** Uses fallback list

---

## Alternative: Just Use SDK for Location IDs

**Simpler approach:** Always use SDK for location IDs, no fallback

**Pros:**
- ✅ Simpler code
- ✅ Truly dynamic
- ✅ No hardcoded list to maintain

**Cons:**
- ❌ If SDK fails, discovery fails
- ❌ But we already have retry logic in `initialize_metadata_cache()`

**Feasibility:** ✅ **Viable** - Simpler, relies on existing retry logic

---

## Decision Matrix

| Approach | Complexity | Maintenance | Reliability | Dynamic Discovery |
|----------|-----------|-------------|-------------|------------------|
| **Current (hardcoded)** | Low | High (manual updates) | High | ❌ No |
| **SDK only** | Low | Low | Medium | ✅ Yes |
| **Hybrid (SDK + fallback)** | Medium | Low | High | ✅ Yes |
| **Cloud Resource Manager** | Medium | Low | Medium | ⚠️ Partial |

---

## Recommendation

**Option: Use SDK for location IDs, keep hardcoded list as comment/documentation**

**Rationale:**
1. SDK `list_locations()` works for getting location IDs (we know this works)
2. We only need location IDs, not metadata (metadata comes from REST API)
3. If SDK fails, retry logic in `initialize_metadata_cache()` handles it
4. Keep hardcoded list as comment for reference/documentation

**Implementation:**
```python
def _get_speech_location_ids(project_id: str) -> list[str]:
    """
    Get Speech V2 location IDs dynamically from API.
    
    Falls back to known locations if API unavailable.
    Known locations (as of 2025-11): us, us-central1, us-east1, us-east4,
    us-west1-4, europe-west1-4, europe-west6, asia-east1-2, asia-northeast1-2,
    asia-south1, asia-southeast1, australia-southeast1, northamerica-northeast1,
    southamerica-east1
    """
    try:
        client = SpeechClient()
        request = locations_pb2.ListLocationsRequest(name=f"projects/{project_id}")
        response = client.list_locations(request=request)
        location_ids = [loc.location_id for loc in response.locations]
        logger.debug(f"Discovered {len(location_ids)} locations from API")
        return location_ids
    except Exception as e:
        logger.warning(f"Failed to get locations from API: {e}, using known locations")
        # Fallback to known locations
        return [
            'us', 'us-central1', 'us-east1', 'us-east4', 'us-west1', 
            'us-west2', 'us-west3', 'us-west4',
            'europe-west1', 'europe-west2', 'europe-west3', 'europe-west4', 'europe-west6',
            'asia-east1', 'asia-east2', 'asia-northeast1', 'asia-northeast2', 
            'asia-south1', 'asia-southeast1',
            'australia-southeast1', 'northamerica-northeast1', 'southamerica-east1'
        ]
```

**Benefits:**
- ✅ Dynamic discovery when possible
- ✅ Safe fallback when needed
- ✅ Low complexity
- ✅ No breaking changes

---

## Questions to Answer

1. **Does `list_locations()` reliably return all Speech V2 locations?**
   - Need to test: Does it return all 20+ locations we know about?
   - Or does it only return locations where project has resources?

2. **What happens if project doesn't have resources in a region?**
   - Does `list_locations()` still return that region?
   - Or only regions where project has resources?

3. **Should we cache the location list?**
   - Locations don't change often
   - Could cache for performance
   - But adds complexity

---

## Next Steps

1. **Test SDK `list_locations()`** - Verify it returns all known locations
2. **Implement hybrid approach** - Use SDK, fallback to hardcoded
3. **Test edge cases** - Empty response, API failures, etc.
4. **Document known locations** - Keep as comment for reference

