# Critical Questions for Gemini: Empty Transcript Root Cause

## The Problem

We're experiencing a persistent issue where **batch recognition jobs complete successfully** (200 segments processed) but **return NO transcript text** - only metadata (`resultEndOffset`, `languageCode`).

**This has been going on for a long time.** We've tried many approaches but haven't found the root cause. We need your help to get us on the right track.

---

## What We Know

### 1. The Symptoms
- ✅ Jobs complete successfully (status: "complete")
- ✅ Google processes 200 segments (audio is segmented correctly)
- ✅ Segments contain timing metadata (`resultEndOffset`, `languageCode`)
- ❌ **NO transcript text** in any segment's `alternatives` field
- ❌ Segments only contain: `{"resultEndOffset": "30s", "languageCode": "en-US"}`

### 2. The Audio File
- ✅ **We can listen to it** - it contains clear speech
- ✅ File is valid MP3 format
- ✅ Uploaded to GCS successfully
- ✅ Audio metadata extracted correctly (sample_rate, channels, duration)

### 3. Our Request Structure
We're using `BatchRecognizeRequest` with:
```python
request = cloud_speech.BatchRecognizeRequest(
    recognizer=f"projects/{PROJECT_ID}/locations/{LOCATION}/recognizers/_",
    config=config,  # RecognitionConfig (see below)
    files=[file_metadata],  # BatchRecognizeFileMetadata with GCS URI
    recognition_output_config=cloud_speech.RecognitionOutputConfig(
        gcs_output_config=cloud_speech.GcsOutputConfig(
            uri=f"gs://{bucket}/transcripts/"
        )
    ),
    processing_strategy=cloud_speech.BatchRecognizeRequest.ProcessingStrategy.DYNAMIC_BATCHING,  # Just added
)
```

### 4. Our RecognitionConfig
We build a complex config with:
- `auto_decoding_config` or `explicit_decoding_config` (based on file format)
- `language_codes=["en-US"]`
- `model="chirp"` (or other models)
- `features=RecognitionFeatures(...)` with:
  - `enable_word_time_offsets=True` (always enabled)
  - `enable_automatic_punctuation=True` (if supported)
  - `enable_word_confidence=False` (Chirp doesn't support it)

### 5. What We've Tried

#### A. Parsing Approaches
- ✅ Tried Protobuf deserialization → Failed (empty alternatives)
- ✅ Tried direct JSON parsing → Failed (no alternatives in JSON)
- ✅ Verified we're downloading the correct GCS file
- ✅ Confirmed JSON structure: `{"results": [{"resultEndOffset": "30s", "languageCode": "en-US"}, ...]}`

#### B. Configuration Debugging
- ✅ Added extensive debug logging
- ✅ Verified config is being created with decoding config
- ✅ Verified features are enabled
- ✅ Logs show: `auto_decoding_config` is present in config object

#### C. Comparison with Official Examples
- ✅ Compared our code to Google's official Python examples
- ✅ Found we were missing `processing_strategy` → **Just added it**
- ✅ Structure matches official examples (except we use regional locations for Chirp)

### 6. The GCS JSON Output

When we download the result file from GCS, it contains:
```json
{
  "results": [
    {
      "resultEndOffset": "30s",
      "languageCode": "en-US"
    },
    {
      "resultEndOffset": "60s",
      "languageCode": "en-US"
    },
    // ... 200 segments, all with same structure
  ]
}
```

**No `alternatives` field. No `transcript` field. No `words` field.**

---

## Critical Questions

### Question 1: Is `processing_strategy` Required?

We just discovered Google's official examples always include:
```python
processing_strategy=cloud_speech.BatchRecognizeRequest.ProcessingStrategy.DYNAMIC_BATCHING
```

**We were missing this field.** 

- **Is this field REQUIRED for batch recognition to work correctly?**
- **Could omitting it cause the API to process audio but not generate transcript text?**
- **What happens if you omit it - does it default to something, or fail silently?**

### Question 2: Why Are Segments Empty?

The segments contain timing metadata but no transcript:
- Audio is being segmented correctly (200 segments)
- Language is detected correctly (`en-US`)
- But no transcription text is generated

**What could cause this?**
- Is it a config issue (decoding, features, model)?
- Is it an output format issue (GCS vs inline)?
- Is it a processing strategy issue?
- Is it something else entirely?

### Question 3: RecognitionConfig - Are We Over-Complicating?

Google's official examples use a **very simple config**:
```python
config = cloud_speech.RecognitionConfig(
    auto_decoding_config=cloud_speech.AutoDetectDecodingConfig(),
    language_codes=["en-US"],
    model="chirp_3",
)
```

**We build a complex config** with:
- Feature detection (checking metadata for supported features)
- Conditional feature enabling
- Phrase hints (for non-Chirp models)
- Explicit vs auto decoding based on file format

**Could our complex config be causing issues?**
- Are we accidentally disabling something critical?
- Are we setting conflicting options?
- Should we simplify to match the official example?

### Question 4: GCS Output Format - Is This Expected?

When using `GcsOutputConfig`, the JSON file we download contains segments with only metadata:
- `resultEndOffset`
- `languageCode`
- **No `alternatives` array**

**Is this the expected format for GCS output?**
- Or should it contain `alternatives` with transcript text?
- Is there a different file we should be downloading?
- Is there a different output format we should be using?

### Question 5: Regional vs Global Location

Google's examples use:
```python
recognizer=f"projects/{PROJECT_ID}/locations/global/recognizers/_"
```

**We use regional locations** (e.g., `us-central1`) because:
- Chirp models require regional endpoints
- We discovered this through testing

**Could using regional locations cause issues?**
- Is there a difference in how results are formatted?
- Could this affect transcript generation?

### Question 6: What Should We Test Next?

**We've been debugging for a long time.** We need direction:

1. **Should we test with inline results first?** (eliminate GCS parsing complexity)
2. **Should we simplify our config?** (match official example exactly)
3. **Should we test with a different model?** (e.g., `long` instead of `chirp`)
4. **Is there something fundamental we're missing?**

---

## What We Need

**We need you to challenge our assumptions and get us on the right track.**

1. **What's the most likely root cause?** (Be direct - we've been debugging too long)
2. **What should we test first?** (Prioritize - what's most likely to reveal the issue)
3. **Are we missing something obvious?** (Sometimes the simplest things are overlooked)
4. **What would you do differently?** (Fresh perspective needed)

---

## Our Current Hypothesis

We suspect one of these:
1. **Missing `processing_strategy`** - We just added it, haven't tested yet
2. **Over-complicated config** - Our feature detection might be breaking something
3. **GCS output format misunderstanding** - Maybe we're parsing the wrong structure
4. **Something fundamental we're missing** - We need your expertise

---

## Code Context

### Our submit_job method:
```python
def submit_job(self, gcs_uri: str, language_code: str = "en-US", 
               audio_metadata: Optional[Dict] = None, 
               output_bucket: str = None):
    config = self._build_config(
        audio_encoding=gcs_uri.split('.')[-1],
        language_code=language_code,
        audio_metadata=audio_metadata
    )
    
    file_metadata = cloud_speech.BatchRecognizeFileMetadata(uri=gcs_uri)
    request = cloud_speech.BatchRecognizeRequest(
        recognizer=f"projects/{self.project_id}/locations/{self.location}/recognizers/_",
        config=config,
        files=[file_metadata],
        recognition_output_config=cloud_speech.RecognitionOutputConfig(
            gcs_output_config=cloud_speech.GcsOutputConfig(
                uri=f"gs://{output_bucket}/transcripts/"
            )
        ),
        processing_strategy=cloud_speech.BatchRecognizeRequest.ProcessingStrategy.DYNAMIC_BATCHING,  # Just added
    )
    
    operation = self.client.batch_recognize(request=request)
    return operation
```

### Our _build_config method:
- Determines explicit vs auto decoding based on file format
- Queries metadata for supported features
- Conditionally enables features
- Adds phrase hints for non-Chirp models
- Returns `RecognitionConfig` object

---

## The Challenge

**Help us stop debugging and start fixing.** 

We've been adding band-aids (debug logging, parsing fixes) but haven't found the root cause. We need your expertise to:
1. Identify the most likely cause
2. Tell us what to test first
3. Get us on the right track

**What would you do if this was your problem?**

