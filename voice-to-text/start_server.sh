#!/bin/bash
# Start the FastAPI server for voice-to-text

# Activate virtual environment
source venv/bin/activate

# Start server with auto-reload
echo "Starting Voice-to-Text server..."
echo "Server will be available at: http://localhost:8000"
echo "Press Ctrl+C to stop"
echo ""

python -m app.main

