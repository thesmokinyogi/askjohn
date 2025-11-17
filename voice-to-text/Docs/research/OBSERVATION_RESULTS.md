# Observation Results: Cache Structure Analysis

**Date:** 2025-11-13  
**Purpose:** Understand discovered metadata to build MODEL_REGION_CONFIG and REGION_PROXIMITY_MAP dynamically

---

## ✅ Key Findings

### 1. Cache Inversion Works!

**OBSERVED:** We can successfully invert `_AVAILABLE_MODELS` cache:
- **Current structure:** `(location, language) -> Set[model_ids]`
- **Inverted structure:** `model_id -> Set[locations]` ✅ WORKS
- **This is exactly what we need for MODEL_REGION_CONFIG!**

### 2. Discovered Models vs Hardcoded

**OBSERVED Model -> Locations:**
```
chirp: ['asia-southeast1', 'europe-west4', 'us-central1']
long: ['asia-northeast1', 'asia-south1', 'asia-southeast1', 'asia-southeast2', 
       'eu', 'europe-west1', 'europe-west3', 'europe-west4', 'europe-west6', 
       'us', 'us-central1', 'us-east1', 'us-west1']
short: [same as long]
```

**Hardcoded config:**
```
chirp: ['us-central1', 'europe-west4', 'asia-southeast1']  ✅ MATCHES (order different)
long: ['us-central1', 'us-west1', 'us-east1', 'europe-west1', 'asia-southeast1']  ⚠️ MISSING 8 regions!
short: [same as long]  ⚠️ MISSING 8 regions!
```

**Finding:** Hardcoded config is **incomplete** - missing many regions that actually support these models!

### 3. Model Name Variations

**OBSERVED model IDs:**
- `chirp`, `chirp_2`, `chirp_3`, `chirp_telephony`
- `long`, `short`
- `telephony`, `telephony_short`
- `medical_conversation`, `medical_dictation`
- `usm`

**Issue:** Current code uses `'chirp'`, `'long'`, `'short'` but discovered metadata has variations.

**Question:** How do we map user's model choice (`'chirp'`) to actual model IDs (`'chirp'`, `'chirp_2'`, `'chirp_3'`)?

### 4. Default Region Selection

**OBSERVED:** When inverting cache, sorted order gives:
- `chirp`: default would be `'asia-southeast1'` (first alphabetically)
- **Hardcoded:** uses `'us-central1'`

**Question:** Should default_region be:
- First alphabetically? (current dynamic approach)
- Most common across models? (`us-central1` appears in most)
- Specific logic? (prefer US regions?)

### 5. Proximity Map Logic

**OBSERVED current REGION_PROXIMITY_MAP:**
```python
'us-west1': ['us-central1', 'us-west2', 'us-east1']
'us-west2': ['us-central1', 'us-west1', 'us-east1']
```

**Pattern observed:**
- Groups regions by continent/area (us-west, us-east, europe-west, asia-*)
- Returns nearby regions from same continent
- Some regions map to themselves (already optimal)

**Question:** Is this:
- Geographic proximity? (probably not - no coordinates)
- Naming-based proximity? (same continent prefix)
- Just "nearby in list"? (appears to be this)

### 6. Locations Discovered

**OBSERVED:** 16 locations support Speech V2 (out of 22 probed):
- ✅ Found: us, us-central1, us-east1, us-west1, eu, europe-west1-4, europe-west6, asia-*, etc.
- ❌ Not found: us-east4, us-west2-4, asia-east1-2, asia-northeast2, southamerica-east1

**Finding:** Some regions in probe list don't support Speech V2 (expected - that's why we probe!)

---

## 🎯 Answers to Key Questions

### Q1: Can we build MODEL_REGION_CONFIG from discovered metadata?
**Answer:** ✅ **YES** - Cache inversion works perfectly!

### Q2: How do we handle model name normalization?
**Answer:** ⚠️ **NEED TO DECIDE:**
- Option A: Use exact model ID from discovery (`chirp`, `chirp_2`, `chirp_3` separately)
- Option B: Map user's `'chirp'` to latest version (`chirp_3`) or all variants
- Option C: Use base name (`'chirp'`) and include all variants in supported_regions

**Recommendation:** Option C - Use base name, include all variants' locations

### Q3: What does 'requires_regional' actually control?
**Answer:** ✅ **OBSERVED:** Flag is **NOT USED** in code - only in config dict
- Grep search shows it's only defined, never read
- It's just documentation/metadata
- We can derive it: `requires_regional = len(supported_regions) > 0`

### Q4: How should we choose default_region?
**Answer:** ⚠️ **NEED TO DECIDE:**
- Current hardcoded: `us-central1` (appears in most models)
- Alphabetical: First in sorted list
- Most common: Region that appears in most models
- Preference-based: Prefer US regions, then Europe, then Asia

**Recommendation:** Use `us-central1` if available, otherwise first in list (maintains current behavior)

### Q5: Can we calculate proximity dynamically?
**Answer:** ✅ **YES** - Based on region naming patterns:
- Parse region name: `{continent}-{area}{number}` (e.g., `us-west1`)
- Group by continent and area
- Return regions from same continent/area

### Q6: What's the actual proximity logic?
**Answer:** ✅ **OBSERVED:** Two-tier approach:
1. **Primary:** Hardcoded REGION_PROXIMITY_MAP (specific mappings)
2. **Fallback:** Region prefix matching (lines 685-689)
   - `us-west1` → looks for any `us-*` region in available list
   - `europe-west1` → looks for any `europe-*` region in available list
   
**Finding:** The fallback logic already does what we need! We can use prefix matching as primary, only need hardcoded map for edge cases (or eliminate it entirely).

---

## 📋 Next Steps

### Immediate Observations Needed:
1. [ ] Check if `requires_regional` flag is actually used in code
2. [ ] Understand model name mapping (how user's 'chirp' maps to discovered models)
3. [ ] Test proximity calculation logic (parse region names, group by continent)

### Then Design:
1. Design `_build_model_region_config()` function
2. Design `_calculate_region_proximity()` function
3. Handle model name normalization
4. Handle default_region selection

### Then Implement:
1. Replace hardcoded MODEL_REGION_CONFIG
2. Replace hardcoded REGION_PROXIMITY_MAP
3. Test location selection logic

---

## 💡 Key Insights

1. **Hardcoded config is incomplete** - Missing 8+ regions for long/short models
2. **Dynamic discovery is better** - Automatically finds all supported regions
3. **Model name mapping needed** - User says 'chirp', but metadata has 'chirp', 'chirp_2', 'chirp_3'
4. **Proximity is naming-based** - Can calculate from region name patterns
5. **Default region logic** - Need to match current behavior (us-central1 preference)

