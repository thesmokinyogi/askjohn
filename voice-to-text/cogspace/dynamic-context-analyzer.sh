#!/bin/bash
# COGSPACE v40.2.1
# DYNAMIC CONTEXT ANALYZER
# Intelligent session context detection and priority generation
# Replaces hardcoded templates with project-specific analysis
# Version: 1.0.0

set -euo pipefail

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

PROJECT_ROOT="${PROJECT_ROOT:-$(pwd)}"
PROJECT_NAME="${PROJECT_NAME:-$(basename "$PROJECT_ROOT")}"

#######################################
# Analyze current work state and generate intelligent next session priority
# Globals:
#   PROJECT_ROOT, PROJECT_NAME
# Arguments:
#   None
# Returns:
#   Next session priority string based on actual project state
#######################################
analyze_current_work_state() {
    local priority_items=()
    local context_score=0
    
    if [[ "${COGSPACE_QUIET:-}" != "1" ]]; then
        echo -e "${CYAN}🔍 Analyzing current work state for ${PROJECT_NAME}...${NC}" >&2
    fi
    
    # 1. Check git status for uncommitted work
    if command -v git &> /dev/null && [[ -d ".git" ]]; then
        local git_status
        git_status=$(git status --porcelain 2>/dev/null || echo "")
        if [[ -n "$git_status" ]]; then
            local modified_count=$(echo "$git_status" | grep -c "^ M" || echo "0")
            local added_count=$(echo "$git_status" | grep -c "^A" || echo "0")
            local untracked_count=$(echo "$git_status" | grep -c "^??" || echo "0")
            
            if [[ $modified_count -gt 0 ]]; then
                priority_items+=("Review and commit $modified_count modified files")
                ((context_score += 20))
            fi
            if [[ $added_count -gt 0 ]]; then
                priority_items+=("Complete commit of $added_count staged files")
                ((context_score += 15))
            fi
            if [[ $untracked_count -gt 0 ]]; then
                priority_items+=("Address $untracked_count untracked files")
                ((context_score += 10))
            fi
        fi
    fi
    
    # 2. TODO/FIXME detection removed per v21.3.4+ policy
    # Developers manage their own TODO comments without dashboard noise
    
    # 3. Check for common project artifacts needing attention
    if [[ -f "package.json" && ! -d "node_modules" ]]; then
        priority_items+=("Run npm install - missing dependencies")
        ((context_score += 25))
    fi
    
    if [[ -f "requirements.txt" && ! -d "venv" && ! -d ".venv" ]]; then
        priority_items+=("Set up Python virtual environment and install requirements")
        ((context_score += 25))
    fi
    
    # 4. Check for build/test failures
    if [[ -f ".github/workflows" ]] && command -v gh &> /dev/null; then
        local workflow_status
        workflow_status=$(gh run list --limit 1 --json conclusion --jq '.[0].conclusion' 2>/dev/null || echo "")
        if [[ "$workflow_status" == "failure" ]]; then
            priority_items+=("Fix failing CI/CD workflow")
            ((context_score += 30))
        fi
    fi
    
    # 5. Analyze project-specific patterns
    case "$PROJECT_NAME" in
        *dashboard*|*ui*|*frontend*)
            if [[ -f "index.html" || -f "src/index.js" ]]; then
                priority_items+=("Continue UI development and testing")
                ((context_score += 15))
            fi
            ;;
        *api*|*backend*|*server*)
            if [[ -f "server.js" || -f "app.py" || -f "main.go" ]]; then
                priority_items+=("Continue API development and endpoint testing")
                ((context_score += 15))
            fi
            ;;
        *cogspace*|*session*)
            priority_items+=("Continue session management system development")
            ((context_score += 20))
            ;;
        *test*|*spec*)
            priority_items+=("Continue test suite development and validation")
            ((context_score += 15))
            ;;
    esac
    
    # 6. Check for recent file modifications (last 24 hours)
    local recent_files
    recent_files=$(find . -type f -mtime -1 -not -path "./.git/*" -not -path "./node_modules/*" | head -10)
    if [[ -n "$recent_files" ]]; then
        local recent_count=$(echo "$recent_files" | wc -l)
        if [[ $recent_count -gt 5 ]]; then
            priority_items+=("Review recent changes to $recent_count files")
            ((context_score += 10))
        fi
    fi
    
    # 7. Generate intelligent priority based on analysis
    if [[ ${#priority_items[@]} -eq 0 ]]; then
        if [[ $context_score -lt 10 ]]; then
            echo "Continue project development and planning"
        else
            echo "Resume development work with focus on code quality"
        fi
    elif [[ ${#priority_items[@]} -eq 1 ]]; then
        echo "${priority_items[0]}"
    elif [[ ${#priority_items[@]} -le 3 ]]; then
        local joined_priorities
        joined_priorities=$(IFS=", "; echo "${priority_items[*]}")
        echo "$joined_priorities"
    else
        # Too many items, prioritize by context score
        if [[ $context_score -gt 50 ]]; then
            echo "Address critical project issues: ${priority_items[0]}, ${priority_items[1]}, and $(( ${#priority_items[@]} - 2 )) other tasks"
        else
            echo "Continue development: ${priority_items[0]} and ${priority_items[1]}"
        fi
    fi
}

#######################################
# Extract pending tasks from current session context
# Globals:
#   PROJECT_ROOT
# Arguments:
#   None
# Returns:
#   Comma-separated list of remaining challenges
#######################################
extract_pending_tasks_from_session() {
    local challenges=()
    local session_context=""
    
    if [[ "${COGSPACE_QUIET:-}" != "1" ]]; then
        echo -e "${CYAN}📋 Extracting pending tasks from session context...${NC}" >&2
    fi
    
    # 1. Check for existing session management context
    if [[ -d "session-management/cognitive-context" ]]; then
        local latest_context
        latest_context=$(ls session-management/cognitive-context/complete-context-*.json 2>/dev/null | tail -1 || echo "")
        if [[ -n "$latest_context" ]]; then
            session_context=$(cat "$latest_context" 2>/dev/null || echo "")
        fi
    fi
    
    # 2. Extract challenges from previous context if available
    if [[ -n "$session_context" ]] && command -v jq &> /dev/null; then
        local prev_challenges
        prev_challenges=$(echo "$session_context" | jq -r '.mentalModel.blockingIssues[]? // empty' 2>/dev/null || echo "")
        if [[ -n "$prev_challenges" ]]; then
            while IFS= read -r challenge; do
                if [[ -n "$challenge" && "$challenge" != "null" ]]; then
                    challenges+=("$challenge")
                fi
            done <<< "$prev_challenges"
        fi
    fi
    
    # 3. Analyze current blockers
    local current_blockers=()
    
    # Check for failing tests
    if [[ -f "package.json" ]] && command -v npm &> /dev/null; then
        if ! npm test --silent &> /dev/null 2>&1; then
            current_blockers+=("failing test suite")
        fi
    fi
    
    # Check for build issues
    if [[ -f "Makefile" ]]; then
        if ! make --dry-run &> /dev/null 2>&1; then
            current_blockers+=("build configuration issues")
        fi
    fi
    
    # Check for missing dependencies
    if [[ -f "package.json" && ! -d "node_modules" ]]; then
        current_blockers+=("missing Node.js dependencies")
    fi
    
    if [[ -f "requirements.txt" ]] && ! python -c "import pkg_resources; pkg_resources.require(open('requirements.txt').read())" &> /dev/null 2>&1; then
        current_blockers+=("missing Python dependencies")
    fi
    
    # 4. Combine and prioritize challenges
    if [[ ${#current_blockers[@]} -gt 0 ]]; then
        challenges+=("${current_blockers[@]}")
    fi
    
    # 5. Generate intelligent challenge summary
    if [[ ${#challenges[@]} -eq 0 ]]; then
        echo "Code review and optimization opportunities"
    elif [[ ${#challenges[@]} -eq 1 ]]; then
        echo "${challenges[0]}"
    elif [[ ${#challenges[@]} -le 3 ]]; then
        local joined_challenges
        joined_challenges=$(IFS=", "; echo "${challenges[*]}")
        echo "$joined_challenges"
    else
        echo "${challenges[0]}, ${challenges[1]}, and $(( ${#challenges[@]} - 2 )) other technical issues"
    fi
}

#######################################
# Generate project-specific immediate actions
# Globals:
#   PROJECT_ROOT, PROJECT_NAME
# Arguments:
#   None
# Returns:
#   JSON array of immediate actions
#######################################
generate_immediate_actions() {
    local actions=()
    local priority_level="high"
    
    # Get dynamic analysis results (suppress debug output)
    local next_priority
    next_priority=$(COGSPACE_QUIET=1 analyze_current_work_state)
    
    local remaining_tasks
    remaining_tasks=$(COGSPACE_QUIET=1 extract_pending_tasks_from_session)
    
    # Create primary action
    if [[ "$next_priority" != *"Continue project development"* ]]; then
        actions+=("{\"description\": \"$next_priority\", \"command\": null, \"priority\": \"critical\", \"context\": \"Primary focus based on current work state\"}")
        priority_level="high"
    else
        priority_level="medium"
    fi
    
    # Create secondary action for challenges
    if [[ "$remaining_tasks" != *"Code review and optimization"* ]]; then
        actions+=("{\"description\": \"Address: $remaining_tasks\", \"command\": null, \"priority\": \"$priority_level\", \"context\": \"Technical challenges requiring attention\"}")
    fi
    
    # Add project-specific actions based on type
    case "$PROJECT_NAME" in
        *dashboard*|*ui*)
            actions+=("{\"description\": \"Test UI components and user experience\", \"command\": null, \"priority\": \"medium\", \"context\": \"UI/UX validation\"}")
            ;;
        *api*|*backend*)
            actions+=("{\"description\": \"Validate API endpoints and data flow\", \"command\": null, \"priority\": \"medium\", \"context\": \"Backend functionality verification\"}")
            ;;
        *cogspace*)
            actions+=("{\"description\": \"Test session management and cognitive preservation\", \"command\": null, \"priority\": \"high\", \"context\": \"Core COGSPACE functionality\"}")
            ;;
    esac
    
    # Return JSON array
    if [[ ${#actions[@]} -eq 0 ]]; then
        echo '[]'
    else
        local json_actions
        json_actions=$(IFS=','; echo "[${actions[*]}]")
        echo "$json_actions"
    fi
}

# Main execution if called directly
if [[ "${BASH_SOURCE[0]:-}" == "${0}" ]]; then
    case "${1:-}" in
        "work_state")
            analyze_current_work_state
            ;;
        "pending_tasks")
            extract_pending_tasks_from_session
            ;;
        "immediate_actions")
            generate_immediate_actions
            ;;
        *)
            echo "Usage: $0 {work_state|pending_tasks|immediate_actions}"
            echo ""
            echo "Commands:"
            echo "  work_state       - Analyze current work state and generate next session priority"
            echo "  pending_tasks    - Extract pending tasks from session context"
            echo "  immediate_actions - Generate JSON array of immediate actions"
            ;;
    esac
fi

