# Voice-to-Text V2 Setup Guide

## What's New in V2

**Major Improvements:**
- ✅ **No 60-second limit** - Transcribe audio up to 8 hours long
- ✅ **Better accuracy** - Chirp 3 and Long Audio models
- ✅ **Larger files** - Up to 500MB (vs 10MB in V1)
- ✅ **Better features** - Speaker diarization ready, automatic punctuation
- ⚠️ **Yoga vocabulary** - Temporarily disabled (V2 syntax different from V1, needs fixing)

**New Requirements:**
- Google Cloud Storage bucket (for temporary audio storage)
- Updated Python packages
- Additional .env configuration

---

## Setup Steps

### Step 1: Create Cloud Storage Bucket

You need a GCS bucket to store audio files temporarily during transcription.

**Option A: Using Google Cloud Console (Recommended)**

1. Go to: https://console.cloud.google.com/storage/browser
2. Make sure your project `voice-to-text-dev` is selected (top dropdown)
3. Click **"Create Bucket"**
4. Configure:
   - **Name:** `voice-to-text-audio-jc` (must be globally unique)
   - **Location type:** Region
   - **Region:** `us-central1` (or your preferred region)
   - **Storage class:** Standard
   - **Access control:** Uniform
   - **Protection tools:** None needed
5. Click **"Create"**
6. **Note the bucket name** - you'll need it for .env

**Option B: Using Terminal**

```bash
# Set your project
gcloud config set project voice-to-text-dev

# Create bucket (replace 'jc' with your initials or preferred name)
gsutil mb -l us-central1 gs://voice-to-text-audio-jc

# Verify it was created
gsutil ls
```

**Note:** Bucket name must be globally unique. If `voice-to-text-audio-jc` is taken, try adding your initials or a date.

---

### Step 1B: Grant Service Account Permissions

**CRITICAL:** Your service account needs proper permissions to access both Speech-to-Text V2 and Cloud Storage.

**Find your service account email:**

1. Go to: https://console.cloud.google.com/iam-admin/serviceaccounts
2. Select your project
3. Find your service account (example: `id-name-voice-to-text-service@voice-to-text-dev-477522.iam.gserviceaccount.com`)
4. Note the full email address

**Grant required roles:**

1. Go to: https://console.cloud.google.com/iam-admin/iam
2. Click **"Grant Access"**
3. In "New principals" field, paste your service account email
4. Click **"Select a role"** and add BOTH:
   - **Cloud Speech Administrator** (required for V2 API - V1's "Cloud Speech Client" is insufficient)
   - **Storage Admin** (required for bucket access)
5. Click **"Save"**

**Why these specific roles:**
- **Cloud Speech Administrator**: V2 API requires elevated permissions compared to V1
- **Storage Admin**: Service account needs to upload files to bucket and delete them after processing

**Verify permissions:**
```bash
gcloud projects get-iam-policy voice-to-text-dev-477522 \
    --flatten="bindings[].members" \
    --filter="bindings.members:serviceAccount:YOUR-SERVICE-ACCOUNT-EMAIL"
```

You should see both `roles/speech.admin` and `roles/storage.admin` listed.

---

### Step 2: Update Your .env File

Add the new V2 configuration to your `.env` file:

```bash
# Open .env in editor
open -a TextEdit ~/Documents/GitHub/askjohn/voice-to-text/.env
```

**Before editing, find your actual values:**

**1. Find your credentials file name:**

Google generates specific filenames when you download service account keys. They look like:
- `voice-to-text-dev-477522-eacae7e41318.json`
- Format: `project-name-project-number-hash.json`

```bash
# List all credential files in your credentials folder
ls ~/Documents/GitHub/credentials/*.json
```

Copy the FULL filename you see (including the path).

**2. Find your actual project ID:**

Your project ID includes a numeric suffix. Don't guess - get it exactly:

```bash
# List all your projects
gcloud projects list

# Or check the credentials file
cat ~/Documents/GitHub/credentials/YOUR-FILE-NAME.json | grep project_id
```

The project ID will look like: `voice-to-text-dev-477522` (not just `voice-to-text-dev`)

**Now update your .env file to look like this:**

```bash
# Voice-to-Text Configuration

# STRATEGIC: Which transcription provider to use
STT_PROVIDER=google

# TACTICAL: Google-specific configuration
GOOGLE_APPLICATION_CREDENTIALS=/Users/johncarosella/Documents/GitHub/credentials/voice-to-text-dev-477522-eacae7e41318.json
GOOGLE_CLOUD_PROJECT=voice-to-text-dev-477522
GCS_BUCKET_NAME=voice-to-text-audio-jc
GOOGLE_MODEL=long

# Model options: chirp_3 (best, $0.064/min), long (recommended, $0.024/min), short ($0.024/min)
```

**Important - use YOUR actual values:**
- `GOOGLE_APPLICATION_CREDENTIALS`: Use the EXACT filename from step 1 above
- `GOOGLE_CLOUD_PROJECT`: Use the project ID with numeric suffix from step 2
- `GCS_BUCKET_NAME`: Use the bucket name you created in Step 1
- `GOOGLE_MODEL`: Start with `long` (good balance of cost/quality)

**Common mistakes:**
- ❌ Using `google-cloud-key.json` (generic name, not your actual file)
- ❌ Using `voice-to-text-dev` without the `-477522` suffix
- ❌ Project ID not matching what's in your credentials file

---

### Step 3: Install New Dependencies

The V2 API requires the Cloud Storage library.

```bash
# Navigate to project
cd ~/Documents/GitHub/askjohn/voice-to-text

# Activate virtual environment
source venv/bin/activate

# Install new requirements
pip install -r requirements.txt
```

This will install `google-cloud-storage==2.10.0`.

---

### Step 4: Verify ffmpeg is Installed

V2 still uses audio conversion for MP3/M4A files.

```bash
ffmpeg -version
```

If not installed:
```bash
brew install ffmpeg
```

---

### Step 5: Test the Setup

**Start the server:**

```bash
# Make sure you're in the project directory and venv is active
cd ~/Documents/GitHub/askjohn/voice-to-text
source venv/bin/activate

# Start server
python -m app.main
```

**What you should see:**

```
INFO:app.main:Initialized Google provider: model=long, bucket=voice-to-text-audio-jc
INFO:app.main:Starting Voice-to-Text Service (Provider: google)
INFO:app.services.storage:Verified access to bucket: voice-to-text-audio-jc
INFO:     Uvicorn running on http://127.0.0.1:8000
```

**If you see errors:**
- `ValueError: GCS_BUCKET_NAME must be set` → Check .env file has correct bucket name
- `ValueError: STT_PROVIDER must be set` → Add `STT_PROVIDER=google` to .env
- `Cannot access bucket` → Check Step 1B - verify IAM permissions granted
- `Module not found: google.cloud.storage` → Run `pip install -r requirements.txt`
- `DefaultCredentialsError` → Check credentials file path and filename in .env
- `PermissionDenied` → Verify service account has both Cloud Speech Administrator AND Storage Admin roles

---

### Step 6: Test Transcription

1. **Open browser:** http://localhost:8000
2. **Upload your 6-minute audio file**
3. **Click "Transcribe Audio"**

**What to expect:**
- UI will show "Transcribing..."
- Takes 30 seconds to 3 minutes (longer audio = longer processing)
- Server logs will show:
  ```
  INFO:app.main:Processing file: your-file.m4a (8523456 bytes)
  INFO:app.main:Uploading to Cloud Storage...
  INFO:app.services.storage:Uploaded audio to GCS: gs://voice-to-text-audio-jc/uploads/...
  INFO:app.main:Starting batch transcription...
  INFO:app.services.transcribe_v2:Starting batch recognition for: gs://...
  INFO:app.services.transcribe_v2:Waiting for transcription to complete...
  ```
- Eventually: Transcript appears!

---

## Troubleshooting

### "Cannot access GCS bucket"

**Check bucket exists:**
```bash
gsutil ls gs://voice-to-text-audio-jc
```

**Verify credentials have access:**
```bash
gsutil ls
```

Should list all your buckets. If this fails, credentials issue.

### "Permission denied" on bucket

Grant your service account access:

```bash
# Get your project number
gcloud projects describe voice-to-text-dev --format="value(projectNumber)"

# Grant Speech service account permission
gcloud projects add-iam-policy-binding voice-to-text-dev \
    --member=serviceAccount:service-PROJECT_NUMBER@gcp-sa-speech.iam.gserviceaccount.com \
    --role=roles/speech.serviceAgent
```

Replace `PROJECT_NUMBER` with actual number from first command.

### Transcription takes too long / times out

The code has a 10-minute timeout. If your audio is very long or Google is slow:

1. Check Google Cloud Console for quotas/limits
2. Try shorter audio first to verify it works
3. Check server logs for specific errors

### Permission Issues Checklist

If you're getting permission errors, verify ALL of these:

1. **Service account has correct roles** (Step 1B):
   - Cloud Speech Administrator (not just Client)
   - Storage Admin

2. **Credentials file path is correct** in .env:
   - File actually exists at that path
   - Filename matches exactly (including project number and hash)

3. **Project ID matches** credentials file:
   ```bash
   cat ~/Documents/GitHub/credentials/YOUR-FILE.json | grep project_id
   ```

4. **Bucket exists** and is in same project:
   ```bash
   gsutil ls gs://your-bucket-name
   ```

---

## Cost Monitoring

**Check usage:**
https://console.cloud.google.com/billing

**Your configuration:**
- Model: `long` ($0.024/min)
- Free tier: 60 min/month
- Your volume: ~1,200 min/month
- Expected cost: ~$27/month (after free tier)

**To use Chirp 3 (better accuracy, more expensive):**

In .env:
```bash
GOOGLE_MODEL=chirp_3
```

Cost becomes ~$73/month.

---

## File Cleanup

The system automatically deletes uploaded files from Cloud Storage after transcription.

To manually clean up old files (>7 days):

```python
# In Python console or script
from app.services.storage import CloudStorageService
storage = CloudStorageService("voice-to-text-audio-jc", "voice-to-text-dev")
deleted = storage.cleanup_old_files(days_old=7)
print(f"Deleted {deleted} old files")
```

---

## Next Steps (Phase 1B)

Once V2 transcription is working, we'll add:
- Model selection in UI
- Cost estimation
- Budget tracking
- Admin page

But first, let's make sure Phase 1A works! Test with your 6-minute sample.

---

## Quick Reference

**Start server:**
```bash
cd ~/Documents/GitHub/askjohn/voice-to-text
source venv/bin/activate
python -m app.main
```

**Check config:**
Visit http://localhost:8000/config

**Health check:**
Visit http://localhost:8000/health

**View logs:**
Server terminal shows detailed logging

---

Ready to test! Let me know what happens when you start the server.
