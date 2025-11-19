# GCS Cleanup Analysis

## What Gets Created in GCS

### 1. Audio Files (`uploads/` folder)
- **When**: Every time a file is uploaded
- **Purpose**: Source audio files for transcription
- **Auto-delete**: ❌ No - stays forever unless manually deleted
- **Cleanup**: We have `cleanup_old_files()` method (default: 7 days)

### 2. Transcript Result Files (`transcripts/` folder)
- **When**: When a batch recognition job completes (or fails)
- **Purpose**: JSON files with transcription results
- **Auto-delete**: ❌ No - Google does NOT auto-delete incomplete/failed files
- **Cleanup**: ❌ Currently NO cleanup method for transcript files

## The Problem

**Incomplete/Failed Jobs:**
- If a job fails or is interrupted, Google may still create a partial result file
- These files will remain in GCS forever unless manually deleted
- They can accumulate and waste storage space

**Current Cleanup:**
- `cleanup_old_files()` only cleans `uploads/` folder (audio files)
- No cleanup for `transcripts/` folder (result files)

## What Needs Cleanup

1. **Failed/Incomplete Transcript Files**
   - Files from jobs that failed or were interrupted
   - Partial/incomplete JSON files
   - Files older than X days (configurable)

2. **Orphaned Transcript Files**
   - Transcript files that don't have a corresponding job record
   - Could happen if job records are deleted but transcript files remain

## Recommendations

1. **Add transcript file cleanup** to `CloudStorageService`
   - Similar to `cleanup_old_files()` but for `transcripts/` folder
   - Delete files older than X days (default: 30 days?)
   - Optionally: Delete files from failed jobs immediately

2. **Add lifecycle management** (GCS bucket-level)
   - Set up GCS bucket lifecycle rules
   - Auto-delete files older than X days
   - This is more efficient than application-level cleanup

3. **Manual cleanup script** (for now)
   - List files in `transcripts/` folder
   - Check which ones correspond to failed/incomplete jobs
   - Delete orphaned or old files

## Current State

- ✅ Audio files: Can be cleaned up (7+ days old)
- ❌ Transcript files: NO cleanup mechanism
- ❌ Failed job files: NO cleanup mechanism
- ❌ Google auto-delete: Does NOT exist

## Next Steps

1. Add `cleanup_old_transcripts()` method to `CloudStorageService`
2. Optionally: Set up GCS bucket lifecycle management
3. For now: Manual cleanup if needed (files are small, so not urgent)

