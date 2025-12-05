#!/bin/bash
#
# Wrapper script for cleanup_jobs.py
# Designed to be run from cron or manually
#
# Usage:
#   ./scripts/run_cleanup.sh [--dry-run]
#

set -e  # Exit on error

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Change to project root
cd "$PROJECT_ROOT"

# Activate virtual environment
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
else
    echo "Error: Virtual environment not found at venv/bin/activate"
    exit 1
fi

# Run cleanup script with all options
python scripts/cleanup_jobs.py --all "$@"

# Exit with script's exit code
exit $?

