# Deferred Items

**Purpose:** Track non-critical improvements and cleanup tasks that are deferred to avoid distraction from core work.

**Last Updated:** 2025-11-18

---

## Medium Priority

### 1. Make `primary_languages` Configurable
**Status:** Deferred  
**Location:** `app/main.py:141`  
**Current:** Hardcoded `primary_languages = ['en-US']`  
**Proposed:** Move to environment variable (e.g., `PRIMARY_LANGUAGES=en-US,es-ES`)  
**Rationale:** User's material is in English, so not urgent. User dislikes hardcoded values but doesn't want distraction.

---

### 2. Replace Hardcoded `'en-US'` Strings
**Status:** Deferred  
**Locations:** 
- `app/main.py` (multiple)
- `app/services/transcribe_v2.py` (multiple)
- `app/services/transcribe_v1.py` (1 occurrence)
- **Total:** 21 occurrences

**Current:** Hardcoded `'en-US'` as default language code throughout codebase  
**Proposed:** Use configurable default language variable  
**Rationale:** User's material is in English, so not urgent. User dislikes hardcoded values but doesn't want distraction.

**Note:** The `discover_speech_metadata()` function already accepts a `languages` parameter, so this is just about replacing hardcoded defaults with a configurable variable.

---

### 3. Build `model_mapping` Dynamically
**Status:** Deferred  
**Location:** `app/main.py:256-268`  
**Current:** Hardcoded dict mapping UI names to API models:
```python
model_mapping = {
    'Long': 'long',
    'Chirp': 'chirp_standard',
    'Chirp 2': 'chirp_2',
    'Chirp 3': 'chirp_3',
    'Short': 'short',
    'Telephony': 'telephony',
}
```
**Proposed:** Generate from discovered models in metadata cache  
**Rationale:** Would automatically include new models as they're discovered. Low priority since current mapping works.

---

## Low Priority

### 4. Schedule Weekly Cleanup Job
**Status:** Deferred  
**Location:** `scripts/cleanup_jobs.py`  
**Current:** Manual execution only  
**Proposed:** 
- **Option A (Recommended):** Cron job - runs every Sunday at 2 AM
  - Wrapper script created: `scripts/run_cleanup.sh`
  - Documentation: `docs/CLEANUP_CRON_SETUP.md`
  - Command: `0 2 * * 0 /path/to/scripts/run_cleanup.sh >> logs/cleanup.log 2>&1`
- **Option B:** Background task in FastAPI using APScheduler
  - Integrated with app, but only runs when app is running
  - Requires adding `APScheduler` dependency

**Rationale:** 
- Cleanup script is ready and tested
- Weekly schedule prevents accumulation of stuck jobs, duplicates, orphaned files
- Cron job is recommended for reliability (runs independently of app)
- See `docs/CLEANUP_SCHEDULING_OPTIONS.md` for full comparison

**Next Steps:**
1. Test wrapper script: `./scripts/run_cleanup.sh --dry-run`
2. Add to crontab: `crontab -e`
3. Monitor logs: `tail -f logs/cleanup.log`

---

### 5. Standardize Cache Key Format
**Status:** Deferred  
**Location:** `app/services/transcribe_v2.py` - `_FEATURE_CACHE`  
**Current:** Mixed cache key formats  
**Proposed:** Standardize to `(location, language, model)` tuple consistently  
**Rationale:** Code cleanup for consistency. No functional impact.

---

### 6. Clean Up DEBUG Logging
**Status:** Deferred  
**Location:** `app/services/transcribe_v2.py` (multiple locations)  
**Current:** Extensive DEBUG print statements  
**Proposed:** Change to `logger.debug()` or remove  
**Rationale:** Code cleanup. No functional impact.

---

### 7. Implement V2 Phrase Hints
**Status:** Deferred  
**Location:** `app/services/transcribe_v2.py:1186, 1198`  
**Current:** Commented out with TODO:
```python
# TODO: Fix phrase hints syntax for V2 API
# V2 has different syntax than V1 for custom vocabulary
# Temporarily disabled to get transcription working
```
**Proposed:** Fix V2 phrase hints syntax or remove if not needed  
**Rationale:** Feature not currently used. Can be implemented when needed.

---

### 8. Implement Library Validation
**Status:** Deferred  
**Location:** `app/services/library.py:310`  
**Current:** Stub function returns placeholder:
```python
def validate_library(self) -> Dict[str, Any]:
    # TODO: Implement validation logic
    # - Check each library entry has corresponding transcript file
    # - Check for transcript files without library entries
    # - Report mismatches
    return {
        "total_entries": len(self.library),
        "missing_transcripts": [],
        "orphaned_transcripts": [],
        "note": "Validation not yet implemented"
    }
```
**Proposed:** Implement validation logic to check for orphaned files/missing transcripts  
**Rationale:** Useful for data integrity but not critical for current functionality.

---

### 9. GCS Cleanup for Transcript Files
**Status:** Deferred  
**Location:** `app/services/storage.py`  
**Current:** 
- `cleanup_old_files()` exists for audio files (`uploads/` folder)
- No cleanup for transcript result files (`transcripts/` folder)
- Google does NOT auto-delete incomplete/failed job result files

**Proposed:** 
- Methods already added: `cleanup_old_transcripts(days_old=30)` and `list_transcript_files()`
- Consider: Add API endpoint or scheduled task to run cleanup
- Consider: Set up GCS bucket lifecycle management rules (more efficient)

**Rationale:** 
- Transcript files are small (JSON), so storage impact is minimal
- Incomplete/failed jobs will create result files that persist
- Not urgent - can be addressed when needed

**Manual Deletion Options:**
- Via GCS Console: Navigate to bucket → `transcripts/` folder → delete files
- Via `gsutil`: `gsutil rm gs://bucket-name/transcripts/filename.json`
- Via code: Use `storage_service.delete_file(gcs_uri)` or `storage_service.cleanup_old_transcripts()`

---

## Notes

- **All critical functionality is working** - these are improvements and cleanup tasks
- Items are organized by priority (Medium vs Low)
- Each item includes location, current state, and proposed solution
- Items can be moved to active work when ready
- New items should be added as they're discovered

---

## How to Use This List

1. **When starting new work:** Review this list to see if any deferred items should be prioritized
2. **When completing work:** If a deferred item is addressed, move it to a "Completed" section or remove it
3. **When discovering new issues:** Add to appropriate priority section with full context
4. **When prioritizing:** Use this list to inform what to tackle next when core work is complete

