# Audio Processing Architecture Review

**Date:** 2025-11-19  
**Reviewer:** Self-review following working agreement principles

## Issues Identified

### 1. **Metadata Extraction Duplication** ⚠️

**Problem:**
- `AudioProcessingService` uses `mediainfo` (from pydub) directly
- `AudioMetadataService` uses `mutagen` library
- Two different libraries doing similar work
- Inconsistent metadata format returned

**Impact:**
- Code duplication
- Maintenance burden (two places to update)
- Inconsistent behavior if libraries differ
- Violates DRY principle

**Current Code:**
```python
# audio_processing.py
info = mediainfo(file_path)
metadata = {
    'sample_rate': int(info.get('sample_rate', 0)),
    'channels': int(info.get('channels', 1)),
    ...
}

# audio_metadata.py (different format)
metadata = {
    'sample_rate': 44100,
    'channels': 2,
    'duration': 125.5,
    'format': 'mp3',
    ...
}
```

**Fix:**
- Use `AudioMetadataService` for all metadata extraction
- Convert between formats if needed
- Single source of truth for metadata

---

### 2. **Single Responsibility Violation** ⚠️

**Problem:**
- `prepare_for_upload()` does too much:
  1. Video extraction
  2. Channel extraction
  3. Format conversion (M4A→MP3)
  4. Metadata extraction
  5. Error handling for each step

**Impact:**
- Hard to test individual operations
- Hard to reuse operations independently
- Violates Single Responsibility Principle
- Method is 100+ lines doing multiple things

**Fix:**
- Break into focused methods:
  - `extract_audio_from_video()`
  - `convert_format()` (M4A→MP3)
  - `prepare_for_upload()` orchestrates but doesn't do everything

---

### 3. **Inconsistent Metadata Format** ⚠️

**Problem:**
- `AudioMetadataService` returns: `duration`, `format`, `codec`, `sample_rate`, `channels`, `bit_rate`, `file_size`
- `AudioProcessingService` returns: `sample_rate`, `channels`, `duration`, `codec`, `bit_rate`
- Missing fields: `format`, `file_size`
- Different field order

**Impact:**
- Downstream code might break if it expects specific format
- Inconsistent API surface

**Fix:**
- Use `AudioMetadataService` consistently
- Or define a standard metadata format/schema

---

### 4. **Error Handling Fragility** ⚠️

**Problem:**
```python
try:
    processed_path, metadata = self.extract_channel(processed_path, channel)
except ValueError as e:
    # File is mono or invalid channel - log and continue with original
    logger.warning(f"Channel extraction skipped: {e}")
    # Load metadata for original file
    try:
        info = mediainfo(processed_path)  # Could fail again!
        ...
    except Exception as e2:
        # Nested try/except
```

**Impact:**
- Nested exception handling is fragile
- Metadata extraction could fail silently
- Hard to debug

**Fix:**
- Use `AudioMetadataService` which has proper error handling
- Simplify error handling flow

---

### 5. **Filename Mutation** ⚠️

**Problem:**
- `prepare_for_upload()` modifies `filename` parameter:
```python
filename = filename.rsplit('.', 1)[0] + '.mp3'
```

**Impact:**
- Parameter mutation is confusing
- Caller might not expect filename to change
- Hard to track what filename was used

**Fix:**
- Don't modify parameter
- Return processed filename separately if needed
- Or use a new variable name

---

## Recommended Improvements

### Priority 1: Use AudioMetadataService

**Why:** Eliminates duplication, ensures consistency

**Change:**
```python
# Instead of:
info = mediainfo(file_path)
metadata = {...}

# Use:
from app.services.audio_metadata import get_audio_metadata_service
metadata_service = get_audio_metadata_service()
metadata = metadata_service.analyze_file(file_path)
```

**Benefits:**
- Single source of truth
- Consistent format
- Better error handling
- Easier to maintain

---

### Priority 2: Refactor prepare_for_upload()

**Why:** Improves testability and maintainability

**Change:**
```python
def extract_audio_from_video(self, file_path: str) -> str:
    """Extract audio from video, return path to audio file."""
    
def convert_format(self, file_path: str, target_format: str = "mp3") -> str:
    """Convert audio format, return path to converted file."""
    
def prepare_for_upload(self, file_path: str, filename: str, channel: Optional[str] = None) -> Tuple[str, Dict]:
    """Orchestrate full pipeline."""
    # Step 1: Video extraction
    if is_video(filename):
        file_path = self.extract_audio_from_video(file_path)
    
    # Step 2: Channel extraction
    if channel:
        file_path = self.extract_channel(file_path, channel)
    
    # Step 3: Format conversion
    if needs_conversion(file_path):
        file_path = self.convert_format(file_path)
    
    # Step 4: Metadata (using AudioMetadataService)
    metadata = get_audio_metadata_service().analyze_file(file_path)
    
    return file_path, metadata
```

**Benefits:**
- Each method has single responsibility
- Easier to test
- Easier to reuse
- Clearer flow

---

### Priority 3: Standardize Metadata Format

**Why:** Prevents downstream breakage

**Options:**
1. Always use `AudioMetadataService` format
2. Create a metadata schema/model
3. Convert between formats explicitly

**Recommendation:** Option 1 - always use `AudioMetadataService`

---

## Summary

**Critical Issues:**
1. ⚠️ Metadata extraction duplication
2. ⚠️ Single responsibility violation
3. ⚠️ Inconsistent metadata format

**Nice to Have:**
4. Error handling improvements
5. Filename mutation cleanup

**Estimated Fix Time:**
- Priority 1: 30 minutes
- Priority 2: 1 hour
- Priority 3: Included in Priority 1

**Total:** ~1.5 hours for architectural improvements

