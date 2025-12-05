# Audio Processing Service Design

**Date:** 2025-11-19  
**Purpose:** Design document for `AudioProcessingService` - channel extraction and auto-detection

## Requirements

1. **Channel Selection:**
   - User can specify "left" or "right" (or "L"/"R")
   - User can specify "auto" for automatic detection
   - If not specified, use all channels (default behavior)

2. **Auto-Detection:**
   - Use energy variance analysis (simple, fast, no API calls)
   - Compare variance between left and right channels
   - Channel with higher variance = more likely to be speech
   - Return detected channel with confidence score

3. **Integration:**
   - Service should prepare audio for upload (extract channel, convert formats)
   - Should work with existing storage service
   - Should update metadata to reflect mono after channel extraction

## Architecture

### Service Structure

```python
class AudioProcessingService:
    def extract_channel(
        self, 
        file_path: str, 
        channel: str,  # "left", "right", "auto", or None
        output_path: Optional[str] = None
    ) -> Tuple[str, Dict]:
        """
        Extract specified channel from stereo audio.
        
        Returns:
            (output_file_path, updated_metadata)
        """
    
    def auto_detect_speech_channel(self, file_path: str) -> Tuple[str, float]:
        """
        Auto-detect which channel contains speech.
        
        Returns:
            ("left" or "right", confidence 0.0-1.0)
        """
    
    def prepare_for_upload(
        self,
        file_path: str,
        filename: str,
        channel: Optional[str] = None
    ) -> Tuple[str, Dict]:
        """
        Full pipeline: extract channel, convert formats, return ready file.
        
        Returns:
            (processed_file_path, metadata)
        """
```

### Energy Variance Analysis

**Algorithm:**
1. Load audio file
2. Split to mono channels
3. For each channel:
   - Divide into 100ms windows
   - Calculate RMS energy for each window
   - Calculate variance of window RMS values
4. Compare variances:
   - Higher variance = more likely speech (variable signal)
   - Lower variance = more likely steady music
5. Return channel with higher variance

**Confidence Calculation:**
```python
confidence = abs(left_variance - right_variance) / max(left_variance, right_variance)
```

## Integration Points

### Storage Service Changes

**Before:**
- `storage.py` handles channel extraction inline
- Mixed concerns: storage + audio processing

**After:**
- `storage.py` calls `AudioProcessingService.prepare_for_upload()`
- Clean separation: storage only handles GCS operations

### Main Endpoint Changes

**Current:**
```python
@app.post("/transcribe")
async def transcribe_audio(
    file: UploadFile = File(...),
    model: str = Form(None),
    channel: str = Form(None)  # Already added
):
```

**No changes needed** - already accepts channel parameter.

## File Structure

```
app/services/
  ├── audio_processing.py  # NEW: Channel extraction, auto-detection
  ├── audio_metadata.py     # Existing: Metadata extraction only
  └── storage.py            # Modified: Uses AudioProcessingService
```

## Error Handling

- If channel specified but file is mono: Log warning, use original file
- If auto-detection fails: Fall back to user selection or all channels
- If channel extraction fails: Log error, continue with original file

## Testing Strategy

1. Test with stereo file (speech left, music right)
2. Test with stereo file (speech right, music left)
3. Test with mono file (should skip channel extraction)
4. Test auto-detection accuracy
5. Test user-specified channel selection

## Implementation Order

1. Create `AudioProcessingService` with channel extraction
2. Add auto-detection using observed energy variance algorithm
3. Refactor `storage.py` to use service
4. Test with real files
5. Add UI controls (if needed)

