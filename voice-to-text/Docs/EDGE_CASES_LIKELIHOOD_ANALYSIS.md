# Edge Cases: Likelihood & Root Cause Analysis

**Date:** 2025-11-14  
**Purpose:** Understand likelihood and root causes of each edge case before implementation

---

## Analysis Framework

**Likelihood Scale:**
- **Very High:** Will likely occur in normal operation
- **High:** Common in certain scenarios
- **Medium:** Possible but uncommon
- **Low:** Rare, requires specific circumstances
- **Very Low:** Extremely rare, requires multiple failures

**Root Cause Categories:**
- **User Action:** Manual file/directory manipulation
- **System Failure:** OS, disk, power issues
- **Code Bug:** Application error
- **External Factor:** Other processes, tools
- **Normal Operation:** Valid states in certain scenarios

---

## Edge Case Analysis

### 1. Empty Library
**Likelihood:** **Medium**  
**Circumstances:**
- **Normal Operation:** Fresh installation, library cleared intentionally
- **User Action:** Manual deletion of all entries from `library.json`
- **Code Bug:** Logic error that clears library (unlikely with current code)

**Root Causes:**
- Intentional: User wants fresh start
- Accidental: Manual edit of `library.json` removes all entries
- Bug: `delete_entry()` called in loop incorrectly (very unlikely)

**Preventable?** No - this is a valid state  
**Detectable?** Yes - `len(self.library) == 0`  
**Risk:** Low - just a valid empty state

**Verdict:** Handle gracefully, not an error

---

### 2. Empty Transcripts Directory
**Likelihood:** **Low**  
**Circumstances:**
- **User Action:** Manual deletion of all transcript files (but library.json not updated)
- **System Failure:** Disk corruption or accidental `rm -rf data/transcripts/*`
- **Code Bug:** Files deleted but library entries not removed (would be a bug in `delete_entry()`)

**Root Causes:**
- Manual cleanup: User deletes transcript files but forgets to update library
- Accidental deletion: `rm` command on wrong directory
- Bug: `delete_entry()` fails to delete file (unlikely - has explicit file deletion)
- External tool: File manager or script deletes files

**Preventable?** Partially - `delete_entry()` should handle this, but manual deletion can't be prevented  
**Detectable?** Yes - check if directory is empty while library has entries  
**Risk:** Medium - indicates data loss or inconsistency

**Verdict:** Report as warning - indicates potential data loss

---

### 3. Missing Transcripts Directory
**Likelihood:** **Very Low**  
**Circumstances:**
- **User Action:** Manual deletion of `data/transcripts/` directory
- **System Failure:** Disk issues, filesystem corruption
- **Code Bug:** Directory creation fails silently (unlikely - `mkdir(parents=True, exist_ok=True)` is robust)

**Root Causes:**
- Manual deletion: `rm -rf data/transcripts/`
- Disk failure: Filesystem corruption
- Permission issues: Can't create directory (would be caught earlier)
- Bug: `__init__()` not called (very unlikely)

**Preventable?** Yes - `__init__()` creates it, but can't prevent manual deletion  
**Detectable?** Yes - `TRANSCRIPTS_DIR.exists()`  
**Risk:** High - validation would crash

**Verdict:** Handle - check and create if missing (like `__init__` does)

---

### 4. Permission Errors
**Likelihood:** **Low**  
**Circumstances:**
- **User Action:** Changed file permissions manually (`chmod`)
- **System Failure:** Filesystem issues, permission corruption
- **External Factor:** Running as different user, Docker container permission issues
- **Code Bug:** Application changes permissions incorrectly (very unlikely)

**Root Causes:**
- Manual permission change: `chmod 000 library.json` or `chmod 000 data/transcripts/`
- User switch: Running app as different user than created files
- Docker/container: Volume mount permission issues
- System update: OS update changes permission model
- Security tool: Antivirus or security tool locks files

**Preventable?** No - external factors  
**Detectable?** Yes - catch `PermissionError`  
**Risk:** High - validation would crash

**Verdict:** Handle - catch and report gracefully

---

### 5. Malformed Entry Structure
**Likelihood:** **Low**  
**Circumstances:**
- **User Action:** Manual edit of `library.json` with incorrect structure
- **Code Bug:** Old version of code wrote different structure (version migration issue)
- **System Failure:** Partial write corruption (would likely cause JSON decode error first)

**Root Causes:**
- Manual edit: User edits `library.json` and makes mistake (e.g., `"transcript_file": {}` instead of `"transcript_file": "file.json"`)
- Version migration: Old code version wrote different structure, new code expects different format
- Partial corruption: JSON is valid but structure is wrong (rare - usually causes decode error)
- Copy-paste error: User copies entry and modifies incorrectly

**Preventable?** Partially - code should validate, but can't prevent manual edits  
**Detectable?** Yes - validate field types  
**Risk:** Medium - validation would fail when accessing fields

**Verdict:** Handle - validate field types to prevent crashes

---

### 6. Duplicate Library IDs
**Likelihood:** **Very Low**  
**Circumstances:**
- **User Action:** Manual edit of `library.json` with duplicate keys (JSON allows, Python dict doesn't)
- **Code Bug:** `_generate_unique_id()` fails to generate unique ID (very unlikely - has increment logic)
- **System Failure:** Race condition in concurrent access (very unlikely - single user)

**Root Causes:**
- Manual edit: User copies entry and doesn't change `library_id`
- JSON quirk: JSON spec allows duplicate keys, but Python dict keeps last one
- Bug: `_generate_unique_id()` collision (extremely unlikely with current logic)
- Race condition: Two processes add entries simultaneously (very unlikely - single user)

**Preventable?** Yes - current code prevents this  
**Detectable?** Yes - but Python dict would hide it (only last entry visible)  
**Risk:** Low - Python dict naturally handles (keeps last), but data loss possible

**Verdict:** Low priority - very unlikely, but could check if needed

---

### 7. Invalid File References
**Likelihood:** **Very Low**  
**Circumstances:**
- **User Action:** Creates directory with same name as expected transcript file
- **System Failure:** Filesystem corruption creates directory instead of file
- **Code Bug:** `transcript_file` set to directory path (very unlikely)

**Root Causes:**
- Manual creation: User creates `data/transcripts/some_file.json/` as directory
- Filesystem bug: Rare filesystem corruption
- Bug: Code incorrectly sets `transcript_file` to directory path (very unlikely)
- External tool: Script or tool creates directory with transcript filename

**Preventable?** Partially - code should validate, but can't prevent manual creation  
**Detectable?** Yes - check `is_file()` not just `exists()`  
**Risk:** Medium - file appears to exist but isn't usable

**Verdict:** Handle - simple check, prevents confusion

---

### 8. Transcript File Format
**Likelihood:** **Low**  
**Circumstances:**
- **User Action:** Manual edit of transcript file with invalid JSON
- **System Failure:** Partial write corruption (file exists but JSON is malformed)
- **Code Bug:** Old version wrote different format (version migration)

**Root Causes:**
- Manual edit: User edits transcript file and breaks JSON syntax
- Partial write: Application crashes during write, file is incomplete
- Disk corruption: Filesystem corruption damages file
- Version migration: Old code wrote different format
- External tool: Script or editor corrupts file

**Preventable?** Partially - atomic writes help, but can't prevent manual edits  
**Detectable?** Yes - try to parse JSON  
**Risk:** Medium - file exists but can't be loaded

**Verdict:** Defer - adds complexity, can be caught when trying to load

---

### 9. Circular References
**Likelihood:** **None (Not Applicable)**  
**Circumstances:**
- **Not Applicable:** Current structure doesn't support this
- **Future:** Only relevant if transcript files start referencing library entries

**Root Causes:**
- N/A - structure doesn't allow circular references

**Preventable?** N/A  
**Detectable?** N/A  
**Risk:** None

**Verdict:** Document for future, not needed now

---

### 10. Concurrent Access
**Likelihood:** **Very Low**  
**Circumstances:**
- **User Action:** Multiple instances of application running simultaneously
- **External Factor:** Script or tool modifies `library.json` while app is running
- **System Failure:** OS doesn't handle file locking correctly

**Root Causes:**
- Multiple instances: User accidentally runs app twice
- External script: Backup script or tool modifies `library.json`
- No file locking: Current code doesn't use file locks (atomic writes help but not perfect)
- Network filesystem: NFS or network share with poor locking

**Preventable?** Partially - file locking could help, but single-user system makes this rare  
**Detectable?** Yes - corrupted JSON detection would catch it  
**Risk:** Low - single-user system, atomic writes help

**Verdict:** Defer - very unlikely in single-user system

---

## Summary by Likelihood

### Very High Likelihood
- None

### High Likelihood
- None

### Medium Likelihood
- **#1 Empty Library** - Valid state, normal operation

### Low Likelihood
- **#2 Empty Transcripts Directory** - Manual deletion
- **#4 Permission Errors** - Manual permission changes, user switch
- **#5 Malformed Entry Structure** - Manual edit mistakes
- **#8 Transcript File Format** - Manual edits, partial writes

### Very Low Likelihood
- **#3 Missing Transcripts Directory** - Manual deletion
- **#6 Duplicate Library IDs** - Manual edit with duplicate keys
- **#7 Invalid File References** - Manual directory creation
- **#10 Concurrent Access** - Multiple instances

### Not Applicable
- **#9 Circular References** - Structure doesn't allow

---

## Root Cause Patterns

### Most Common Causes:
1. **Manual File Manipulation** (6 cases: #2, #3, #4, #5, #7, #8)
   - User edits files directly
   - User deletes files/directories
   - User changes permissions
   - **Prevention:** Can't prevent, but can detect and report

2. **System Failures** (4 cases: #2, #3, #4, #8)
   - Disk corruption
   - Filesystem issues
   - Power failures during writes
   - **Prevention:** Atomic writes help, but can't prevent all

3. **Code Bugs** (3 cases: #2, #5, #6)
   - Version migration issues
   - Logic errors
   - **Prevention:** Code review, testing

4. **Normal Operation** (1 case: #1)
   - Valid states
   - **Prevention:** Not needed - handle gracefully

---

## Risk Assessment

### High Risk (Would Crash Validation)
- **#3 Missing Directory** - Very low likelihood, but high impact
- **#4 Permission Errors** - Low likelihood, but high impact

### Medium Risk (Would Cause Issues)
- **#2 Empty Directory** - Low likelihood, indicates data loss
- **#5 Malformed Structure** - Low likelihood, causes validation failures
- **#7 Invalid File References** - Very low likelihood, causes confusion
- **#8 Invalid JSON Format** - Low likelihood, causes load failures

### Low Risk (Minor Issues)
- **#1 Empty Library** - Medium likelihood, but valid state
- **#6 Duplicate IDs** - Very low likelihood, Python handles it
- **#10 Concurrent Access** - Very low likelihood, single-user system

---

## Implementation Priority Based on Risk × Likelihood

### Must Handle (High Risk)
1. **#3 Missing Directory** - Very low likelihood, but would crash
2. **#4 Permission Errors** - Low likelihood, but would crash

### Should Handle (Medium Risk, Detectable)
3. **#7 Invalid File References** - Very low likelihood, but simple check
4. **#5 Malformed Structure** - Low likelihood, prevents crashes
5. **#2 Empty Directory** - Low likelihood, indicates data loss

### Can Defer (Low Risk or Very Low Likelihood)
6. **#1 Empty Library** - Valid state, handle gracefully
7. **#8 Invalid JSON Format** - Low likelihood, adds complexity
8. **#6 Duplicate IDs** - Very low likelihood, Python handles
9. **#10 Concurrent Access** - Very low likelihood, single-user
10. **#9 Circular References** - Not applicable

---

## Key Insights

1. **Most issues come from manual file manipulation** - Can't prevent, but can detect
2. **System failures are rare but possible** - Atomic writes help, but not perfect
3. **Code bugs are unlikely** - Current code is robust
4. **Single-user system reduces concurrent access risk** - Very low priority
5. **Validation should be defensive** - Handle gracefully, don't crash

---

## Recommendation

**Handle Now (5 cases):**
- #3, #4 (would crash - must handle)
- #7, #5, #2 (medium risk, simple to handle)

**Defer (5 cases):**
- #1 (valid state, just report)
- #8, #6, #10, #9 (low risk or very low likelihood)

This balances risk mitigation with implementation effort.

