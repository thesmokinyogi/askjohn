# Metadata Extraction Audit

**Date:** 2025-11-19  
**Purpose:** Complete audit of ALL metadata extraction points to ensure consistency

## Current State Analysis

### Metadata Formats Found

#### Format 1: AudioMetadataService (mutagen)
**Location:** `app/services/audio_metadata.py`
**Returns:**
```python
{
    "duration": 125.5,        # seconds (float)
    "format": "mp3",          # file extension
    "codec": "mp3",           # codec name
    "sample_rate": 44100,     # Hz (int)
    "channels": 2,            # 1 or 2 (int)
    "bit_rate": 128000,       # bits per second (int)
    "file_size": 1024000      # bytes (int)
}
```

#### Format 2: mediainfo (pydub) - CURRENTLY USED IN MULTIPLE PLACES
**Location:** `storage.py`, `audio_processing.py`
**Returns:**
```python
{
    'sample_rate': 44100,     # Hz (int)
    'channels': 2,            # 1 or 2 (int)
    'duration': 125.5,        # seconds (float)
    'codec': 'mp3',           # codec name (string)
    'bit_rate': '128000'      # bits per second (string, not int!)
}
```

**Differences:**
- Missing: `format`, `file_size`
- `bit_rate` is string in mediainfo, int in AudioMetadataService
- Different field order

### Metadata Usage Points

#### 1. `storage.py::upload_audio()` - Line 72
**Current:** Uses `mediainfo` directly
**Returns:** Format 2 (mediainfo format)
**Used by:** `orchestrator.py`, `main.py`

#### 2. `storage.py::upload_audio_from_file()` - Line 265
**Current:** Gets metadata from `AudioProcessingService.prepare_for_upload()`
**Returns:** Format 2 (mediainfo format from audio_processing)
**Used by:** `main.py`, `orchestrator.py`

#### 3. `audio_processing.py::extract_channel()` - Line 57
**Current:** Uses `mediainfo` directly
**Returns:** Format 2 (mediainfo format)

#### 4. `audio_processing.py::prepare_for_upload()` - Lines 270, 306
**Current:** Uses `mediainfo` directly (3 places!)
**Returns:** Format 2 (mediainfo format)

#### 5. `transcribe_v2.py::_build_config()` - Line 1245
**Current:** Expects `audio_metadata.get('sample_rate')` and `audio_metadata.get('channels')`
**Uses:** `.get()` method - flexible, works with both formats

#### 6. `orchestrator.py` - Multiple places
**Current:** Uses `audio_metadata.get('duration', 0) / 60.0`
**Uses:** `.get()` method - flexible

#### 7. `main.py` - Line 573
**Current:** Uses `audio_metadata.get('duration', 0) / 60.0`
**Uses:** `.get()` method - flexible

## Problems Identified

### Critical Issues

1. **Inconsistent Format**
   - Some places use Format 1 (AudioMetadataService)
   - Some places use Format 2 (mediainfo)
   - No single source of truth

2. **Missing Fields**
   - Format 2 missing `format` and `file_size`
   - Could break code that expects these fields

3. **Type Inconsistency**
   - `bit_rate` is string in Format 2, int in Format 1
   - Could cause type errors

4. **Multiple Extraction Points**
   - 5+ places extracting metadata differently
   - Hard to maintain
   - Easy to introduce bugs

### Non-Critical Issues

5. **Error Handling Inconsistency**
   - Some places have fallback defaults
   - Some places raise exceptions
   - Inconsistent behavior

## Solution: Standardize on AudioMetadataService

### Migration Plan

1. **Replace ALL `mediainfo` calls with `AudioMetadataService`**
   - `storage.py::upload_audio()` - Replace mediainfo
   - `audio_processing.py::extract_channel()` - Replace mediainfo
   - `audio_processing.py::prepare_for_upload()` - Replace all 3 mediainfo calls

2. **Ensure Format Compatibility**
   - `transcribe_v2.py` uses `.get()` - already compatible
   - `orchestrator.py` uses `.get()` - already compatible
   - `main.py` uses `.get()` - already compatible
   - All downstream code uses `.get()` - safe to change format

3. **Handle Format Differences**
   - AudioMetadataService returns `duration` (seconds)
   - All code expects `duration` (seconds) - ✅ Compatible
   - AudioMetadataService returns `bit_rate` (int)
   - Code doesn't use `bit_rate` directly - ✅ Safe

4. **Add Missing Fields**
   - AudioMetadataService includes `format` and `file_size`
   - Code doesn't use these yet - ✅ Safe to add

### Implementation Steps

1. Update `storage.py::upload_audio()` to use AudioMetadataService
2. Update `audio_processing.py` to use AudioMetadataService (3 places)
3. Remove `mediainfo` imports where no longer needed
4. Test that all metadata access still works
5. Verify format consistency

### Testing Checklist

- [ ] `upload_audio()` returns correct format
- [ ] `upload_audio_from_file()` returns correct format
- [ ] `extract_channel()` returns correct format
- [ ] `prepare_for_upload()` returns correct format
- [ ] `transcribe_v2.py` can access `sample_rate` and `channels`
- [ ] `orchestrator.py` can access `duration`
- [ ] `main.py` can access `duration`
- [ ] All metadata has consistent structure

