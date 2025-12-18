#!/usr/bin/env bash
# COGSPACE v40.0.0
# COGSPACE Deployment Expert Skill v1.0
# Provides expert guidance for COGSPACE v26+ deployment, troubleshooting, and validation

set -euo pipefail

# Skill metadata
SKILL_NAME="deployment-expert"
SKILL_VERSION="1.0.0"
SKILL_DESCRIPTION="Expert guidance for COGSPACE v26+ deployment and troubleshooting"
DNA_SOURCE="${DNA_SOURCE:-/Volumes/FOUR-TB/cogspace-dna-source}"

# Color codes
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly CYAN='\033[0;36m'
readonly NC='\033[0m' # No Color

# Main deployment expert function
deployment_expert() {
    local operation="${1:-help}"

    case "$operation" in
        help|--help|-h)
            show_help
            ;;
        validate|check)
            validate_deployment
            ;;
        diagnose)
            diagnose_issues
            ;;
        guide)
            show_deployment_guide
            ;;
        test)
            run_deployment_tests
            ;;
        status)
            show_deployment_status
            ;;
        rollback)
            show_rollback_procedure
            ;;
        versions)
            check_versions
            ;;
        ollama-check)
            check_ollama_status
            ;;
        node-check)
            check_nodejs_system
            ;;
        *)
            echo -e "${RED}❌ Unknown operation: $operation${NC}"
            show_help
            return 1
            ;;
    esac
}

# Display help information
show_help() {
    cat <<'EOF'
╔═══════════════════════════════════════════════════════════╗
║         COGSPACE Deployment Expert v1.0                   ║
║     Comprehensive v26+ Deployment & Troubleshooting       ║
╚═══════════════════════════════════════════════════════════╝

USAGE:
  ./cogspace/skills/deployment-expert.sh [OPERATION]

OPERATIONS:

  📋 validate | check
     Validate current COGSPACE deployment
     - Checks version files
     - Verifies Node.js context system
     - Detects Ollama issues
     - Validates file structure

  🔍 diagnose
     Diagnose deployment issues
     - Identifies common problems
     - Provides specific fixes
     - Checks auto-healing status

  📖 guide
     Show deployment guide summary
     - Quick start instructions
     - Deployment scenarios
     - Testing checklist

  🧪 test
     Run deployment validation tests
     - Hi cycle test
     - Bye cycle test
     - Context generation test
     - jq error detection

  📊 status
     Show current deployment status
     - Version information
     - System health
     - Recent issues

  ⏪ rollback
     Show rollback procedure
     - Backup instructions
     - Version downgrade steps
     - Recovery commands

  🔢 versions
     Check version consistency
     - DNA source version
     - Local project version
     - Version file locations

  🚫 ollama-check
     Check Ollama code status
     - Detect Ollama files
     - Verify disabled status
     - Show removal procedure

  ✅ node-check
     Verify Node.js context system
     - Check required files
     - Validate analyzers
     - Test context generation

EXAMPLES:

  # Quick validation of current deployment
  ./cogspace/skills/deployment-expert.sh validate

  # Diagnose jq parse errors
  ./cogspace/skills/deployment-expert.sh diagnose

  # Check if Ollama code is disabled
  ./cogspace/skills/deployment-expert.sh ollama-check

  # Run full deployment tests
  ./cogspace/skills/deployment-expert.sh test

EXPERTISE EMBEDDED:
  ✅ v26.2.9 deployment procedures
  ✅ Auto-healing diagnostics knowledge
  ✅ Ollama removal and Node.js migration
  ✅ jq parse error troubleshooting
  ✅ Dashboard v26 deployment
  ✅ Version management best practices

DOCUMENTATION:
  - Full Guide: ${DNA_SOURCE}/current/DEPLOYMENT-GUIDE-v26.md
  - Test Report: ${DNA_SOURCE}/current/DEPLOYMENT-TEST-REPORT.md
  - Troubleshooting: Use 'diagnose' operation

EOF
}

# Validate current deployment
validate_deployment() {
    echo -e "${CYAN}🔍 COGSPACE Deployment Validation${NC}\n"

    local issues=0

    # v40.0.0: Check version file (single source - cogspace-version.json)
    echo -e "${BLUE}📋 Checking version files...${NC}"
    if [[ -f "cogspace/cogspace-version.json" ]]; then
        local_version=$(jq -r '.version // "MISSING"' cogspace/cogspace-version.json 2>/dev/null || echo "MISSING")
        echo -e "  ✅ Local version: ${GREEN}$local_version${NC}"
    else
        echo -e "  ${RED}❌ Missing cogspace/cogspace-version.json${NC}"
        ((issues++))
    fi

    if [[ -f "$DNA_SOURCE/current/cogspace/cogspace-version.json" ]]; then
        dna_version=$(jq -r '.version // "MISSING"' "$DNA_SOURCE/current/cogspace/cogspace-version.json" 2>/dev/null || echo "MISSING")
        echo -e "  ✅ DNA source version: ${GREEN}$dna_version${NC}"
    else
        echo -e "  ${YELLOW}⚠️  Cannot check DNA source version${NC}"
    fi

    # Check Node.js context system
    echo -e "\n${BLUE}📦 Checking Node.js context system...${NC}"
    local nodejs_files=(
        "cogspace/generate-complete-context.js"
        "cogspace/create-welcome-context.js"
        "cogspace/analyzers/context-analyzer.js"
        "cogspace/analyzers/serializer.cjs"
    )

    for file in "${nodejs_files[@]}"; do
        if [[ -f "$file" ]]; then
            echo -e "  ✅ $file"
        else
            echo -e "  ${RED}❌ Missing: $file${NC}"
            ((issues++))
        fi
    done

    # Check for Ollama code
    echo -e "\n${BLUE}🚫 Checking Ollama status...${NC}"
    if [[ -f "cogspace/skills/context-synthesizer.sh" ]]; then
        if grep -q "ollama run" cogspace/skills/context-synthesizer.sh 2>/dev/null; then
            echo -e "  ${YELLOW}⚠️  Ollama code present in context-synthesizer.sh${NC}"

            # Check if disabled in sleep.sh
            if grep -q "if false; then" sleep.sh 2>/dev/null && \
               grep -q "DISABLED.*Ollama" sleep.sh 2>/dev/null; then
                echo -e "  ✅ Ollama code DISABLED in sleep.sh (safe)"
            else
                echo -e "  ${RED}❌ Ollama code NOT DISABLED - will cause jq errors!${NC}"
                ((issues++))
            fi
        else
            echo -e "  ✅ No Ollama code found"
        fi
    else
        echo -e "  ℹ️  context-synthesizer.sh not present (OK)"
    fi

    # Check critical scripts
    echo -e "\n${BLUE}📜 Checking critical scripts...${NC}"
    local scripts=("hi" "bye" "wake.sh" "sleep.sh" "cogspace/cogspace/src/cogspace-diagnostics.sh")
    for script in "${scripts[@]}"; do
        if [[ -f "$script" && -x "$script" ]]; then
            echo -e "  ✅ $script (executable)"
        else
            echo -e "  ${RED}❌ Missing or not executable: $script${NC}"
            ((issues++))
        fi
    done

    # Summary
    echo -e "\n${CYAN}═══════════════════════════════════════════════${NC}"
    if [[ $issues -eq 0 ]]; then
        echo -e "${GREEN}✅ Deployment validation PASSED (0 issues)${NC}"
        return 0
    else
        echo -e "${RED}❌ Deployment validation FAILED ($issues issues)${NC}"
        echo -e "\nRun '${YELLOW}deployment-expert.sh diagnose${NC}' for fixes"
        return 1
    fi
}

# Diagnose deployment issues
diagnose_issues() {
    echo -e "${CYAN}🔍 COGSPACE Issue Diagnosis${NC}\n"

    # Check for common issues

    # Issue 1: jq parse errors
    echo -e "${BLUE}1. Checking for jq parse error symptoms...${NC}"
    if [[ -f "cogspace/logs/sleep-"*.log ]] 2>/dev/null; then
        if grep -q "jq: parse error" cogspace/logs/sleep-*.log 2>/dev/null; then
            echo -e "  ${RED}❌ FOUND: jq parse errors in logs${NC}"
            echo -e "  ${YELLOW}💡 FIX: Ollama code needs to be disabled${NC}"
            echo -e "     Run: ${GREEN}deployment-expert.sh ollama-check${NC}\n"
        else
            echo -e "  ✅ No jq parse errors detected\n"
        fi
    else
        echo -e "  ℹ️  No recent logs to check\n"
    fi

    # Issue 2: Version mismatch (v40.0.0: single source - cogspace-version.json)
    echo -e "${BLUE}2. Checking version consistency...${NC}"
    if [[ -f "cogspace/cogspace-version.json" && -f "$DNA_SOURCE/current/cogspace/cogspace-version.json" ]]; then
        local_ver=$(jq -r '.version // "unknown"' cogspace/cogspace-version.json 2>/dev/null)
        dna_ver=$(jq -r '.version // "unknown"' "$DNA_SOURCE/current/cogspace/cogspace-version.json" 2>/dev/null)

        if [[ "$local_ver" != "$dna_ver" ]]; then
            echo -e "  ${YELLOW}⚠️  Version mismatch: local=$local_ver, DNA=$dna_ver${NC}"
            echo -e "  ${YELLOW}💡 FIX: Run ./hi to trigger auto-healing${NC}\n"
        else
            echo -e "  ✅ Versions synchronized ($local_ver)\n"
        fi
    else
        echo -e "  ${RED}❌ Missing version files${NC}\n"
    fi

    # Issue 3: Missing Node.js files
    echo -e "${BLUE}3. Checking Node.js context system...${NC}"
    if [[ ! -f "cogspace/generate-complete-context.js" ]]; then
        echo -e "  ${RED}❌ Missing Node.js context generator${NC}"
        echo -e "  ${YELLOW}💡 FIX: Run ./cogspace/cogspace/src/cogspace-diagnostics.sh --health${NC}\n"
    else
        echo -e "  ✅ Node.js context system present\n"
    fi

    # Issue 4: Corrupted context errors
    echo -e "${BLUE}4. Checking for context validation errors...${NC}"
    if [[ -f "cogspace/logs/wake-"*.log ]] 2>/dev/null; then
        if grep -q "corrupted context" cogspace/logs/wake-*.log 2>/dev/null; then
            echo -e "  ${RED}❌ FOUND: Corrupted context errors${NC}"
            echo -e "  ${YELLOW}💡 FIX: Legacy context format detected${NC}"
            echo -e "     1. Backup: cp -r session-management/cognitive-context backup/"
            echo -e "     2. Fresh: ./bye \"Fresh v26 context\""
            echo -e "     3. Test: ./hi\n"
        else
            echo -e "  ✅ No context validation errors\n"
        fi
    else
        echo -e "  ℹ️  No recent logs to check\n"
    fi

    echo -e "${CYAN}═══════════════════════════════════════════════${NC}"
    echo -e "For complete troubleshooting guide:"
    echo -e "${GREEN}cat $DNA_SOURCE/current/DEPLOYMENT-GUIDE-v26.md | grep -A50 'Troubleshooting'${NC}"
}

# Show deployment guide summary
show_deployment_guide() {
    cat <<'EOF'
╔═══════════════════════════════════════════════════════════╗
║        COGSPACE v26+ Deployment Quick Guide               ║
╚═══════════════════════════════════════════════════════════╝

🚀 QUICK START (Existing Projects)

  Automatic upgrade (recommended):
    cd /path/to/project
    ./hi  # Auto-detects version mismatch and self-heals

  Force healing:
    ./cogspace/cogspace/src/cogspace-diagnostics.sh --health

📦 NEW PROJECT DEPLOYMENT

  1. Create directories:
     mkdir -p session-management/cognitive-context memories src cogspace

  2. Sync cogspace:
     rsync -av --delete --exclude="node_modules" \
       /Volumes/FOUR-TB/cogspace-dna-source/current/cogspace/ cogspace/

  3. Copy scripts:
     cp /Volumes/FOUR-TB/cogspace-dna-source/current/{hi,bye,wake.sh,sleep.sh,save.sh} .
     chmod +x hi bye wake.sh sleep.sh save.sh

  4. Copy diagnostics:
     cp /Volumes/FOUR-TB/cogspace-dna-source/current/cogspace/cogspace/src/cogspace-diagnostics.sh src/
     chmod +x cogspace/cogspace/src/cogspace-diagnostics.sh

  5. Set version:
     # v40.0.0: Version is set via cogspace-version.json during deployment

  6. Test:
     ./hi  # Should show PERFECT health check

🧪 VALIDATION TESTS

  1. Hi cycle:     ./hi  # Should show "PERFECT (4/4 checks passed)"
  2. Bye cycle:    ./bye "Test"  # Should complete with NO jq errors
  3. Context:      ls -lh session-management/cognitive-context/
  4. Ollama check: grep "ollama run" cogspace/skills/*.sh
  5. Node.js:      ls -1 cogspace/analyzers/*.{js,cjs}

✅ SUCCESS CRITERIA

  ✅ Version shows v26.2.9
  ✅ Hi cycle: PERFECT health check
  ✅ Bye cycle: NO jq parse errors
  ✅ Context files created (15KB complete-context.json)
  ✅ Node.js system present (6 files)
  ✅ Ollama disabled (if present)

📚 FULL DOCUMENTATION

  Complete guide: /Volumes/FOUR-TB/cogspace-dna-source/current/DEPLOYMENT-GUIDE-v26.md
  Test report:    /Volumes/FOUR-TB/cogspace-dna-source/current/DEPLOYMENT-TEST-REPORT.md

EOF
}

# Run deployment tests
run_deployment_tests() {
    echo -e "${CYAN}🧪 Running Deployment Validation Tests${NC}\n"

    local tests_passed=0
    local tests_failed=0

    # Test 1: Version check (v40.0.0: single source - cogspace-version.json)
    echo -e "${BLUE}Test 1: Version Check${NC}"
    if [[ -f "cogspace/cogspace-version.json" ]]; then
        version=$(jq -r '.version // "unknown"' cogspace/cogspace-version.json 2>/dev/null)
        # v40.0.0+: Accept any 40.x.x version or higher
        if [[ "$version" =~ ^4[0-9]\. ]]; then
            echo -e "  ${GREEN}✅ PASS${NC} - Version is $version"
            ((tests_passed++))
        else
            echo -e "  ${YELLOW}⚠️  PASS${NC} - Version is $version (consider upgrading)"
            ((tests_passed++))
        fi
    else
        echo -e "  ${RED}❌ FAIL${NC} - cogspace-version.json missing"
        ((tests_failed++))
    fi

    # Test 2: Node.js files
    echo -e "\n${BLUE}Test 2: Node.js Context System${NC}"
    local required_files=6
    local found_files=0

    [[ -f "cogspace/generate-complete-context.js" ]] && ((found_files++))
    [[ -f "cogspace/create-welcome-context.js" ]] && ((found_files++))
    [[ -f "cogspace/analyzers/context-analyzer.js" ]] && ((found_files++))
    [[ -f "cogspace/analyzers/generate-context.js" ]] && ((found_files++))
    [[ -f "cogspace/analyzers/priority-engine.js" ]] && ((found_files++))
    [[ -f "cogspace/analyzers/serializer.cjs" ]] && ((found_files++))

    if [[ $found_files -eq $required_files ]]; then
        echo -e "  ${GREEN}✅ PASS${NC} - All $required_files Node.js files present"
        ((tests_passed++))
    else
        echo -e "  ${RED}❌ FAIL${NC} - Found $found_files/$required_files files"
        ((tests_failed++))
    fi

    # Test 3: Ollama disabled check
    echo -e "\n${BLUE}Test 3: Ollama Disabled Check${NC}"
    if [[ -f "cogspace/skills/context-synthesizer.sh" ]]; then
        if grep -q "ollama run" cogspace/skills/context-synthesizer.sh 2>/dev/null; then
            if grep -q "if false; then" sleep.sh 2>/dev/null; then
                echo -e "  ${GREEN}✅ PASS${NC} - Ollama code present but disabled"
                ((tests_passed++))
            else
                echo -e "  ${RED}❌ FAIL${NC} - Ollama code present and NOT disabled"
                ((tests_failed++))
            fi
        else
            echo -e "  ${GREEN}✅ PASS${NC} - No Ollama code found"
            ((tests_passed++))
        fi
    else
        echo -e "  ${GREEN}✅ PASS${NC} - context-synthesizer.sh not present"
        ((tests_passed++))
    fi

    # Test 4: Executable scripts
    echo -e "\n${BLUE}Test 4: Executable Scripts${NC}"
    local all_executable=true
    for script in hi bye wake.sh sleep.sh cogspace/cogspace/src/cogspace-diagnostics.sh; do
        if [[ ! -x "$script" ]]; then
            all_executable=false
            break
        fi
    done

    if $all_executable; then
        echo -e "  ${GREEN}✅ PASS${NC} - All critical scripts executable"
        ((tests_passed++))
    else
        echo -e "  ${RED}❌ FAIL${NC} - Some scripts not executable"
        ((tests_failed++))
    fi

    # Summary
    local total=$((tests_passed + tests_failed))
    echo -e "\n${CYAN}═══════════════════════════════════════════════${NC}"
    echo -e "Tests Passed: ${GREEN}$tests_passed${NC}/$total"
    echo -e "Tests Failed: ${RED}$tests_failed${NC}/$total"

    if [[ $tests_failed -eq 0 ]]; then
        echo -e "\n${GREEN}✅ All validation tests PASSED${NC}"
        return 0
    else
        echo -e "\n${RED}❌ Some tests FAILED${NC}"
        echo -e "Run '${YELLOW}deployment-expert.sh diagnose${NC}' for fixes"
        return 1
    fi
}

# Show deployment status
show_deployment_status() {
    echo -e "${CYAN}📊 COGSPACE Deployment Status${NC}\n"

    # v40.0.0: Version info from single source - cogspace-version.json
    echo -e "${BLUE}📋 Version Information${NC}"
    if [[ -f "cogspace/cogspace-version.json" ]]; then
        echo -e "  Local:      $(jq -r '.version // "UNKNOWN"' cogspace/cogspace-version.json 2>/dev/null)"
    else
        echo -e "  Local:      ${RED}NOT FOUND${NC}"
    fi

    if [[ -f "$DNA_SOURCE/current/cogspace/cogspace-version.json" ]]; then
        echo -e "  DNA Source: $(jq -r '.version // "UNKNOWN"' $DNA_SOURCE/current/cogspace/cogspace-version.json 2>/dev/null)"
    else
        echo -e "  DNA Source: ${YELLOW}CANNOT CHECK${NC}"
    fi

    # System health
    echo -e "\n${BLUE}🏥 System Health${NC}"
    if command -v node >/dev/null 2>&1; then
        echo -e "  Node.js:    ${GREEN}✅ Available${NC} ($(node --version))"
    else
        echo -e "  Node.js:    ${YELLOW}⚠️  Not in PATH${NC}"
    fi

    if [[ -x "cogspace/cogspace/src/cogspace-diagnostics.sh" ]]; then
        echo -e "  Diagnostics: ${GREEN}✅ Ready${NC}"
    else
        echo -e "  Diagnostics: ${RED}❌ Missing${NC}"
    fi

    # Recent issues
    echo -e "\n${BLUE}🔍 Recent Issues${NC}"
    if [[ -f "cogspace/logs/sleep-"*.log ]] 2>/dev/null; then
        local recent_log=$(ls -t cogspace/logs/sleep-*.log 2>/dev/null | head -1)
        if grep -q "jq: parse error" "$recent_log" 2>/dev/null; then
            echo -e "  ${RED}❌ jq parse errors detected${NC}"
        else
            echo -e "  ${GREEN}✅ No jq errors in recent logs${NC}"
        fi
    else
        echo -e "  ${YELLOW}ℹ️  No recent logs to analyze${NC}"
    fi

    echo -e "\n${CYAN}═══════════════════════════════════════════════${NC}"
}

# Show rollback procedure
show_rollback_procedure() {
    cat <<'EOF'
╔═══════════════════════════════════════════════════════════╗
║           COGSPACE v26 Rollback Procedure                 ║
╚═══════════════════════════════════════════════════════════╝

⏪ ROLLBACK TO v23.1.3

If v26 deployment causes issues, rollback to stable v23.1.3:

1. BACKUP CURRENT STATE
   cp -r session-management/cognitive-context backup-context-$(date +%s)/
   cp cogspace/cogspace-version.json backup-version.json

2. STOP SESSIONS
   ./bye "Rollback preparation"

3. DEPLOY FROM DNA SOURCE
   rsync -av /Volumes/FOUR-TB/cogspace-dna-source/current/cogspace/ cogspace/
   # v40.0.0: Version is automatically set via cogspace-version.json

4. RESTORE CONTEXT (if needed)
   cp -r backup-context-*/complete-context-*.json session-management/cognitive-context/

5. TEST
   ./hi  # Verify v23 systems operational

⚠️  ROLLBACK NOTES

- Contexts from v26 are compatible with v23
- No data loss expected
- Auto-healing will be disabled in v23
- Node.js context generation will revert to bash/jq

📊 ROLLBACK VERIFICATION

After rollback, verify:
  ✅ Version shows 23.1.3
  ✅ Hi cycle runs without errors
  ✅ Context files accessible
  ✅ No "corrupted context" errors

EOF
}

# Check version consistency
check_versions() {
    echo -e "${CYAN}🔢 Version Consistency Check${NC}\n"

    echo -e "${BLUE}Local Project:${NC}"
    if [[ -f "cogspace/.cogspace-version" ]]; then
        echo -e "  .cogspace-version: ${GREEN}$(cat cogspace/.cogspace-version)${NC}"
    else
        echo -e "  .cogspace-version: ${RED}MISSING${NC}"
    fi

    if [[ -f "cogspace/.version" ]]; then
        echo -e "  .version:          ${YELLOW}$(cat cogspace/.version)${NC} (legacy)"
    fi

    echo -e "\n${BLUE}DNA Source:${NC}"
    if [[ -f "$DNA_SOURCE/.session-dna-version" ]]; then
        echo -e "  .session-dna-version: ${GREEN}$(cat $DNA_SOURCE/.session-dna-version)${NC}"
    else
        echo -e "  .session-dna-version: ${RED}MISSING${NC}"
    fi

    if [[ -f "$DNA_SOURCE/current/cogspace/.cogspace-version" ]]; then
        echo -e "  cogspace/.cogspace-version: ${GREEN}$(cat $DNA_SOURCE/current/cogspace/.cogspace-version)${NC}"
    fi

    echo -e "\n${CYAN}═══════════════════════════════════════════════${NC}"
}

# Check Ollama status
check_ollama_status() {
    echo -e "${CYAN}🚫 Ollama Code Status Check${NC}\n"

    local ollama_found=false

    # Check for Ollama in skills
    if [[ -f "cogspace/skills/context-synthesizer.sh" ]]; then
        if grep -q "ollama run" cogspace/skills/context-synthesizer.sh 2>/dev/null; then
            ollama_found=true
            echo -e "${YELLOW}⚠️  Ollama code found in context-synthesizer.sh${NC}\n"

            # Check if disabled
            if grep -q "if false; then" sleep.sh 2>/dev/null && \
               grep -q "DISABLED.*Ollama" sleep.sh 2>/dev/null; then
                echo -e "${GREEN}✅ STATUS: DISABLED (Safe)${NC}"
                echo -e "   Ollama code present but wrapped in 'if false' in sleep.sh\n"
            else
                echo -e "${RED}❌ STATUS: ACTIVE (Dangerous!)${NC}"
                echo -e "   ${RED}This WILL cause jq parse errors!${NC}\n"

                echo -e "${BLUE}🔧 FIX PROCEDURE:${NC}"
                echo -e "1. Backup file:"
                echo -e "   ${GREEN}mv cogspace/skills/context-synthesizer.sh \\${NC}"
                echo -e "   ${GREEN}   cogspace/skills/context-synthesizer.sh.BROKEN-OLLAMA-BACKUP${NC}\n"
                echo -e "2. Trigger healing:"
                echo -e "   ${GREEN}./cogspace/cogspace/src/cogspace-diagnostics.sh --health${NC}\n"
                echo -e "3. Verify:"
                echo -e "   ${GREEN}./bye \"Test after Ollama fix\"${NC}"
                echo -e "   ${GREEN}# Should complete with NO jq errors${NC}\n"
            fi
        else
            echo -e "${GREEN}✅ No Ollama code found in context-synthesizer.sh${NC}\n"
        fi
    else
        echo -e "${GREEN}✅ context-synthesizer.sh not present${NC}\n"
    fi

    # Show line where Ollama is called
    if $ollama_found; then
        echo -e "${BLUE}📍 Ollama Call Location:${NC}"
        grep -n "ollama run" cogspace/skills/context-synthesizer.sh 2>/dev/null | head -3
        echo ""
    fi

    echo -e "${CYAN}═══════════════════════════════════════════════${NC}"
}

# Check Node.js context system
check_nodejs_system() {
    echo -e "${CYAN}✅ Node.js Context System Check${NC}\n"

    local all_present=true

    echo -e "${BLUE}Required Files:${NC}"

    local files=(
        "cogspace/generate-complete-context.js:Main context generator"
        "cogspace/create-welcome-context.js:Welcome context creator"
        "cogspace/analyzers/context-analyzer.js:Canvas integration"
        "cogspace/analyzers/generate-context.js:Context generation logic"
        "cogspace/analyzers/priority-engine.js:Priority analysis"
        "cogspace/analyzers/serializer.cjs:Cognitive serialization"
    )

    for entry in "${files[@]}"; do
        IFS=':' read -r file description <<< "$entry"
        if [[ -f "$file" ]]; then
            size=$(stat -f%z "$file" 2>/dev/null || stat -c%s "$file" 2>/dev/null || echo "?")
            echo -e "  ${GREEN}✅${NC} $file"
            echo -e "     ${BLUE}$description${NC} (${size} bytes)"
        else
            echo -e "  ${RED}❌${NC} $file"
            echo -e "     ${RED}MISSING - $description${NC}"
            all_present=false
        fi
    done

    echo -e "\n${BLUE}Integration Point:${NC}"
    if grep -q "node cogspace/generate-complete-context.js" sleep.sh 2>/dev/null; then
        echo -e "  ${GREEN}✅ Node.js generator called in sleep.sh${NC}"
    else
        echo -e "  ${RED}❌ Node.js generator NOT called in sleep.sh${NC}"
        all_present=false
    fi

    echo -e "\n${CYAN}═══════════════════════════════════════════════${NC}"

    if $all_present; then
        echo -e "${GREEN}✅ Node.js context system: COMPLETE${NC}\n"
        return 0
    else
        echo -e "${RED}❌ Node.js context system: INCOMPLETE${NC}"
        echo -e "\n${YELLOW}🔧 FIX: Run auto-healing to restore missing files${NC}"
        echo -e "   ${GREEN}./cogspace/cogspace/src/cogspace-diagnostics.sh --health${NC}\n"
        return 1
    fi
}

# Execute main function if called directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    deployment_expert "$@"
fi


