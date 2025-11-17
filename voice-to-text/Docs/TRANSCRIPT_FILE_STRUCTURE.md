# Transcript File Structure

## Current Implementation

### Single JSON File Structure
Currently, we save **one JSON file** per transcription with the following structure:

```json
{
  "transcript": "Full transcript text here...",
  "confidence": 0.95,
  "saved_at": "2025-11-13T17:38:56.551090",
  "metadata": {
    "total_words": 519,
    "model": "chirp",
    "language": "en-US",
    "api_version": "v2",
    "words": [
      {
        "word": "Okay",
        "start_time": 0.5,
        "end_time": 0.8,
        "confidence": 0.98
      },
      {
        "word": "so",
        "start_time": 0.9,
        "end_time": 1.1,
        "confidence": 0.95
      }
      // ... more words
    ]
  }
}
```

### File Location
- **Path**: `data/transcripts/<job_id>_<filename>.json`
- **Example**: `data/transcripts/20251113_173825_Voice_Memo.json`

## Word Timings Structure

Each word object in `metadata.words` contains:
- `word`: The transcribed word text
- `start_time`: Start time in seconds (float)
- `end_time`: End time in seconds (float)
- `confidence`: Word-level confidence (0.0-1.0, or 0.0 for models like Chirp that don't support it)

## Requirements Clarification

### Option A: Current Approach (Single JSON File)
**Pros:**
- Simple, single file to manage
- All data in one place
- Easy to parse programmatically

**Cons:**
- Can't easily get "just the text" without parsing JSON
- Larger file size if you only need text

### Option B: Split Files
**Structure:**
- `transcript_<id>.txt` - Plain text, transcript only
- `transcript_<id>_words.json` - Word timings array

**Pros:**
- Easy to read transcript text directly
- Separates concerns
- Smaller files if you only need one or the other

**Cons:**
- Two files to manage
- Need to keep them in sync

## Current Status

✅ **Words are now being saved** in `metadata.words` (fixed in latest implementation)
✅ **Confidence handling** returns `None` for models that don't support it
✅ **Word timings** include `start_time` and `end_time` in seconds

## Next Steps

Please confirm:
1. Do you need **separate files** (Option B) or is the **single JSON file** (Option A) sufficient?
2. If separate files, should we:
   - Keep the JSON file AND create a .txt file?
   - OR replace the JSON with two separate files?

