# Implementation Plan: Item 7 - Library Validation

**Date:** 2025-11-14  
**Status:** Ready for Implementation  
**Requirement:** Handle all manual manipulation cases gracefully (system is component in larger product)

---

## Observed Structure

**Library Entry Fields:**
- `library_id`: str (required)
- `filename`: str (required)
- `transcript_file`: str (required)
- `duration_minutes`: float (required)
- `model`: str (required)
- `cost`: float (required)
- `file_size_bytes`: int (optional, defaults to 0)
- `added_at`: str (required, ISO format)
- `metadata`: dict (optional, defaults to {})

**File Structure:**
- `data/library.json` - Library metadata
- `data/transcripts/` - Transcript files (shared with JobStorage)
- `data/library.json.corrupted` - Backup if corruption detected

---

## Implementation Requirements

### Core Validation
1. ✅ Missing transcript files (entry references non-existent file)
2. ✅ Orphaned transcript files (file exists but no entry references it)
3. ✅ Missing required metadata fields (all fields validated)
4. ✅ Corrupted JSON (historical + current)

### Manual Manipulation Cases (Handle Gracefully)
5. ✅ **#1 Empty Library** - Valid state, report count
6. ✅ **#2 Empty Transcripts Directory** - Report warning if library has entries
7. ✅ **#3 Missing Transcripts Directory** - Check and create if needed
8. ✅ **#4 Permission Errors** - Catch and report gracefully
9. ✅ **#5 Malformed Entry Structure** - Validate field types
10. ✅ **#6 Duplicate Library IDs** - Detect and report
11. ✅ **#7 Invalid File References** - Check `is_file()` not just `exists()`
12. ✅ **#8 Transcript File Format** - Validate JSON format

---

## Return Structure

```python
{
    "total_entries": int,
    "missing_transcripts": [library_id, ...],
    "orphaned_transcripts": [filename, ...],
    "missing_metadata": [
        {
            "library_id": str,
            "missing_fields": [field_name, ...]
        },
        ...
    ],
    "malformed_entries": [
        {
            "library_id": str,
            "field": str,
            "expected_type": str,
            "actual_type": str
        },
        ...
    ],
    "duplicate_library_ids": [library_id, ...],  # If detected
    "invalid_file_references": [library_id, ...],  # Points to directory, not file
    "invalid_transcript_files": [filename, ...],  # Not valid JSON
    "corrupted_json": bool,
    "corrupted_backup_exists": bool,
    "corrupted_backup_path": str,  # If exists
    "corruption_error": str,  # If currently corrupted
    "empty_library": bool,  # True if library is empty (valid state)
    "empty_transcripts_directory": bool,  # True if directory empty but library has entries
    "missing_transcripts_directory": bool,  # True if directory doesn't exist
    "permission_errors": {
        "library_file": bool,  # Can't read library.json
        "transcripts_directory": bool  # Can't read transcripts/
    },
    "validation_timestamp": str  # ISO timestamp
}
```

---

## Implementation Steps

1. **Observe actual structure** ✅ (Done)
2. **Implement core validation logic**
3. **Add manual manipulation case handling**
4. **Test with known scenarios**
5. **Verify graceful error handling**

---

## Error Handling Strategy

**Never Crash:**
- All file operations wrapped in try/except
- Permission errors caught and reported
- Missing directories created automatically
- Invalid data reported, not rejected

**Graceful Degradation:**
- If can't read library.json → report permission error, return what we can
- If can't read transcripts/ → report permission error, skip file checks
- If entry is malformed → report issue, continue with other entries

**Comprehensive Reporting:**
- All issues reported in return structure
- No silent failures
- Clear indication of what's wrong and where

