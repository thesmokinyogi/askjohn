# Transcript Parsing Fix: BatchRecognizeResults Structure

## Problem Identified

The transcript parsing was extracting 0 segments from 200 results because we were iterating over the wrong level of the data structure.

## Root Cause

**`BatchRecognizeResults.results` is a MAP (dictionary), not a list!**

- **What we thought:** `batch_results.results` is a list of `SpeechRecognitionResult` objects
- **Reality:** `batch_results.results` is a dictionary keyed by filename, where values are `BatchRecognizeFileResult` objects
- **Actual transcript location:** Nested under `file_result.inline_result.transcript.results[]`

## The Fix

### Old Code (WRONG):
```python
for result in batch_results.results:  # This iterates over dict keys, not values!
    if result.alternatives:  # This never finds anything
        alternative = result.alternatives[0]
        results.append(alternative.transcript)
```

### New Code (CORRECT):
```python
# Iterate over the VALUES of the results map (BatchRecognizeFileResult objects)
for filename, file_result in batch_results.results.items():
    # Access transcript segments from inline_result.transcript.results
    if hasattr(file_result, 'inline_result') and file_result.inline_result:
        if hasattr(file_result.inline_result, 'transcript') and file_result.inline_result.transcript:
            if hasattr(file_result.inline_result.transcript, 'results'):
                batch_segments = file_result.inline_result.transcript.results
                
                # Now iterate through the actual SpeechRecognitionResult segments
                for result_segment in batch_segments:
                    if result_segment.alternatives:
                        alternative = result_segment.alternatives[0]
                        results.append(alternative.transcript)
```

## Structure Diagram

```
BatchRecognizeResults
└── results (dict/map)
    └── key: filename (e.g., "gs://bucket/file.mp3")
        └── value: BatchRecognizeFileResult
            └── inline_result
                └── transcript
                    └── results (list)
                        └── SpeechRecognitionResult[]
                            └── alternatives[]
                                └── transcript (the actual text!)
```

## Key Insights from Gemini

1. **GCS output structure is different from inline output** - even though we use GCS output, the segments are still accessible via `inline_result.transcript.results`

2. **`results` is a map, not a list** - The keys are the original input filenames (GCS URIs), values are `BatchRecognizeFileResult` objects

3. **Nested structure** - Transcript segments are nested 4 levels deep:
   - `batch_results.results` (map)
   - `file_result` (BatchRecognizeFileResult)
   - `inline_result.transcript` (Transcript object)
   - `results[]` (list of SpeechRecognitionResult)

## Changes Made

1. ✅ Fixed main parsing loop to iterate over `batch_results.results.items()`
2. ✅ Added proper traversal of nested structure: `file_result.inline_result.transcript.results`
3. ✅ Fixed word extraction to work within the nested loop
4. ✅ Fixed confidence calculation fallback to use new structure
5. ✅ Fixed metadata extraction to use new structure
6. ✅ Fixed debug logging to use new structure

## Testing

The fix should now correctly extract transcripts from completed jobs. The next test job should show:
- "Parsed X segments, Y words" where X > 0
- Actual transcript text in the output
- Word-level timestamps if available

## References

- Gemini consultation provided the structure explanation
- Google Cloud Speech-to-Text V2 API documentation
- `docs/GEMINI_QUESTIONS_TRANSCRIPT_PARSING.md` - Questions asked
- `docs/TRANSCRIPT_PARSING_ANALYSIS.md` - Original analysis

