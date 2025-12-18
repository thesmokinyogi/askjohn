#!/bin/bash
# COGSPACE v40.2.1
# COGSPACE Git Integration Helper Functions
# Provides GitHub sync, DNA version checking, and README enhancement utilities

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m'

# ============================================================================
# GITHUB CONFIGURATION FUNCTIONS
# ============================================================================

# Check if git is configured for this project
cogspace_git_configured() {
  [[ -f ".cogspace-git-config.json" ]] && \
  [[ $(jq -r '.enabled // false' .cogspace-git-config.json 2>/dev/null) == "true" ]]
}

# Get git config value
cogspace_git_config() {
  local key="$1"
  local default="${2:-false}"
  if [[ -f ".cogspace-git-config.json" ]]; then
    jq -r ".${key} // \"${default}\"" .cogspace-git-config.json 2>/dev/null || echo "$default"
  else
    echo "$default"
  fi
}

# Check if git repository exists and is healthy
cogspace_git_healthy() {
  [[ -d ".git" ]] && \
  git rev-parse --git-dir >/dev/null 2>&1 && \
  git remote get-url origin >/dev/null 2>&1
}

# ============================================================================
# GIT OPERATIONS
# ============================================================================

# Safe git pull with conflict handling
cogspace_git_pull() {
  local strategy=$(cogspace_git_config "conflictResolution" "stash-pull-pop")

  # Check if remote branch exists first
  if ! git ls-remote --exit-code --heads origin main >/dev/null 2>&1; then
    # Get developer name for personalized message
    local dev_name=$(git config user.name 2>/dev/null || echo "Developer")

    echo ""
    echo -e "${YELLOW}ℹ️  Remote branch 'main' doesn't exist yet${NC}"
    echo -e "${BLUE}   This is normal for new repositories before the first push${NC}"
    echo ""
    echo -e "${CYAN}💡 ${dev_name}, would you like to push your code to GitHub now?${NC}"
    echo -e "${BLUE}   This will:${NC}"
    echo -e "${BLUE}   • Create the remote 'main' branch${NC}"
    echo -e "${BLUE}   • Back up your code to the cloud${NC}"
    echo -e "${BLUE}   • Enable automatic sync on future wake/sleep cycles${NC}"
    echo ""
    echo -e "${GREEN}Push to GitHub now? (Y/n):${NC}"
    read -r should_push

    if [[ ! "$should_push" =~ ^[Nn]$ ]]; then
      echo ""
      echo -e "${CYAN}🚀 Pushing to GitHub...${NC}"

      # Ensure there's at least one commit
      if ! git rev-parse HEAD >/dev/null 2>&1; then
        echo -e "${YELLOW}   Creating initial commit first...${NC}"
        git add .gitignore README.md .cogspace-git-config.json 2>/dev/null || true
        git commit -m "Initial commit: COGSPACE project

🤖 Auto-initialized by COGSPACE wake cycle
" >/dev/null 2>&1 || true
      fi

      # Push to create remote branch
      if git push -u origin main 2>&1; then
        echo -e "${GREEN}✅ Successfully pushed to GitHub!${NC}"
        echo -e "${GREEN}   Remote branch 'main' created${NC}"
        echo -e "${BLUE}   Future wake cycles will auto-pull from here${NC}"
      else
        echo -e "${YELLOW}⚠️  Push failed - you may need to authenticate or check remote URL${NC}"
        echo -e "${YELLOW}   Run 'git push -u origin main' manually when ready${NC}"
      fi
    else
      echo ""
      echo -e "${YELLOW}ℹ️  Skipping push - continuing with local repository${NC}"
      echo -e "${BLUE}   You can push manually anytime with: git push -u origin main${NC}"
    fi

    echo ""
    return 0  # Success - nothing to pull yet
  fi

  case "$strategy" in
    "stash-pull-pop")
      if [[ -n $(git status --porcelain) ]]; then
        git stash push -m "COGSPACE auto-stash $(date +%s)" >/dev/null 2>&1
      fi

      if git pull --rebase origin main >/dev/null 2>&1; then
        if git stash list | grep -q "COGSPACE auto-stash"; then
          git stash pop >/dev/null 2>&1
        fi
        return 0
      else
        if git stash list | grep -q "COGSPACE auto-stash"; then
          git stash pop >/dev/null 2>&1
        fi
        return 1
      fi
      ;;
    "abort")
      git pull origin main || return 1
      ;;
    "keep-local")
      # Don't pull - keep local version
      return 0
      ;;
  esac
}

# Safe git push with retry logic
cogspace_git_push() {
  local max_retries=3
  local retry_count=0

  while [[ $retry_count -lt $max_retries ]]; do
    if git push origin main 2>&1; then
      return 0
    else
      retry_count=$((retry_count + 1))
      if [[ $retry_count -lt $max_retries ]]; then
        echo -e "${YELLOW}⚠️  Push failed, retrying ($retry_count/$max_retries)...${NC}"
        sleep 2
      fi
    fi
  done

  return 1
}

# Generate commit message from cognitive context
cogspace_git_commit_msg() {
  local prefix="$1"
  local message="$2"
  local session_id="$3"
  local work_summary="${4:-Session completed}"

  cat <<EOF
${prefix} ${message}

Session: ${session_id}
Timestamp: $(date -u +"%Y-%m-%dT%H:%M:%S.%3NZ")
Work Summary: ${work_summary}

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>
EOF
}

# ============================================================================
# DNA VERSION CHECKING FUNCTIONS
# ============================================================================

# Check COGSPACE DNA version
cogspace_check_dna_version() {
  local project_version=$(cat .session-dna-version 2>/dev/null || echo "unknown")
  local dna_source="/Volumes/FOUR-TB/cogspace-dna-source/DNA-VERSION.json"

  if [[ ! -f "$dna_source" ]]; then
    return 0  # DNA source not available, skip check
  fi

  local latest_version=$(jq -r '.version' "$dna_source" 2>/dev/null || echo "unknown")

  if [[ "$project_version" != "$latest_version" ]] && [[ "$latest_version" != "unknown" ]]; then
    return 1  # Versions don't match
  fi

  return 0  # Up to date or can't determine
}

# Get DNA version info for display
cogspace_dna_version_info() {
  local project_version=$(cat .session-dna-version 2>/dev/null || echo "unknown")
  local dna_source="/Volumes/FOUR-TB/cogspace-dna-source/DNA-VERSION.json"

  if [[ ! -f "$dna_source" ]]; then
    echo "unknown|unknown|unknown"
    return
  fi

  local latest_version=$(jq -r '.version' "$dna_source" 2>/dev/null || echo "unknown")
  local codename=$(jq -r '.codename' "$dna_source" 2>/dev/null || echo "unknown")

  echo "${project_version}|${latest_version}|${codename}"
}

# Display DNA update banner
cogspace_display_dna_update() {
  local info=$(cogspace_dna_version_info)
  IFS='|' read -r current latest codename <<< "$info"

  if [[ "$current" == "$latest" ]] || [[ "$latest" == "unknown" ]]; then
    return 0  # No update needed
  fi

  local dna_source="/Volumes/FOUR-TB/cogspace-dna-source/DNA-VERSION.json"

  echo ""
  echo -e "${CYAN}╔═══════════════════════════════════════════════════════════╗${NC}"
  echo -e "${CYAN}║${NC}  ${YELLOW}📦 COGSPACE DNA Update Available${NC}                       ${CYAN}║${NC}"
  echo -e "${CYAN}╠═══════════════════════════════════════════════════════════╣${NC}"
  printf "${CYAN}║${NC}  Current Version:  ${RED}v%-33s${NC} ${CYAN}║${NC}\n" "$current"
  printf "${CYAN}║${NC}  Latest Version:   ${GREEN}v%-33s${NC} ${CYAN}║${NC}\n" "$latest ($codename)"
  echo -e "${CYAN}║${NC}                                                           ${CYAN}║${NC}"
  echo -e "${CYAN}║${NC}  ${WHITE}What's New:${NC}                                            ${CYAN}║${NC}"

  # Extract and display features
  local version_key="v${latest//./_}_${codename// /}"
  local features=$(jq -r ".[\"$version_key\"] | .majorFeatures[]? // empty" "$dna_source" 2>/dev/null | head -3)

  if [[ -n "$features" ]]; then
    while IFS= read -r feature; do
      local feature_truncated=$(echo "$feature" | cut -c1-50)
      printf "${CYAN}║${NC}    ${GREEN}•${NC} %-50s ${CYAN}║${NC}\n" "$feature_truncated"
    done <<< "$features"
  else
    echo -e "${CYAN}║${NC}    ${GREEN}•${NC} See DNA-VERSION.json for details                   ${CYAN}║${NC}"
  fi

  echo -e "${CYAN}║${NC}                                                           ${CYAN}║${NC}"
  echo -e "${CYAN}║${NC}  ${BLUE}Upgrade:${NC} ./cogspace/upgrade-dna.sh                     ${CYAN}║${NC}"
  echo -e "${CYAN}╚═══════════════════════════════════════════════════════════╝${NC}"
  echo ""
}

# ============================================================================
# README ENHANCEMENT FUNCTIONS
# ============================================================================

# Check if README enhancement is enabled
cogspace_readme_enhancement_enabled() {
  if ! cogspace_git_configured; then
    return 1
  fi

  local enabled=$(cogspace_git_config "readmeEnhancement.enabled" "false")
  [[ "$enabled" == "true" ]]
}

# Get README interactive mode setting
cogspace_readme_interactive() {
  cogspace_git_config "readmeEnhancement.interactive" "true"
}

# Extract session features from cognitive context
cogspace_extract_session_features() {
  local context_file="session-management/cognitive-context/session-context-enhanced.json"

  if [[ ! -f "$context_file" ]]; then
    echo ""
    return
  fi

  jq -r '.workNarrative.completedTasks[]?.description // empty' "$context_file" 2>/dev/null | \
    tr '\n' '|' | sed 's/|$//'
}

# Extract session work summary from cognitive context
cogspace_extract_work_summary() {
  local context_file="session-management/cognitive-context/session-context-enhanced.json"

  if [[ ! -f "$context_file" ]]; then
    echo "Session work completed"
    return
  fi

  jq -r '.workNarrative.summary // "Session work completed"' "$context_file" 2>/dev/null
}

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

# Check if jq is available
cogspace_check_jq() {
  if ! command -v jq &> /dev/null; then
    echo -e "${RED}❌ jq is required but not installed${NC}"
    echo -e "${YELLOW}Install with: brew install jq${NC}"
    return 1
  fi
  return 0
}

# Check if git is available
cogspace_check_git() {
  if ! command -v git &> /dev/null; then
    echo -e "${RED}❌ git is required but not installed${NC}"
    return 1
  fi
  return 0
}

# Check if node is available (for README enhancement)
cogspace_check_node() {
  if ! command -v node &> /dev/null; then
    echo -e "${RED}❌ node is required for README enhancement${NC}"
    echo -e "${YELLOW}Install with: brew install node${NC}"
    return 1
  fi
  return 0
}

# Validate all dependencies
cogspace_validate_dependencies() {
  local all_ok=true

  if ! cogspace_check_jq; then
    all_ok=false
  fi

  if ! cogspace_check_git; then
    all_ok=false
  fi

  # Node is optional - only needed for README enhancement
  if cogspace_readme_enhancement_enabled && ! cogspace_check_node; then
    echo -e "${YELLOW}⚠️  README enhancement will be disabled${NC}"
  fi

  if [[ "$all_ok" == "false" ]]; then
    return 1
  fi

  return 0
}


