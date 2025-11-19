# Why We Use Try/Except/Finally for File Uploads

**Date:** 2025-11-18  
**Question:** What is the nature of the try structure? Why are you using try?

---

## The Try/Except/Finally Structure

```python
temp_path = None
try:
    # 1. Stream file to temp file
    # 2. Upload to GCS
    # 3. Submit job
    # 4. Return success
    
except ValueError as e:
    # Handle validation errors (400 Bad Request)
    
except Exception as e:
    # Handle unexpected errors (500 Internal Server Error)
    
finally:
    # ALWAYS clean up temp file, even if errors occurred
```

---

## Why We Need Try/Except/Finally

### 1. **Errors Can Happen at Multiple Points**

**During file streaming:**
- Network connection drops
- Disk runs out of space
- File system errors
- User cancels upload

**During validation:**
- File too large
- Invalid file format
- Corrupted file

**During GCS upload:**
- Network timeout
- GCS quota exceeded
- Permission errors
- Service unavailable

**During job submission:**
- Google API errors
- Quota exceeded
- Invalid configuration

**Without try/except:** Any of these would crash the server or return a cryptic error.

---

### 2. **Resource Cleanup is Critical**

**The Problem:**
- We create a temp file on disk (215MB for your file!)
- If an error occurs, the temp file stays on disk
- Without cleanup, temp files accumulate
- Server runs out of disk space

**The Solution:**
- `finally` block **always** runs, even if errors occur
- Ensures temp file is deleted
- Prevents disk space leaks

**Example:**
```python
# Without finally:
temp_file = create_temp_file()  # 215MB
upload_to_gcs()  # ERROR! Network timeout
# Temp file still exists! ❌

# With finally:
try:
    temp_file = create_temp_file()  # 215MB
    upload_to_gcs()  # ERROR! Network timeout
finally:
    delete_temp_file()  # Always runs! ✅
```

---

### 3. **Proper Error Responses**

**Without try/except:**
- Python exception → Server crash or 500 error
- User sees: "Internal Server Error"
- No useful information

**With try/except:**
- Catch specific errors
- Return appropriate HTTP status codes
- Provide helpful error messages

**Example:**
```python
except ValueError as e:
    # Validation error (file too large, invalid format)
    raise HTTPException(status_code=400, detail=str(e))
    # User sees: "File too large. Maximum size: 500MB"

except Exception as e:
    # Unexpected error (network, GCS, etc.)
    raise HTTPException(status_code=500, detail="Error submitting transcription")
    # User sees: Clear error message
```

---

## The Structure Breakdown

### Try Block: The Main Workflow

```python
try:
    # Step 1: Stream file to temp file
    temp_path = stream_to_temp_file()
    
    # Step 2: Upload to GCS
    gcs_uri = upload_to_gcs(temp_path)
    
    # Step 3: Submit job
    job_id = submit_job(gcs_uri)
    
    # Step 4: Return success
    return {"job_id": job_id, "status": "queued"}
```

**If everything succeeds:** Returns normally, then `finally` runs.

**If any step fails:** Jumps to appropriate `except` block, then `finally` runs.

---

### Except Blocks: Error Handling

```python
except ValueError as e:
    # Validation errors (file too large, invalid format)
    # Return 400 Bad Request with helpful message
    raise HTTPException(status_code=400, detail=str(e))

except Exception as e:
    # Any other unexpected error
    # Log it, clean up GCS file if needed, return 500
    logger.error(f"Error: {e}")
    if gcs_uri:
        delete_gcs_file(gcs_uri)  # Clean up uploaded file
    raise HTTPException(status_code=500, detail="Error submitting transcription")
```

**Purpose:**
- Catch errors before they crash the server
- Return proper HTTP status codes
- Provide useful error messages
- Clean up resources (GCS files)

---

### Finally Block: Guaranteed Cleanup

```python
finally:
    # This ALWAYS runs, even if:
    # - Everything succeeded
    # - An exception was raised
    # - Return statement was executed
    
    if temp_path and os.path.exists(temp_path):
        try:
            os.unlink(temp_path)  # Delete temp file
            logger.debug(f"Cleaned up temp file: {temp_path}")
        except Exception as e:
            logger.warning(f"Failed to clean up: {e}")
            # Even cleanup can fail, but we log it
```

**Why it's critical:**
- Temp files can be large (215MB+)
- Without cleanup, disk fills up quickly
- `finally` ensures cleanup happens even if errors occur

**Example scenario:**
```python
try:
    temp_file = create_temp_file()  # 215MB
    upload_to_gcs()  # ERROR! Network timeout
    # Exception raised, jumps to except
except Exception as e:
    # Handle error
    raise HTTPException(...)
finally:
    # STILL RUNS! Deletes temp file
    delete_temp_file()  # ✅
```

---

## Real-World Example

**What happens with your 215MB file:**

1. **File streams to temp file** (215MB on disk)
2. **Upload to GCS starts** (streaming from disk)
3. **Network timeout occurs** (after 10 minutes)
4. **Exception raised:** `TimeoutError`
5. **Except block catches it:**
   - Logs the error
   - Returns 500 error to user
   - Cleans up GCS file (if partially uploaded)
6. **Finally block runs:**
   - Deletes temp file (215MB freed!)
   - Even though error occurred

**Without finally:** Temp file stays on disk forever, eating up space.

---

## Alternative Approaches (And Why They're Worse)

### 1. **No Error Handling**
```python
temp_file = create_temp_file()
upload_to_gcs()  # ERROR! Server crashes
# Temp file never deleted ❌
```

### 2. **Cleanup in Success Path Only**
```python
try:
    temp_file = create_temp_file()
    upload_to_gcs()
    delete_temp_file()  # Only runs if success
except:
    # Temp file never deleted if error! ❌
    pass
```

### 3. **Manual Cleanup Everywhere**
```python
temp_file = create_temp_file()
try:
    upload_to_gcs()
except:
    delete_temp_file()  # Need to remember everywhere
    raise
delete_temp_file()  # Also need here
# Easy to forget, error-prone ❌
```

**With finally:** Cleanup happens automatically, guaranteed.

---

## Summary

**Why try?**
- Handle errors gracefully
- Prevent server crashes
- Return proper HTTP responses

**Why except?**
- Catch specific error types
- Return appropriate status codes
- Provide helpful error messages
- Clean up resources (GCS files)

**Why finally?**
- **Guaranteed cleanup** of temp files
- Prevents disk space leaks
- Runs even if errors occur
- Critical for large files (215MB+)

**This is standard Python best practice** for resource management and error handling.

---

## The Pattern

This is a common pattern in Python:

```python
resource = acquire_resource()  # File, connection, etc.
try:
    use_resource(resource)  # Do work
except SpecificError:
    handle_specific_error()  # Handle known errors
except Exception:
    handle_unexpected_error()  # Handle unknown errors
finally:
    cleanup_resource(resource)  # ALWAYS cleanup
```

**Python even has context managers for this:**
```python
with open('file.txt') as f:  # Automatically closes
    f.read()
# File closed automatically, even if error occurs
```

But for temp files that need to persist across multiple operations, we use try/finally.

