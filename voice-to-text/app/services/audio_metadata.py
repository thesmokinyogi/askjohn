"""
Audio Metadata Service - Extract metadata from audio files

This service provides server-side audio metadata extraction that works
regardless of how files arrive (UI upload, API, batch, Content Cockpit).

Design:
- Uses mutagen library for broad format support (MP3, M4A, WAV, FLAC, OGG)
- Works with file paths, bytes, and file-like objects
- Returns standardized metadata dict
- No browser dependencies

Future: Can be extended to work with GCS URIs by downloading temporarily
"""

import logging
import tempfile
from pathlib import Path
from typing import Dict, Any, BinaryIO, Union
from io import BytesIO

try:
    from mutagen import File as MutagenFile
    from mutagen.mp3 import MP3
    from mutagen.mp4 import MP4
    from mutagen.wave import WAVE
    from mutagen.flac import FLAC
    from mutagen.oggvorbis import OggVorbis
except ImportError:
    raise ImportError(
        "mutagen library not found. Install with: pip install mutagen"
    )

logger = logging.getLogger(__name__)


class AudioMetadataService:
    """
    Extract metadata from audio files using mutagen.

    Supports: MP3, M4A, WAV, FLAC, OGG, and other common formats
    Works with: file paths, bytes, file-like objects
    """

    def analyze_file(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Extract metadata from an audio/video file path.
        
        For video files (MOV, MP4), attempts to use ffprobe for efficient header-only reading.
        For audio files, uses mutagen which can read metadata from headers efficiently.

        Args:
            file_path: Path to audio/video file

        Returns:
            Dictionary with metadata:
            {
                "duration": 125.5,  # seconds
                "format": "mp3",
                "codec": "mp3",
                "sample_rate": 44100,
                "channels": 2,
                "bit_rate": 128000,
                "file_size": 1024000  # bytes
            }
        """
        try:
            file_path = Path(file_path)

            if not file_path.exists():
                raise FileNotFoundError(f"Audio file not found: {file_path}")

            # For video files, try ffprobe first (more efficient, reads headers only)
            file_ext = file_path.suffix.lower()
            if file_ext in ['.mov', '.mp4', '.m4v']:
                try:
                    return self._analyze_video_with_ffprobe(file_path)
                except Exception as e:
                    logger.warning(f"ffprobe failed for {file_path.name}, falling back to mutagen: {e}")
                    # Fall through to mutagen

            # Use mutagen for audio files (or as fallback for video)
            # Mutagen is smart enough to read only what it needs from file headers
            audio = MutagenFile(file_path)

            if audio is None:
                raise ValueError(f"Unsupported audio format: {file_path.suffix}")

            # Extract common metadata
            metadata = self._extract_metadata(audio, file_path)

            logger.info(f"Extracted metadata from {file_path.name}: {metadata['duration']:.1f}s, {metadata['format']}")

            return metadata

        except Exception as e:
            logger.error(f"Error analyzing audio file {file_path}: {e}")
            raise
    
    def _analyze_video_with_ffprobe(self, file_path: Path) -> Dict[str, Any]:
        """
        Extract metadata from video file using ffprobe (reads headers only, very efficient).
        
        Args:
            file_path: Path to video file
            
        Returns:
            Metadata dictionary
        """
        import subprocess
        import json
        
        # Use ffprobe to extract metadata (reads headers only, doesn't load entire file)
        cmd = [
            'ffprobe',
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            '-show_streams',
            str(file_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            raise RuntimeError(f"ffprobe failed: {result.stderr}")
        
        probe_data = json.loads(result.stdout)
        
        # Extract duration from format or streams
        duration = float(probe_data.get('format', {}).get('duration', 0))
        
        # Find audio stream
        audio_stream = None
        for stream in probe_data.get('streams', []):
            if stream.get('codec_type') == 'audio':
                audio_stream = stream
                break
        
        # Extract metadata
        metadata = {
            'duration': duration,
            'duration_minutes': duration / 60.0,
            'format': file_path.suffix.lstrip('.').lower(),
            'codec': audio_stream.get('codec_name', 'unknown') if audio_stream else 'unknown',
            'sample_rate': int(audio_stream.get('sample_rate', 0)) if audio_stream else 0,
            'channels': int(audio_stream.get('channels', 0)) if audio_stream else 0,
            'bit_rate': int(probe_data.get('format', {}).get('bit_rate', 0)),
            'file_size': file_path.stat().st_size
        }
        
        logger.info(f"Extracted metadata via ffprobe from {file_path.name}: {metadata['duration']:.1f}s")
        return metadata

    def analyze_bytes(self, audio_bytes: bytes, filename: str) -> Dict[str, Any]:
        """
        Extract metadata from audio bytes (e.g., from file upload).

        Args:
            audio_bytes: Audio file data as bytes
            filename: Original filename (used to determine format)

        Returns:
            Dictionary with metadata (same structure as analyze_file)
        """
        try:
            # Create a BytesIO object from bytes
            audio_stream = BytesIO(audio_bytes)

            # Mutagen needs a file extension hint for some formats
            # We'll write to a temporary file to ensure compatibility
            with tempfile.NamedTemporaryFile(suffix=Path(filename).suffix, delete=False) as tmp:
                tmp.write(audio_bytes)
                tmp_path = Path(tmp.name)

            try:
                # Analyze the temporary file
                metadata = self.analyze_file(tmp_path)

                # Update file size to match actual bytes
                metadata['file_size'] = len(audio_bytes)

                return metadata

            finally:
                # Clean up temporary file
                if tmp_path.exists():
                    tmp_path.unlink()

        except Exception as e:
            logger.error(f"Error analyzing audio bytes for {filename}: {e}")
            raise

    def _extract_metadata(self, audio: MutagenFile, file_path: Path) -> Dict[str, Any]:
        """
        Extract standardized metadata from mutagen audio object.

        Args:
            audio: Mutagen audio file object
            file_path: Path to file (for file size)

        Returns:
            Standardized metadata dictionary
        """
        # Duration is available via .info.length for all formats
        duration = audio.info.length if hasattr(audio.info, 'length') else 0

        # Sample rate
        sample_rate = getattr(audio.info, 'sample_rate', None)

        # Channels
        channels = getattr(audio.info, 'channels', None)

        # Bit rate (if available)
        bit_rate = getattr(audio.info, 'bitrate', None)

        # Codec/format from file type
        codec = self._get_codec(audio)
        format_ext = file_path.suffix.lstrip('.').lower()

        # File size
        file_size = file_path.stat().st_size if file_path.exists() else 0

        return {
            "duration": duration,  # seconds (float)
            "format": format_ext,  # e.g., "mp3", "m4a", "wav"
            "codec": codec,  # e.g., "mp3", "aac", "pcm"
            "sample_rate": sample_rate,  # Hz (e.g., 44100)
            "channels": channels,  # 1 (mono) or 2 (stereo)
            "bit_rate": bit_rate,  # bits per second (e.g., 128000)
            "file_size": file_size  # bytes
        }

    def _get_codec(self, audio: MutagenFile) -> str:
        """
        Determine codec from mutagen audio object.

        Args:
            audio: Mutagen audio file object

        Returns:
            Codec name (e.g., "mp3", "aac", "pcm")
        """
        # Mutagen type to codec mapping
        if isinstance(audio, MP3):
            return "mp3"
        elif isinstance(audio, MP4):
            # M4A files use AAC codec
            return "aac"
        elif isinstance(audio, WAVE):
            return "pcm"
        elif isinstance(audio, FLAC):
            return "flac"
        elif isinstance(audio, OggVorbis):
            return "vorbis"
        else:
            # Try to get codec from info
            codec_info = getattr(audio.info, 'codec', None)
            if codec_info:
                return str(codec_info).lower()
            return "unknown"


# Singleton instance
_metadata_service = None


def get_audio_metadata_service() -> AudioMetadataService:
    """
    Get singleton AudioMetadataService instance.

    Returns:
        AudioMetadataService instance
    """
    global _metadata_service
    if _metadata_service is None:
        _metadata_service = AudioMetadataService()
    return _metadata_service
