# "file is not defined" Error - Root Cause Analysis

**Date:** 2025-11-18  
**Error:** `NameError: name 'file' is not defined`

---

## The Error

When an exception occurs in the `detect_duration` or `transcribe_audio` endpoints, the exception handler tries to access `file.filename` to include it in the error log. However, this can itself raise a `NameError: name 'file' is not defined`.

---

## Root Causes

### 1. **Exception Occurs During Parameter Binding**

In FastAPI, if an exception occurs **before** the function parameters are fully bound (e.g., during request parsing, validation, or dependency injection), the parameter `file` might not be in scope yet.

**Example scenario:**
```python
async def detect_duration(
    file: UploadFile = File(...),  # ← If exception occurs here during binding
    metadata_service: AudioMetadataService = Depends(...)
):
    try:
        audio_bytes = await file.read()  # ← Never reached
    except Exception as e:
        filename = file.filename  # ← NameError: 'file' not defined!
```

### 2. **Exception in Dependency Injection**

If the `Depends(get_audio_metadata_service)` fails, the function might not execute with proper parameter binding, leaving `file` undefined in the exception handler scope.

### 3. **Python Exception Handler Scoping**

Python's exception handlers have access to the function's local scope, but if an exception occurs **during** parameter binding (before the function body executes), those parameters might not be in the local scope yet.

### 4. **FastAPI Request Parsing Failures**

If FastAPI fails to parse the multipart form data (e.g., malformed request, missing boundary, connection reset), the `file` parameter might not be bound before the exception is raised.

---

## Why Our Original Code Failed

**Original code:**
```python
except Exception as e:
    filename_str = file.filename if file and hasattr(file, 'filename') else 'unknown'
    logger.error(f"Error detecting duration for {filename_str}: {e}")
```

**Problem:**
- The check `file and hasattr(file, 'filename')` assumes `file` exists
- If `file` itself raises a `NameError` (not defined), the entire expression fails
- We can't check `file` if `file` doesn't exist!

---

## The Fix

**Fixed code:**
```python
except Exception as e:
    # Safely get filename - file might not be accessible in exception handler
    try:
        filename_str = file.filename if file and hasattr(file, 'filename') else 'unknown'
    except (NameError, AttributeError):
        filename_str = 'unknown'
    
    logger.error(f"Error detecting duration for {filename_str}: {e}", exc_info=True)
```

**Why this works:**
1. **Inner try-except** catches `NameError` if `file` doesn't exist
2. **Also catches `AttributeError`** if `file` exists but doesn't have `filename`
3. **Falls back to 'unknown'** if we can't access the filename
4. **Still logs the actual error** with full traceback (`exc_info=True`)

---

## When This Error Occurs

This error is most likely to occur when:

1. **Malformed HTTP request** - Request doesn't have proper multipart/form-data structure
2. **Connection reset during upload** - Client disconnects before file is fully received
3. **FastAPI validation failure** - Request validation fails before parameters are bound
4. **Dependency injection failure** - `Depends()` raises an exception
5. **Request parsing error** - FastAPI can't parse the request body

---

## Prevention Strategy

### 1. **Always Wrap Variable Access in Exception Handlers**

If you're accessing function parameters in exception handlers, wrap them in try-except:

```python
try:
    param_value = param.attribute
except (NameError, AttributeError):
    param_value = 'unknown'
```

### 2. **Use `exc_info=True` for Full Tracebacks**

Always include `exc_info=True` in error logs to see the full stack trace, which helps diagnose the root cause:

```python
logger.error(f"Error: {e}", exc_info=True)
```

### 3. **Validate Parameters Early**

If you need to access parameters in exception handlers, validate them early:

```python
def my_function(param: SomeType):
    # Validate early
    if not param:
        raise ValueError("param is required")
    
    try:
        # ... do work
    except Exception as e:
        # Now we know param exists
        logger.error(f"Error with {param}: {e}")
```

---

## Related Issues

This is similar to the "file is not defined" error we saw in `app/main.py`'s `detect_duration` endpoint. The same fix pattern applies:

1. Wrap parameter access in try-except
2. Catch `NameError` and `AttributeError`
3. Provide a safe fallback value
4. Still log the actual error with full context

---

## Key Takeaway

**Exception handlers can't assume variables exist.** If an exception occurs during parameter binding or dependency injection, those parameters might not be in scope. Always wrap parameter access in exception handlers with try-except to handle `NameError` gracefully.

