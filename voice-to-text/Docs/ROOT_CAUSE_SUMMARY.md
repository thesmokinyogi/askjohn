# Root Cause Summary: Empty Transcripts

## Gemini's Diagnosis: ASR Starvation

**The Problem:** The recognition engine receives segmented audio but cannot extract enough high-confidence acoustic data to form words.

**Root Cause:** MP3 (lossy codec) + subtle background music creates computational conflict for V2 ASR engine, especially with Chirp models.

## What We Know

### The Format We're Seeing IS Expected (for Failed Transcription)
- Segments with only `resultEndOffset` and `languageCode` = **ASR failure signature**
- This means: segmentation succeeded ✅, transcription failed ❌
- We're downloading the correct file - it's just empty of transcript data

### Why This Happens
1. **MP3 is lossy** - discards data in frequency bands shared by music and speech
2. **Background music** - confuses ASR engine's speech separation
3. **Chirp sensitivity** - Chirp models are particularly sensitive to this combination

## Your New Test (No Background Music)

**This is the critical test!** It will tell us:

### If It WORKS (no music, still MP3):
- ✅ Background music was the issue
- ✅ MP3 alone is acceptable
- ✅ We can proceed with MP3 files (as long as no music)

### If It FAILS (no music, still MP3):
- ❌ MP3 encoding is still problematic (or something else)
- ❌ We need to convert to lossless WAV
- ❌ Or there's another issue we haven't identified

## Next Steps Based on Your Test

### Scenario A: New Test WORKS
1. **Root cause confirmed:** Background music + MP3 + Chirp = failure
2. **Solution:** 
   - Use "long" model for speech+music content
   - Use Chirp for clean speech-only content
   - Or preprocess audio to remove/isolate music

### Scenario B: New Test FAILS
1. **Root cause:** MP3 encoding or something else
2. **Solution:**
   - Convert to lossless WAV (LINEAR16 @ 16000 Hz)
   - Test with simplified config
   - Test with "long" model (as Gemini recommended)

## Gemini's Recommendations (If New Test Fails)

### Test 1: Eliminate Lossy Codec (Priority 1)
1. Re-encode to LINEAR16 (WAV) @ 16000 Hz
2. Use minimal config with "long" model
3. Enable only `enable_word_time_offsets`
4. This will confirm if MP3 is the issue

### Test 2: Isolate Chirp's Tolerance (Priority 2)
1. Use lossless WAV from Test 1
2. Switch to "chirp_3" or "chirp_2"
3. This will determine if Chirp can handle the audio with clean encoding

## What We Should Do Now

1. **Wait for your test results** (no music audio)
2. **Analyze the results** - does it work or fail?
3. **Based on results:**
   - If works → Music was the issue, implement model selection strategy
   - If fails → Follow Gemini's Test 1 (convert to WAV, use "long" model)

## Key Insight

**The format we're seeing is correct** - it's just that the transcription failed. The segments exist, but they have no transcript text because the ASR engine couldn't extract speech from the audio.

This is NOT a parsing issue. This is NOT a config issue (though simplifying helps). This IS an audio quality/compatibility issue.

