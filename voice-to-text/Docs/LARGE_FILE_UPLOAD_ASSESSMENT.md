# Large File Upload Pipeline Assessment

**Date:** 2025-11-18  
**Purpose:** Thorough assessment of code handling large file uploads and transcription

---

## Pipeline Flow

1. **Frontend** → `POST /api/v1/transcribe` (FastAPI endpoint)
2. **API Endpoint** (`app/api/v1/transcription.py`) → Streams file to temp file
3. **Orchestrator** (`app/services/orchestrator.py`) → Validates, uploads to GCS, submits job
4. **Storage Service** (`app/services/storage.py`) → Handles GCS upload and file conversion

---

## Issues Found

### 🔴 Critical Issues

#### 1. Missing Error Handling: `file.filename` Can Be None
**Location:** `app/api/v1/transcription.py:63`
```python
file_extension = Path(file.filename).suffix if file.filename else '.tmp'
```
**Issue:** If `file.filename` is `None`, `Path(None).suffix` will raise `TypeError`
**Fix:** Already handled with ternary, but should verify `file` is not None first

#### 2. Missing Error Handling: File Read During Streaming
**Location:** `app/api/v1/transcription.py:72`
```python
chunk = await file.read(chunk_size)
```
**Issue:** If `file.read()` fails (network error, connection reset), exception is caught by outer handler but no specific logging
**Fix:** Add specific exception handling for read errors

#### 3. Missing Error Handling: Temp File Write Failures
**Location:** `app/api/v1/transcription.py:75`
```python
temp_file.write(chunk)
```
**Issue:** If disk is full or write fails, exception is caught but no specific handling
**Fix:** Add specific exception handling for write errors

#### 4. Missing Error Handling: File Size Check After Streaming
**Location:** `app/api/v1/transcription.py:77`
```python
os.path.getsize(temp_path)
```
**Issue:** If temp file was deleted or doesn't exist, this will fail
**Fix:** Check file exists before getting size

#### 5. Missing Error Handling: File Path Validation
**Location:** `app/services/orchestrator.py:304`
```python
file_size = Path(file_path).stat().st_size
```
**Issue:** If `file_path` doesn't exist, `stat()` will raise `FileNotFoundError`
**Fix:** Check file exists before calling `stat()`

#### 6. Missing Error Handling: File Size Check in Storage
**Location:** `app/services/storage.py:264`
```python
file_size = os.path.getsize(upload_file_path)
```
**Issue:** If file doesn't exist (e.g., conversion failed), this will raise `OSError`
**Fix:** Check file exists before getting size

#### 7. Temp File Cleanup: Converted Files Not Always Cleaned Up
**Location:** `app/services/storage.py:321-326`
**Issue:** If GCS upload fails AFTER video/M4A conversion, the converted temp file (`mp3_path`) is cleaned up. But if conversion fails partway, temp file might remain.
**Fix:** Use try/finally to ensure cleanup

### ⚠️ Medium Priority Issues

#### 8. Missing Logging: No Error Context
**Location:** Multiple locations
**Issue:** When exceptions occur, we log the error but don't log the file size, filename, or other context that would help debug
**Fix:** Add context to error logs (file size, filename, temp path)

#### 9. Missing Validation: File Size During Streaming
**Location:** `app/api/v1/transcription.py:71-75`
**Issue:** We stream the file but don't check size until after it's fully written to disk
**Fix:** Track total size during streaming and validate incrementally

#### 10. Missing Error Handling: Metadata Extraction Failure
**Location:** `app/services/storage.py:188-206`
**Issue:** If `mediainfo()` fails, we use defaults, but if the file is completely invalid, we should fail fast
**Fix:** Validate file is readable before proceeding

---

## Error Handling Flow Analysis

### Current Flow (Good)
1. ✅ Temp file cleanup in `finally` block (API endpoint)
2. ✅ GCS file cleanup on error (orchestrator)
3. ✅ Converted file cleanup (storage service)
4. ✅ Exception logging with context

### Missing Error Handling
1. ❌ No validation that `file` object is valid before use
2. ❌ No specific handling for network errors during streaming
3. ❌ No specific handling for disk full errors
4. ❌ No validation that temp file exists before passing to orchestrator
5. ❌ No validation that file path exists before calling `stat()`

---

## Recommended Fixes

### Priority 1: Critical Fixes

1. **Add file validation in API endpoint:**
   ```python
   if not file or not file.filename:
       raise HTTPException(status_code=400, detail="File is required")
   ```

2. **Add file existence check in orchestrator:**
   ```python
   if not os.path.exists(file_path):
       raise ValueError(f"File not found: {file_path}")
   ```

3. **Add file existence check in storage:**
   ```python
   if not os.path.exists(upload_file_path):
       raise FileNotFoundError(f"File not found: {upload_file_path}")
   ```

4. **Add specific exception handling for streaming:**
   ```python
   try:
       chunk = await file.read(chunk_size)
   except Exception as e:
       logger.error(f"Error reading file chunk: {e}")
       raise HTTPException(status_code=500, detail="Error reading uploaded file")
   ```

5. **Add specific exception handling for temp file write:**
   ```python
   try:
       temp_file.write(chunk)
   except OSError as e:
       logger.error(f"Error writing temp file: {e}")
       raise HTTPException(status_code=500, detail="Error writing file to disk")
   ```

### Priority 2: Improved Error Context

1. **Add context to all error logs:**
   - File size
   - Filename
   - Temp file path
   - Error type

2. **Add validation during streaming:**
   - Track total size
   - Validate incrementally
   - Fail fast if size exceeds limit

---

## Testing Recommendations

1. **Test with None filename**
2. **Test with network interruption during upload**
3. **Test with disk full scenario**
4. **Test with invalid file path**
5. **Test with file that doesn't exist**
6. **Test with corrupted audio file**
7. **Test with very large file (approaching 500MB limit)**

---

## Summary

**Status:** ⚠️ **Needs Fixes** - Several critical error handling gaps

**Critical Issues:** 7  
**Medium Priority Issues:** 3

**Recommendation:** Fix Priority 1 issues before testing large file uploads.

