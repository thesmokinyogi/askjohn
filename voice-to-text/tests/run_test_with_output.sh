#!/bin/bash
# Run transcription test and save output to file

# Create logs directory if it doesn't exist
mkdir -p ../logs

# Generate timestamp for log file
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="../logs/test_transcription_${TIMESTAMP}.log"

echo "Running transcription test..."
echo "Output will be saved to: $LOG_FILE"
echo ""

# Activate venv and run test, saving all output
source ../venv/bin/activate
python3 test_transcription_job.py 2>&1 | tee "$LOG_FILE"

# Show summary
echo ""
echo "=" | tee -a "$LOG_FILE"
echo "Test complete. Full output saved to: $LOG_FILE" | tee -a "$LOG_FILE"
echo "=" | tee -a "$LOG_FILE"

