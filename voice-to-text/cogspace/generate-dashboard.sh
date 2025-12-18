#!/bin/bash
# COGSPACE v40.2.1
# DASHBOARD GENERATOR: Dynamic COGSPACE Dashboard Creation
# Generates project-specific dashboard from template
# Version: 23.1.3 "COGSPACE Dashboard" (synced with COGSPACE DNA)

set -euo pipefail

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Function to display usage
usage() {
    echo -e "${CYAN}🎛️ DASHBOARD GENERATOR${NC}"
    echo "Usage: $0 <project_name> <session_id> <timestamp> <project_root>"
    echo ""
    echo "Parameters:"
    echo "  project_name  - Name of the project (e.g., benefits-bridge)"
    echo "  session_id    - Session ID (e.g., 1756025083-834a)"
    echo "  timestamp     - Timestamp string"
    echo "  project_root  - Full path to project root"
    echo ""
    echo "Example:"
    echo "  $0 benefits-bridge 1756025083-834a 'Sun, Aug 24, 2025...' /Volumes/FOUR-TB/root/benefits-bridge"
}

# Validate parameters
if [[ $# -ne 4 ]]; then
    echo -e "${RED}❌ ERROR: Invalid number of parameters${NC}"
    usage
    exit 1
fi

PROJECT_NAME="$1"
SESSION_ID="$2"
TIMESTAMP="$3"
PROJECT_ROOT="$4"

# Validate project root exists
if [[ ! -d "$PROJECT_ROOT" ]]; then
    echo -e "${RED}❌ ERROR: Project root directory does not exist: $PROJECT_ROOT${NC}"
    exit 1
fi

# Get script directory for template location
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Template source
TEMPLATE_PATH="${SCRIPT_DIR}/dashboard-template.html"

# Validate template exists
if [[ ! -f "$TEMPLATE_PATH" ]]; then
    echo -e "${RED}❌ ERROR: Dashboard template not found: $TEMPLATE_PATH${NC}"
    exit 1
fi

# Output location
DASHBOARD_DIR="${PROJECT_ROOT}/dashboard"
OUTPUT_FILE="${DASHBOARD_DIR}/dashboard-${SESSION_ID}.html"

echo -e "${CYAN}🎛️ GENERATING COGSPACE DASHBOARD${NC}"
echo -e "${BLUE}Project: ${PROJECT_NAME}${NC}"
echo -e "${BLUE}Session: ${SESSION_ID}${NC}"
echo -e "${BLUE}Template: ${TEMPLATE_PATH}${NC}"
echo -e "${BLUE}Output: ${OUTPUT_FILE}${NC}"

# Create dashboard directory
if [[ ! -d "$DASHBOARD_DIR" ]]; then
    echo -e "${YELLOW}📁 Creating dashboard directory: $DASHBOARD_DIR${NC}"
    mkdir -p "$DASHBOARD_DIR"
fi

# Generate dashboard from template
echo -e "${YELLOW}🔄 Processing template...${NC}"

# v40.0.0: Get COGSPACE version from single source - cogspace-version.json
COGSPACE_VERSION="unknown"
if [[ -f "$PROJECT_ROOT/cogspace/cogspace-version.json" ]]; then
    COGSPACE_VERSION=$(jq -r '.version // "unknown"' "$PROJECT_ROOT/cogspace/cogspace-version.json" 2>/dev/null || echo "unknown")
fi

# Get developer name from environment or system
DEV_NAME="${USER:-wizard}"
if [[ -f "$PROJECT_ROOT/package.json" ]]; then
    DEV_NAME=$(jq -r '.author.name // .author // empty' "$PROJECT_ROOT/package.json" 2>/dev/null | head -1 || echo "${USER:-wizard}")
fi

# Extract Short Description from README.md
echo -e "${YELLOW}📖 Extracting README content...${NC}"
README_SHORT_DESC="[No README.md found]"
README_PATH="$PROJECT_ROOT/README.md"
if [[ -f "$README_PATH" ]]; then
    # Extract content between "## Short Description" and the next "##" header
    README_SHORT_DESC=$(awk '/^## Short Description/{found=1; next} /^## /{if(found) exit} found{print}' "$README_PATH" | sed '/^[[:space:]]*$/d' | head -10)
    if [[ -z "$README_SHORT_DESC" ]]; then
        # Fallback: try to get first paragraph after title
        README_SHORT_DESC=$(awk 'NR>2 && /^[^#]/ && !/^\*\*/ {print; exit}' "$README_PATH")
    fi
    if [[ -z "$README_SHORT_DESC" ]]; then
        README_SHORT_DESC="[Short description not found in README.md]"
    fi
    echo -e "${BLUE}   Extracted: ${README_SHORT_DESC:0:60}...${NC}"
else
    echo -e "${YELLOW}   No README.md found at $README_PATH${NC}"
fi

# Escape special characters for sed replacement
README_SHORT_DESC_ESCAPED=$(echo "$README_SHORT_DESC" | sed 's/[&/\]/\\&/g' | tr '\n' ' ')

# Load session context data for dashboard injection
echo -e "${YELLOW}📊 Loading session context data...${NC}"
SESSION_CONTEXT_JSON="{}"
COGNITIVE_CONTEXT_DIR="${PROJECT_ROOT}/session-management/cognitive-context"

if [[ -d "$COGNITIVE_CONTEXT_DIR" ]]; then
    # Find most recent complete-context file
    LATEST_CONTEXT=$(ls -t "$COGNITIVE_CONTEXT_DIR"/complete-context-*.json 2>/dev/null | head -1)

    if [[ -n "$LATEST_CONTEXT" && -f "$LATEST_CONTEXT" ]]; then
        echo -e "${BLUE}   Found context: $(basename "$LATEST_CONTEXT")${NC}"
        # Read and escape for JavaScript injection - use -a for ASCII output
        SESSION_CONTEXT_JSON=$(cat "$LATEST_CONTEXT" | jq -ac '.')
    else
        echo -e "${YELLOW}   No context file found (new session)${NC}"
    fi

    # Read session-summary.json if available (v21.3.1)
    SESSION_SUMMARY_PATH="$COGNITIVE_CONTEXT_DIR/session-summary.json"
    if [[ -f "$SESSION_SUMMARY_PATH" ]]; then
        echo -e "${BLUE}   Found session summary: session-summary.json${NC}"
        # Strip box-drawing table from description and sessionStory fields (causes JS parse errors)
        SESSION_SUMMARY_JSON=$(cat "$SESSION_SUMMARY_PATH" | jq -c '.workState.description = (.workState.description | split("\n") | .[0]) | .workState.sessionStory = (.workState.sessionStory | split("\n") | .[0])')

        # Check size and truncate if too large (browser parse limit ~50KB per field)
        SUMMARY_SIZE=$(echo "$SESSION_SUMMARY_JSON" | wc -c)
        if [[ $SUMMARY_SIZE -gt 50000 ]]; then
            echo -e "${YELLOW}   ⚠️  Session summary too large (${SUMMARY_SIZE} bytes), creating lightweight version${NC}"
            # Create lightweight summary with only essential fields
            SESSION_SUMMARY_JSON=$(cat "$SESSION_SUMMARY_PATH" | jq -c '{
                meta: .meta,
                workState: {
                    description: (.workState.description // "Session in progress"),
                    currentFocus: (.workState.currentFocus // "Continuing work")
                },
                planned: {
                    nextActions: (.planned.nextActions[0:3] // ["Continue current objectives"])
                },
                progress: {
                    achievements: (.progress.achievements[0:5] // [])
                }
            }')
        fi
    else
        echo -e "${YELLOW}   No session summary (will be generated on next sleep)${NC}"
        SESSION_SUMMARY_JSON="{}"
    fi
else
    echo -e "${YELLOW}   Context directory not found (new session)${NC}"
    SESSION_SUMMARY_JSON="{}"
fi

# Use sed to replace template variables
sed -e "s/\${PROJECT_NAME}/$PROJECT_NAME/g" \
    -e "s/\${SESSION_ID}/$SESSION_ID/g" \
    -e "s/\${TIMESTAMP}/$TIMESTAMP/g" \
    -e "s/\${DEV_NAME}/$DEV_NAME/g" \
    -e "s/{{VERSION}}/$COGSPACE_VERSION/g" \
    -e "s/\${README_SHORT_DESC}/$README_SHORT_DESC_ESCAPED/g" \
    "$TEMPLATE_PATH" > "$OUTPUT_FILE"

# Inject session context data into dashboard
if [[ "$SESSION_CONTEXT_JSON" != "{}" || "$SESSION_SUMMARY_JSON" != "{}" ]]; then
    echo -e "${YELLOW}💉 Injecting session context into dashboard...${NC}"

    # Find the DASHBOARD_CONFIG line and inject sessionContext and sessionSummary
    # This happens after the sed replacements
    awk -v context="$SESSION_CONTEXT_JSON" -v summary="$SESSION_SUMMARY_JSON" '
    /const DASHBOARD_CONFIG = \{/ {
        print
        if (context != "{}") {
            print "            sessionContext: " context ","
        }
        if (summary != "{}") {
            print "            sessionSummary: " summary ","
        }
        next
    }
    { print }
    ' "$OUTPUT_FILE" > "$OUTPUT_FILE.tmp" && mv "$OUTPUT_FILE.tmp" "$OUTPUT_FILE"

    echo -e "${GREEN}   ✅ Context injected${NC}"
else
    echo -e "${YELLOW}   ⚠️  No context to inject (new session)${NC}"
fi

# Validate generated file
if [[ ! -f "$OUTPUT_FILE" ]]; then
    echo -e "${RED}❌ ERROR: Dashboard generation failed${NC}"
    exit 1
fi

# Get file size for verification
FILE_SIZE=$(wc -c < "$OUTPUT_FILE")

echo -e "${GREEN}✅ Dashboard generated successfully!${NC}"
echo -e "${BLUE}📄 File: $OUTPUT_FILE${NC}"
echo -e "${BLUE}📊 Size: $FILE_SIZE bytes${NC}"
echo -e "${BLUE}🌐 URL: file://$OUTPUT_FILE${NC}"

# Optional: Auto-open dashboard
if command -v open &> /dev/null; then
    echo -e "${YELLOW}🚀 Auto-opening dashboard in browser...${NC}"
    open "$OUTPUT_FILE"
elif command -v xdg-open &> /dev/null; then
    echo -e "${YELLOW}🚀 Auto-opening dashboard in browser...${NC}"
    xdg-open "$OUTPUT_FILE"
elif command -v start &> /dev/null; then
    echo -e "${YELLOW}🚀 Auto-opening dashboard in browser...${NC}"
    start "$OUTPUT_FILE"
else
    echo -e "${YELLOW}💡 Tip: Open the dashboard manually: file://$OUTPUT_FILE${NC}"
fi

echo -e "${GREEN}🎉 Dashboard generation complete!${NC}"


