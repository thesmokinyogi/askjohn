#!/bin/bash
# COGSPACE v40.2.1
# COGSPACE Automated Test Suite v40.0.0
# Run before every release to catch bugs like the v34.0.3 infinite loop
# v40.0.0: Updated to use cogspace-version.json as single source of truth
#
# Usage: ./src/run-cogspace-tests.sh
#
# Author: Bob (Clarity Engineer)
# Created: 2025-11-24

set -euo pipefail

# macOS compatibility: use gtimeout if timeout not available
if command -v timeout &>/dev/null; then
    TIMEOUT_CMD="timeout"
elif command -v gtimeout &>/dev/null; then
    TIMEOUT_CMD="gtimeout"
else
    # Fallback: no timeout available, use simple execution
    TIMEOUT_CMD=""
    echo "⚠️  Warning: 'timeout' command not available. Tests may hang if scripts don't complete."
fi

# Helper function to run with timeout
run_with_timeout() {
    local secs=$1
    shift
    if [[ -n "$TIMEOUT_CMD" ]]; then
        $TIMEOUT_CMD "$secs" "$@"
    else
        "$@"
    fi
}

echo "🧪 COGSPACE Test Suite v40.0.0"
echo "==============================="
echo "Testing DNA Source: $(pwd)"
echo "Date: $(date)"
echo ""

# Configuration
# v38.2.1: Fixed path - script is at cogspace/src/, so need /../.. to reach DNA root
DNA_SOURCE="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TEST_PROJECT="/tmp/cogspace-test-$$"
PASS_COUNT=0
FAIL_COUNT=0
TESTS_RUN=0

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Helper functions
pass() {
    ((PASS_COUNT++))
    ((TESTS_RUN++))
    echo -e "${GREEN}✅ PASS:${NC} $1"
}

fail() {
    ((FAIL_COUNT++))
    ((TESTS_RUN++))
    echo -e "${RED}❌ FAIL:${NC} $1"
}

skip() {
    echo -e "${YELLOW}⏭️  SKIP:${NC} $1"
}

section() {
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

cleanup() {
    if [[ -d "$TEST_PROJECT" ]]; then
        rm -rf "$TEST_PROJECT"
    fi
}

trap cleanup EXIT

# ============================================================================
# PHASE 1: STATIC ANALYSIS
# ============================================================================
section "Phase 1: Static Analysis"

cd "$DNA_SOURCE"

# Test 1.1: Shell script syntax
echo "Testing shell script syntax..."
for script in wake.sh sleep.sh save.sh; do
    if [[ -f "$script" ]]; then
        if bash -n "$script" 2>/dev/null; then
            pass "$script syntax valid"
        else
            fail "$script has syntax errors"
        fi
    else
        fail "$script not found"
    fi
done

# Test 1.2: Version file exists (v40.0.0: JSON only)
if [[ -f "cogspace/cogspace-version.json" ]]; then
    pass "cogspace/cogspace-version.json exists"
else
    fail "cogspace/cogspace-version.json missing"
fi

# Test 1.3: Version readable from JSON
DNA_VERSION=$(jq -r '.version // "0.0.0"' cogspace/cogspace-version.json 2>/dev/null | tr -d '\n')

if [[ -n "$DNA_VERSION" ]] && [[ "$DNA_VERSION" != "0.0.0" ]]; then
    pass "Version readable from JSON: $DNA_VERSION"
else
    fail "Cannot read version from cogspace-version.json"
fi

# Test 1.4: Critical files exist (v38.0.0+: All-In-One architecture)
CRITICAL_FILES=(
    "cogspace/analyzers/serializer.cjs"
    "cogspace/cogspace-version.json"
    "cogspace/dashboard/generate.sh"
    "cogspace/src/cogspace-diagnostics.sh"
)

for file in "${CRITICAL_FILES[@]}"; do
    if [[ -f "$file" ]]; then
        pass "Critical file exists: $file"
    else
        fail "Critical file missing: $file"
    fi
done

# Test 1.5: Dangerous pattern check (exec without version update)
# This is the v34.0.3 bug pattern - v40.0.0: Updated to check for JSON version update
echo "Checking for dangerous patterns..."
EXEC_LINES=$(grep -n 'exec "\$0"' wake.sh 2>/dev/null || echo "")
if [[ -n "$EXEC_LINES" ]]; then
    # Check if there's a version update before each exec
    # v40.0.0: Look for jq-based version update pattern
    if grep -B10 'exec "\$0"' wake.sh | grep -q 'cogspace-version.json\|jq.*version'; then
        pass "exec \$0 has JSON version update before it (v40.0.0 pattern)"
    else
        fail "exec \$0 found WITHOUT version update - potential infinite loop!"
    fi
else
    pass "No self-exec patterns found"
fi

# ============================================================================
# PHASE 2: FRESH INSTALL TEST
# ============================================================================
section "Phase 2: Fresh Install Test"

# Setup test project
echo "Creating test project: $TEST_PROJECT"
mkdir -p "$TEST_PROJECT"
cp -r "$DNA_SOURCE"/* "$TEST_PROJECT/"
cd "$TEST_PROJECT"

# Ensure we have a clean state - v40.0.0: Only manage JSON version
# Set version to 0.0.0 to simulate fresh install
jq '.version = "0.0.0"' cogspace/cogspace-version.json > cogspace/cogspace-version.json.tmp && \
    mv cogspace/cogspace-version.json.tmp cogspace/cogspace-version.json

# Test 2.1: Fresh wake (simulated fresh install with 0.0.0)
echo "Testing fresh wake..."
if echo "n" | run_with_timeout 60 ./wake.sh > /tmp/fresh-wake.log 2>&1; then
    pass "Fresh wake completed"
else
    fail "Fresh wake failed or timed out"
    cat /tmp/fresh-wake.log | tail -20
fi

# Test 2.2: Version updated in JSON (v40.0.0: JSON is single source)
CREATED_VERSION=$(jq -r '.version // "0.0.0"' cogspace/cogspace-version.json 2>/dev/null | tr -d '\n')
if [[ "$CREATED_VERSION" == "$DNA_VERSION" ]]; then
    pass "Version updated with correct version: $CREATED_VERSION"
else
    fail "Version not updated correctly: $CREATED_VERSION (expected $DNA_VERSION)"
fi

# Test 2.3: Sleep cycle
echo "Testing sleep cycle..."
if run_with_timeout 60 ./sleep.sh "Automated test - fresh install" > /tmp/fresh-sleep.log 2>&1; then
    pass "Sleep cycle completed"
else
    fail "Sleep cycle failed or timed out"
    cat /tmp/fresh-sleep.log | tail -20
fi

# Test 2.4: Context file created
CONTEXT_FILES=$(find session-management/cognitive-context -name "complete-context-*.json" 2>/dev/null | wc -l | tr -d ' ')
if [[ $CONTEXT_FILES -gt 0 ]]; then
    pass "Context file created ($CONTEXT_FILES files)"
else
    fail "No context files created"
fi

# ============================================================================
# PHASE 3: VERSION UPGRADE TEST (CRITICAL - v34.0.3 regression)
# ============================================================================
section "Phase 3: Version Upgrade Test (CRITICAL)"

echo -e "${YELLOW}⚠️  This test catches the v34.0.3 infinite loop bug${NC}"

# Simulate old version - v40.0.0: Use JSON only
OLD_VERSION="32.1.0"
jq --arg v "$OLD_VERSION" '.version = $v' cogspace/cogspace-version.json > cogspace/cogspace-version.json.tmp && \
    mv cogspace/cogspace-version.json.tmp cogspace/cogspace-version.json
echo "Simulated old version: $OLD_VERSION"
echo "DNA version: $DNA_VERSION"

# Test 3.1: Upgrade wake with timeout
echo "Testing version upgrade wake..."
START_TIME=$(date +%s)
if echo "n" | run_with_timeout 30 ./wake.sh > /tmp/upgrade-wake.log 2>&1; then
    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))
    pass "Upgrade wake completed in ${DURATION}s"
else
    EXIT_CODE=$?
    if [[ $EXIT_CODE -eq 124 ]]; then
        fail "CRITICAL: Wake timed out - likely INFINITE LOOP!"
        echo "Last 30 lines of output:"
        tail -30 /tmp/upgrade-wake.log
    else
        fail "Upgrade wake failed with exit code $EXIT_CODE"
    fi
fi

# Test 3.2: Check for infinite loop indicators
UPGRADE_COUNT=$(grep -c "COGSPACE upgrade detected" /tmp/upgrade-wake.log 2>/dev/null || echo "0")
REEXEC_COUNT=$(grep -c "Re-executing wake" /tmp/upgrade-wake.log 2>/dev/null || echo "0")

echo "  Upgrade detections: $UPGRADE_COUNT"
echo "  Re-executions: $REEXEC_COUNT"

if [[ $UPGRADE_COUNT -le 1 ]] && [[ $REEXEC_COUNT -le 1 ]]; then
    pass "No infinite loop detected"
else
    fail "CRITICAL: Multiple upgrade cycles detected - possible infinite loop regression!"
fi

# Test 3.3: Version updated correctly (v40.0.0: JSON only)
CURRENT_VERSION=$(jq -r '.version // "MISSING"' cogspace/cogspace-version.json 2>/dev/null | tr -d '\n')
if [[ "$CURRENT_VERSION" == "$DNA_VERSION" ]]; then
    pass "Version updated correctly: $CURRENT_VERSION"
else
    fail "Version NOT updated: $CURRENT_VERSION (expected $DNA_VERSION)"
fi

# ============================================================================
# PHASE 4: EDGE CASE TESTS
# ============================================================================
section "Phase 4: Edge Case Tests"

# Test 4.1: Missing version in JSON recovery (v40.0.0: JSON only)
# Remove version from JSON to simulate missing
jq 'del(.version)' cogspace/cogspace-version.json > cogspace/cogspace-version.json.tmp && \
    mv cogspace/cogspace-version.json.tmp cogspace/cogspace-version.json
echo "Testing missing version in JSON..."
if echo "n" | run_with_timeout 30 ./wake.sh > /tmp/missing-version.log 2>&1; then
    RECOVERED_VERSION=$(jq -r '.version // "missing"' cogspace/cogspace-version.json 2>/dev/null)
    if [[ "$RECOVERED_VERSION" != "missing" ]] && [[ -n "$RECOVERED_VERSION" ]]; then
        pass "Recovered from missing version: $RECOVERED_VERSION"
    else
        fail "Did not recover version in JSON"
    fi
else
    fail "Failed to handle missing version"
fi

# Test 4.2: Corrupted version value (v40.0.0: JSON only)
jq '.version = "garbage-not-a-version"' cogspace/cogspace-version.json > cogspace/cogspace-version.json.tmp && \
    mv cogspace/cogspace-version.json.tmp cogspace/cogspace-version.json
echo "Testing corrupted version value..."
if echo "n" | run_with_timeout 30 ./wake.sh > /tmp/corrupted-version.log 2>&1; then
    LOOP_CHECK=$(grep -c "upgrade detected\|Re-executing" /tmp/corrupted-version.log 2>/dev/null || echo "0")
    if [[ $LOOP_CHECK -lt 3 ]]; then
        pass "Handled corrupted version gracefully"
    else
        fail "Potential loop with corrupted version"
    fi
else
    fail "Failed with corrupted version value"
fi

# Test 4.3: Wake after sleep (continuity)
echo "Testing wake after sleep..."
./sleep.sh "Edge case test" > /dev/null 2>&1 || true
if echo "n" | run_with_timeout 60 ./wake.sh > /tmp/continuity.log 2>&1; then
    if grep -q "Continuity Score" /tmp/continuity.log; then
        SCORE=$(grep "Continuity Score" /tmp/continuity.log | grep -o '[0-9]*' | head -1)
        pass "Context restored with continuity score: ${SCORE}%"
    else
        pass "Wake after sleep completed (no continuity score shown)"
    fi
else
    fail "Wake after sleep failed"
fi

# ============================================================================
# PHASE 5: COMPONENT TESTS
# ============================================================================
section "Phase 5: Component Tests"

# Test 5.1: Node.js availability
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    pass "Node.js available: $NODE_VERSION"
else
    fail "Node.js not available"
fi

# Test 5.2: Serializer loads
if node -e "require('./cogspace/analyzers/serializer.cjs')" 2>/dev/null; then
    pass "Cognitive serializer loads"
else
    fail "Cognitive serializer failed to load"
fi

# Test 5.3: Dashboard generator exists and is executable
if [[ -x "cogspace/dashboard/generate.sh" ]]; then
    pass "Dashboard generator executable"
else
    fail "Dashboard generator not executable"
fi

# ============================================================================
# SUMMARY
# ============================================================================
section "Test Summary"

echo ""
echo "Tests run:   $TESTS_RUN"
echo -e "Passed:      ${GREEN}$PASS_COUNT${NC}"
echo -e "Failed:      ${RED}$FAIL_COUNT${NC}"
echo ""

if [[ $FAIL_COUNT -eq 0 ]]; then
    echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}✅ ALL TESTS PASSED - Safe to release COGSPACE $DNA_VERSION${NC}"
    echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"
    exit 0
else
    echo -e "${RED}════════════════════════════════════════════════════════════${NC}"
    echo -e "${RED}❌ $FAIL_COUNT TEST(S) FAILED - DO NOT RELEASE${NC}"
    echo -e "${RED}════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo "Review the failures above before proceeding."
    exit 1
fi


