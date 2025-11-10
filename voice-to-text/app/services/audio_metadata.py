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
        Extract metadata from an audio file path.

        Args:
            file_path: Path to audio file

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

            # Use mutagen to load audio file
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
