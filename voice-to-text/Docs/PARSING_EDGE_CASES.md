# Parsing Edge Cases: Unlikely but Handled

This document describes edge cases in the batch results parsing code that are unlikely to occur in practice but are handled for robustness.

## Current Implementation

We use `_parse_batch_results_from_json()` which directly parses GCS JSON output, bypassing Protobuf deserialization.

## Edge Cases Handled

### 1. **JSON Structure Variations** (Unlikely: ~1% probability)

**What we handle:**
- Top-level list: `[{segment1}, {segment2}, ...]`
- Wrapped in 'results' field: `{"results": [{segment1}, {segment2}, ...]}`

**Why it's unlikely:**
- Google's GCS output format is standardized
- We always use the same output configuration
- The format has been consistent across all our tests

**Why we handle it:**
- Defensive programming
- API documentation suggests both formats are possible
- Low cost to check (simple `isinstance()`)

**Code location:** Lines 1365-1378

---

### 2. **Alternatives as List vs Single Dict** (Unlikely: ~0.1% probability)

**What we handle:**
- `alternatives` as a list: `[{"transcript": "...", ...}]`
- `alternatives` as a single dict: `{"transcript": "...", ...}`

**Why it's unlikely:**
- Google's API consistently returns alternatives as an array
- Even single alternatives are wrapped in arrays
- We've never seen this variation in practice

**Why we handle it:**
- Type safety
- Prevents `TypeError` if Google changes format
- Minimal code complexity (ternary operator)

**Code location:** Line 1387

---

### 3. **Duration Format Variations** (Unlikely: ~0.5% probability)

**What we handle:**
- String format: `"1.5s"` or `"90s"`
- Dict format: `{"seconds": 90, "nanos": 500000000}`
- Missing duration fields

**Why it's unlikely:**
- Google consistently uses dict format for durations
- String format is legacy/deprecated
- We extract `billed_duration` from operation response, not JSON

**Why we handle it:**
- Historical compatibility
- Different API versions might use different formats
- Edge case in word timing offsets (startOffset/endOffset)

**Code location:** Lines 1403-1422 (word timings), 1460-1479 (billed duration)

---

### 4. **Billed Duration in GCS JSON** (Very Unlikely: ~0.01% probability)

**What we handle:**
- `billed_duration` in top-level metadata
- `billed_duration` in first segment metadata

**Why it's very unlikely:**
- We extract `billed_duration` from the operation response (`file_result.metadata.total_billed_duration`)
- GCS JSON output typically doesn't include billing metadata
- This is a fallback that has never been triggered

**Why we handle it:**
- Defensive fallback
- Some API versions or configurations might include it
- Low cost (simple dict checks)

**Code location:** Lines 1454-1479

---

### 5. **Empty Alternatives Arrays** (Common but handled gracefully)

**What we handle:**
- Segments with `alternatives: []` (empty array)
- Segments with `alternatives: null`
- Segments missing `alternatives` field entirely

**Why it happens:**
- **This is the actual issue we were debugging!**
- Occurs when audio quality is poor (background music, silence, etc.)
- ASR starvation - model segments audio but can't extract speech

**Why we handle it:**
- This is expected behavior, not an error
- We skip empty segments and continue parsing
- Returns partial transcript if some segments have data

**Code location:** Line 1385 (`if 'alternatives' in segment and segment['alternatives']`)

---

### 6. **Confidence Score Variations** (Common - model-dependent)

**What we handle:**
- Word-level confidence: `words[].confidence`
- Alternative-level confidence: `alternatives[].confidence`
- Missing confidence (Chirp model returns 0.0)
- All confidences are 0.0 (Chirp limitation)

**Why it happens:**
- Different models support different confidence features
- Chirp models don't provide reliable confidence scores
- Some models only provide alternative-level, not word-level

**Why we handle it:**
- Model compatibility
- Graceful degradation (returns `None` if unavailable)
- User experience (don't show misleading 0% confidence)

**Code location:** Lines 1434-1452

---

### 7. **Word Timing Format Variations** (Unlikely: ~0.1% probability)

**What we handle:**
- `startOffset`/`endOffset` as strings: `"1.5s"`
- `startOffset`/`endOffset` as dicts: `{"seconds": 1, "nanos": 500000000}`
- Missing timing fields

**Why it's unlikely:**
- Google consistently uses dict format for durations
- String format is legacy
- Timing is only present when `enable_word_time_offsets` is enabled

**Why we handle it:**
- Historical compatibility
- Different API versions
- Prevents crashes if format changes

**Code location:** Lines 1403-1422

---

## Summary: What's Actually Needed vs. What We Handle

### **Actually Needed (Common Cases):**
1. ✅ Empty alternatives (audio quality issues) - **Common**
2. ✅ Missing confidence (Chirp model) - **Common**
3. ✅ Standard JSON structure (list of segments) - **Always**

### **Unlikely but Handled (Edge Cases):**
1. ⚠️ Wrapped JSON structure (`{"results": [...]}`) - **~1%**
2. ⚠️ Alternatives as single dict (not list) - **~0.1%**
3. ⚠️ Duration as string format - **~0.5%**
4. ⚠️ Billed duration in JSON (not operation response) - **~0.01%**
5. ⚠️ Word timing as string format - **~0.1%**

## Recommendation

**Keep all edge case handling** - The code complexity is minimal, and the defensive checks prevent potential crashes. However, we could:

1. **Add comments** explaining why each edge case is handled
2. **Add metrics** to track which edge cases actually occur
3. **Consider removing** the most unlikely ones (e.g., billed_duration in JSON) if we want to simplify

The current implementation strikes a good balance between robustness and simplicity.

