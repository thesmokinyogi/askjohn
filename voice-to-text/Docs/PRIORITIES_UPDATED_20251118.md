# Updated Priorities - Post Cleanup

**Date:** 2025-11-18  
**Context:** After parsing code cleanup and architectural analysis

---

## ✅ Recently Completed

1. **Parsing Code Cleanup** ✅
   - Removed unused Protobuf parser (~250 lines)
   - Reduced debug logging
   - Documented edge cases
   - Changed transcript warnings to debug level

2. **Duplicate Budget Recording Fix** ✅
   - Added guards to prevent duplicate cost recording
   - Fixed historical duplicates

3. **Billed Duration Storage** ✅
   - Now stored in job records
   - Extracted from operation response

---

## 🔴 CRITICAL - Blocking Core Functionality

### 1. Long File Transcription - Empty Transcripts
- **Status:** Needs testing with WAV format and "long" model
- **Root Cause:** ASR starvation (MP3 + background music + Chirp)
- **Next Steps:**
  1. Test with lossless WAV format
  2. Test with "long" model (better for speech+music)
  3. Verify audio contains speech
- **Priority:** P0 - BLOCKING
- **Documentation:** `docs/TRANSCRIPT_EMPTY_ROOT_CAUSE.md`

---

## 🟡 HIGH PRIORITY - Integration Readiness

### 2. Metadata Standardization
- **Status:** Identified, needs implementation
- **Problem:** Inconsistent metadata across job, library, and transcript files
- **Impact:** Blocks clean cross-service consumption
- **Solution:** Create unified `TranscriptMetadata` model
- **Priority:** P1 - HIGH (for integration readiness)
- **Documentation:** `docs/ARCHITECTURAL_REFACTOR_ANALYSIS.md`

### 3. Storage Abstraction Layer
- **Status:** Identified, needs implementation
- **Problem:** Direct file system access prevents database migration
- **Impact:** Blocks Content Cockpit integration
- **Solution:** Create storage adapter interface
- **Priority:** P1 - HIGH (for database migration)
- **Documentation:** `docs/ARCHITECTURAL_REFACTOR_ANALYSIS.md`

### 4. Slow Upload Speeds
- **Status:** Monitoring added, needs verification
- **Problem:** 1.33 Mbps observed vs 50+ Mbps expected
- **Progress:** Added progress monitoring
- **Next Steps:** Verify actual upload speed from logs
- **Priority:** P1 - HIGH

### 5. Server Restart Impact
- **Status:** Temp file cleanup added, needs health check
- **Problem:** Lost jobs during server restart
- **Progress:** ✅ Temp file cleanup on startup
- **Remaining:** Health check endpoint, graceful shutdown
- **Priority:** P1 - HIGH

---

## 🟢 MEDIUM PRIORITY - Code Quality

### 6. Event Publishing
- **Status:** Identified, needs implementation
- **Problem:** No way to notify downstream services of completion
- **Impact:** Blocks async processing pipelines
- **Solution:** Add event publisher interface
- **Priority:** P2 - MEDIUM
- **Documentation:** `docs/ARCHITECTURAL_REFACTOR_ANALYSIS.md`

### 7. API Contract Cleanup
- **Status:** Identified, needs implementation
- **Problem:** API responses include UI-specific fields (`check_status_url`)
- **Impact:** Not ideal for programmatic access
- **Solution:** Remove UI-specific fields, ensure Pydantic models
- **Priority:** P2 - MEDIUM
- **Documentation:** `docs/ARCHITECTURAL_REFACTOR_ANALYSIS.md`

### 8. Duplicate Endpoints
- **Status:** Identified, needs cleanup
- **Problem:** Two endpoints for `/api/estimate-processing-time`
- **Impact:** Confusion, potential conflicts
- **Solution:** Remove old endpoint, update frontend
- **Priority:** P2 - MEDIUM

### 9. "file is not defined" Error
- **Status:** Partially fixed, needs monitoring
- **Problem:** NameError in exception handlers
- **Progress:** Captured filename early
- **Next Steps:** Monitor for recurrence
- **Priority:** P2 - MEDIUM

---

## 🔵 LOW PRIORITY - Future Improvements

### 10. Transcript Structure Refactoring
- **Status:** Identified, optional
- **Problem:** Mixed content and metadata in transcript files
- **Impact:** Low - current structure works
- **Priority:** P3 - LOW

### 11. Billing Source of Truth
- **Status:** Deferred
- **Problem:** Calculate costs internally vs. Google Billing API
- **Impact:** Cost tracking may not match actual charges
- **Priority:** P4 - DEFERRED
- **Documentation:** `docs/BILLING_SOURCE_OF_TRUTH.md`

---

## Recommended Implementation Order

### Phase 1: Foundation (This Week)
1. **Metadata Standardization** (P1)
   - Create unified `TranscriptMetadata` model
   - Update services to use it
   - Enables consistent cross-service consumption

2. **Storage Abstraction** (P1)
   - Create storage adapter interface
   - Move JSON logic to adapter
   - Enables database migration

### Phase 2: Integration Readiness (Next Week)
3. **Event Publishing** (P2)
   - Create event publisher interface
   - Add local implementation
   - Enables async processing pipelines

4. **API Contract Cleanup** (P2)
   - Remove UI-specific fields
   - Ensure Pydantic models
   - Cleaner API for programmatic access

### Phase 3: Polish (Following Week)
5. Fix remaining issues (upload speeds, server restart, duplicate endpoints)

---

## Questions for User

1. **Integration Timeline:** When do you plan to integrate with Content Cockpit? This affects priority of storage abstraction.

2. **Event Publishing:** Do you want event publishing now, or can it wait until Content Cockpit integration?

3. **Metadata Extensibility:** What additional metadata fields do you anticipate needing? (e.g., `project_id`, `tags`, `speaker_id`)

4. **API Versioning:** Do you want to maintain backward compatibility, or can we break the API for v2?

---

## Summary

**Immediate Focus:**
- Fix long file transcription (P0)
- Standardize metadata (P1)
- Abstract storage layer (P1)

**Integration Readiness:**
- Event publishing (P2)
- API contract cleanup (P2)

**Code Quality:**
- Duplicate endpoints (P2)
- Error handling improvements (P2)

