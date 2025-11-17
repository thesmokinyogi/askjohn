# Gemini Prompt: Chirp Model Confidence Scores

## Question

Does Google Cloud Speech-to-Text V2's **Chirp model** support confidence scores? If yes, how do I enable and retrieve them?

## Context

I'm using Google Cloud Speech-to-Text V2 API with the Chirp model for batch recognition. I'm observing:

1. **Metadata Discovery**: When I query the Locations API metadata, Chirp shows support for `word_level_timestamps` but NOT `word_level_confidence` in the feature list.

2. **API Response**: When I submit a batch recognition job with Chirp:
   - The response includes a `confidence` field in the `alternative` object
   - However, the value is always `0.0` (not `null`, but explicitly `0.0`)
   - Word-level data is empty (because `enable_word_time_offsets` is rejected by the API)

3. **Feature Enablement**: When I try to enable:
   - `enable_word_time_offsets` → API rejects it (returns error)
   - `enable_word_confidence` → API rejects it (returns error)
   - Only `enable_automatic_punctuation` works

4. **Comparison**: The `long` model works fine and returns confidence scores (~95%) with word-level timestamps enabled.

## Specific Questions

1. **Does Chirp support confidence scores at all?** (Alternative-level or word-level)
2. **If yes, what's the correct way to enable them?** (Which feature flags/configuration?)
3. **Why does the API return `confidence: 0.0` instead of `null`?** Is this indicating "not available" or a configuration issue?
4. **Is there a difference between Chirp variants?** (chirp, chirp_2, chirp_3, chirp_telephony)
5. **Are confidence scores only available with certain features enabled?** (e.g., do I need word timestamps first?)

## What I've Tried

- Enabling `enable_word_confidence` → API error
- Enabling `enable_word_time_offsets` → API error  
- Checking metadata via Locations API → Shows `word_level_timestamps` but not `word_level_confidence`
- Using alternative-level `confidence` field → Always returns `0.0`

## API Details

- **API Version**: Speech-to-Text V2 (batch_recognize)
- **Model**: `chirp`
- **Location**: `us-central1`
- **Language**: `en-US`
- **Request Type**: Batch recognition with GCS input/output

Thank you for your help!

