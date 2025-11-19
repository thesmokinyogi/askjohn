# Long File Test Checklist

**File Duration:** 1:34:19 (94.3 minutes)  
**Model:** Chirp Batch  
**Format:** Native MP3  
**Purpose:** Test edge cases for long audio files

---

## Pre-Test Checks

### File Format: Native MP3 (First Time Testing)
- [x] **This is the first native MP3 file test** - Important!
- [x] MP3 is in `AUTO_DETECT_FORMATS` - should use `AutoDetectDecodingConfig`
- [x] No conversion needed (unlike M4A which gets converted)
- [x] Should be handled directly by Google Speech API
- **Test Started:** 2025-11-18 (1:34:19 duration, Chirp Batch)

### File Size
- [ ] File size < 500MB (Google limit)
- [ ] File format: **Native MP3** (not converted)
- [ ] Estimated file size calculation:
  - **MP3 (128kbps, 90 min):** ~86MB ✅ (well under limit)
  - **MP3 (192kbps, 90 min):** ~129MB ✅ (under limit)
  - **MP3 (320kbps, 90 min):** ~216MB ✅ (under limit)
  - **WAV (44.1kHz, 16-bit, stereo):** ~950MB ❌ (over limit - would need compression)

### System Limits
- ✅ **File size limit:** 500MB (configured in `app/config.py`)
- ✅ **Batch recognition:** Supports long files (no duration limit for batch)
- ✅ **Processing time:** Will be long (90 min = ~1.5 hours processing time)
- ✅ **Cost estimate:** ~$0.36 for 90 minutes at $0.004/min (chirp_batch)

---

## What to Monitor During Test

### 1. Job Submission
- [ ] File uploads successfully
- [ ] **MP3 format detected correctly** (check metadata)
- [ ] **No conversion applied** (MP3 should go straight through, unlike M4A)
- [ ] Cost estimate displays correctly (~$0.36)
- [ ] Processing time estimate displays (may be inaccurate for first long file)
- [ ] Job ID returned
- [ ] Status: "queued" or "processing"

### 2. Status Transitions
- [ ] Status: `queued` → `processing` → `complete`
- [ ] `processing_started_at` is set when status becomes "processing"
- [ ] Status updates visible in UI
- [ ] No timeout errors

### 3. Processing Time
- [ ] Actual processing time recorded
- [ ] Processing time excludes queueing time (uses `processing_started_at`)
- [ ] Processing time estimate improves for future long files

### 4. Cost Calculation
- [ ] `actual_cost` calculated correctly
- [ ] Free tier usage calculated correctly (if any remaining)
- [ ] Cost matches estimate (within rounding)

### 5. Results
- [ ] Transcript generated successfully
- [ ] Transcript length reasonable (~90 minutes of speech)
- [ ] Word timings present (if enabled)
- [ ] Confidence score present (or null for Chirp)
- [ ] Metadata complete

### 6. Library Integration
- [ ] Entry added to library automatically
- [ ] Transcript file saved correctly
- [ ] File size recorded correctly
- [ ] Metadata complete

### 7. Error Handling
- [ ] No timeout errors
- [ ] No memory errors
- [ ] No GCS upload errors
- [ ] No API errors

---

## Expected Behavior

### Processing Time
- **Queueing:** Usually < 1 minute
- **Processing:** ~1.5-2 hours for 94 minutes of audio (batch processing)
- **Total:** ~1.5-2 hours from submission to completion
- **Note:** First long file may have inaccurate estimate (system learns from this)

### Cost
- **94.3 minutes @ $0.004/min (chirp_batch):** ~$0.38
- **If free tier remaining:** Part free, part paid
- **If free tier exhausted:** Full ~$0.38

### API Behavior
- Uses **batch recognition** (no duration limit)
- Processing happens asynchronously
- Status polling required to check completion

---

## Potential Issues to Watch For

### 1. MP3 Format Handling (First Time)
- **Issue:** MP3 encoding/decoding not working correctly
- **Symptom:** API error about audio format, or job fails
- **Expected:** MP3 should use `AutoDetectDecodingConfig` (no explicit encoding needed)
- **Solution:** Check logs for encoding-related errors

### 2. File Size
- **Issue:** File > 500MB
- **Symptom:** Upload rejected with "File too large"
- **Solution:** Compress file or use lower bitrate

### 3. Timeout
- **Issue:** Request timeout during upload
- **Symptom:** Connection error or timeout
- **Solution:** Check network, file may be too large for upload method

### 4. Processing Time Estimate
- **Issue:** Estimate may be inaccurate for first long file
- **Symptom:** Estimate way off (e.g., says 10 min, takes 2 hours)
- **Solution:** Expected - system learns from actual processing times

### 5. Memory
- **Issue:** Large file processing uses significant memory
- **Symptom:** Server errors or slowdowns
- **Solution:** Monitor server resources

### 6. GCS Upload
- **Issue:** Large file upload to GCS fails or times out
- **Symptom:** Upload error or job stuck in "queued"
- **Solution:** Check GCS bucket, network connection

---

## Test Steps

1. **Prepare File**
   - Verify file size < 500MB
   - Note file format and size

2. **Submit Job**
   - Upload via UI or API
   - Select model (recommend `chirp_batch` for cost efficiency)
   - Note job ID

3. **Monitor Status**
   - Check status every 5-10 minutes
   - Watch for status transitions
   - Note `processing_started_at` timestamp

4. **Wait for Completion**
   - Be patient - 90 minutes of audio = ~1.5-2 hours processing
   - Don't close browser/server
   - Check status periodically

5. **Verify Results**
   - Check transcript quality
   - Verify cost calculation
   - Check library entry
   - Verify all metadata

---

## Success Criteria

✅ **Job completes successfully**
✅ **Transcript generated**
✅ **Cost calculated correctly**
✅ **Library entry created**
✅ **No errors or timeouts**
✅ **Processing time tracked correctly**

---

## Notes

- This is a **stress test** - will test system limits
- Processing time will be **long** - be patient
- First long file may have **inaccurate time estimates** - expected
- System will **learn** from this job for future estimates

---

**Ready to test?** Upload your 90-minute file and let's see how the system handles it!

