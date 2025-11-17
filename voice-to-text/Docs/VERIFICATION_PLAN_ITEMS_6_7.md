# Verification Plan: Items 6 & 7

**Date:** 2025-11-14  
**Items:** 
- Item 6: Implement V2 Phrase Hints
- Item 7: Implement Library Validation

**Principle:** Observe Before Implement (WORKING_AGREEMENT.md)

---

## Item 6: V2 Phrase Hints - Verification Plan

### Current State
- V1 implementation works: `phrases=self.yoga_vocabulary` (line 167 in `transcribe_v1.py`)
- V2 implementation commented out (lines 1186-1201 in `transcribe_v2.py`)
- Comment says: "V2 has different syntax than V1 for custom vocabulary"
- Yoga vocabulary list exists (30+ terms, lines 656-676)

### What We Need to Observe

#### Phase 1: Understand V2 API Structure
**Goal:** See actual V2 API syntax for `SpeechAdaptation` and `AdaptationPhraseSet`

**Observation Steps:**
1. **Find official V2 examples:**
   - Search Google Cloud Python SDK GitHub for V2 phrase hints examples
   - Check official documentation for `SpeechAdaptation` usage
   - Look for working code samples (not just type definitions)

2. **Observe actual API structure:**
   - What is the correct import path?
   - What is the correct constructor syntax?
   - What parameters does `AdaptationPhraseSet` actually take?
   - How is `SpeechAdaptation` constructed?
   - How is it passed to `RecognitionConfig`?

3. **Compare V1 vs V2:**
   - What changed from V1?
   - Why does the commented code not work?
   - What's the migration path?

**Deliverable:** Working example code that demonstrates correct V2 syntax

#### Phase 2: Test the Syntax
**Goal:** Verify the syntax actually works before implementing

**Observation Steps:**
1. **Create minimal test script:**
   ```python
   # test_v2_phrase_hints.py
   # Minimal script to test V2 phrase hints syntax
   # - Import correct classes
   # - Construct phrase hints
   # - Construct SpeechAdaptation
   # - Verify it can be passed to RecognitionConfig
   ```

2. **Run and observe:**
   - Does it import without errors?
   - Does it construct without errors?
   - Does it pass validation?
   - What does the actual object structure look like?

**Deliverable:** Verified working syntax that can be transcribed to production code

#### Phase 3: Understand Impact
**Goal:** Confirm phrase hints are needed (USER CONFIRMED: Required for multi-language corpus)

**User Requirements:**
- Multiple languages/traditions: Sanskrit (yoga), Chinese medicine/Qigong, Celtic/Wiccan
- Need ability to add custom words/phrases that may not be obvious
- Will be used over time as corpus grows

**Observation Steps:**
1. **Understand vocabulary management:**
   - How should custom vocabulary be managed? (hardcoded list vs configurable)
   - Should different language groups be separate phrase sets?
   - How to add new terms over time?

**Deliverable:** Understanding of vocabulary management needs

### Verification Checklist
- [ ] Found official V2 example code (not just docs)
- [ ] Observed actual API structure (imports, constructors, parameters)
- [ ] Tested syntax in isolation (minimal test script)
- [ ] Verified it works (no errors, constructs correctly)
- [ ] Understood V1 vs V2 differences
- [ ] **CONFIRMED: Implementation is needed** (user requirement for multi-language corpus)

### Success Criteria
- Working example code that demonstrates correct V2 syntax
- Test script that verifies syntax works
- Clear understanding of what changed from V1
- **Implementation required** - user needs this for multi-language corpus (Sanskrit, Chinese medicine/Qigong, Celtic/Wiccan)

---

## Item 7: Library Validation - Verification Plan

### Current State
- Stub function returns placeholder data (lines 296-320 in `library.py`)
- Function signature is correct
- Return structure is documented
- Logic is not implemented

### What We Need to Observe

#### Phase 1: Understand Library Structure
**Goal:** See actual library data structure and file system

**Observation Steps:**
1. **Examine library.json:**
   ```python
   # test_library_structure.py
   # - Load library.json
   # - Print structure of entries
   # - See what fields exist
   # - Understand transcript_file references
   ```

2. **Examine transcripts directory:**
   ```python
   # - List all files in data/transcripts/
   # - See actual filenames
   # - Understand naming patterns
   ```

3. **Map relationships:**
   - Which library entries reference which transcript files?
   - Are there any missing files?
   - Are there any orphaned files?

**Deliverable:** Complete picture of library structure and file relationships

#### Phase 2: Test Validation Logic
**Goal:** Verify validation logic works correctly

**Observation Steps:**
1. **Create test scenarios:**
   - Normal case: All entries have files, all files have entries
   - Missing transcript: Entry references non-existent file
   - Orphaned file: File exists but no entry references it
   - Missing metadata: Entry missing required fields (library_id, filename, transcript_file, etc.)
   - Corrupted JSON: Already handled in `_load_library()`, but should be reported
   - Edge cases: Empty library, empty transcripts dir (documented for future)

2. **Test validation logic:**
   ```python
   # test_validation_logic.py
   # - Test each scenario
   # - Verify correct detection
   # - Verify return structure matches spec
   ```

**Deliverable:** Working validation logic that handles all scenarios

**Required Fields to Validate:**
- `library_id` (required)
- `filename` (required)
- `transcript_file` (required)
- `duration_minutes` (required)
- `model` (required)
- `cost` (required)
- `file_size_bytes` (optional, defaults to 0)
- `added_at` (required)
- `metadata` (optional, defaults to {})

#### Phase 3: Verify Integration
**Goal:** Ensure validation works with actual library service

**Observation Steps:**
1. **Test with real library:**
   - Call `validate_library()` on actual library
   - Verify it doesn't break anything
   - Verify return structure is correct

2. **Test edge cases:**
   - What if library.json is corrupted?
   - What if transcripts directory doesn't exist?
   - What if permissions are wrong?

**Deliverable:** Validation that works in production context

### Verification Checklist
- [ ] Observed actual library.json structure
- [ ] Observed actual transcripts directory contents
- [ ] Mapped relationships between entries and files
- [ ] Tested validation logic with known scenarios
- [ ] Verified return structure matches spec
- [ ] Tested missing metadata fields
- [ ] Tested corrupted JSON detection (already handled, but report it)
- [ ] Documented edge cases for future consideration
- [ ] Verified integration with LibraryService

### Success Criteria
- Complete understanding of library structure
- Working validation logic that handles all scenarios
- Proper error handling for edge cases
- Return structure matches documented spec
- Missing metadata fields detected and reported
- Edge cases documented for future implementation

---

## Implementation Approach

### For Item 6 (V2 Phrase Hints):
1. **Research phase:** Find official examples, understand syntax
2. **Observation phase:** Test syntax in isolation
3. **Decision phase:** Determine if needed
4. **Implementation phase:** Transcribe working syntax to production code

### For Item 7 (Library Validation):
1. **Observation phase:** Understand actual library structure
2. **Design phase:** Design validation logic based on observations
3. **Test phase:** Test with known scenarios
4. **Implementation phase:** Implement and verify

---

## Questions to Answer Before Implementation

### Item 6:
- What is the correct V2 API syntax?
- Does it actually work? (tested, not assumed)
- Is it needed? (transcription quality without it)
- What's the migration path from V1?

### Item 7:
- What does the actual library structure look like?
- What are the real-world scenarios we need to handle?
- How should we handle edge cases?
- Should validation be exposed as an API endpoint?

---

## Next Steps

1. **Create observation scripts** for both items
2. **Run observations** and document findings
3. **Review findings** with user
4. **Decide on implementation** based on observations
5. **Implement** following "Observe Before Implement" principle

