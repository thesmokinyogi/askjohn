#!/bin/bash
# COGSPACE v40.0.0
# COGSPACE Revolution v20.0.0 - Conversation Weaver Skill
# Brilliant Binary Speed Implementation by Bob
# Mission Critical: Conversation context capture and weaving

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

#═══════════════════════════════════════════════════════════════════════════════
# CONVERSATION WEAVER - Intelligent Conversation Context Capture
#═══════════════════════════════════════════════════════════════════════════════

cogspace_weave_conversation() {
  local session_id="$1"
  local work_summary="${2:-}"
  local sleep_message="${3:-}"

  # Extract conversation context from multiple sources
  local conversation=$(cat <<EOF
{
  "sessionId": "$session_id",
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "summary": $(cogspace_extract_conversation_summary "$work_summary" "$sleep_message" | jq -Rs .),
  "keyTopics": $(cogspace_extract_key_topics "$work_summary" | jq -R . | jq -s .),
  "decisions": $(cogspace_extract_decisions | jq -R . | jq -s .),
  "codeReferences": $(cogspace_extract_code_references | jq -R . | jq -s .),
  "questionsAsked": $(cogspace_extract_questions "$work_summary" "$sleep_message" | jq -R . | jq -s .),
  "solutionsProvided": $(cogspace_extract_solutions "$work_summary" | jq -R . | jq -s .),
  "contextualLinks": {
    "previousSessions": $(cogspace_find_related_sessions),
    "relatedPatterns": $(cogspace_find_related_patterns)
  },
  "metadata": {
    "workSummary": $(echo "$work_summary" | jq -Rs .),
    "sleepMessage": $(echo "$sleep_message" | jq -Rs .),
    "conversationQuality": $(cogspace_assess_conversation_quality "$work_summary" "$sleep_message")
  }
}
EOF
)

  echo "$conversation"
}

cogspace_extract_conversation_summary() {
  local work_summary="$1"
  local sleep_message="$2"

  # Combine multiple sources into comprehensive summary
  local summary=""

  # Add work summary
  if [[ -n "$work_summary" ]]; then
    summary+="Work completed: $work_summary"$'\n'
  fi

  # Add sleep message
  if [[ -n "$sleep_message" ]]; then
    summary+="Session notes: $sleep_message"$'\n'
  fi

  # Add git commit messages as conversation context
  local recent_commits=$(git log --oneline -5 2>/dev/null || echo "")
  if [[ -n "$recent_commits" ]]; then
    summary+="Recent commits:"$'\n'"$recent_commits"$'\n'
  fi

  # Add file change context
  local changed_files=$(git diff --name-only HEAD 2>/dev/null | head -10)
  if [[ -n "$changed_files" ]]; then
    local file_count=$(echo "$changed_files" | wc -l | tr -d ' ')
    summary+="Modified $file_count files including key changes to:"$'\n'"$changed_files"$'\n'
  fi

  # If summary is still empty, provide default
  if [[ -z "$summary" ]]; then
    summary="Development session completed. Context preserved for continuity."
  fi

  echo "$summary"
}

cogspace_extract_key_topics() {
  local work_summary="$1"

  # Extract topics from work summary and git messages
  local all_text="$work_summary $(git log --oneline -10 2>/dev/null || echo '')"

  # Extract action keywords
  local topics=$(echo "$all_text" | \
    tr '[:upper:]' '[:lower:]' | \
    grep -oE '\b(implement|fix|add|update|refactor|optimize|create|build|enhance|improve|debug|test|deploy|configure|setup|install|migrate|upgrade|remove|delete|rename|move|copy|merge|rebase|cherry-pick|rollback|revert|patch|hotfix)\b' | \
    sort | uniq -c | sort -rn | awk '{print $2}')

  # Extract technology keywords
  local tech_topics=$(echo "$all_text" | \
    tr '[:upper:]' '[:lower:]' | \
    grep -oE '\b(react|vue|angular|node|python|typescript|javascript|golang|rust|java|ruby|php|bash|sql|redis|postgres|mysql|mongodb|docker|kubernetes|api|rest|graphql|auth|oauth|jwt|csrf|xss|sql-injection|performance|cache|optimization|test|unit|integration|e2e)\b' | \
    sort | uniq -c | sort -rn | awk '{print $2}')

  # Combine and deduplicate
  echo -e "$topics\n$tech_topics" | grep -v "^$" | sort | uniq
}

cogspace_extract_decisions() {
  # Extract architectural and technical decisions from commits
  git log --oneline -20 2>/dev/null | \
    grep -iE '(choose|decide|switch|migrate|adopt|use|change to|replace|instead of|opt for)' | \
    head -10 || echo "No explicit decisions detected in recent commits"
}

cogspace_extract_code_references() {
  # Extract file and function references from git changes
  local references=()

  # Files changed
  local files=$(git diff --name-only HEAD 2>/dev/null | head -20)
  if [[ -n "$files" ]]; then
    while IFS= read -r file; do
      references+=("$file")
    done <<< "$files"
  fi

  # Function/class definitions changed
  local functions=$(git diff HEAD 2>/dev/null | \
    grep -E '^[+](function|def |const .* =|class |export |async )' | \
    sed 's/^+//' | \
    head -10)

  if [[ -n "$functions" ]]; then
    while IFS= read -r func; do
      references+=("$func")
    done <<< "$functions"
  fi

  # Output unique references
  printf '%s\n' "${references[@]}" | head -20
}

cogspace_extract_questions() {
  local work_summary="$1"
  local sleep_message="$2"

  # Extract questions from work summary and messages
  local all_text="$work_summary $sleep_message"

  # Look for question patterns
  echo "$all_text" | \
    grep -oE '[^.!?]*\?[^.!?]*' | \
    sed 's/^[[:space:]]*//' | \
    head -5 || echo "No explicit questions found"
}

cogspace_extract_solutions() {
  local work_summary="$1"

  # Extract solution patterns from work summary
  echo "$work_summary" | \
    grep -iE '(solved|fixed|resolved|implemented|completed|finished|achieved|succeeded)' | \
    head -5 || echo "Session work completed"
}

cogspace_find_related_sessions() {
  # Find related previous sessions based on file overlap
  local current_files=$(git diff --name-only HEAD 2>/dev/null | tr '\n' '|' | sed 's/|$//')

  if [[ -z "$current_files" ]]; then
    echo "[]"
    return
  fi

  # Search recent context files for similar file changes
  local related=()
  local context_dir=".cogspace"

  if [[ -d "$context_dir" ]]; then
    # Find recent context files
    local recent_contexts=$(find "$context_dir" -name "enriched-context-*.json" -type f 2>/dev/null | sort -r | head -10)

    while IFS= read -r context_file; do
      if [[ -f "$context_file" ]]; then
        # Check if this context references similar files
        local has_overlap=$(jq -r '.git.changes.modifiedFiles[]?, .git.changes.addedFiles[]?' "$context_file" 2>/dev/null | \
          grep -E "$current_files" | head -1)

        if [[ -n "$has_overlap" ]]; then
          local session_id=$(jq -r '.sessionId' "$context_file" 2>/dev/null || echo "unknown")
          related+=("$session_id")
        fi
      fi
    done <<< "$recent_contexts"
  fi

  # Convert to JSON array - handle empty array case
  if [[ ${#related[@]} -gt 0 ]]; then
    printf '%s\n' "${related[@]}" | head -5 | jq -R . | jq -s .
  else
    echo "[]"
  fi
}

cogspace_find_related_patterns() {
  # Find related patterns from knowledge library
  local pattern_library="cogspace/knowledge-library.json"

  if [[ ! -f "$pattern_library" ]]; then
    echo "[]"
    return
  fi

  # Extract technologies from current session
  local current_files=$(git diff --name-only HEAD 2>/dev/null)
  local related_patterns=()

  # Match patterns by file extension/technology
  if echo "$current_files" | grep -q "\.tsx\?$"; then
    while IFS= read -r pattern; do
      [[ -n "$pattern" ]] && related_patterns+=("$pattern")
    done < <(jq -r '.patterns.typescript[]?, .patterns.react[]?' "$pattern_library" 2>/dev/null)
  fi

  if echo "$current_files" | grep -q "\.jsx\?$"; then
    while IFS= read -r pattern; do
      [[ -n "$pattern" ]] && related_patterns+=("$pattern")
    done < <(jq -r '.patterns.javascript[]?, .patterns.react[]?' "$pattern_library" 2>/dev/null)
  fi

  if echo "$current_files" | grep -q "\.py$"; then
    while IFS= read -r pattern; do
      [[ -n "$pattern" ]] && related_patterns+=("$pattern")
    done < <(jq -r '.patterns.python[]?' "$pattern_library" 2>/dev/null)
  fi

  # Convert to JSON array - handle empty array case
  if [[ ${#related_patterns[@]} -gt 0 ]]; then
    printf '%s\n' "${related_patterns[@]}" | head -10 | jq -R . | jq -s . 2>/dev/null || echo "[]"
  else
    echo "[]"
  fi
}

cogspace_assess_conversation_quality() {
  local work_summary="$1"
  local sleep_message="$2"

  local score=0

  # Has work summary (30 points)
  if [[ -n "$work_summary" ]] && [[ "$work_summary" != "Session work completed" ]]; then
    local word_count=$(echo "$work_summary" | wc -w | tr -d ' ')
    if [[ $word_count -gt 50 ]]; then
      score=$((score + 30))
    elif [[ $word_count -gt 20 ]]; then
      score=$((score + 20))
    elif [[ $word_count -gt 5 ]]; then
      score=$((score + 10))
    fi
  fi

  # Has sleep message (25 points)
  if [[ -n "$sleep_message" ]]; then
    local word_count=$(echo "$sleep_message" | wc -w | tr -d ' ')
    if [[ $word_count -gt 20 ]]; then
      score=$((score + 25))
    elif [[ $word_count -gt 10 ]]; then
      score=$((score + 15))
    elif [[ $word_count -gt 3 ]]; then
      score=$((score + 10))
    fi
  fi

  # Has commit messages (20 points)
  local commit_count=$(git log --oneline -5 2>/dev/null | wc -l | tr -d ' ')
  if [[ $commit_count -gt 3 ]]; then
    score=$((score + 20))
  elif [[ $commit_count -gt 0 ]]; then
    score=$((score + 10))
  fi

  # Has code references (15 points)
  local file_count=$(git diff --name-only HEAD 2>/dev/null | wc -l | tr -d ' ')
  if [[ $file_count -gt 5 ]]; then
    score=$((score + 15))
  elif [[ $file_count -gt 0 ]]; then
    score=$((score + 10))
  fi

  # Has related sessions (10 points)
  local related=$(cogspace_find_related_sessions | jq 'length' 2>/dev/null || echo '0')
  if [[ $related -gt 0 ]]; then
    score=$((score + 10))
  fi

  echo "$score"
}

#═══════════════════════════════════════════════════════════════════════════════
# CONVERSATION WEAVER - Main Entry Point
#═══════════════════════════════════════════════════════════════════════════════

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  # Script called directly for testing
  echo -e "${CYAN}🗣️  COGSPACE Conversation Weaver - Test Mode${NC}"

  SESSION_ID="${1:-test-$(date +%s)}"
  WORK_SUMMARY="${2:-Completed development work on core features}"
  SLEEP_MESSAGE="${3:-Session saved with comprehensive context}"

  echo -e "${YELLOW}Weaving conversation context...${NC}"
  RESULT=$(cogspace_weave_conversation "$SESSION_ID" "$WORK_SUMMARY" "$SLEEP_MESSAGE")

  QUALITY=$(echo "$RESULT" | jq -r '.metadata.conversationQuality')

  echo -e "${GREEN}✅ Conversation context woven${NC}"
  echo -e "${CYAN}Quality Score: $QUALITY/100${NC}"
  echo ""
  echo -e "${CYAN}Full JSON context:${NC}"
  echo "$RESULT" | jq .
fi


