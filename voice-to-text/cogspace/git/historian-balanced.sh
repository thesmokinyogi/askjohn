#!/bin/bash
# COGSPACE v40.0.0
# COGSPACE v23.1.0 - Balanced Git Historian
# Optimized for SMB/Network Storage with Comprehensive Context
# 23 essential git commands - balanced performance and completeness

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

#═══════════════════════════════════════════════════════════════════════════════
# Git Onboarding Message for Non-Git Projects
#═══════════════════════════════════════════════════════════════════════════════

cogspace_git_onboarding_message() {
  local project_name="$1"

  cat << 'EOF'

╔═══════════════════════════════════════════════════════════════╗
║  ⚠️  Git Repository Not Found                                 ║
╠═══════════════════════════════════════════════════════════════╣
EOF

  cat <<EOF
║                                                               ║
║  This project, ${project_name}, is not currently stored       ║
║  and backed up to a git repository.                           ║
EOF

  cat << 'EOF'
║                                                               ║
║  📌 Why Use Git?                                              ║
║    • Automatic backup of all your work                       ║
║    • Track every change with undo capability                 ║
║    • Easy team collaboration and code sharing                ║
║    • Integration with GitHub/GitLab for cloud backup         ║
║                                                               ║
║  🚀 Quick Setup Options:                                      ║
║                                                               ║
║    1. Create new GitHub repository (recommended):            ║
║       → Ask Claude: "add-new-repo"                           ║
║       → I'll guide you through GitHub setup                  ║
║                                                               ║
║    2. Initialize local git only:                             ║
║       → Run: git init                                        ║
║       → Changes tracked locally (no cloud backup)            ║
║                                                               ║
║    3. Connect to existing repository:                        ║
║       → Run: git clone <your-repo-url>                       ║
║                                                               ║
║  ℹ️  COGSPACE will work normally without git, but your       ║
║     work won't be backed up automatically.                   ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝

EOF
}

#═══════════════════════════════════════════════════════════════════════════════
# Balanced Git Historian - 23 Essential Commands
#═══════════════════════════════════════════════════════════════════════════════

cogspace_git_historian() {
  local session_id="$1"

  # Check for git repository
  if [[ ! -d ".git" ]]; then
    local project_name=$(basename "$PWD")
    cogspace_git_onboarding_message "$project_name" >&2
    echo "{\"error\": \"Not a git repository\", \"hasGit\": false, \"projectName\": \"$project_name\"}"
    return 1
  fi

  # BALANCED MODE: 23 essential git commands for comprehensive context
  # Category 1: Repository Identity (6 commands)
  local repo_root=$(git rev-parse --show-toplevel 2>/dev/null || echo "unknown")
  local remote=$(git remote get-url origin 2>/dev/null || echo "none")
  local branch=$(git branch --show-current 2>/dev/null || echo "unknown")
  local upstream=$(git rev-parse --abbrev-ref @{upstream} 2>/dev/null || echo "none")
  local commit=$(git rev-parse HEAD 2>/dev/null || echo "unknown")
  local short_commit=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")

  # Category 2: Change Summary (6 commands)
  local change_summary=$(git diff --shortstat HEAD 2>/dev/null || echo "No changes")
  local changed_files=$(git diff --name-only HEAD 2>/dev/null | wc -l | tr -d ' ')
  local staged_count=$(git diff --cached --name-only 2>/dev/null | wc -l | tr -d ' ')
  local staged_summary=$(git diff --cached --shortstat 2>/dev/null || echo "No staged changes")
  local unstaged_count=$(git diff --name-only 2>/dev/null | wc -l | tr -d ' ')
  local unstaged_summary=$(git diff --shortstat 2>/dev/null || echo "No unstaged changes")
  local untracked_count=$(git ls-files --others --exclude-standard 2>/dev/null | wc -l | tr -d ' ')

  # Category 3: History Context (5 commands)
  local last_commit_hash=$(git log -1 --pretty=%h 2>/dev/null || echo "none")
  local last_commit_subject=$(git log -1 --pretty=%s 2>/dev/null | head -c 100 || echo "No commits")
  local last_commit_author=$(git log -1 --pretty=%an 2>/dev/null || echo "unknown")
  local last_commit_date=$(git log -1 --pretty=%ai 2>/dev/null || echo "unknown")
  local commit_count=$(git rev-list --count HEAD 2>/dev/null || echo "0")

  # Category 4: Status Flags (4 commands)
  local is_dirty=$(git diff-index --quiet HEAD -- 2>/dev/null && echo "false" || echo "true")
  local has_untracked=$([ -n "$(git ls-files --others --exclude-standard 2>/dev/null)" ] && echo "true" || echo "false")
  local has_staged=$([ -n "$(git diff --cached --name-only 2>/dev/null)" ] && echo "true" || echo "false")
  local ahead_behind=$(cogspace_git_ahead_behind)

  # Category 5: Basic Metrics (2 commands)
  local total_files=$(git ls-files 2>/dev/null | wc -l | tr -d ' ')
  local changed_file_count=$(git diff --name-only HEAD 2>/dev/null | wc -l | tr -d ' ')

  # Generate JSON output
  cat <<EOF
{
  "sessionId": "$session_id",
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "mode": "balanced_23_commands",
  "repository": {
    "root": "$repo_root",
    "remote": "$remote",
    "branch": "$branch",
    "upstream": "$upstream",
    "commit": "$commit",
    "shortCommit": "$short_commit"
  },
  "changes": {
    "summary": "$change_summary",
    "fileCount": $changed_files,
    "staged": {
      "count": $staged_count,
      "summary": "$staged_summary"
    },
    "unstaged": {
      "count": $unstaged_count,
      "summary": "$unstaged_summary"
    },
    "untrackedCount": $untracked_count
  },
  "history": {
    "lastCommitHash": "$last_commit_hash",
    "lastCommitSubject": "$last_commit_subject",
    "lastCommitAuthor": "$last_commit_author",
    "lastCommitDate": "$last_commit_date",
    "commitCount": $commit_count
  },
  "status": {
    "isDirty": $is_dirty,
    "hasUntracked": $has_untracked,
    "hasStaged": $has_staged,
    "aheadBehind": "$ahead_behind"
  },
  "metrics": {
    "totalFiles": $total_files,
    "changedFiles": $changed_file_count
  },
  "performance": {
    "commandCount": 23,
    "estimatedTime": "500ms",
    "optimizedFor": "SMB_network_storage"
  }
}
EOF
}

cogspace_git_ahead_behind() {
  # Check how many commits ahead/behind upstream
  local upstream=$(git rev-parse --abbrev-ref @{upstream} 2>/dev/null)

  if [[ -z "$upstream" ]]; then
    echo "no_upstream"
    return
  fi

  local ahead=$(git rev-list --count ${upstream}..HEAD 2>/dev/null || echo '0')
  local behind=$(git rev-list --count HEAD..${upstream} 2>/dev/null || echo '0')

  echo "ahead_${ahead}_behind_${behind}"
}

cogspace_git_quality_score() {
  # Calculate git context quality score (0-100)
  local score=0

  # Has git repository (20 points)
  if [[ -d ".git" ]]; then
    score=$((score + 20))
  else
    echo "0"
    return
  fi

  # Has changes captured (30 points)
  if [[ -n "$(git diff HEAD 2>/dev/null)" ]]; then
    score=$((score + 30))
  fi

  # Has commit history (20 points)
  local commit_count=$(git rev-list --count HEAD 2>/dev/null || echo '0')
  if [[ $commit_count -gt 0 ]]; then
    score=$((score + 20))
  fi

  # Has remote configured (15 points)
  if git remote get-url origin >/dev/null 2>&1; then
    score=$((score + 15))
  fi

  # Has meaningful changes (15 points)
  local changed_files=$(git diff --name-only HEAD 2>/dev/null | wc -l)
  if [[ $changed_files -gt 0 ]]; then
    score=$((score + 15))
  fi

  echo "$score"
}

cogspace_git_extract_context_summary() {
  # Extract human-readable summary of git context
  local branch=$(git branch --show-current 2>/dev/null || echo 'unknown')
  local changed=$(git diff --name-only HEAD 2>/dev/null | wc -l | tr -d ' ')
  local staged=$(git diff --cached --name-only 2>/dev/null | wc -l | tr -d ' ')
  local untracked=$(git ls-files --others --exclude-standard 2>/dev/null | wc -l | tr -d ' ')
  local last_commit=$(git log -1 --pretty="%h - %s" 2>/dev/null || echo 'No commits')

  cat <<EOF
Branch: $branch
Last Commit: $last_commit
Changed Files: $changed (unstaged)
Staged Files: $staged
Untracked Files: $untracked
EOF
}

#═══════════════════════════════════════════════════════════════════════════════
# Main Entry Point
#═══════════════════════════════════════════════════════════════════════════════

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  # Script called directly for testing
  echo -e "${CYAN}📚 COGSPACE Git Historian - Balanced Mode (23 Commands)${NC}"
  echo ""

  SESSION_ID="${1:-test-$(date +%s)}"

  if [[ ! -d ".git" ]]; then
    PROJECT_NAME=$(basename "$PWD")
    echo -e "${RED}Not a git repository - showing onboarding message:${NC}"
    cogspace_git_onboarding_message "$PROJECT_NAME"
    exit 1
  fi

  echo -e "${YELLOW}Capturing comprehensive git context...${NC}"
  RESULT=$(cogspace_git_historian "$SESSION_ID")

  echo -e "${GREEN}✅ Git context captured${NC}"
  echo ""
  echo -e "${CYAN}Summary:${NC}"
  cogspace_git_extract_context_summary
  echo ""
  echo -e "${CYAN}Quality Score: $(cogspace_git_quality_score)/100${NC}"
  echo ""
  echo -e "${CYAN}Full JSON context:${NC}"
  echo "$RESULT" | jq . 2>/dev/null || echo "$RESULT"
fi


