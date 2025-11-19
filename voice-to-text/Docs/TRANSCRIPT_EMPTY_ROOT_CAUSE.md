# Root Cause Analysis: Empty Transcript Segments

## Problem

Completed transcription jobs show 200 segments with timing metadata (`resultEndOffset`, `languageCode`) but **no transcript text** in the `alternatives` field.

## Root Cause (Per Gemini)

**This is NOT a parsing error - it's an input configuration error.**

The transcript text was never generated because the RecognitionConfig sent to Google's API was incorrect or incomplete. The model successfully segmented the audio (hence 200 segments with timing), but failed to generate transcription text.

## Common Causes

1. **Incorrect Audio Configuration**
   - Wrong encoding format
   - Wrong sample rate
   - Mismatched audio parameters

2. **Language Mismatch**
   - Language code doesn't match audio content
   - Model can't identify speech in specified language

3. **Missing Critical Features**
   - Word timings not enabled (should always be enabled for debugging)
   - Features that force verbose output missing

4. **Silence/Unintelligible Audio**
   - Audio contains only silence or noise
   - Model can't confidently transcribe

## Fixes Implemented

1. ✅ **Always enable word timings** (per Gemini recommendation)
   - Forces verbose output for debugging
   - Even if metadata says unsupported, we enable it anyway

2. ✅ **Added detailed config logging**
   - Log RecognitionFeatures (word timings, confidence, punctuation)
   - Log decoding config (encoding, sample rate, channels)
   - Log whether auto-detection is used

3. ✅ **Direct JSON parsing** (already implemented)
   - Bypasses Protobuf deserializer issues
   - Ready to extract transcript once it's generated

## Next Steps

1. **Test with a new job** to see what config is actually being sent
2. **Check the debug logs** for:
   - Is `enable_word_time_offsets` actually enabled?
   - What encoding/sample rate is being used?
   - Is auto-detection working correctly?

3. **Verify audio file**:
   - Is the MP3 file valid and contains speech?
   - Are the audio parameters correct?

4. **If still empty**, check:
   - Audio file quality (listen to it)
   - Language code matches audio content
   - Model supports the language/audio format

## Expected Behavior After Fix

Once the config is correct, the JSON segments should contain:
```json
{
  "resultEndOffset": "30s",
  "languageCode": "en-US",
  "alternatives": [
    {
      "transcript": "actual transcript text here",
      "confidence": 0.95,
      "words": [...]
    }
  ]
}
```

## References

- Gemini consultation: Input configuration failure diagnosis
- `docs/GEMINI_FINAL_TRANSCRIPT_PARSING.md` - Our findings
- `app/services/transcribe_v2.py` - Config building code

