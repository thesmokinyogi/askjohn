# Metadata Access Audit - Post-Refactoring

**Date:** 2025-11-18  
**Issue:** After refactoring to use Pydantic `TranscriptMetadata` models, some code still tries to access metadata using dict-style `.get()` calls, which fails because Pydantic models don't have `.get()` method.

---

## Root Cause

During refactoring, `metadata` changed from `Dict[str, Any]` to `TranscriptMetadata` model objects. However, some code paths still treat metadata as dictionaries.

---

## Fixed Issues

### ✅ Fixed: `app/main.py` line 668-669
**Problem:** Trying to get `billed_duration_minutes` from `metadata.get()` when metadata is a model.

**Fix:** Changed to get `billed_duration_minutes` directly from `status_result` (it's a top-level field, not in metadata).

```python
# BEFORE (WRONG):
metadata = status_result.get("metadata", {})
billed_duration_minutes = metadata.get("billed_duration_minutes")

# AFTER (CORRECT):
billed_duration_minutes = status_result.get("billed_duration_minutes")
```

### ✅ Fixed: `app/main.py` line 697-707
**Problem:** Trying to call `.copy()` on metadata model and access as dict.

**Fix:** Handle metadata as a model object, with fallback to create minimal model if None.

```python
# BEFORE (WRONG):
metadata = status_result.get("metadata", {}).copy()

# AFTER (CORRECT):
metadata = status_result.get("metadata")
if metadata is None:
    # Fallback: create minimal metadata
    from app.models.transcript import TranscriptMetadata
    metadata = TranscriptMetadata(...)
```

---

## Verified Safe (No Changes Needed)

### ✅ Safe: `app/services/jobs.py` lines 340, 522
**Reason:** `transcript_data` is loaded from JSON files using `json.load()`, so it's always a dict. Accessing `.get("metadata")` is correct.

```python
transcript_data = self._load_transcript(job["transcript_file"])  # Returns dict from JSON
job_copy["transcript_metadata"] = transcript_data.get("metadata")  # OK - dict access
```

### ✅ Safe: `app/services/orchestrator.py` line 552
**Reason:** `updated_job` comes from `job_storage.get_job()` which returns a dict loaded from JSON. Job records don't store metadata directly (they reference transcript files), so `updated_job.get("metadata", {})` will return `{}` if not found, which is safe.

```python
updated_job = self.job_storage.get_job(job_id, include_transcript=True)  # Returns dict
"metadata": updated_job.get("metadata", {})  # OK - dict access, returns {} if not found
```

### ✅ Safe: `app/services/orchestrator.py` lines 561, 617, 650
**Reason:** These already have proper type checking and conversion:

```python
metadata = status_result.get("metadata")
if not isinstance(metadata, TranscriptMetadata):
    # Fallback: convert dict to model
    metadata = dict_to_transcript_metadata(metadata if metadata else {})
```

### ✅ Safe: `app/main.py` lines 779, 803
**Reason:** These are getting metadata from `status_result` dict and passing it to functions that accept `TranscriptMetadata` models. The functions handle the conversion internally.

```python
metadata=status_result.get("metadata")  # OK - getting from dict, function accepts model
```

---

## Data Flow Summary

### Where Metadata is a Model:
1. **`transcribe_v2.py`** → Returns `TranscriptMetadata` model in `status_result["metadata"]`
2. **`orchestrator.py`** → Receives model, passes model to `job_storage.mark_complete()` and `library_service.add_entry()`
3. **`jobs.py`** → `mark_complete()` accepts model, converts to dict only at JSON storage boundary
4. **`library.py`** → `add_entry()` accepts model, converts to dict only at JSON storage boundary

### Where Metadata is a Dict:
1. **JSON files** (`data/transcripts/*.json`, `data/library.json`) → Always dicts (JSON storage)
2. **Job records** (`data/jobs.json`) → Don't store metadata directly (reference transcript files)
3. **`_load_transcript()`** → Returns dict from JSON file

---

## Testing Checklist

- [x] Fixed `app/main.py` line 668-669 (billed_duration access)
- [x] Fixed `app/main.py` line 697-707 (metadata handling)
- [x] Verified `app/services/jobs.py` lines 340, 522 (safe - dict access)
- [x] Verified `app/services/orchestrator.py` line 552 (safe - dict access)
- [x] Verified `app/services/orchestrator.py` lines 561, 617, 650 (safe - type checking)
- [x] Verified `app/main.py` lines 779, 803 (safe - passing to functions)

---

## Remaining Risks

**None identified.** All metadata access points have been audited and either fixed or verified safe.

---

## Prevention

To prevent similar issues in the future:
1. **Type hints:** Use `TranscriptMetadata` type hints consistently
2. **Type checking:** Use `isinstance(metadata, TranscriptMetadata)` before accessing
3. **Conversion functions:** Use `dict_to_transcript_metadata()` and `transcript_metadata_to_dict()` at boundaries
4. **Code review:** Check for `.get()` calls on metadata objects

