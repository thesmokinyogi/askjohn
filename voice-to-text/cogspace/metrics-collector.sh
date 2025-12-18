#!/bin/bash
# COGSPACE v40.2.1
# COGSPACE Revolution v20.0.0 - Metrics Collector
# Brilliant Binary Speed Implementation by Bob
# Mission Critical: Prometheus-compatible metrics

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

#═══════════════════════════════════════════════════════════════════════════════
# METRICS COLLECTOR - Prometheus Format
#═══════════════════════════════════════════════════════════════════════════════

METRICS_FILE="/tmp/cogspace-metrics.txt"

cogspace_metric_increment() {
  local metric_name="$1"
  local value="${2:-1}"
  local timestamp=$(date +%s)000  # milliseconds

  echo "cogspace_${metric_name}_total $value $timestamp" >> "$METRICS_FILE"
}

cogspace_metric_set() {
  local metric_name="$1"
  local value="$2"
  local timestamp=$(date +%s)000

  echo "cogspace_${metric_name} $value $timestamp" >> "$METRICS_FILE"
}

cogspace_metric_gauge() {
  local metric_name="$1"
  local value="$2"

  # For gauges, we write to a separate file that Prometheus scrapes
  local gauge_file="/tmp/cogspace-gauges.txt"

  # Update or append gauge value
  if grep -q "^cogspace_${metric_name} " "$gauge_file" 2>/dev/null; then
    sed -i.bak "s/^cogspace_${metric_name} .*/cogspace_${metric_name} $value/" "$gauge_file"
  else
    echo "cogspace_${metric_name} $value" >> "$gauge_file"
  fi
}

#═══════════════════════════════════════════════════════════════════════════════
# SESSION METRICS
#═══════════════════════════════════════════════════════════════════════════════

cogspace_record_session_wake() {
  cogspace_metric_increment "session_wake"
}

cogspace_record_session_sleep() {
  cogspace_metric_increment "session_sleep"
}

cogspace_record_session_duration() {
  local duration_seconds="$1"
  cogspace_metric_set "session_duration_seconds" "$duration_seconds"
}

cogspace_record_session_files_changed() {
  local count="$1"
  cogspace_metric_set "session_files_changed" "$count"
}

#═══════════════════════════════════════════════════════════════════════════════
# GITHUB METRICS
#═══════════════════════════════════════════════════════════════════════════════

cogspace_record_github_pull() {
  local success="${1:-false}"

  cogspace_metric_increment "github_pull"

  if [[ "$success" == "true" ]]; then
    cogspace_metric_increment "github_pull_success"
  else
    cogspace_metric_increment "github_pull_failure"
  fi
}

cogspace_record_github_push() {
  local success="${1:-false}"

  cogspace_metric_increment "github_push"

  if [[ "$success" == "true" ]]; then
    cogspace_metric_increment "github_push_success"
  else
    cogspace_metric_increment "github_push_failure"
  fi
}

#═══════════════════════════════════════════════════════════════════════════════
# CACHE METRICS
#═══════════════════════════════════════════════════════════════════════════════

cogspace_record_cache_stats() {
  # Source cache manager if available
  if [[ -f "cogspace/cache-manager.sh" ]]; then
    source cogspace/cache-manager.sh

    if cogspace_cache_available; then
      local stats=$(cogspace_cache_stats 2>/dev/null)

      if [[ -n "$stats" ]]; then
        local hit_rate=$(echo "$stats" | jq -r '.hitRate // 0' 2>/dev/null || echo "0")
        local total_keys=$(echo "$stats" | jq -r '.totalKeys // 0' 2>/dev/null || echo "0")

        cogspace_metric_gauge "cache_hit_rate" "$hit_rate"
        cogspace_metric_gauge "cache_keys_total" "$total_keys"
      fi
    fi
  fi
}

#═══════════════════════════════════════════════════════════════════════════════
# CONTEXT QUALITY METRICS
#═══════════════════════════════════════════════════════════════════════════════

cogspace_record_context_quality() {
  local quality_score="$1"
  cogspace_metric_set "context_quality_score" "$quality_score"
}

cogspace_record_context_validation() {
  local passed="${1:-false}"

  cogspace_metric_increment "context_validation"

  if [[ "$passed" == "true" ]]; then
    cogspace_metric_increment "context_validation_passed"
  else
    cogspace_metric_increment "context_validation_failed"
  fi
}

#═══════════════════════════════════════════════════════════════════════════════
# KNOWLEDGE SYNTHESIS METRICS
#═══════════════════════════════════════════════════════════════════════════════

cogspace_record_patterns_extracted() {
  local count="$1"
  cogspace_metric_set "patterns_extracted" "$count"
}

cogspace_record_patterns_library_size() {
  if [[ -f "cogspace/knowledge-library.json" ]]; then
    local total=$(jq -r '.metadata.totalPatterns // 0' cogspace/knowledge-library.json 2>/dev/null || echo "0")
    cogspace_metric_gauge "patterns_library_size" "$total"
  fi
}

#═══════════════════════════════════════════════════════════════════════════════
# METRICS SUMMARY
#═══════════════════════════════════════════════════════════════════════════════

cogspace_metrics_summary() {
  echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
  echo -e "${CYAN}   COGSPACE REVOLUTION v20.0 - METRICS SUMMARY${NC}"
  echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
  echo ""

  if [[ -f "$METRICS_FILE" ]]; then
    echo -e "${GREEN}✅ Metrics file: $METRICS_FILE${NC}"
    echo -e "${BLUE}Recent metrics (last 10):${NC}"
    tail -10 "$METRICS_FILE" 2>/dev/null || echo "No metrics yet"
  else
    echo -e "${YELLOW}⚠️  No metrics collected yet${NC}"
  fi

  echo ""

  if [[ -f "/tmp/cogspace-gauges.txt" ]]; then
    echo -e "${GREEN}✅ Gauges file: /tmp/cogspace-gauges.txt${NC}"
    echo -e "${BLUE}Current gauges:${NC}"
    cat /tmp/cogspace-gauges.txt 2>/dev/null || echo "No gauges yet"
  fi

  echo ""
  echo -e "${CYAN}Prometheus URL: http://localhost:9090${NC}"
  echo -e "${CYAN}Grafana URL: http://localhost:3000${NC}"
  echo ""
}

#═══════════════════════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
#═══════════════════════════════════════════════════════════════════════════════

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  # Script called directly
  case "${1:-summary}" in
    test)
      echo "Recording test metrics..."
      cogspace_record_session_wake
      cogspace_record_context_quality 95
      cogspace_record_patterns_extracted 5
      echo "Test metrics recorded"
      ;;
    summary|*)
      cogspace_metrics_summary
      ;;
  esac
fi


