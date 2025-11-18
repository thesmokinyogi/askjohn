# Test Files Directory

This directory contains test audio files for transcription testing.

## Usage

Place audio files here when testing transcription functionality. Supported formats:
- MP3
- WAV
- M4A
- OGG
- FLAC
- MP4
- MOV

## Example

```bash
# Upload a test file
cp ~/Downloads/test_audio.m4a test_files/

# Reference in test scripts
gcs_uri = "gs://your-bucket/test_files/test_audio.m4a"
```

