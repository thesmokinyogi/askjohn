# Testing Queued vs Processing Status Detection

**Date:** 2025-11-14  
**Purpose:** Observe what metadata Google's operation object provides

---

## What to Test

1. **Operation Metadata Structure**
   - What fields are in `operation.metadata`?
   - Does it have `state`, `progress_percent`, or other status fields?
   - Can we differentiate "queued" from "processing"?

2. **Status Detection**
   - Does our new code correctly identify queued vs processing?
   - What does the UI show?

3. **Feedback Loop**
   - Is processing time being recorded correctly?
   - Are estimates improving?

---

## How to Test

### Step 1: Submit a Job
1. Upload an audio file via the UI
2. Note the job_id from the response

### Step 2: Check Logs Immediately
Right after submission, check the logs for:
```
Operation metadata type: <type>
Operation metadata: <content>
Job <job_id> state from metadata: <state>
```

### Step 3: Poll Status
Check job status multiple times:
- Immediately after submission (should be "queued" if detectable)
- A few seconds later (might transition to "processing")
- When complete

### Step 4: Check What We Got
Look for:
- **If metadata has state field:** We can differentiate queued/processing
- **If metadata has progress_percent:** We can show actual progress
- **If metadata is empty/None:** We can't differentiate (current behavior)

---

## What to Look For in Logs

### Good Signs (We Can Differentiate):
```
Operation metadata type: <protobuf message>
Operation metadata: state: QUEUED
Job <id> state from metadata: QUEUED
Status: queued
```

### Or:
```
Operation metadata: progress_percent: 0
Job <id> is processing (progress available)
Status: processing
```

### If We Can't Differentiate:
```
Operation metadata type: <type>
Operation metadata: <empty or minimal>
Could not extract status from metadata: <error>
Status: processing (default)
```

---

## Expected Outcomes

### Scenario A: Metadata Has State
- ✅ We can show "Queued" in UI
- ✅ We can track when processing actually starts
- ✅ We can record only processing time (exclude queue time)
- ✅ More accurate estimates

### Scenario B: Metadata Has Progress
- ✅ We can show actual progress percentage
- ✅ Better progress indicator
- ✅ Still can't differentiate queue vs processing start

### Scenario C: No Useful Metadata
- ⚠️ Can't differentiate (current behavior)
- ⚠️ Include queue time in estimates (current approach)
- ⚠️ Show "Processing" for both queued and active

---

## Next Steps Based on Results

**If we can detect queued:**
1. Update UI to show "Queued" status
2. Track `processing_started_at` timestamp
3. Record only processing time (not queue time) for learning
4. Update estimates to exclude queue time

**If we can't detect queued:**
1. Keep current approach (include queue time)
2. Maybe add heuristic: "If elapsed < 5s, probably queued"
3. Document limitation

---

## Commands to Check Logs

```bash
# Watch logs in real-time
tail -f logs/app.log | grep -E "metadata|status|queued|processing"

# Or if using console output
# Just watch the terminal where uvicorn is running
```

