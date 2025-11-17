# Edge Cases Impact Analysis

**Date:** 2025-11-14  
**Purpose:** Brief discussion of each edge case and its practical impact

---

## Edge Case Impact Summary

### 1. Empty Library
**Scenario:** `library.json` exists but is empty `{}`  
**Impact:** 
- **Low** - This is a valid state (new installation, library cleared)
- Validation would report `total_entries: 0`, which is correct
- **Action:** Not an error, just report the count

**Recommendation:** Handle gracefully - not an error state

---

### 2. Empty Transcripts Directory
**Scenario:** `data/transcripts/` directory exists but is empty  
**Impact:**
- **Medium** - Could indicate:
  - All transcripts deleted but library entries remain (data loss)
  - Fresh installation (valid state)
- If library has entries but directory is empty → **data loss detected**
- If library is also empty → **valid state**

**Recommendation:** Report as warning if library has entries but directory is empty

---

### 3. Missing Transcripts Directory
**Scenario:** `data/transcripts/` directory doesn't exist  
**Impact:**
- **High** - Would cause validation to crash with `FileNotFoundError`
- Directory is created in `__init__()`, so shouldn't happen in normal operation
- Could happen if directory was manually deleted

**Recommendation:** Check if directory exists, create if missing (like `__init__` does), report if had to create

---

### 4. Permission Errors
**Scenario:** Can't read `library.json` or `transcripts/` directory due to permissions  
**Impact:**
- **High** - Would crash validation with `PermissionError`
- Could happen if file permissions changed, or running as different user
- Would prevent validation from completing

**Recommendation:** Catch `PermissionError`, report gracefully, don't crash

---

### 5. Malformed Entry Structure
**Scenario:** Entry exists but has wrong structure (e.g., `transcript_file` is a dict instead of string)  
**Impact:**
- **Medium** - Would cause validation to fail when accessing fields
- Could happen if library.json was manually edited incorrectly
- Would prevent validation from checking that entry

**Recommendation:** Validate field types, report malformed entries separately

---

### 6. Duplicate Library IDs
**Scenario:** Multiple entries with same `library_id` (shouldn't happen, but...)  
**Impact:**
- **Low** - Python dict would overwrite, only one entry visible
- Can't actually happen with current structure (dict keys are unique)
- But if library.json was manually edited, could have duplicate keys (JSON allows this, but Python dict doesn't)

**Recommendation:** Low priority - unlikely to occur, but could check for it

---

### 7. Invalid File References
**Scenario:** `transcript_file` references a directory, not a file  
**Impact:**
- **Medium** - `transcript_path.exists()` would be True, but it's not a file
- Would cause issues when trying to load transcript
- Could happen if someone created a directory with same name as expected file

**Recommendation:** Check `is_file()` not just `exists()`, report invalid references

---

### 8. Transcript File Format
**Scenario:** Transcript file exists but isn't valid JSON  
**Impact:**
- **Medium** - Would fail when trying to load transcript (e.g., in download endpoints)
- File exists, but can't be used
- Could happen if file was corrupted or manually edited incorrectly

**Recommendation:** Could validate JSON format, but adds complexity - defer for now

---

### 9. Circular References
**Scenario:** Entry A references file B, but file B's metadata references entry A  
**Impact:**
- **None** - Not applicable with current structure
- Transcript files don't reference library entries
- Only relevant if structure changes in future

**Recommendation:** Document for future, not needed now

---

### 10. Concurrent Access
**Scenario:** Library.json being written while validation runs  
**Impact:**
- **Low** - Could read partial/corrupted state
- Single-user system, unlikely to happen
- Would be caught by corrupted JSON detection anyway

**Recommendation:** Low priority for single-user system, could add file locking if needed later

---

## Prioritized Impact Assessment

### High Impact (Should Handle Now)
1. **#4 Permission Errors** - Would crash validation
2. **#3 Missing Transcripts Directory** - Would crash validation

### Medium Impact (Should Handle Now)
3. **#7 Invalid File References** - File exists but isn't actually a file
4. **#5 Malformed Entry Structure** - Could cause validation to fail
5. **#2 Empty Transcripts Directory** - Could indicate data loss

### Low Impact (Can Defer)
6. **#1 Empty Library** - Valid state, just report
7. **#8 Transcript File Format** - Adds complexity, defer
8. **#6 Duplicate Library IDs** - Unlikely to occur
9. **#10 Concurrent Access** - Single-user system
10. **#9 Circular References** - Not applicable

---

## Recommended Implementation

### Phase 1 (Current): Core + High Impact
- Missing transcripts
- Orphaned files
- Missing metadata (all fields)
- Corrupted JSON (historical + current)
- **#4 Permission Errors** (catch and report)
- **#3 Missing Transcripts Directory** (check and create if needed)

### Phase 2 (Current): Medium Impact
- **#7 Invalid File References** (check `is_file()`)
- **#5 Malformed Entry Structure** (validate field types)
- **#2 Empty Transcripts Directory** (report as warning if library has entries)

### Phase 3 (Future): Low Impact
- All others can be deferred

---

## Questions for User

1. **Permission Errors (#4):** Should validation catch and report gracefully, or is it okay to let it crash? (Recommended: catch and report)

2. **Missing Directory (#3):** Should validation create the directory if missing, or just report the error? (Recommended: create it, like `__init__` does)

3. **Invalid File References (#7):** Should we check that transcript files are actually files (not directories)? (Recommended: yes, simple check)

4. **Malformed Entry Structure (#5):** Should we validate field types (e.g., `transcript_file` must be string)? (Recommended: yes, prevents crashes)

5. **Empty Directory Warning (#2):** If library has entries but transcripts directory is empty, should this be a warning? (Recommended: yes, indicates data loss)

