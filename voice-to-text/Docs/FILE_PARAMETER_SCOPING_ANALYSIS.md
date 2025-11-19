# File Parameter Scoping Analysis

**Question:** Why would `file` (a function parameter) not be accessible in an exception handler?

---

## The Code Structure

```python
@router.post("/detect-duration", response_model=AudioMetadataResponse)
async def detect_duration(
    file: UploadFile = File(...),
    metadata_service: AudioMetadataService = Depends(get_audio_metadata_service)
):
    try:
        audio_bytes = await file.read()  # ← If exception here, file should be in scope
        # ...
    except Exception as e:
        filename_str = file.filename  # ← Why would file not be defined here?
```

---

## Analysis: When Would `file` Not Be Defined?

### Scenario 1: FastAPI Parameter Binding Failure
**If FastAPI fails to bind `file`, the function wouldn't be called at all.**
- FastAPI would return a 400 error before our function executes
- We wouldn't be in our exception handler
- **This is NOT the cause**

### Scenario 2: Dependency Injection Failure
**If `Depends(get_audio_metadata_service)` fails:**
- FastAPI might not call our function
- Or FastAPI might call it but parameters might not be fully bound
- **This COULD be the cause** - but FastAPI should handle this before calling us

### Scenario 3: Exception During Parameter Access
**If accessing `file` itself raises an exception:**
- `file` exists but accessing it fails
- This would be an `AttributeError`, not `NameError`
- **This is NOT the cause** (we're getting `NameError`)

### Scenario 4: Python Scoping Issue
**Function parameters are ALWAYS in local scope:**
- If the function executes, parameters are bound
- Exception handlers have access to function's local scope
- **This should NOT happen** - parameters are always accessible

---

## The Real Question

**If we're in the exception handler, the function WAS called, which means:**
1. FastAPI successfully parsed the request
2. FastAPI successfully bound the `file` parameter
3. FastAPI successfully injected dependencies
4. Our function body started executing

**So `file` SHOULD be in scope.**

---

## Possible Root Causes

### 1. **Dependency Injection Exception**
If `get_audio_metadata_service()` raises an exception DURING dependency injection, FastAPI might:
- Still call our function (to handle the exception)
- But parameters might not be fully bound
- This is a FastAPI edge case

### 2. **Request Parsing Exception**
If FastAPI fails to parse the multipart form data:
- FastAPI might call our function with a partially bound request
- `file` might be None or not bound
- But FastAPI should handle this before calling us

### 3. **Our Code Structure Issue**
Looking at our code:
```python
async def detect_duration(
    file: UploadFile = File(...),
    metadata_service: AudioMetadataService = Depends(get_audio_metadata_service)
):
    try:
        audio_bytes = await file.read()  # ← file is used here
```

If `file.read()` fails, we're in the exception handler. `file` should be accessible.

**BUT** - if the exception is in `Depends(get_audio_metadata_service)`, FastAPI might:
- Call our function to handle the exception
- But `file` might not be bound yet (dependency injection happens in order)

---

## The Fix: Capture Filename Early

Instead of accessing `file.filename` in the exception handler, we should capture it early:

```python
async def detect_duration(
    file: UploadFile = File(...),
    metadata_service: AudioMetadataService = Depends(get_audio_metadata_service)
):
    # Capture filename early, before any operations
    filename = getattr(file, 'filename', None) if file else None
    
    try:
        audio_bytes = await file.read()
        # ...
    except Exception as e:
        # Now we have filename captured, no need to access file
        filename_str = filename or 'unknown'
        logger.error(f"Error detecting duration for {filename_str}: {e}", exc_info=True)
```

This ensures:
1. We capture the filename as soon as the function starts
2. We don't need to access `file` in the exception handler
3. We avoid any scoping issues

---

## Recommendation

**Fix at the implementation level:**
1. Capture `file.filename` at the start of the function
2. Use the captured value in exception handlers
3. This eliminates the need for defensive coding in exception handlers
4. Makes the code clearer and more predictable

