# Validation Script Usage Guide

**Script:** `scripts/validate_transcript_data.py`

---

## Do You Need to Start the Server?

**Short answer:** No, but you need the Python environment with dependencies.

**Long answer:**
- The script is **standalone** - it doesn't need the server running
- The script **does need** the Python environment with dependencies (pydantic, etc.)
- If your server runs, that means your environment is ready, so you can run the script
- You can also run it in any Python environment that has the dependencies installed

---

## How to Run

### Option 1: Run in Same Environment as Server (Recommended)

If your server is running, your environment is ready:

```bash
# In the same terminal/environment where you run the server
python scripts/validate_transcript_data.py
```

### Option 2: Run in Virtual Environment

If you have a venv:

```bash
# Activate venv first
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Then run script
python scripts/validate_transcript_data.py
```

### Option 3: Run with Server Running

You can run it while the server is running (they don't conflict):

```bash
# In a separate terminal
cd /path/to/voice-to-text
python scripts/validate_transcript_data.py
```

---

## What the Script Needs

1. **Python environment** with:
   - `pydantic` (for models)
   - Standard library (json, pathlib, etc.)

2. **Access to:**
   - `app/models/transcript.py` (for conversion functions)
   - `data/transcripts/` directory
   - `data/library.json` file

3. **No server required:**
   - Script reads files directly
   - Doesn't make HTTP requests
   - Doesn't need server running

---

## Troubleshooting

### "ModuleNotFoundError: No module named 'pydantic'"

**Solution:** Activate your virtual environment or install dependencies:
```bash
pip install pydantic
```

### "ModuleNotFoundError: No module named 'app'"

**Solution:** Run from project root directory:
```bash
cd /path/to/voice-to-text
python scripts/validate_transcript_data.py
```

### Script works but server doesn't

**Different issue:** Server might have different environment. Check server's Python environment.

---

## Recommendation

**Easiest approach:**
1. If server is running → Your environment is ready → Run script
2. If server not running → Activate venv → Run script

**The script is independent** - it just needs the Python dependencies, not the running server.

