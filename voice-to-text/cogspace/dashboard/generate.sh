#!/bin/bash
# COGSPACE v40.0.0
# COGSPACE v33.0.0 - Dashboard Generation Wrapper
# v33.0.0: Updated for session-management/dashboard/ path
# v33.0.0-fix: Pass session ID and timestamp to generator
#

set -e

# Arguments from session-wake.sh:
# $1 = PROJECT_NAME
# $2 = WAKE_SESSION_ID
# $3 = TIMESTAMP
# $4 = PROJECT_ROOT
PROJECT_NAME="${1:-}"
WAKE_SESSION_ID="${2:-}"
TIMESTAMP="${3:-}"
PROJECT_ROOT="${4:-$(pwd)}"

echo "🎨 COGSPACE Dashboard Generator v33.0.0"
echo ""

# Run the simplified Node.js generator (.cjs for ESM compatibility)
# Pass all parameters: PROJECT_ROOT, SESSION_ID, TIMESTAMP, PROJECT_NAME
node "$(dirname "$0")/generate-simple.cjs" "$PROJECT_ROOT" "$WAKE_SESSION_ID" "$TIMESTAMP" "$PROJECT_NAME"

# v33.0.0: Dashboard moved to session-management/dashboard/
LATEST_DASHBOARD=$(ls -t "$PROJECT_ROOT"/session-management/dashboard/dashboard-*.html 2>/dev/null | head -1)

if [[ -n "$LATEST_DASHBOARD" ]]; then
    echo "✅ Dashboard ready at: $LATEST_DASHBOARD"
    echo ""
    echo "Open with: open \"$LATEST_DASHBOARD\""
else
    echo "⚠️  No dashboard file found"
    exit 1
fi


