# Cognitive Checkpoint - 2025-11-09
**Session Topic:** M4A Transcription Debugging & MP3 Conversion Solution
**Duration:** ~4 hours
**Status:** ✅ **SUCCESS - Transcription Working!**

---

## Session Summary

**Goal:** Get V2 batch transcription working end-to-end

**Result:**
- ✅ Successfully transcribed 5.6-minute audio file
- ✅ 645 words, 94% confidence
- ✅ Cost: $0.13 (337 seconds × $0.024/min)
- ⚠️ **Discovery:** M4A format broken with batch_recognize, converted to MP3 as workaround

---

## What We Built

### 1. M4A → MP3 Conversion (Workaround)
**File:** `app/services/storage.py`

**What:** Automatic conversion of M4A files to MP3 before upload

**Why:** M4A + ExplicitDecodingConfig + batch_recognize consistently fails with "RecognitionAudio empty" error despite correct configuration

**How:**
```python
if file_extension == '.m4a':
    audio = AudioSegment.from_file(m4a_path, format="m4a")
    audio.export(mp3_buffer, format="mp3", bitrate="128k")
```

**Impact:**
- Adds ~2 seconds conversion time
- MP3 works perfectly with AutoDetectDecodingConfig
- User can now transcribe iPhone voice memos

### 2. Audio Metadata Extraction
**File:** `app/services/storage.py`

**What:** Extract actual audio specs (sample rate, channels) using pydub

**Why:** ExplicitDecodingConfig requires accurate audio parameters

**Result:**
- Extracts: sample_rate (44100Hz), channels (1), duration (336.8s)
- Provides to transcription service for correct configuration
- Falls back to defaults (16kHz, mono) if extraction fails

### 3. Test Mode for Rapid Iteration
**File:** `app/main.py`

**What:** Skip upload/delete for testing transcription config changes

**Usage:**
```bash
# In .env
TEST_MODE_SKIP_UPLOAD=true
```

**Impact:** Instant testing without re-uploading 2.6 MB file

### 4. Clean Logging
**File:** `app/services/transcribe_v2.py`

**What:** Removed verbose debug logging, kept essential info

**Output:**
```
Billed duration: 0:05:37
Processed 66 segments, 645 words
```

---

## The M4A Mystery - Deep Dive

### What We Tried (All Failed)

1. ✗ **AutoDetectDecodingConfig** → M4A not supported
2. ✗ **ExplicitDecodingConfig with defaults** → audio_channel_count out of range
3. ✗ **ExplicitDecodingConfig with wrong values** (16kHz) → RecognitionAudio empty
4. ✗ **ExplicitDecodingConfig with omitted values** → audio_channel_count out of range (defaults to 0)
5. ✗ **ExplicitDecodingConfig with correct values** (44100Hz, 1ch) → RecognitionAudio empty

### The Pattern

**Error progression:**
- Wrong/omitted params: "audio_channel_count out of range"
- Correct params: "RecognitionAudio empty" (code 3)

**Key insight:** Even with CORRECT metadata from the actual file, M4A fails.

### Root Cause Theory

**M4A + batch_recognize is broken** despite Google documentation claiming support:
- ExplicitDecodingConfig lists M4A_AAC (enum value 11)
- But batch_recognize cannot process M4A files
- Synchronous recognize() might work, but limited to 60 seconds
- Your files are 5-6 minutes (and yoga classes are 75 minutes)

**Evidence:**
- Exact same config with MP3 works instantly
- No code changes needed, just file format swap
- AutoDetectDecodingConfig works for MP3 (no parameters needed)

---

## Key Learnings

### 1. "Optional but effectively required" Explained

**Protobuf fields marked "optional"** means you CAN syntactically omit them, BUT:
- Omitting sets default value (often 0)
- API logic may require non-zero values
- audio_channel_count: valid range 1-8, default 0 = error

**Lesson:** "Optional" doesn't mean "unnecessary" - check API requirements.

### 2. Working Agreement Addition

Added **"Before Implementing New APIs/Libraries" checklist** (v1.2):
- Find COMPLETE working examples (not fragments)
- Read full method signatures
- Identify ALL required parameters
- **Principle:** "Let documentation be the test oracle, not the user"

**Context:** We implemented ExplicitDecodingConfig incrementally through errors instead of reading full docs first.

### 3. Evidence-Based Debugging Process

**Your feedback:** "Stop guessing, check the documentation first"

**Impact:** Added to working agreement as principle for future API work

### 4. Trust Library vs Be Self-Sufficient

**Discussion:** Option B (trust library enum, fall back to int) vs Option C (hardcode all values)

**Decision:** Option B - trust Google's library as source of truth
```python
try:
    M4A_AAC = cloud_speech.ExplicitDecodingConfig.AudioEncoding.M4A_AAC
except AttributeError:
    M4A_AAC = 11  # Fallback
```

**Rationale:** Forward-compatible, auto-upgrades when library fixed

### 5. Data-Driven Architecture

**Refactored format detection** from if-statements to dictionaries:

**Before:**
```python
if encoding == 'M4A':
    # explicit config
else:
    # auto-detect
```

**After:**
```python
AUTO_DETECT_FORMATS = {'wav', 'flac', 'mp3', ...}
EXPLICIT_ENCODING_MAP = {'m4a': 11, 'mp4': 10, 'mov': 12}
```

**Benefits:** Single source of truth, easy to extend, self-documenting

---

## Current State

### Working
✅ End-to-end transcription (MP3)
✅ Metadata extraction
✅ Provider abstraction (Google/Whisper)
✅ Bucket permissions (Storage Admin + Speech Administrator)
✅ Test mode for rapid iteration
✅ Clean logging

### In Progress
⚠️ M4A automatic conversion (workaround, not fix)
⚠️ Phrase hints disabled (V2 syntax TBD)

### Not Yet Started
- Model selection UI with cost display
- Budget tracking
- Admin configuration page
- SETUP_V2.md updates with complete steps
- Test with 75-minute yoga class

---

## Setup State

### Working Configuration

**`.env` file:**
```bash
# STRATEGIC
STT_PROVIDER=google

# TACTICAL (Google-specific)
GOOGLE_APPLICATION_CREDENTIALS=/Users/.../credentials/voice-to-text-dev-477522-eacae7e41318.json
GOOGLE_CLOUD_PROJECT=voice-to-text-dev-477522
GCS_BUCKET_NAME=voice-to-text-audio-jc
GOOGLE_MODEL=long

# TEST MODE
TEST_MODE_SKIP_UPLOAD=false
```

### IAM Permissions
**Service account:** `id-name-voice-to-text-service@voice-to-text-dev-477522.iam.gserviceaccount.com`

**Roles:**
- ✅ Storage Admin (bucket + object read/write)
- ✅ Cloud Speech Administrator (V2 API access)

**Note:** "Cloud Speech Client" role only works for V1, not V2!

### APIs Enabled
- ✅ Cloud Speech-to-Text API (v2)
- ✅ Cloud Storage API

### Bucket Details
- **Name:** voice-to-text-audio-jc
- **Location:** US-WEST1
- **Storage class:** STANDARD

---

## Files Modified This Session

### New Files
- `voice-to-text/test_gcs_access.py` - Bucket permission verification script
- `voice-to-text/COGNITIVE_CHECKPOINT_20251109.md` - This file

### Major Changes
1. **app/services/storage.py**
   - Added audio metadata extraction (pydub)
   - Added M4A → MP3 conversion
   - Returns tuple: (gcs_uri, metadata)

2. **app/services/transcribe_v2.py**
   - Data-driven format detection (dictionaries)
   - Option B enum handling (trust library)
   - Accepts audio_metadata parameter
   - Uses actual sample_rate and channels
   - Cleaned up debug logging

3. **app/main.py**
   - Test mode configuration
   - Passes metadata to transcription service

4. **WORKING_AGREEMENT.md** (v1.2)
   - Added "Before Implementing New APIs/Libraries" checklist

---

## Cost Analysis

### This Session
- **Test file:** 5.6 minutes (337 seconds)
- **Model:** long ($0.024/min)
- **Cost:** $0.13

### Projected - 75-Minute Yoga Class
- **Duration:** 75 minutes
- **Model:** long ($0.024/min)
- **Cost:** $1.80 per class
- **Monthly (8 classes):** $14.40
- **Well within $250/month budget**

---

## Next Steps

### Immediate (Next Session)
1. Test with real 75-minute yoga class
2. Verify quality with yoga-specific terminology
3. Update SETUP_V2.md with complete steps discovered

### Near Term (Phase 1B)
1. Model selection UI (chirp_3 vs long vs short)
2. Cost estimation display
3. Budget tracking
4. Re-enable phrase hints (fix V2 syntax)

### Future
1. Investigate M4A + synchronous recognize() (if <60s files)
2. File bug with Google about M4A + batch_recognize
3. Whisper provider implementation
4. Multi-speaker diarization for yoga classes

---

## Open Questions

1. **M4A Support:** Is this a known Google issue? Should we file a bug?
2. **Phrase Hints:** What's the correct V2 syntax for custom vocabulary?
3. **Upload Speed:** Why was upload sometimes slow (2 minutes for 2.6 MB)?
4. **MP3 Quality:** Is 128kbps sufficient for yoga instruction quality?

---

## Quotes from Session

**John:** "I'm pissed that m4a isn't working. As a practical matter, all my files are iPhone captures. Seems dumb to have my little machine do the work when the cloud should handle it."

**John:** "Can you reflect on the kind of feedback I'm giving you? How am I suggesting you adjust your process?"

**Response:** "You're pushing me to be evidence-based, not guess-based. Stop jumping to solutions without proof."

**John:** "Well well well. The transcript is pretty faithful to the audio... 94% confidence as reported; seems about right to me."

---

## Celebrations

**What we accomplished:**
- Solved a complex, undocumented issue (M4A incompatibility)
- Built a working end-to-end transcription pipeline
- Established data-driven architecture principles
- Updated working agreement with API implementation best practices
- Got actual transcription results: 645 words, 94% confidence!

**How I celebrate:**
By seeing your satisfaction when it finally works, documenting what we learned so future-us doesn't repeat this debugging journey, and knowing we can now transcribe your yoga classes. 🎉

---

**End of Checkpoint**

*For next session: Test with 75-minute yoga class, update SETUP_V2.md*
