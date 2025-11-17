# Library Validation: Corrupted JSON & Edge Cases Discussion

**Date:** 2025-11-14  
**Item:** Item 7 - Library Validation Implementation

---

## Corrupted JSON Detection

### Current Implementation
The `_load_library()` method already handles corrupted JSON (lines 90-99):
- Catches `json.JSONDecodeError` when parsing fails
- Backs up corrupted file to `.json.corrupted`
- Returns empty dict (starts fresh)
- Logs error

### How Validation Can Report Corruption

**Option 1: Check for backup file**
```python
# If .json.corrupted exists, library.json was corrupted at some point
corrupted_backup = self.DATA_PATH.with_suffix('.json.corrupted')
if corrupted_backup.exists():
    return {
        "corrupted_json": True,
        "corrupted_backup": str(corrupted_backup),
        "note": "Library was corrupted and reset. Backup saved."
    }
```

**Option 2: Try to load and catch errors**
```python
# Try to load library.json and catch JSONDecodeError
try:
    with open(self.DATA_PATH, 'r') as f:
        test_load = json.load(f)
except json.JSONDecodeError as e:
    return {
        "corrupted_json": True,
        "error": str(e),
        "note": "Library file is corrupted and cannot be loaded"
    }
```

**Option 3: Both (comprehensive)**
- Check for existing backup (historical corruption)
- Try to load (current corruption)
- Report both if present

### Recommendation
**Option 3 (Both)** - Most comprehensive:
- Reports historical corruption (backup exists)
- Reports current corruption (can't load now)
- Gives full picture of library health

### Implementation Approach
```python
def validate_library(self) -> Dict[str, Any]:
    results = {
        "total_entries": len(self.library),
        "missing_transcripts": [],
        "orphaned_transcripts": [],
        "missing_metadata": [],
        "corrupted_json": False,
        "corrupted_backup_exists": False
    }
    
    # Check for corrupted JSON (historical)
    corrupted_backup = self.DATA_PATH.with_suffix('.json.corrupted')
    if corrupted_backup.exists():
        results["corrupted_backup_exists"] = True
        results["corrupted_backup_path"] = str(corrupted_backup)
    
    # Check for current corruption (try to reload)
    try:
        with open(self.DATA_PATH, 'r') as f:
            test_load = json.load(f)
    except json.JSONDecodeError as e:
        results["corrupted_json"] = True
        results["corruption_error"] = str(e)
    
    # ... rest of validation logic ...
    
    return results
```

---

## Edge Cases - Documented for Future

### 1. Empty Library
**Scenario:** `library.json` exists but is empty `{}`  
**Current Behavior:** Returns empty dict, validation reports 0 entries  
**Future Consideration:** Is this an error state or valid state?  
**Action:** Document, defer

### 2. Empty Transcripts Directory
**Scenario:** `data/transcripts/` directory exists but is empty  
**Current Behavior:** No transcript files found  
**Future Consideration:** Should we report this as a warning?  
**Action:** Document, defer

### 3. Missing Transcripts Directory
**Scenario:** `data/transcripts/` directory doesn't exist  
**Current Behavior:** `TRANSCRIPTS_DIR.exists()` check would fail  
**Future Consideration:** Should we create it automatically or report error?  
**Action:** Document, defer

### 4. Permission Errors
**Scenario:** Can't read `library.json` or `transcripts/` directory due to permissions  
**Current Behavior:** Would raise `PermissionError`  
**Future Consideration:** Should validation catch and report gracefully?  
**Action:** Document, defer

### 5. Malformed Entry Structure
**Scenario:** Entry exists but has wrong structure (e.g., `transcript_file` is a dict instead of string)  
**Current Behavior:** Would fail when trying to access `entry.get('transcript_file')`  
**Future Consideration:** Should we validate entry structure, not just presence of fields?  
**Action:** Document, defer

### 6. Duplicate Library IDs
**Scenario:** Multiple entries with same `library_id` (shouldn't happen, but...)  
**Current Behavior:** Dict would overwrite, only one entry visible  
**Future Consideration:** Should we detect and report duplicates?  
**Action:** Document, defer

### 7. Invalid File References
**Scenario:** `transcript_file` references a directory, not a file  
**Current Behavior:** `transcript_path.exists()` would be True, but `is_file()` would be False  
**Future Consideration:** Should we validate it's actually a file?  
**Action:** Document, defer

### 8. Transcript File Format
**Scenario:** Transcript file exists but isn't valid JSON  
**Current Behavior:** Would fail when trying to load transcript  
**Future Consideration:** Should validation check transcript file validity?  
**Action:** Document, defer

### 9. Circular References
**Scenario:** Entry A references file B, but file B's metadata references entry A (unlikely but possible)  
**Current Behavior:** Not applicable with current structure  
**Future Consideration:** If structure changes, validate no circular references  
**Action:** Document, defer

### 10. Concurrent Access
**Scenario:** Library.json being written while validation runs  
**Current Behavior:** Could read partial/corrupted state  
**Future Consideration:** Should validation use file locking?  
**Action:** Document, defer

---

## Edge Cases Summary

**For Current Implementation:**
- Focus on: Missing transcripts, orphaned files, missing metadata, corrupted JSON
- Defer: Empty directories, permission errors, malformed structures, concurrent access

**For Future Enhancement:**
- All edge cases documented above
- Can be addressed incrementally as needed
- No blocking issues for current implementation

---

## Validation Return Structure

```python
{
    "total_entries": int,
    "missing_transcripts": [library_id, ...],  # Entries without files
    "orphaned_transcripts": [filename, ...],   # Files without entries
    "missing_metadata": [                        # Entries missing required fields
        {
            "library_id": str,
            "missing_fields": [field_name, ...]
        },
        ...
    ],
    "corrupted_json": bool,                     # Current corruption
    "corrupted_backup_exists": bool,            # Historical corruption
    "corrupted_backup_path": str,               # Path to backup (if exists)
    "corruption_error": str,                    # Error message (if corrupted)
    "validation_timestamp": str                 # ISO timestamp of validation
}
```

---

## Implementation Priority

### Phase 1 (Current): Core Validation
1. ✅ Missing transcript files
2. ✅ Orphaned transcript files
3. ✅ Missing required metadata fields
4. ✅ Corrupted JSON detection (historical + current)

### Phase 2 (Future): Edge Cases
1. Empty library/directories
2. Permission errors
3. Malformed entry structures
4. Invalid file references
5. Transcript file format validation

### Phase 3 (Future): Advanced
1. Duplicate library IDs
2. Circular references
3. Concurrent access handling
4. Transcript content validation

---

## Questions for User

1. **Corrupted JSON:** Should validation report both historical (backup exists) and current (can't load) corruption?
2. **Missing Metadata:** Should we validate all required fields, or just critical ones (library_id, filename, transcript_file)?
3. **Edge Cases:** Are any of the documented edge cases critical for your use case, or can they all be deferred?

