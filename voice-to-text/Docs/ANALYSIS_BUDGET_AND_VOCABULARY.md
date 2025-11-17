# Analysis: Budget Tracking & Vocabulary UI

**Date:** 2025-11-14  
**Status:** Pre-Implementation Analysis

---

## Issue 1: Budget Tracking Not Updating Free Tier Usage

### Current State

**Budget Tracking File Shows:**
- 7 transcriptions recorded
- All have `free_min: 0` (should be tracking free tier usage)
- All have `cost: $0.00` (correct if free tier covers it)
- Free tier used: `0.0 minutes` (WRONG - should be ~24.1 minutes total)
- Free tier remaining: `60.0 minutes` (WRONG - should be ~35.9 minutes)

**Recent Transcriptions:**
- 5.6 min, $0.00, free_min: 0
- 5.6 min, $0.00, free_min: 0
- 6.1 min, $0.00, free_min: 0
- 5.8 min, $0.00, free_min: 0
- 1.8 min, $0.00, free_min: 0
- **Total: ~24.1 minutes, all should be free tier**

### Root Cause Analysis

**Problem Location:** `app/main.py` lines 520-525

**Current Code:**
```python
budget_service.record_transcription(
    provider=STT_PROVIDER,
    model=job_record["model"],
    duration_minutes=job_record["duration_minutes"],
    cost=actual_cost
    # ❌ MISSING: free_minutes_used parameter
)
```

**What Should Happen:**
1. Cost estimate is calculated with `free_minutes_used` (line 326-331)
2. Cost estimate includes `free_minutes_used` in return value (pricing.py line 124)
3. But `free_minutes_used` is NOT passed to `record_transcription()`
4. Budget service expects `free_minutes_used` parameter (budget.py line 175)
5. Without it, free tier tracking never updates

**The Fix:**
- Extract `free_minutes_used` from cost estimate (stored in job_record or recalculate)
- Pass it to `record_transcription()`
- Also need to calculate actual billed duration from transcription metadata

### Additional Issues

**1. Actual Cost Calculation:**
- Line 500: `actual_cost = job_record["estimated_cost"]`
- Comment says "For now, use estimated cost (we'll enhance this later)"
- Should use actual billed duration from transcription metadata
- Metadata includes `total_billed_duration` (transcribe_v2.py line 1395)
- **BUT:** Billed duration is logged but NOT extracted and returned in metadata
- Current metadata only includes: `total_words`, `model`, `language`, `api_version`, `words`
- Need to extract `total_billed_duration` from result and include in returned metadata

**2. Billed Duration Extraction:**
- Available in: `result.metadata.total_billed_duration` (line 1395)
- Currently only logged, not extracted
- Need to extract and include in returned metadata
- Then use it to calculate actual cost and free minutes

**3. Free Minutes Calculation:**
- Need to recalculate based on actual billed duration
- Or store `free_minutes_used` from estimate in job_record
- Then use it when recording
- Current: Free minutes calculated in estimate but not used when recording

### Data Flow

**Current Flow:**
```
Upload → Estimate Cost (includes free_minutes_used) → Submit Job → 
Complete → Record Transcription (❌ missing free_minutes_used)
```

**Correct Flow:**
```
Upload → Estimate Cost (includes free_minutes_used) → Submit Job → 
Complete → Get Actual Billed Duration → Recalculate free_minutes_used → 
Record Transcription (✓ with free_minutes_used)
```

### Required Changes

1. **Extract actual billed duration** from transcription metadata
2. **Recalculate free_minutes_used** based on actual duration and remaining free tier
3. **Recalculate actual_cost** based on actual billed duration
4. **Pass free_minutes_used** to `record_transcription()`
5. **Update job_record** with actual_cost and free_minutes_used

---

## Issue 2: Vocabulary UI for Managing Words & Phrases

### Current State

**Vocabulary Storage:**
- Hardcoded in `app/services/transcribe_v2.py` (lines 656-676)
- Hardcoded in `app/services/transcribe_v1.py` (lines 53-63)
- ~30 yoga terms (Sanskrit, English pose names, yoga styles)
- User needs to add: Chinese medicine/Qigong, Celtic/Wiccan terms

**No UI Exists:**
- No way to add/edit/remove phrases
- No way to organize by language/tradition
- No persistence beyond code changes

### Requirements Analysis

**User Needs:**
1. Add custom words/phrases (Sanskrit, Chinese medicine, Celtic/Wiccan)
2. Organize by language/tradition (optional grouping)
3. Edit/remove existing phrases
4. Persist across restarts
5. Apply to all transcriptions automatically

**Current API Structure:**
- V2 requires: `[{'value': phrase} for phrase in vocabulary]`
- No language/boost per phrase (just the phrase text)
- Applied to all transcriptions (no per-transcription selection)

### Storage Options

**Option 1: JSON Config File**
- **File:** `config/vocabulary.json`
- **Structure:**
  ```json
  {
    "phrases": [
      "asana",
      "pranayama",
      "qigong",
      "meridian",
      ...
    ],
    "last_updated": "2025-11-14T..."
  }
  ```
- **Pros:** Simple, human-readable, easy to edit manually
- **Cons:** No grouping/organization, single flat list

**Option 2: JSON with Categories**
- **File:** `config/vocabulary.json`
- **Structure:**
  ```json
  {
    "categories": {
      "yoga": ["asana", "pranayama", ...],
      "chinese_medicine": ["qigong", "meridian", ...],
      "celtic": ["samhain", "imbolc", ...]
    },
    "last_updated": "2025-11-14T..."
  }
  ```
- **Pros:** Organized, can enable/disable categories
- **Cons:** Slightly more complex

**Option 3: Database (Future)**
- **Pros:** More flexible, can add metadata per phrase
- **Cons:** Overkill for current needs, adds complexity

### UI Design Considerations

**Where to Add UI:**
- New page: `/vocabulary` or `/settings/vocabulary`
- Or add to existing settings/admin area
- Should be accessible but not cluttering main UI

**UI Components Needed:**
1. **List of phrases** (editable)
2. **Add phrase** input + button
3. **Remove phrase** button (per phrase)
4. **Category/tag** selector (if using categories)
5. **Save** button (writes to config file)
6. **Apply** indicator (shows if vocabulary is active)

**API Endpoints Needed:**
- `GET /api/vocabulary` - Get current vocabulary
- `POST /api/vocabulary` - Add phrase(s)
- `DELETE /api/vocabulary/{phrase}` - Remove phrase
- `PUT /api/vocabulary` - Update entire vocabulary

### Implementation Questions

1. **Storage:** JSON file or categories?
2. **UI Location:** New page or existing settings?
3. **Validation:** Should we validate phrases (length, format)?
4. **Backup:** Should we keep history of changes?
5. **Apply Immediately:** Should changes apply to in-progress jobs?

---

## Summary

### Budget Tracking Issues

**Critical:**
- ❌ `free_minutes_used` not passed to `record_transcription()`
- ❌ Free tier tracking never updates
- ❌ Actual billed duration not extracted from metadata

**Enhancement:**
- Use actual billed duration instead of estimated cost
- Recalculate free tier usage based on actual duration

### Vocabulary UI Requirements

**Storage:**
- Need to move from hardcoded to config file
- Decide: flat list vs. categories

**UI:**
- Need new page/component for managing phrases
- Need API endpoints for CRUD operations
- Need to reload vocabulary in services when updated

**Integration:**
- Services need to load vocabulary from config file
- Need to reload when vocabulary changes (or restart service)

---

## Next Steps

1. **Fix Budget Tracking** (Critical)
   - Extract actual billed duration
   - Recalculate free_minutes_used
   - Pass to record_transcription()

2. **Design Vocabulary Storage** (Decision needed)
   - Choose: flat list vs. categories
   - Create config file structure

3. **Implement Vocabulary API** (Backend)
   - CRUD endpoints
   - File persistence
   - Service reload mechanism

4. **Build Vocabulary UI** (Frontend)
   - List/edit interface
   - Add/remove functionality
   - Save/apply mechanism

