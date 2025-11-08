# Voice-to-Text Transcription Service - Setup Guide

Complete step-by-step setup instructions for your Mac.

---

## Prerequisites

- Mac computer
- Internet connection
- Google Cloud account (you have $250 credit!)
- Terminal comfort (we'll walk through it)

---

## Part 1: Install Python

### Check if Python is installed

Open Terminal (Applications → Utilities → Terminal) and type:

```bash
python3 --version
```

**If you see:** `Python 3.11.x` or `Python 3.12.x` → **You're good! Skip to Part 2.**

**If you see:** `command not found` or version less than 3.11 → **Continue below.**

### Install Python via Homebrew

**Step 1: Install Homebrew** (if you don't have it)

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Follow the prompts. This will take a few minutes.

**Step 2: Install Python**

```bash
brew install python@3.12
```

**Step 3: Install ffmpeg** (required for audio conversion)

```bash
brew install ffmpeg
```

This is required for converting MP3/M4A files to WAV format.

**Step 4: Verify**

```bash
python3.12 --version
ffmpeg -version
```

Should show: `Python 3.12.x` and ffmpeg version info.

---

## Part 2: Set Up Google Cloud

### Step 1: Create Google Cloud Project

1. Go to: https://console.cloud.google.com/
2. Sign in with your Google account
3. Click **"Select a project"** → **"New Project"**
4. Project name: `voice-to-text-dev` (or whatever you prefer)
5. Click **"Create"**
6. Wait for project creation (~30 seconds)

### Step 2: Enable Speech-to-Text API

1. With your new project selected, go to: https://console.cloud.google.com/apis/library
2. Search for: `Speech-to-Text API`
3. Click on **"Cloud Speech-to-Text API"**
4. Click **"Enable"**
5. Wait for activation (~30 seconds)

### Step 3: Create Service Account (Your API Key)

1. Go to: https://console.cloud.google.com/iam-admin/serviceaccounts
2. Click **"+ Create Service Account"**
3. Service account details:
   - **Name:** `voice-to-text-service`
   - **ID:** (auto-fills, leave it)
   - Click **"Create and Continue"**
4. Grant permissions:
   - **Role:** Select `Cloud Speech Client`
   - Click **"Continue"**
5. Click **"Done"** (skip user access)

### Step 4: Download Credentials JSON

1. You should see your new service account in the list
2. Click on the **email address** (something like `voice-to-text-service@...`)
3. Go to the **"Keys"** tab
4. Click **"Add Key"** → **"Create new key"**
5. Select **"JSON"** format
6. Click **"Create"**
7. A JSON file downloads → **Save it somewhere safe!**
   - Suggestion: Save to `~/Documents/google-cloud-key.json`
   - **Important:** Never share this file or commit it to git!

---

## Part 3: Set Up Your Project

### Step 1: Navigate to Project Directory

In Terminal:

```bash
cd ~/Documents/askjohn/voice-to-text
```

(Adjust path if your askjohn folder is elsewhere)

### Step 2: Create Virtual Environment

This keeps your Python packages isolated (good practice):

```bash
python3.12 -m venv venv
```

**Important:** Use `python3.12` (not `python3`) to ensure correct version.

This creates a `venv` folder.

### Step 3: Activate Virtual Environment

```bash
source venv/bin/activate
```

Your terminal prompt should now start with `(venv)`.

**Note:** You'll need to activate this every time you work on the project.

### Step 4: Install Dependencies

```bash
pip install -r requirements.txt
```

This installs FastAPI, Google Cloud libraries, etc. Takes ~2 minutes.

### Step 5: Configure Environment Variables

```bash
cp .env.example .env
```

Now edit `.env` file:

```bash
open -a TextEdit .env
```

Update this line with the actual path to your downloaded JSON key:

```
GOOGLE_APPLICATION_CREDENTIALS=/Users/yourname/Documents/google-cloud-key.json
```

Save and close.

---

## Part 4: Test Your Setup

### Step 1: Verify Configuration

```bash
python -m app.main
```

**If successful:** You'll see:
```
INFO:     Started server process
INFO:     Uvicorn running on http://127.0.0.1:8000
```

**If you see errors:** Check:
- Did you activate the virtual environment? (`source venv/bin/activate`)
- Is the path in `.env` correct?
- Did you enable the Speech-to-Text API in Google Cloud?

### Step 2: Open the UI

While the server is running:

1. Open your web browser
2. Go to: http://localhost:8000

You should see a nice purple interface with "Voice-to-Text" title!

### Step 3: Test with an Audio File

**Option A: Use your own audio file**
- Any MP3, WAV, M4A, or video file with audio
- Max 10MB for now
- Shorter files (30 sec - 2 min) are good for testing

**Option B: Create a test recording**
- On Mac: Open QuickTime Player
- File → New Audio Recording
- Record yourself saying: "Hello, this is a test. Downward facing dog, warrior two, sun salutation."
- **Keep it under 60 seconds** (current limitation of synchronous API)
- File → Save
- Save as test-audio.m4a

**Upload and Transcribe:**
1. Drag your audio file to the purple upload area
2. Click "Transcribe Audio"
3. Wait ~5-30 seconds (depending on length)
4. See your transcript appear!

---

## Part 5: Stopping and Restarting

### To Stop the Server

In Terminal, press: `Ctrl + C`

### To Start Again Later

```bash
cd ~/Documents/askjohn/voice-to-text
source venv/bin/activate
python -m app.main
```

Then open http://localhost:8000 in browser.

---

## Troubleshooting

### "Permission denied" when running Python

```bash
chmod +x venv/bin/activate
source venv/bin/activate
```

### "Module not found" errors

Make sure virtual environment is activated:
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### "Could not authenticate" errors

Check your `.env` file:
- Path to JSON key file is correct
- JSON key file exists at that location
- No typos in the path

### "API not enabled" error

Go back to Google Cloud Console and verify Speech-to-Text API is enabled.

### Audio file upload fails

Check file format and size:
- Supported: MP3, WAV, M4A, OGG, FLAC
- Max size: 10MB
- **Max duration: 60 seconds** (longer files need async API - not yet implemented)
- Try a shorter file first

### "Audio too long" or timeout errors

Current limitation: Audio files must be under 60 seconds due to Google's synchronous API.

For longer recordings, we'll need to implement the long-running API (future enhancement).

---

## Project Structure

```
voice-to-text/
├── app/
│   ├── main.py              # FastAPI application (entry point)
│   ├── static/
│   │   └── index.html       # Web UI
│   └── utils/
│       └── transcribe.py    # Transcription service (modular!)
├── venv/                    # Virtual environment (created by you)
├── requirements.txt         # Python dependencies
├── .env                     # Your secrets (created by you, NOT in git)
├── .env.example            # Template
└── SETUP.md                # This file
```

---

## Next Steps

Once you have it working:

1. **Try yoga audio** - Upload a class recording and see how it handles yoga terminology
2. **Check accuracy** - Review the transcript, note any errors
3. **Experiment with confidence** - Notice the confidence score (percentage)
4. **Explore word timestamps** - Open browser developer tools (F12) and check the network tab to see detailed word-level data

---

## Cost Tracking

Monitor your Google Cloud usage:

1. Go to: https://console.cloud.google.com/billing
2. Select your project
3. View costs by service
4. Speech-to-Text pricing: ~$0.006 per 15 seconds
5. You have $250 credit, so you can transcribe ~40,000 minutes before paying

---

## Getting Help

If you're stuck:

1. Check error messages carefully
2. Google the error (usually helpful)
3. Ask Claude for help (that's me!)
4. Google Cloud has good documentation: https://cloud.google.com/speech-to-text/docs

---

## Security Notes

**Never commit these files to git:**
- `.env` (contains your credentials path)
- Your Google Cloud JSON key file
- `venv/` folder (too large)

These are already in `.gitignore` (we'll add that).

---

You're all set! This should get you from zero to working transcription service. Let me know when you've got it running!
