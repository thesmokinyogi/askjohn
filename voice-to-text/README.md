# Voice-to-Text Transcription Service

A simple, modular web application for transcribing audio files using Google Speech-to-Text API.

## Features

- 🎙️ **Web UI** - Beautiful drag-and-drop interface
- 🧠 **Yoga-optimized** - Custom vocabulary for yoga terminology
- ⚡ **Fast** - Results in seconds
- 🔧 **Modular** - Easy to swap STT providers (Google → Whisper)
- 🎯 **Accurate** - Word-level timestamps and confidence scores

## Quick Start

👉 **[See SETUP.md for complete installation instructions](./SETUP.md)**

**Short version:**

```bash
# 1. Install dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Configure Google Cloud credentials (see SETUP.md)
cp .env.example .env
# Edit .env with your credentials path

# 3. Run the server
python -m app.main

# 4. Open browser
open http://localhost:8000
```

## Supported Audio Formats

- MP3
- WAV
- M4A
- OGG
- FLAC
- MP4/MOV (extracts audio)

## Architecture

```
┌─────────────┐
│   Web UI    │  ← Upload audio files
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  FastAPI    │  ← Python backend
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ Transcribe  │  ← Modular service (Google or Whisper)
│   Service   │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Google     │  ← Cloud Speech-to-Text API
│   STT API   │
└─────────────┘
```

## Project Structure

```
voice-to-text/
├── app/
│   ├── main.py              # FastAPI application
│   ├── static/
│   │   └── index.html       # Web UI
│   └── utils/
│       └── transcribe.py    # Modular transcription service
├── requirements.txt         # Dependencies
├── .env.example            # Environment template
├── SETUP.md                # Detailed setup guide
└── README.md               # This file
```

## Why Modular?

The transcription logic is isolated in `app/utils/transcribe.py`:

```python
# Easy to swap providers
transcription_service = get_transcription_service("google")  # or "whisper"
```

Change one line in `app/main.py` to switch from Google to Whisper (or any other service).

## Next Steps

Part of a larger **Content Cockpit** system for processing and analyzing yoga class recordings. Future enhancements:

- Video processing (green screen removal, scene detection)
- Content analysis (asana identification, theme extraction)
- Semantic search (find specific concepts across all classes)
- Clip generation (extract segments by topic)
- Contextual Librarian (AI-powered content understanding)

## Cost

With $250 Google Cloud credit:
- ~$0.006 per 15 seconds of audio
- Can transcribe ~40,000 minutes before paying
- Plenty for development and testing

## License

Personal project - use freely for your own learning!

---

**Ready to get started?** → [Open SETUP.md](./SETUP.md)
