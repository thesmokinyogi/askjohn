#!/bin/bash
# COGSPACE v40.0.0
# COGSPACE Revolution v20.0.0 - Quality Validator Skill
# Brilliant Binary Speed Implementation by Bob
# Mission Critical: Multi-layer context quality validation

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

#═══════════════════════════════════════════════════════════════════════════════
# QUALITY VALIDATOR - 5-Layer Validation System
#═══════════════════════════════════════════════════════════════════════════════

cogspace_validate_context_quality() {
  local context_input="$1"
  local context_data=""

  # Accept file path or JSON string
  if [[ -f "$context_input" ]]; then
    context_data=$(cat "$context_input")
  else
    context_data="$context_input"
  fi

  # Validate JSON structure
  if ! echo "$context_data" | jq empty 2>/dev/null; then
    echo "{\"error\": \"Invalid JSON input\", \"overallScore\": 0}"
    return 1
  fi

  # Layer 1: Schema Validation
  local layer1=$(cogspace_validate_schema "$context_data")
  local layer1_score=$(echo "$layer1" | jq -r '.score')

  # Layer 2: Content Validation
  local layer2=$(cogspace_validate_content "$context_data")
  local layer2_score=$(echo "$layer2" | jq -r '.score')

  # Layer 3: Completeness Validation
  local layer3=$(cogspace_validate_completeness "$context_data")
  local layer3_score=$(echo "$layer3" | jq -r '.score')

  # Layer 4: Continuity Validation
  local layer4=$(cogspace_validate_continuity "$context_data")
  local layer4_score=$(echo "$layer4" | jq -r '.score')

  # Layer 5: Cross-Project Validation
  local layer5=$(cogspace_validate_crossproject "$context_data")
  local layer5_score=$(echo "$layer5" | jq -r '.score')

  # Calculate overall score (weighted average)
  local overall_score=$(echo "$layer1_score $layer2_score $layer3_score $layer4_score $layer5_score" | \
    awk '{print int(($1*0.25 + $2*0.30 + $3*0.25 + $4*0.15 + $5*0.05))}')

  # Collect issues and recommendations
  local all_issues=$(cat <<EOF | jq -s 'add'
$layer1
$layer2
$layer3
$layer4
$layer5
EOF
)

  local issues=$(echo "$all_issues" | jq -s '[.[].issues[]?] | unique')
  local recommendations=$(echo "$all_issues" | jq -s '[.[].recommendations[]?] | unique')

  # Build validation result
  local validation_result=$(cat <<EOF
{
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "overallScore": $overall_score,
  "layers": {
    "layer1_schema": $layer1,
    "layer2_content": $layer2,
    "layer3_completeness": $layer3,
    "layer4_continuity": $layer4,
    "layer5_crossproject": $layer5
  },
  "issues": $issues,
  "recommendations": $recommendations,
  "quality_grade": "$(cogspace_quality_grade $overall_score)",
  "passed": $([ $overall_score -ge 60 ] && echo 'true' || echo 'false')
}
EOF
)

  echo "$validation_result"
}

#═══════════════════════════════════════════════════════════════════════════════
# LAYER 1: Schema Validation
#═══════════════════════════════════════════════════════════════════════════════

cogspace_validate_schema() {
  local context_data="$1"
  local score=100
  local issues=()
  local recommendations=()

  # Required fields
  local required_fields=("sessionId" "timestamp" "synthesized" "git" "conversation")

  for field in "${required_fields[@]}"; do
    if ! echo "$context_data" | jq -e ".$field" >/dev/null 2>&1; then
      score=$((score - 20))
      issues+=("Missing required field: $field")
      recommendations+=("Add $field to context structure")
    fi
  done

  # Validate timestamp format
  local timestamp=$(echo "$context_data" | jq -r '.timestamp // empty')
  if [[ -n "$timestamp" ]] && ! [[ "$timestamp" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2} ]]; then
    score=$((score - 10))
    issues+=("Invalid timestamp format")
    recommendations+=("Use ISO 8601 timestamp format")
  fi

  # Ensure score doesn't go negative
  if [[ $score -lt 0 ]]; then
    score=0
  fi

  # Build result
  local issues_json=$(if [[ ${#issues[@]} -gt 0 ]]; then printf '%s\n' "${issues[@]}"; fi | jq -R . | jq -s .)
  local recommendations_json=$(if [[ ${#recommendations[@]} -gt 0 ]]; then printf '%s\n' "${recommendations[@]}"; fi | jq -R . | jq -s .)

  cat <<EOF
{
  "layer": "schema",
  "score": $score,
  "issues": $issues_json,
  "recommendations": $recommendations_json
}
EOF
}

#═══════════════════════════════════════════════════════════════════════════════
# LAYER 2: Content Validation
#═══════════════════════════════════════════════════════════════════════════════

cogspace_validate_content() {
  local context_data="$1"
  local score=100
  local issues=()
  local recommendations=()

  # Check for generic/placeholder content
  local synthesized=$(echo "$context_data" | jq -r '.synthesized.technicalSummary // .synthesized // empty' 2>/dev/null)

  if echo "$synthesized" | grep -qiE '(lorem ipsum|placeholder|todo|tbd|fixme|xxx|generic|template)'; then
    score=$((score - 40))
    issues+=("Generic or placeholder content detected")
    recommendations+=("Replace placeholder content with actual session context")
  fi

  # Check git diff exists and is meaningful
  local git_diff=$(echo "$context_data" | jq -r '.git.changes.diff // empty' 2>/dev/null)

  if [[ -z "$git_diff" ]] || [[ "$git_diff" == "null" ]] || [[ "$git_diff" == '""' ]]; then
    score=$((score - 30))
    issues+=("No git diff captured")
    recommendations+=("Capture git diff in session context")
  fi

  # Check conversation content quality
  local conversation=$(echo "$context_data" | jq -r '.conversation.summary // empty' 2>/dev/null)

  if [[ -z "$conversation" ]] || [[ "$conversation" == "null" ]] || [[ "$conversation" == '""' ]]; then
    score=$((score - 20))
    issues+=("No conversation context captured")
    recommendations+=("Add conversation summary to context")
  elif [[ ${#conversation} -lt 50 ]]; then
    score=$((score - 10))
    issues+=("Conversation summary too brief")
    recommendations+=("Expand conversation summary with more details")
  fi

  # Check work summary exists
  local work_summary=$(echo "$context_data" | jq -r '.workSummary // .metadata.workSummary // empty' 2>/dev/null)

  if [[ -z "$work_summary" ]] || [[ "$work_summary" == "null" ]] || [[ "$work_summary" == '""' ]]; then
    score=$((score - 10))
    issues+=("No work summary provided")
    recommendations+=("Add work summary describing session accomplishments")
  fi

  # Ensure score doesn't go negative
  if [[ $score -lt 0 ]]; then
    score=0
  fi

  # Build result
  local issues_json=$(if [[ ${#issues[@]} -gt 0 ]]; then printf '%s\n' "${issues[@]}"; fi | jq -R . | jq -s .)
  local recommendations_json=$(if [[ ${#recommendations[@]} -gt 0 ]]; then printf '%s\n' "${recommendations[@]}"; fi | jq -R . | jq -s .)

  cat <<EOF
{
  "layer": "content",
  "score": $score,
  "issues": $issues_json,
  "recommendations": $recommendations_json
}
EOF
}

#═══════════════════════════════════════════════════════════════════════════════
# LAYER 3: Completeness Validation
#═══════════════════════════════════════════════════════════════════════════════

cogspace_validate_completeness() {
  local context_data="$1"
  local score=100
  local issues=()
  local recommendations=()

  # Check for key context components
  local components=(
    "sessionId:20:Session ID missing"
    "git.changes.modifiedFiles:15:No modified files tracked"
    "git.history.recentCommits:10:No commit history"
    "conversation.keyTopics:15:No key topics extracted"
    "conversation.codeReferences:10:No code references"
    "synthesized.technicalSummary:20:No technical summary"
    "git.metrics.totalLinesChanged:10:No change metrics"
  )

  for component in "${components[@]}"; do
    IFS=':' read -r path points message <<< "$component"

    if ! echo "$context_data" | jq -e ".$path" >/dev/null 2>&1; then
      score=$((score - points))
      issues+=("$message")
      recommendations+=("Add $path to context")
    else
      # Check if value is meaningful (not empty array/object/string)
      local value=$(echo "$context_data" | jq -r ".$path // empty" 2>/dev/null)

      if [[ "$value" == "[]" ]] || [[ "$value" == "{}" ]] || [[ "$value" == '""' ]] || [[ -z "$value" ]]; then
        score=$((score - points / 2))
        issues+=("$message (empty value)")
        recommendations+=("Populate $path with actual data")
      fi
    fi
  done

  # Ensure score doesn't go negative
  if [[ $score -lt 0 ]]; then
    score=0
  fi

  # Build result
  local issues_json=$(if [[ ${#issues[@]} -gt 0 ]]; then printf '%s\n' "${issues[@]}"; fi | jq -R . | jq -s .)
  local recommendations_json=$(if [[ ${#recommendations[@]} -gt 0 ]]; then printf '%s\n' "${recommendations[@]}"; fi | jq -R . | jq -s .)

  cat <<EOF
{
  "layer": "completeness",
  "score": $score,
  "issues": $issues_json,
  "recommendations": $recommendations_json
}
EOF
}

#═══════════════════════════════════════════════════════════════════════════════
# LAYER 4: Continuity Validation
#═══════════════════════════════════════════════════════════════════════════════

cogspace_validate_continuity() {
  local context_data="$1"
  local score=100
  local issues=()
  local recommendations=()

  # Check for cross-session references
  local previous_sessions=$(echo "$context_data" | jq -r '.conversation.contextualLinks.previousSessions // empty' 2>/dev/null)

  if [[ -z "$previous_sessions" ]] || [[ "$previous_sessions" == "[]" ]]; then
    score=$((score - 25))
    issues+=("No links to previous sessions")
    recommendations+=("Add references to related previous sessions")
  fi

  # Check for pattern references
  local related_patterns=$(echo "$context_data" | jq -r '.conversation.contextualLinks.relatedPatterns // empty' 2>/dev/null)

  if [[ -z "$related_patterns" ]] || [[ "$related_patterns" == "[]" ]]; then
    score=$((score - 20))
    issues+=("No pattern library references")
    recommendations+=("Link to relevant patterns from knowledge library")
  fi

  # Check for temporal context (timestamp validity)
  local timestamp=$(echo "$context_data" | jq -r '.timestamp // empty')

  if [[ -z "$timestamp" ]]; then
    score=$((score - 15))
    issues+=("Missing timestamp for continuity tracking")
    recommendations+=("Add timestamp to enable session sequencing")
  fi

  # Check for session progression indicators
  local next_steps=$(echo "$context_data" | jq -r '.synthesized.nextSteps // empty' 2>/dev/null)

  if [[ -z "$next_steps" ]] || [[ "$next_steps" == "null" ]]; then
    score=$((score - 20))
    issues+=("No next steps defined for continuity")
    recommendations+=("Add nextSteps to guide future sessions")
  fi

  # Check for decision trail
  local decisions=$(echo "$context_data" | jq -r '.conversation.decisions // empty' 2>/dev/null)

  if [[ -z "$decisions" ]] || [[ "$decisions" == "[]" ]]; then
    score=$((score - 20))
    issues+=("No decision trail captured")
    recommendations+=("Document key decisions for future reference")
  fi

  # Ensure score doesn't go negative
  if [[ $score -lt 0 ]]; then
    score=0
  fi

  # Build result
  local issues_json=$(if [[ ${#issues[@]} -gt 0 ]]; then printf '%s\n' "${issues[@]}"; fi | jq -R . | jq -s .)
  local recommendations_json=$(if [[ ${#recommendations[@]} -gt 0 ]]; then printf '%s\n' "${recommendations[@]}"; fi | jq -R . | jq -s .)

  cat <<EOF
{
  "layer": "continuity",
  "score": $score,
  "issues": $issues_json,
  "recommendations": $recommendations_json
}
EOF
}

#═══════════════════════════════════════════════════════════════════════════════
# LAYER 5: Cross-Project Validation
#═══════════════════════════════════════════════════════════════════════════════

cogspace_validate_crossproject() {
  local context_data="$1"
  local score=100
  local issues=()
  local recommendations=()

  # This layer validates context can be shared across projects
  # Lower weight (5%) but important for COGSPACE ecosystem

  # Check for project identification
  local project_root=$(echo "$context_data" | jq -r '.git.repository.root // empty' 2>/dev/null)

  if [[ -z "$project_root" ]] || [[ "$project_root" == "null" ]]; then
    score=$((score - 30))
    issues+=("No project identification")
    recommendations+=("Add project root to enable cross-project linking")
  fi

  # Check for technology tags
  local technologies=$(echo "$context_data" | jq -r '.synthesized.technicalSummary.technologies // empty' 2>/dev/null)

  if [[ -z "$technologies" ]] || [[ "$technologies" == "[]" ]]; then
    score=$((score - 25))
    issues+=("No technology tags for cross-project discovery")
    recommendations+=("Add technology tags to enable project clustering")
  fi

  # Check for reusable patterns
  local patterns=$(echo "$context_data" | jq -r '.conversation.contextualLinks.relatedPatterns // empty' 2>/dev/null)

  if [[ -z "$patterns" ]] || [[ "$patterns" == "[]" ]]; then
    score=$((score - 25))
    issues+=("No reusable patterns identified")
    recommendations+=("Extract patterns that can benefit other projects")
  fi

  # Check for remote repository (for collaboration)
  local remote=$(echo "$context_data" | jq -r '.git.repository.remote // empty' 2>/dev/null)

  if [[ -z "$remote" ]] || [[ "$remote" == "none" ]]; then
    score=$((score - 20))
    issues+=("No remote repository for collaboration")
    recommendations+=("Configure remote repository for team collaboration")
  fi

  # Ensure score doesn't go negative
  if [[ $score -lt 0 ]]; then
    score=0
  fi

  # Build result
  local issues_json=$(if [[ ${#issues[@]} -gt 0 ]]; then printf '%s\n' "${issues[@]}"; fi | jq -R . | jq -s .)
  local recommendations_json=$(if [[ ${#recommendations[@]} -gt 0 ]]; then printf '%s\n' "${recommendations[@]}"; fi | jq -R . | jq -s .)

  cat <<EOF
{
  "layer": "crossproject",
  "score": $score,
  "issues": $issues_json,
  "recommendations": $recommendations_json
}
EOF
}

#═══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
#═══════════════════════════════════════════════════════════════════════════════

cogspace_quality_grade() {
  local score=$1

  if [[ $score -ge 90 ]]; then
    echo "EXCELLENT"
  elif [[ $score -ge 80 ]]; then
    echo "GOOD"
  elif [[ $score -ge 70 ]]; then
    echo "ACCEPTABLE"
  elif [[ $score -ge 60 ]]; then
    echo "NEEDS_IMPROVEMENT"
  else
    echo "POOR"
  fi
}

cogspace_display_validation_report() {
  local validation_result="$1"

  local overall_score=$(echo "$validation_result" | jq -r '.overallScore')
  local grade=$(echo "$validation_result" | jq -r '.quality_grade')
  local passed=$(echo "$validation_result" | jq -r '.passed')

  echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
  echo -e "${CYAN}   COGSPACE CONTEXT QUALITY VALIDATION REPORT${NC}"
  echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
  echo ""

  # Overall score
  if [[ "$passed" == "true" ]]; then
    echo -e "${GREEN}✅ OVERALL SCORE: $overall_score/100 ($grade)${NC}"
  else
    echo -e "${RED}❌ OVERALL SCORE: $overall_score/100 ($grade)${NC}"
  fi

  echo ""
  echo -e "${YELLOW}Layer Scores:${NC}"
  echo "$validation_result" | jq -r '.layers | to_entries[] | "  \(.key): \(.value.score)/100"'

  echo ""
  local issue_count=$(echo "$validation_result" | jq -r '.issues | length')

  if [[ $issue_count -gt 0 ]]; then
    echo -e "${RED}Issues Found ($issue_count):${NC}"
    echo "$validation_result" | jq -r '.issues[] | "  ❌ \(.)"'
    echo ""
  fi

  local rec_count=$(echo "$validation_result" | jq -r '.recommendations | length')

  if [[ $rec_count -gt 0 ]]; then
    echo -e "${YELLOW}Recommendations ($rec_count):${NC}"
    echo "$validation_result" | jq -r '.recommendations[] | "  💡 \(.)"'
  fi

  echo ""
  echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
}

#═══════════════════════════════════════════════════════════════════════════════
# QUALITY VALIDATOR - Main Entry Point
#═══════════════════════════════════════════════════════════════════════════════

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  # Script called directly for testing
  echo -e "${CYAN}✅ COGSPACE Quality Validator - Test Mode${NC}"

  CONTEXT_FILE="${1:-.cogspace/context.json}"

  if [[ ! -f "$CONTEXT_FILE" ]]; then
    echo -e "${RED}❌ Context file not found: $CONTEXT_FILE${NC}"
    exit 1
  fi

  echo -e "${YELLOW}Validating context: $CONTEXT_FILE${NC}"
  echo ""

  RESULT=$(cogspace_validate_context_quality "$CONTEXT_FILE")

  cogspace_display_validation_report "$RESULT"
fi


