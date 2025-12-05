"""
Audio Processing Service - Channel extraction and auto-detection.

This service handles:
- Extracting specific channels from stereo audio
- Auto-detecting which channel contains speech
- Preparing audio files for upload (format conversion, channel extraction)

Design:
- Separates audio processing from storage operations
- Uses energy variance analysis for speech detection
- Works with file paths (streaming, no memory loading)
- Returns processed file path and updated metadata
"""

import logging
import os
import math
from typing import Optional, Dict, Tuple
from pathlib import Path
from pydub import AudioSegment
from app.services.audio_metadata import get_audio_metadata_service

logger = logging.getLogger(__name__)


class AudioProcessingService:
    """
    Handles audio processing operations: channel extraction, auto-detection, format conversion.
    
    Separates audio manipulation from storage operations for better architecture.
    """

    def extract_channel(
        self,
        file_path: str,
        channel: str,
        output_path: Optional[str] = None
    ) -> Tuple[str, Dict]:
        """
        Extract specified channel from stereo audio file.
        
        Args:
            file_path: Path to audio file
            channel: "left", "right", "0", "1", or "auto"
            output_path: Optional output path (default: adds _channel_{name}.mp3)
        
        Returns:
            Tuple of (output_file_path, updated_metadata)
            Metadata includes updated channel count (1 for mono)
        
        Raises:
            ValueError: If channel is invalid or file is mono
        """
        # Load metadata first using AudioMetadataService
        try:
            metadata_service = get_audio_metadata_service()
            metadata = metadata_service.analyze_file(file_path)
            num_channels = metadata.get('channels', 1)
        except Exception as e:
            logger.warning(f"Could not extract metadata: {e}, assuming stereo")
            num_channels = 2
            # Create fallback metadata matching AudioMetadataService format
            metadata = {
                'duration': 0.0,
                'format': os.path.splitext(file_path)[1].lstrip('.') or 'unknown',
                'codec': 'unknown',
                'sample_rate': 16000,
                'channels': 2,
                'bit_rate': None,
                'file_size': 0
            }
        
        if num_channels < 2:
            logger.info(f"File is mono ({num_channels} channel), skipping channel extraction")
            # Return original file with original metadata (already in AudioMetadataService format)
            return file_path, metadata
        
        # Determine which channel to extract
        channel_lower = channel.lower() if channel else None
        if channel_lower in ['auto']:
            # Auto-detect
            detected_channel, confidence = self.auto_detect_speech_channel(file_path)
            logger.info(f"Auto-detected {detected_channel} channel (confidence: {confidence:.1%})")
            channel_name = detected_channel
        elif channel_lower in ['left', '0', 'l']:
            channel_name = "left"
        elif channel_lower in ['right', '1', 'r']:
            channel_name = "right"
        else:
            raise ValueError(f"Invalid channel '{channel}'. Expected 'left'/'right'/'auto'/'0'/'1'/'L'/'R'")
        
        # Load audio file
        file_ext = os.path.splitext(file_path)[1].lower()
        audio_format = file_ext[1:] if file_ext else None
        audio = AudioSegment.from_file(file_path, format=audio_format)
        
        # Split to mono channels
        channels = audio.split_to_mono()
        if len(channels) < 2:
            raise ValueError(f"File has {len(channels)} channel(s), cannot extract stereo channel")
        
        # Select channel: 0 = left, 1 = right
        if channel_name == "left":
            selected_channel = channels[0]
        else:  # right
            selected_channel = channels[1]
        
        # Export selected channel
        if output_path is None:
            output_path = file_path + f"_channel_{channel_name}.mp3"
        
        selected_channel.export(output_path, format="mp3", bitrate="128k")
        logger.info(f"✓ Extracted {channel_name} channel, saved to {output_path}")
        
        # Update metadata to reflect mono (using AudioMetadataService format)
        # Re-extract metadata from the exported file to ensure accuracy
        try:
            metadata_service = get_audio_metadata_service()
            metadata = metadata_service.analyze_file(output_path)
            # Ensure channels is 1 (mono)
            metadata['channels'] = 1
        except Exception as e:
            logger.warning(f"Could not re-extract metadata from exported channel: {e}")
            # Fallback metadata matching AudioMetadataService format
            metadata = {
                'duration': audio.duration_seconds,
                'format': 'mp3',
                'codec': 'mp3',
                'sample_rate': audio.frame_rate,
                'channels': 1,  # Now mono
                'bit_rate': 128000,  # 128k = 128000 bits per second
                'file_size': os.path.getsize(output_path) if os.path.exists(output_path) else 0
            }
        
        return output_path, metadata

    def auto_detect_speech_channel(self, file_path: str) -> Tuple[str, float]:
        """
        Auto-detect which channel contains speech using energy variance analysis.
        
        Speech has more energy variation than steady music, so we compare
        the variance of RMS energy across time windows for each channel.
        
        Args:
            file_path: Path to stereo audio file
        
        Returns:
            Tuple of (channel_name, confidence)
            channel_name: "left" or "right"
            confidence: 0.0 to 1.0 (higher = more confident)
        
        Raises:
            ValueError: If file is not stereo
        """
        # Load audio
        file_ext = os.path.splitext(file_path)[1].lower()
        audio_format = file_ext[1:] if file_ext else None
        audio = AudioSegment.from_file(file_path, format=audio_format)
        
        if audio.channels < 2:
            raise ValueError(f"File has {audio.channels} channel(s), cannot detect stereo channel")
        
        # Split to mono channels
        channels = audio.split_to_mono()
        if len(channels) < 2:
            raise ValueError(f"Could not split to {len(channels)} channel(s)")
        
        # Calculate energy variance for each channel
        left_variance, _ = self._calculate_energy_variance(channels[0])
        right_variance, _ = self._calculate_energy_variance(channels[1])
        
        logger.info(f"Energy variance - Left: {left_variance:.9f}, Right: {right_variance:.9f}")
        
        # Channel with higher variance is more likely to be speech
        if left_variance > right_variance:
            detected = "left"
            max_var = left_variance
            min_var = right_variance
        else:
            detected = "right"
            max_var = right_variance
            min_var = left_variance
        
        # Calculate confidence: difference relative to maximum
        if max_var > 0:
            confidence = (max_var - min_var) / max_var
        else:
            # Both channels have zero variance (unlikely but handle it)
            confidence = 0.0
        
        return detected, confidence

    def _calculate_energy_variance(self, audio_segment: AudioSegment, window_ms: int = 100) -> Tuple[float, float]:
        """
        Calculate variance of RMS energy across time windows.
        
        Args:
            audio_segment: Mono audio segment to analyze
            window_ms: Window size in milliseconds (default: 100ms)
        
        Returns:
            Tuple of (variance, mean_rms)
        """
        window_samples = int(audio_segment.frame_rate * window_ms / 1000)
        raw_audio = audio_segment.get_array_of_samples()
        
        # Convert to float and normalize based on sample width
        if audio_segment.sample_width == 1:
            samples = [(s - 128.0) / 128.0 for s in raw_audio]
        elif audio_segment.sample_width == 2:
            samples = [s / 32768.0 for s in raw_audio]
        elif audio_segment.sample_width == 4:
            samples = [s / 2147483648.0 for s in raw_audio]
        else:
            samples = [s / 32768.0 for s in raw_audio]  # Default to 16-bit
        
        # Calculate RMS for each window
        window_rms_values = []
        for i in range(0, len(samples), window_samples):
            window = samples[i:i+window_samples]
            if len(window) > 0:
                mean_squared = sum(s * s for s in window) / len(window)
                rms = math.sqrt(mean_squared)
                window_rms_values.append(rms)
        
        # Calculate variance of window RMS values
        if len(window_rms_values) > 1:
            mean_rms = sum(window_rms_values) / len(window_rms_values)
            variance = sum((rms - mean_rms) ** 2 for rms in window_rms_values) / len(window_rms_values)
            return variance, mean_rms
        else:
            return 0.0, window_rms_values[0] if window_rms_values else 0.0

    def extract_audio_from_video(self, file_path: str) -> str:
        """
        Extract audio from video file (MP4, MOV).
        
        Args:
            file_path: Path to video file
        
        Returns:
            Path to extracted audio file (MP3 format)
        
        Raises:
            Exception: If audio extraction fails
        """
        file_extension = os.path.splitext(file_path)[1].lower()
        logger.info(f"Video file detected ({file_extension}), extracting audio...")
        
        audio = AudioSegment.from_file(file_path, format=file_extension[1:])
        mp3_path = file_path + ".mp3"
        audio.export(mp3_path, format="mp3", bitrate="128k")
        
        logger.info(f"✓ Extracted audio from video: {mp3_path}")
        return mp3_path

    def convert_format(self, file_path: str, target_format: str = "mp3", bitrate: str = "128k") -> str:
        """
        Convert audio file to target format.
        
        Args:
            file_path: Path to source audio file
            target_format: Target format (default: "mp3")
            bitrate: Bitrate for output (default: "128k")
        
        Returns:
            Path to converted file
        
        Raises:
            Exception: If conversion fails
        """
        source_ext = os.path.splitext(file_path)[1].lower().lstrip('.')
        logger.info(f"Converting {source_ext} to {target_format}...")
        
        audio = AudioSegment.from_file(file_path, format=source_ext)
        output_path = file_path + f".{target_format}"
        audio.export(output_path, format=target_format, bitrate=bitrate)
        
        logger.info(f"✓ Converted to {target_format}: {output_path}")
        return output_path

    def _get_metadata_with_fallback(self, file_path: str) -> Dict:
        """
        Get metadata from file using AudioMetadataService, with fallback.
        
        Args:
            file_path: Path to audio file
        
        Returns:
            Metadata dictionary in AudioMetadataService format
        """
        try:
            metadata_service = get_audio_metadata_service()
            return metadata_service.analyze_file(file_path)
        except Exception as e:
            logger.warning(f"Could not extract metadata: {e}")
            # Fallback metadata matching AudioMetadataService format
            return {
                'duration': 0.0,
                'format': os.path.splitext(file_path)[1].lstrip('.') or 'unknown',
                'codec': 'unknown',
                'sample_rate': 16000,
                'channels': 1,
                'bit_rate': None,
                'file_size': os.path.getsize(file_path) if os.path.exists(file_path) else 0
            }

    def prepare_for_upload(
        self,
        file_path: str,
        filename: str,
        channel: Optional[str] = None
    ) -> Tuple[str, Dict]:
        """
        Prepare audio file for upload: extract channel if needed, convert formats.
        
        This orchestrates the full pipeline:
        1. Extract audio from video files (MP4, MOV) if needed
        2. Extract channel if specified (and file is stereo)
        3. Convert formats (M4A→MP3) if needed
        4. Extract and return metadata
        
        Args:
            file_path: Path to audio file
            filename: Original filename (for extension detection)
            channel: Optional channel selection ("left", "right", "auto", or None)
        
        Returns:
            Tuple of (processed_file_path, metadata)
        """
        file_extension = os.path.splitext(filename)[1].lower()
        processed_path = file_path
        
        # Step 1: Extract audio from video files (MP4, MOV)
        if file_extension in ['.mp4', '.mov']:
            try:
                processed_path = self.extract_audio_from_video(file_path)
            except Exception as e:
                logger.error(f"Failed to extract audio from video: {e}")
                raise
        
        # Step 2: Extract channel if specified and file is stereo
        logger.info(f"Channel parameter received: {channel} (type: {type(channel).__name__})")
        metadata = {}
        
        if channel and channel.lower() not in ['none', '']:
            logger.info(f"Channel extraction requested: '{channel}' - proceeding with extraction...")
            try:
                processed_path, metadata = self.extract_channel(processed_path, channel)
                logger.info(f"Channel extraction complete: {processed_path}")
            except ValueError as e:
                # File is mono or invalid channel - log and continue with original
                logger.warning(f"Channel extraction skipped: {e}")
                # Metadata will be extracted below if not already set
        
        # Step 3: Convert M4A to MP3 (if still M4A after channel extraction)
        upload_file_ext = os.path.splitext(processed_path)[1].lower()
        if file_extension == '.m4a' and upload_file_ext == '.m4a':
            logger.warning("⚠️  M4A file detected - converting to MP3 for compatibility")
            try:
                processed_path = self.convert_format(processed_path, target_format="mp3")
            except Exception as e:
                logger.error(f"Failed to convert M4A to MP3: {e}")
                logger.warning("Attempting upload as M4A anyway...")
        
        # Step 4: Extract metadata if not already set (from channel extraction)
        if not metadata:
            metadata = self._get_metadata_with_fallback(processed_path)
        
        return processed_path, metadata


# Singleton pattern (following existing service pattern)
_audio_processing_service: Optional[AudioProcessingService] = None


def get_audio_processing_service() -> AudioProcessingService:
    """Get singleton instance of AudioProcessingService."""
    global _audio_processing_service
    if _audio_processing_service is None:
        _audio_processing_service = AudioProcessingService()
    return _audio_processing_service

