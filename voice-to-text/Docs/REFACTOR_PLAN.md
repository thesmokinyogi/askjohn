# Refactor Plan: Models Throughout

**Date:** 2025-11-18  
**Goal:** Remove redundant conversions, use models throughout  
**Approach:** Systematic, multi-pass, following working agreement

---

## Phase 1: Observation ✅ IN PROGRESS

### Metadata Access Points Identified

1. **Creation Point:**
   - `transcribe_v2.py` - Creates metadata dict, converts to model, then back to dict
   - **Current:** Model → Dict (for storage compatibility)
   - **Target:** Return model directly

2. **Storage Layer:**
   - `jobs.py._save_transcript()` - Accepts `Dict[str, Any]`, stores as JSON
   - `jobs.py.mark_complete()` - Accepts `Dict[str, Any]`, passes to `_save_transcript()`
   - **Current:** Dict → JSON
   - **Target:** Model → Dict (only at JSON boundary)

3. **Library Layer:**
   - `library.py.add_entry()` - Accepts `Dict[str, Any]`, stores in library.json
   - **Current:** Dict → JSON
   - **Target:** Model → Dict (only at JSON boundary)

4. **Event Publishing:**
   - `orchestrator.py` - Converts dict → model → dict for event publishing
   - `events.py.publish_job_completed()` - Accepts `Dict[str, Any]`
   - **Current:** Dict → Model → Dict
   - **Target:** Model throughout, convert only at serialization boundary

5. **Reading/Retrieval:**
   - `jobs.py.get_job()` - Loads transcript file, returns dict
   - `library.py` - Loads library.json, returns dict
   - **Current:** JSON → Dict
   - **Target:** JSON → Dict → Model (validate on load)

---

## Phase 2: Design

### Integration Points Map

```
transcribe_v2.py
  ├─> Creates TranscriptMetadata model
  ├─> Returns model (not dict)
  └─> Called by: orchestrator.py

orchestrator.py
  ├─> Receives TranscriptMetadata model
  ├─> Passes model to jobs.py.mark_complete()
  ├─> Passes model to library.py.add_entry()
  └─> Builds TranscriptOutput model for events

jobs.py
  ├─> mark_complete() - Accepts TranscriptMetadata model
  ├─> _save_transcript() - Accepts TranscriptMetadata model
  └─> Converts model → dict only at JSON.write() boundary

library.py
  ├─> add_entry() - Accepts TranscriptMetadata model
  └─> Converts model → dict only at JSON.write() boundary

events.py
  ├─> publish_job_completed() - Accepts TranscriptOutput model
  └─> Converts model → dict only at serialization boundary (if needed)
```

### Changes Required

#### 1. transcribe_v2.py
**Current:**
```python
metadata_model = TranscriptMetadata(...)
metadata = transcript_metadata_to_dict(metadata_model)  # Convert to dict
return {"metadata": metadata}  # Return dict
```

**Target:**
```python
metadata_model = TranscriptMetadata(...)
return {"metadata": metadata_model}  # Return model directly
```

#### 2. jobs.py.mark_complete()
**Current:**
```python
def mark_complete(
    self,
    ...
    metadata: Dict[str, Any] = None,  # Accepts dict
    ...
):
    self._save_transcript(..., metadata=metadata)  # Pass dict
```

**Target:**
```python
def mark_complete(
    self,
    ...
    metadata: TranscriptMetadata,  # Accepts model
    ...
):
    self._save_transcript(..., metadata=metadata)  # Pass model
```

#### 3. jobs.py._save_transcript()
**Current:**
```python
def _save_transcript(
    self,
    ...
    metadata: Dict[str, Any]  # Accepts dict
):
    transcript_data = {
        "metadata": metadata or {}  # Store dict directly
    }
    json.dump(transcript_data, f)  # Dict → JSON
```

**Target:**
```python
def _save_transcript(
    self,
    ...
    metadata: TranscriptMetadata  # Accepts model
):
    # Convert model → dict only at JSON boundary
    metadata_dict = transcript_metadata_to_dict(metadata)
    transcript_data = {
        "metadata": metadata_dict
    }
    json.dump(transcript_data, f)  # Dict → JSON
```

#### 4. library.py.add_entry()
**Current:**
```python
def add_entry(
    self,
    ...
    metadata: Optional[Dict] = None  # Accepts dict
):
    entry = {
        "metadata": metadata or {}  # Store dict directly
    }
```

**Target:**
```python
def add_entry(
    self,
    ...
    metadata: Optional[TranscriptMetadata] = None  # Accepts model
):
    # Convert model → dict only at JSON boundary
    metadata_dict = transcript_metadata_to_dict(metadata) if metadata else {}
    entry = {
        "metadata": metadata_dict
    }
```

#### 5. orchestrator.py
**Current:**
```python
# Receives dict from transcribe_v2
transcript_metadata_dict = status_result.get("metadata", {})
transcript_metadata = dict_to_transcript_metadata(transcript_metadata_dict)  # Convert to model
# ... builds TranscriptOutput ...
transcript_data = transcript_output.model_dump()  # Convert to dict
event_publisher.publish_job_completed(job_id, transcript_data)  # Pass dict
```

**Target:**
```python
# Receives model from transcribe_v2
transcript_metadata = status_result.get("metadata")  # Already a model
# ... builds TranscriptOutput ...
event_publisher.publish_job_completed(job_id, transcript_output)  # Pass model
```

#### 6. events.py.publish_job_completed()
**Current:**
```python
def publish_job_completed(
    self, 
    job_id: str, 
    transcript_data: Dict[str, Any]  # Accepts dict
) -> bool:
    logger.info(f"transcript_id={transcript_data.get('transcript_id')}")  # Dict access
```

**Target:**
```python
def publish_job_completed(
    self, 
    job_id: str, 
    transcript_data: TranscriptOutput  # Accepts model
) -> bool:
    logger.info(f"transcript_id={transcript_data.transcript_id}")  # Model access
    # Convert to dict only if needed for serialization (HTTP/JSON)
    if needs_serialization:
        data_dict = transcript_data.model_dump()
```

---

## Phase 3: Review Checklist

### Pre-Implementation Review
- [ ] All access points identified
- [ ] All integration points mapped
- [ ] Conversion boundaries clearly defined
- [ ] Backward compatibility considered
- [ ] Error handling planned
- [ ] Type hints updated
- [ ] Documentation updated

### Integration Points Verification
- [ ] transcribe_v2 → orchestrator (model flow)
- [ ] orchestrator → jobs.mark_complete (model flow)
- [ ] orchestrator → library.add_entry (model flow)
- [ ] orchestrator → events.publish (model flow)
- [ ] jobs._save_transcript (model → dict at JSON boundary)
- [ ] library.add_entry (model → dict at JSON boundary)
- [ ] events.publish (model → dict at serialization boundary, if needed)

### Edge Cases
- [ ] None/empty metadata handling
- [ ] Missing fields in existing data
- [ ] Validation errors
- [ ] JSON serialization edge cases

---

## Phase 4: Implementation Order

1. **Update type hints and interfaces** (non-breaking)
   - Update function signatures
   - Add type hints
   - Update docstrings

2. **Update storage layer** (jobs.py, library.py)
   - Accept models
   - Convert at JSON boundary
   - Test with existing data

3. **Update event publisher** (events.py)
   - Accept models
   - Update interface
   - Test

4. **Update callers** (orchestrator.py)
   - Pass models instead of dicts
   - Remove conversions
   - Test

5. **Update creation point** (transcribe_v2.py)
   - Return model directly
   - Remove conversion
   - Test

6. **Verify end-to-end**
   - Test complete flow
   - Verify JSON storage still works
   - Verify event publishing works

---

## Phase 5: Testing Plan

### Unit Tests
- [ ] Conversion functions (dict ↔ model)
- [ ] Storage layer (model → JSON → model)
- [ ] Event publisher (model acceptance)

### Integration Tests
- [ ] Complete transcription flow
- [ ] Library entry creation
- [ ] Event publishing
- [ ] Existing data compatibility

### Validation Tests
- [ ] Invalid metadata rejected
- [ ] Missing fields handled gracefully
- [ ] Type errors caught

---

## Success Criteria

✅ **Models used throughout internal flow**
✅ **Conversions only at boundaries** (JSON, serialization)
✅ **Backward compatible** (existing JSON files still work)
✅ **Type safe** (IDE support, validation)
✅ **No redundant conversions** (model → dict → model → dict eliminated)

---

## Risk Assessment

**Low Risk:**
- Conversion functions exist and tested
- Structure already matches
- Small dataset (easy to validate)

**Mitigation:**
- Update one layer at a time
- Test after each change
- Keep conversion functions as fallback
- Validate existing data loads correctly

---

## Next Steps

1. Complete Phase 1 (Observation) - Map all access points
2. Complete Phase 2 (Design) - Finalize integration points
3. Phase 3 (Review) - Multi-pass review of design
4. Phase 4 (Implement) - Systematic implementation
5. Phase 5 (Verify) - End-to-end testing

