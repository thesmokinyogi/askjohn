# Console Output Explanation

## REST API "Request Failed" Messages

### What They Are
The messages like `"REST API request failed for us-east4: 404 Client Error..."` are **expected behavior** when using the "Probe List Strategy" for metadata discovery.

### Why They Appear
1. We probe a list of common GCP regions to discover which ones support Speech V2
2. Some regions (like `us-east4`, `us-west2`, etc.) don't support Speech V2
3. These regions return HTTP 404 (Not Found)
4. This is **normal** - we're discovering which regions work

### Fix Applied
Changed logging level from `WARNING` to `DEBUG` for expected 404 responses. These messages will now only appear if you set logging level to DEBUG.

### How to Suppress (if needed)
- Set logging level to `INFO` or higher (already default)
- Or set to `WARNING` to see only real issues
- DEBUG messages won't show unless explicitly enabled

## Viewing Console Output

### During Test Execution
When running test scripts, output appears in:
1. **Terminal/Console** - Direct output from `python3 tests/test_transcription_job.py`
2. **Logs** - Application logs (if running via FastAPI/uvicorn)

### To See Real-Time Output
```bash
# Run test script directly
python3 tests/test_transcription_job.py

# Or with logging to file
python3 tests/test_transcription_job.py 2>&1 | tee test_output.log
```

### In Production (FastAPI)
- Console output goes to stdout/stderr
- If running via `uvicorn`, logs appear in terminal
- Can redirect to file: `uvicorn app.main:app > app.log 2>&1`

## Test Script Output

The test script (`tests/test_transcription_job.py`) prints:
- Step-by-step progress
- Job ID when submitted
- Real-time polling status
- Final transcript and confidence score

All output is printed to stdout, visible in your terminal.

