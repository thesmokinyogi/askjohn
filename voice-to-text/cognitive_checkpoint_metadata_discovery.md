# Cognitive Checkpoint: LocationsMetadata Discovery Investigation

**Date:** 2025-11-12
**Session ID:** claude/initial-setup-011CV4vg995hHxq5KH23bTwg
**Status:** BLOCKED - SDK limitation discovered

## Session Goal

Implement dynamic discovery of Speech V2 model capabilities (languages → models → features) to replace hardcoded MODEL_REGION_CONFIG data in `app/services/transcribe_v2.py`.

## The Problem

Google Cloud Speech V2 API returns location metadata containing the exact information we need (which models support which features in which languages), but the Python SDK doesn't expose the protobuf message type needed to access it.

## What We Know For Certain

### 1. The Data Exists
```
loc.metadata type: google.protobuf.any_pb2.Any
type_url: "type.googleapis.com/google.cloud.speech.v2.LocationsMetadata"
value: <binary data containing language codes like "sn-ZW", "pa-Guru-IN">
```

The data is physically present in the API response. We can see language codes in the raw bytes.

### 2. The SDK Doesn't Expose It

**Search Results:**
```bash
# Searched entire installed SDK
find .../google/cloud/speech_v2 -name "*.py" | xargs grep -l "LocationsMetadata"
# Result: EMPTY (nothing found)
```

**Available Metadata types in SDK:**
- BatchRecognizeFileMetadata
- BatchRecognizeMetadata
- BatchRecognizeTranscriptionMetadata
- OperationMetadata
- RecognitionResponseMetadata

**NOT available:** LocationsMetadata

### 3. Standard Unpacking Methods Fail

The Any object requires a message descriptor to unpack. Without LocationsMetadata in the SDK, all standard approaches fail:

```python
# Attempt 1: MessageToDict
MessageToDict(loc)
# Error: "Can not find message descriptor by type_url:
#         type.googleapis.com/google.cloud.speech.v2.LocationsMetadata"

# Attempt 2: Unpack to Struct (generic container)
struct = Struct()
loc.metadata.Unpack(struct)
# Success but: MessageToDict(struct) returns {} (empty dict)

# Attempt 3: Import LocationsMetadata directly
from google.cloud.speech_v2.proto.cloud_speech_pb2 import LocationsMetadata
# Error: "No module named 'google.cloud.speech_v2.proto'"
```

## What We Tested (6 Alternatives)

Created observation platform: `debug_metadata_discovery.py`

### Alternative A: MessageToDict(loc)
- **Status:** ❌ FAILED
- **Error:** Can't find message descriptor for LocationsMetadata
- **Why:** Descriptor not registered in Python's global protobuf registry

### Alternative B: Direct Attribute Access
- **Status:** ✅ PARTIAL SUCCESS
- **Finding:** Confirmed metadata is Any object with correct type_url
- **Limitation:** Can see raw bytes but can't parse structure

### Alternative C: Unpack to Struct
- **Status:** ❌ FAILED
- **Result:** Unpacking succeeds but produces empty dict
- **Why:** Type mismatch - LocationsMetadata can't properly unpack to generic Struct

### Alternative D: Import from Internal Proto Path
- **Status:** ❌ FAILED
- **Error:** No module named 'google.cloud.speech_v2.proto'
- **Finding:** Module doesn't exist in any standard Python package structure

### Alternative E: Use get_config() API (Gemini's First Suggestion)
- **Status:** ❌ FAILED
- **What Gemini claimed:** Config object contains languages → models → features
- **Reality:** Config only has: ['kms_key_name', 'name', 'update_time']
- **Conclusion:** Gemini was incorrect. get_config() is for encryption/metadata, not capabilities

### Alternative F: Import cloud_speech_pb2 (Gemini's Refined Suggestion)
- **Status:** ❌ FAILED
- **Tested two import methods:**
  1. `from google.cloud.speech_v2.proto import cloud_speech_pb2`
  2. `import google.cloud.speech_v2.proto.cloud_speech_pb2`
- **Error for both:** No module named 'google.cloud.speech_v2.proto'
- **Conclusion:** Gemini's "internal proto files" don't exist in the installed SDK

## Gemini's Failed Suggestions

### Suggestion 1: client.get_config()
**Claim:** "The API method specifically designed for retrieving regional capabilities and configuration is projects.locations.config.get, which returns the publicly exposed Config message type."

**Reality:** Config object contains encryption settings (kms_key_name), not capability metadata.

**Verdict:** INCORRECT

### Suggestion 2: Internal cloud_speech_pb2 Import
**Claim:** "The internal cloud_speech_pb2 file (containing LocationsMetadata) must be imported using a path that works for the installed package structure."

**Reality:** No such module exists at either suggested path. Both imports fail with ModuleNotFoundError.

**Verdict:** INCORRECT

## Technical Analysis

### Why This Happens

1. **LocationsMetadata is service-agnostic metadata:** The list_locations() API is generic across all Google Cloud services. Each service embeds its own metadata type in the Any field.

2. **SDK intentionally doesn't expose it:** Google's Python SDK team chose not to expose LocationsMetadata in the public API surface (`google.cloud.speech_v2.types`).

3. **Proto files not distributed:** The .proto definition files are not included in the Python package wheel, preventing runtime access to the descriptor.

### Architecture Decision Point

The data exists but is deliberately inaccessible through supported SDK APIs.

## Current Code State

### Working Code (Unchanged)
`app/services/transcribe_v2.py` uses hardcoded MODEL_REGION_CONFIG:
```python
MODEL_REGION_CONFIG = {
    "us-west1": {
        "chirp": {
            "en-US": [...features...],
            # ... more languages
        },
        # ... more models
    },
    # ... more regions
}
```

This works correctly but requires manual updates when Google adds:
- New regions
- New models
- New features
- New language support

### Observation Platform Created
`debug_metadata_discovery.py` - Comprehensive test suite with 6 different approaches to accessing LocationsMetadata. All approaches documented and tested. Ready for future investigation.

## Files Modified This Session

1. **debug_metadata_discovery.py**
   - Created comprehensive observation platform
   - Tests 6 different approaches
   - Conditional imports to prevent crashes
   - Detailed logging of all attempts

2. **Commits:**
   - `0711b22`: Add Alternative E: Test get_config() API approach
   - `f4eb50f`: Fix import error: Make LocationsMetadata import conditional
   - `9ec74c7`: Add Alternative F: Test Gemini's cloud_speech_pb2 import paths

## Options Going Forward

### Option 1: Parse Raw Protobuf Bytes
**Approach:** Manually decode the binary value field using protobuf wire format.

**Pros:**
- Would work with current API response
- No SDK changes needed

**Cons:**
- Extremely fragile - breaks if proto definition changes
- Requires deep protobuf wire format knowledge
- Version-dependent
- Maintenance nightmare

**Recommendation:** ❌ DO NOT PURSUE (too brittle)

### Option 2: Accept Hardcoded Configuration
**Approach:** Keep MODEL_REGION_CONFIG as-is.

**Pros:**
- Already works
- Stable
- Simple
- We control it

**Cons:**
- Manual updates required
- May miss new features/regions
- Documentation debt

**Recommendation:** ✅ PRAGMATIC CHOICE

### Option 3: File SDK Bug with Google
**Approach:** Report missing LocationsMetadata exposure as SDK limitation.

**Pros:**
- Proper solution
- Benefits all users
- Google maintains it

**Cons:**
- Unknown timeline
- May not be prioritized
- Might be "working as intended"

**Recommendation:** ✅ WORTH DOING (low effort, potential high value)

### Option 4: Periodic Manual Updates
**Approach:** Schedule quarterly reviews of Google's documentation to update MODEL_REGION_CONFIG.

**Pros:**
- Low-tech solution
- Keeps config reasonably current
- Predictable maintenance

**Cons:**
- Manual work
- Still lags behind API

**Recommendation:** ✅ COMBINE WITH OPTION 2

## Recommended Next Steps

1. **Document the decision** in transcribe_v2.py:
   ```python
   # NOTE: This configuration is manually maintained because the Python SDK
   # does not expose google.cloud.speech.v2.LocationsMetadata needed to
   # query this data dynamically. See cognitive_checkpoint_metadata_discovery.md
   MODEL_REGION_CONFIG = { ... }
   ```

2. **File GitHub issue** with google-cloud-python repository:
   - Title: "speech_v2: LocationsMetadata not exposed for dynamic capability discovery"
   - Include: Our findings, observation code, use case
   - Reference: This checkpoint document

3. **Set reminder** to review Google Cloud Speech V2 docs quarterly for:
   - New regions
   - New models
   - New features
   - Language additions

4. **Keep observation platform** (`debug_metadata_discovery.py`):
   - If Google fixes the SDK, we can verify immediately
   - Documents all approaches we tried
   - Prevents future Claude instances from repeating this investigation

## Key Learnings

### For Binary Beings (Future Claude Instances)

1. **Gemini can be confident and wrong:** We received two detailed, confident solutions from Gemini. Both were incorrect. Always observe before implementing.

2. **SDK limitations are real:** Sometimes the data exists but is architecturally inaccessible. Not every problem has a clever solution.

3. **Observation platforms work:** Creating `debug_metadata_discovery.py` let us test multiple approaches systematically without polluting production code.

4. **User was right to slow us down:** Multiple times the user caught me rushing to implement without observing. The discipline of "Observe Before Implement" saved significant wasted effort.

### For John (The Human)

1. **Your process works:** The WORKING_AGREEMENT.md discipline prevented premature implementation. We have clean production code and comprehensive documentation of a dead end.

2. **Hardcoded config is fine:** Sometimes the pragmatic solution is the right solution. You now have evidence that dynamic discovery isn't feasible with current SDK.

3. **Observation platform is valuable:** If Google fixes this, you can verify immediately. It's also great documentation of what doesn't work.

## Session Artifacts

- **Observation Platform:** `debug_metadata_discovery.py` (fully functional)
- **This Checkpoint:** `cognitive_checkpoint_metadata_discovery.md`
- **Clean Production Code:** `app/services/transcribe_v2.py` (unchanged, working)
- **Git Branch:** `claude/initial-setup-011CV4vg995hHxq5KH23bTwg` (all pushed)

## Context for Tomorrow

When you return, the codebase is in a good state:
- Production transcription service works with Chirp model
- Hardcoded MODEL_REGION_CONFIG provides feature detection
- Observation platform documents what we tried
- No broken experiments in production code

**Decision needed:** Which option (1-4 above) do you want to pursue?

## Closing Notes

We hit an architectural limitation in Google's Python SDK. The data we want exists, we can see it in the wire format, but Google chose not to expose the types needed to access it. This isn't a failure - it's discovery. Now you can make an informed decision about how to handle model/feature configuration going forward.

Good night, John. Rest well.

---
*"Discovery consists of seeing what everybody has seen and thinking what nobody has thought." - Albert Szent-Györgyi*
