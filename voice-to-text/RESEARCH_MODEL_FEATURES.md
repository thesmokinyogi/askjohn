# Google Speech-to-Text V2: Model Feature Support Research

**Date**: 2025-11-12
**Researcher**: Claude
**Objective**: Understand model-specific feature support to implement dynamic, model-aware configuration

---

## Research Summary

### Problem Statement
Current implementation applies universal `RecognitionFeatures` configuration to all models:
- `enable_automatic_punctuation=True`
- `enable_word_time_offsets=True`
- `enable_word_confidence=True`

**Result**: Chirp model fails with error:
```
400 Config contains unsupported fields.
field_violations {
  field: "features.enable_word_confidence"
  description: "Recognizer does not support feature: word_level_confidence"
}
```

**Root Cause**: Models have different feature support - we're treating the API as model-agnostic when it's model-specific.

---

## Confirmed Findings

### 1. RecognitionFeatures Complete Definition

From protobuf definition (`cloud_speech.proto`):

| Field | Type | Optional | Description |
|-------|------|----------|-------------|
| `profanity_filter` | bool | yes | Mask profanities with asterisks |
| `enable_word_time_offsets` | bool | yes | Include word-level start/end times |
| `enable_word_confidence` | bool | yes | Include confidence scores per word |
| `enable_automatic_punctuation` | bool | yes | Add punctuation (language-dependent) |
| `enable_spoken_punctuation` | bool | yes | Convert "question mark" → "?" |
| `enable_spoken_emojis` | bool | yes | Convert emoji names → Unicode emojis |
| `multi_channel_mode` | enum | yes | How to handle multi-channel audio |
| `diarization_config` | message | yes | Speaker identification configuration |
| `max_alternatives` | int32 | yes | Max hypotheses to return (0-30) |

### 2. Model Feature Support Matrix (from documentation)

#### Chirp (Original)
**Supported:**
- ✅ `enable_automatic_punctuation`
- ✅ `enable_word_time_offsets`

**NOT Supported:**
- ❌ `enable_word_confidence` ← **CAUSES CURRENT ERROR**
- ❌ Speech adaptation
- ❌ `diarization_config`
- ❌ Confidence scores (API returns value but "not truly a confidence score")

**Note**: Docs say "confidence scores not supported" but unclear if this means:
- `max_alternatives` confidence?
- `enable_word_confidence`?
- Both?

#### Chirp 2
**Supported:**
- ✅ `enable_automatic_punctuation`
- ✅ `enable_word_time_offsets`
- ✅ `enable_word_confidence` (with caveat: "not truly a confidence score")
- ✅ Speech adaptation (phrase hints)
- ✅ `profanity_filter`
- ✅ `enable_spoken_punctuation`
- ✅ `enable_spoken_emojis`
- ✅ Translation features

**NOT Supported:**
- ❌ `diarization_config`

#### Chirp 3
**Research Gap**: Documentation found but feature list not fully extracted yet.

#### Long/Latest_Long
**Supported:**
- ✅ `enable_automatic_punctuation`
- ✅ `enable_word_time_offsets`
- ✅ `enable_word_confidence` (with caveat: "not truly a confidence score")
- ✅ `profanity_filter`
- ✅ `enable_spoken_punctuation`
- ✅ `diarization_config` (PREVIEW status)

**Unsure:**
- ⚠️ `enable_spoken_emojis` - not mentioned in docs
- ⚠️ `multi_channel_mode` - docs mention feature but unclear if all modes supported

### 3. Locations API - Capability Discovery

**Confirmed Capabilities:**
- API endpoint exists: `projects.locations.list`
- Returns metadata about available features per model per location
- Supports filtering: `language = en-US AND model = latest_long AND model_feature != profanity_filter`
- Python client has `list_locations()` method

**Filter Syntax Discovered:**
```
filter="language = {BCP-47} AND model = {model_name} AND model_feature != {feature}"
```

**Example Features in Metadata:**
- `profanity_filter` (release state: GA)
- `spoken_punctuation` (release state: GA)
- `automatic_punctuation` (release state: GA)
- `speaker_diarization` (release state: PREVIEW_DIARIZATION)

### 4. Model Naming Conventions

**Observed Model Names:**
- Documentation: `chirp`, `chirp_2`, `chirp_3`, `long`, `short`, `telephony`
- API might also accept: `latest_long`, `latest_short`
- Our UI uses: `chirp_batch`, `chirp_standard`, `long_batch`, `long_standard`
- Our mapping: `chirp_batch` → `chirp`, `long_standard` → `long`

---

## Research Gaps & Uncertainties

### Critical Gaps

1. **Location Metadata Structure**
   - What exactly is in `location.metadata`?
   - Is it structured as: location → models → features?
   - How to access model-specific feature support programmatically?

2. **Model Identifier Ambiguity**
   - Is "chirp" the same as "chirp_3" or different?
   - When docs say "chirp", do they mean original chirp or latest chirp?
   - What model name does the API actually accept?
   - Are `long` and `latest_long` aliases or different models?

3. **Feature Name Mapping**
   - Error says: `enable_word_confidence`
   - Docs say: "word_level_confidence"
   - Location metadata says: unknown (need to query)
   - Are these the same feature with different names?

4. **RecognitionFeatures → model_feature Mapping**
   - Do all 9 RecognitionFeatures map to queryable `model_feature` filters?
   - Or are some features not discoverable via Locations API?
   - Example: Is `max_alternatives` a queryable feature?

5. **Error Handling Behavior**
   - When unsupported feature requested, does API:
     - Reject entire request (current observation)?
     - Accept request but ignore unsupported features?
     - Return error but process anyway?
   - Does behavior differ by feature type?

6. **Version Evolution**
   - When Google updates models, do they:
     - Create new identifiers (chirp → chirp_2 → chirp_3)?
     - Update capabilities of existing identifiers?
   - How to handle API updates in production?

### Secondary Gaps

7. **Multi-Channel Mode Details**
   - Docs say "not supported for `latest_short`"
   - What about other models?
   - Is it all-or-nothing or mode-specific?

8. **Diarization Configuration**
   - Chirp 2: explicitly NOT supported
   - Long: PREVIEW status
   - What does PREVIEW mean for reliability?

9. **Language-Specific Features**
   - `enable_automatic_punctuation` "only available for select languages"
   - How to query which languages support which features?
   - Does Locations API expose this?

10. **Translation Features**
    - Chirp 2 supports translation
    - How does this interact with other features?
    - Are features disabled during translation?

---

## Architecture Options Evaluated

### Option A: Dynamic Feature Detection (API-Based)
**Approach**: Query Locations API at runtime to discover supported features per model.

**Pros:**
- Always up-to-date with Google's latest capabilities
- Self-healing when Google adds/removes features
- No manual maintenance

**Cons:**
- Adds API call latency (though minimal compared to transcription)
- Depends on API availability
- Requires understanding of metadata structure

**Status**: **PREFERRED** - User approved this approach

### Option B: Static Feature Matrix (Code-Based)
**Approach**: Maintain hardcoded feature support matrix in code.

**Pros:**
- Fast - no API calls
- Explicit and testable
- Works offline

**Cons:**
- Requires manual maintenance
- Can drift from Google's changes
- No automatic adaptation

**Status**: Fallback if Option A not feasible

### Option C: Graceful Degradation (Hybrid)
**Approach**: Try features, catch errors, retry without unsupported features.

**Pros:**
- Self-discovering
- Adapts to changes

**Cons:**
- Wasteful (failed API calls cost time/money)
- Slower first-time use
- Relies on consistent error messages

**Status**: Could complement Option A

---

## Next Steps

### Phase 1: Complete Research ✅ IN PROGRESS
1. ✅ Identify all RecognitionFeatures
2. ⏳ Document known model support matrix
3. ❓ Understand Locations API response structure
4. ❓ Clarify model naming conventions
5. ❓ Map RecognitionFeatures to model_feature identifiers

### Phase 2: Design Architecture
1. Design feature detection mechanism
2. Create caching strategy (balance freshness vs performance)
3. Define error handling for unsupported features
4. Plan migration path for existing code

### Phase 3: Implementation
1. Implement Locations API query
2. Build feature support cache
3. Refactor `_build_recognition_config()` to be model-aware
4. Add feature validation before submission
5. Add logging for degraded features

### Phase 4: Validation
1. Test with all models (chirp, chirp_2, long, etc.)
2. Verify each RecognitionFeature
3. Test edge cases (unsupported features, new models)
4. Performance testing (cache hit rates, latency)

---

## Questions for Google Gemini

### Critical Questions

1. **Locations API Metadata Structure**
   - When I call `client.list_locations(request)` and get a `location` object, what does `location.metadata` contain?
   - Is the structure: `{models: [{name: str, features: [...]}]}`?
   - How do I programmatically extract which features each model supports?

2. **Model Naming Authoritative Reference**
   - What are the exact, canonical model identifiers accepted by `RecognitionConfig.model`?
   - Is "chirp" different from "chirp_2" and "chirp_3", or are they versions of the same model?
   - What is the relationship between "long" and "latest_long"?

3. **Feature Name Mapping**
   - The error message references `enable_word_confidence`
   - Documentation sometimes says "word_level_confidence"
   - Locations API filter uses `model_feature`
   - How do RecognitionFeatures field names map to model_feature filter values?
   - Is there a canonical mapping table?

4. **Complete Feature Support Matrix**
   - Can you provide an authoritative table showing:
     - Rows: All available model identifiers (chirp, chirp_2, chirp_3, long, etc.)
     - Columns: All RecognitionFeatures (enable_word_confidence, enable_automatic_punctuation, etc.)
     - Values: Supported (yes/no) and release state (GA/PREVIEW)

5. **API Behavior for Unsupported Features**
   - When I submit a `RecognitionConfig` with features unsupported by the model, what happens?
   - Does the entire request fail (current observation)?
   - Are unsupported features silently ignored?
   - Does behavior differ by feature importance?

### Implementation Questions

6. **Python Client Usage**
   - What is the correct way to use `SpeechClient.list_locations()` to discover features?
   - Can you provide a complete code example showing:
     - Query locations for a project
     - Filter by model
     - Extract supported features from metadata

7. **Caching Strategy**
   - How often do model capabilities change?
   - Is it safe to cache Locations API responses for the duration of a process?
   - Or should we query on every transcription request?

8. **Multi-Language Feature Support**
   - Features like `enable_automatic_punctuation` are "language-dependent"
   - How do I query which languages support which features for a given model?
   - Does the Locations API expose this, or is it in different documentation?

9. **Version Evolution**
   - When Google releases chirp_4 or updates chirp_3 capabilities, will:
     - The model identifier change?
     - The Locations API automatically reflect this?
     - Existing code using "chirp" continue to work?

10. **Error Message Interpretation**
    - Error says: `field: "features.enable_word_confidence" description: "Recognizer does not support feature: word_level_confidence"`
    - Why different names (`enable_word_confidence` vs `word_level_confidence`)?
    - Is this a consistent pattern I can parse for other features?

---

## Research Sources

### Documentation Reviewed
- ✅ Chirp model page: https://cloud.google.com/speech-to-text/v2/docs/chirp-model
- ✅ Chirp 2 model page: https://cloud.google.com/speech-to-text/v2/docs/chirp_2-model
- ⏳ Chirp 3 model page: https://cloud.google.com/speech-to-text/v2/docs/chirp_3-model
- ✅ Transcription models comparison: https://cloud.google.com/speech-to-text/v2/docs/transcription-model
- ✅ Regional availability: https://cloud.google.com/speech-to-text/v2/docs/locations
- ✅ RecognitionFeatures protobuf: https://github.com/googleapis/google-cloud-node/blob/main/packages/google-cloud-speech/protos/google/cloud/speech/v2/cloud_speech.proto

### API References Accessed
- ⏳ Python SpeechClient: https://docs.cloud.google.com/python/docs/reference/speech/latest/google.cloud.speech_v2.services.speech.SpeechClient (403 error)
- ✅ RPC Reference: https://cloud.google.com/speech-to-text/v2/docs/reference/rpc/google.cloud.speech.v2
- ⏳ REST Reference (projects.locations): Searching...

### Code Examples Found
- ✅ GitHub Python client: https://github.com/googleapis/google-cloud-python/blob/main/packages/google-cloud-speech/google/cloud/speech_v2/services/speech/client.py
- ✅ Official samples: https://github.com/GoogleCloudPlatform/python-docs-samples/blob/main/speech/snippets/transcribe_gcs_v2.py

---

## Confidence Assessment

| Area | Confidence | Evidence Quality |
|------|------------|------------------|
| RecognitionFeatures list | **HIGH** | Official protobuf definition |
| Chirp 1 limitations | **HIGH** | Multiple doc sources consistent |
| Chirp 2 capabilities | **MEDIUM** | Docs found but some ambiguity |
| Long model capabilities | **MEDIUM** | Partial documentation |
| Locations API exists | **HIGH** | Multiple references, code examples |
| Locations API structure | **LOW** | No direct access to response format |
| Model naming | **LOW** | Inconsistent across docs |
| Feature name mapping | **LOW** | Error messages don't match docs |

---

## Status: RESEARCH IN PROGRESS

**Blockers:**
- Web documentation access limited (403 errors)
- Web search intermittent
- No direct API testing environment

**Next Action:**
- Compile questions for Google Gemini
- Request specific code examples
- If needed: Test Locations API directly in production environment

**User Approval**: Proceeding with Option A (Dynamic Feature Detection)
