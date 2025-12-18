#!/bin/bash
# COGSPACE v40.2.1
# COGSPACE Revolution v20.0.0 - Cache Manager
# Brilliant Binary Speed Implementation by Bob
# Mission Critical: Redis-backed intelligent caching

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

#═══════════════════════════════════════════════════════════════════════════════
# CACHE MANAGER - Redis-Backed Intelligent Caching
#═══════════════════════════════════════════════════════════════════════════════

# Cache key prefixes
COGSPACE_CACHE_PREFIX="cogspace:v20"

#═══════════════════════════════════════════════════════════════════════════════
# CORE CACHE OPERATIONS
#═══════════════════════════════════════════════════════════════════════════════

cogspace_cache_available() {
  # Check if Redis is available
  if command -v redis-cli >/dev/null 2>&1; then
    if redis-cli ping >/dev/null 2>&1; then
      return 0
    fi
  fi
  return 1
}

cogspace_cache_get() {
  local key="$1"

  if ! cogspace_cache_available; then
    return 1
  fi

  local full_key="${COGSPACE_CACHE_PREFIX}:${key}"
  local value=$(redis-cli GET "$full_key" 2>/dev/null)

  if [[ -n "$value" ]] && [[ "$value" != "(nil)" ]]; then
    echo "$value"
    return 0
  fi

  return 1
}

cogspace_cache_set() {
  local key="$1"
  local value="$2"
  local ttl="${3:-86400}"  # Default 24 hours

  if ! cogspace_cache_available; then
    return 1
  fi

  local full_key="${COGSPACE_CACHE_PREFIX}:${key}"
  redis-cli SETEX "$full_key" "$ttl" "$value" >/dev/null 2>&1
  return $?
}

cogspace_cache_delete() {
  local key="$1"

  if ! cogspace_cache_available; then
    return 1
  fi

  local full_key="${COGSPACE_CACHE_PREFIX}:${key}"
  redis-cli DEL "$full_key" >/dev/null 2>&1
  return $?
}

cogspace_cache_exists() {
  local key="$1"

  if ! cogspace_cache_available; then
    return 1
  fi

  local full_key="${COGSPACE_CACHE_PREFIX}:${key}"
  local exists=$(redis-cli EXISTS "$full_key" 2>/dev/null)

  if [[ "$exists" == "1" ]]; then
    return 0
  fi

  return 1
}

cogspace_cache_ttl() {
  local key="$1"

  if ! cogspace_cache_available; then
    echo "0"
    return 1
  fi

  local full_key="${COGSPACE_CACHE_PREFIX}:${key}"
  local ttl=$(redis-cli TTL "$full_key" 2>/dev/null)

  echo "$ttl"
}

cogspace_cache_flush() {
  local pattern="${1:-*}"

  if ! cogspace_cache_available; then
    return 1
  fi

  local full_pattern="${COGSPACE_CACHE_PREFIX}:${pattern}"

  # Get all matching keys and delete them
  redis-cli --scan --pattern "$full_pattern" 2>/dev/null | while read -r key; do
    redis-cli DEL "$key" >/dev/null 2>&1
  done

  return 0
}

#═══════════════════════════════════════════════════════════════════════════════
# CACHE STATISTICS
#═══════════════════════════════════════════════════════════════════════════════

cogspace_cache_stats() {
  if ! cogspace_cache_available; then
    echo "{\"available\": false}"
    return 1
  fi

  # Count total keys
  local total_keys=$(redis-cli --scan --pattern "${COGSPACE_CACHE_PREFIX}:*" 2>/dev/null | wc -l | tr -d ' ')

  # Get memory usage
  local memory_used=$(redis-cli INFO memory 2>/dev/null | grep "used_memory_human" | cut -d: -f2 | tr -d '\r\n ')

  # Calculate hit rate (stored in Redis)
  local hits=$(redis-cli GET "${COGSPACE_CACHE_PREFIX}:stats:hits" 2>/dev/null || echo "0")
  local misses=$(redis-cli GET "${COGSPACE_CACHE_PREFIX}:stats:misses" 2>/dev/null || echo "0")

  if [[ "$hits" == "(nil)" ]]; then hits=0; fi
  if [[ "$misses" == "(nil)" ]]; then misses=0; fi

  local total=$((hits + misses))
  local hit_rate=0

  if [[ $total -gt 0 ]]; then
    hit_rate=$(echo "scale=2; ($hits * 100) / $total" | bc)
  fi

  cat <<EOF
{
  "available": true,
  "totalKeys": $total_keys,
  "memoryUsed": "$memory_used",
  "hitRate": $hit_rate,
  "hits": $hits,
  "misses": $misses,
  "total": $total
}
EOF
}

cogspace_cache_record_hit() {
  if ! cogspace_cache_available; then
    return 1
  fi

  redis-cli INCR "${COGSPACE_CACHE_PREFIX}:stats:hits" >/dev/null 2>&1
}

cogspace_cache_record_miss() {
  if ! cogspace_cache_available; then
    return 1
  fi

  redis-cli INCR "${COGSPACE_CACHE_PREFIX}:stats:misses" >/dev/null 2>&1
}

#═══════════════════════════════════════════════════════════════════════════════
# DOMAIN-SPECIFIC CACHE OPERATIONS
#═══════════════════════════════════════════════════════════════════════════════

# README Technology Detection Cache
cogspace_cache_readme_tech() {
  local project_path="$1"
  local tech_json="$2"
  local action="${3:-get}"

  local cache_key="readme:tech:$(echo "$project_path" | md5)"

  if [[ "$action" == "set" ]]; then
    cogspace_cache_set "$cache_key" "$tech_json" 604800  # 7 days
    return $?
  else
    local cached=$(cogspace_cache_get "$cache_key")
    if [[ $? -eq 0 ]]; then
      cogspace_cache_record_hit
      echo "$cached"
      return 0
    else
      cogspace_cache_record_miss
      return 1
    fi
  fi
}

# Git Commit Template Cache
cogspace_cache_git_template() {
  local repo_name="$1"
  local template="$2"
  local action="${3:-get}"

  local cache_key="git:commit:$(echo "$repo_name" | md5)"

  if [[ "$action" == "set" ]]; then
    cogspace_cache_set "$cache_key" "$template" 604800  # 7 days
    return $?
  else
    local cached=$(cogspace_cache_get "$cache_key")
    if [[ $? -eq 0 ]]; then
      cogspace_cache_record_hit
      echo "$cached"
      return 0
    else
      cogspace_cache_record_miss
      return 1
    fi
  fi
}

# Research Results Cache
cogspace_cache_research() {
  local technology="$1"
  local query="$2"
  local result_json="$3"
  local action="${4:-get}"

  local query_hash=$(echo "${technology}:${query}" | md5)
  local cache_key="research:${query_hash}"

  if [[ "$action" == "set" ]]; then
    cogspace_cache_set "$cache_key" "$result_json" 2592000  # 30 days
    return $?
  else
    local cached=$(cogspace_cache_get "$cache_key")
    if [[ $? -eq 0 ]]; then
      cogspace_cache_record_hit
      echo "$cached"
      return 0
    else
      cogspace_cache_record_miss
      return 1
    fi
  fi
}

# Pattern Library Cache
cogspace_cache_pattern() {
  local language="$1"
  local category="$2"
  local pattern_json="$3"
  local action="${4:-get}"

  local cache_key="patterns:${language}:${category}"

  if [[ "$action" == "set" ]]; then
    cogspace_cache_set "$cache_key" "$pattern_json" 7776000  # 90 days
    return $?
  else
    local cached=$(cogspace_cache_get "$cache_key")
    if [[ $? -eq 0 ]]; then
      cogspace_cache_record_hit
      echo "$cached"
      return 0
    else
      cogspace_cache_record_miss
      return 1
    fi
  fi
}

# Session Context Cache
cogspace_cache_session_context() {
  local session_id="$1"
  local context_json="$2"
  local action="${3:-get}"

  local cache_key="session:${session_id}:context"

  if [[ "$action" == "set" ]]; then
    cogspace_cache_set "$cache_key" "$context_json" 86400  # 24 hours
    return $?
  else
    local cached=$(cogspace_cache_get "$cache_key")
    if [[ $? -eq 0 ]]; then
      cogspace_cache_record_hit
      echo "$cached"
      return 0
    else
      cogspace_cache_record_miss
      return 1
    fi
  fi
}

# DevDiscover Feed Cache
cogspace_cache_devdiscover_feed() {
  local source="$1"
  local date="$2"
  local feed_json="$3"
  local action="${4:-get}"

  local cache_key="devdiscover:${source}:${date}"

  if [[ "$action" == "set" ]]; then
    cogspace_cache_set "$cache_key" "$feed_json" 604800  # 7 days
    return $?
  else
    local cached=$(cogspace_cache_get "$cache_key")
    if [[ $? -eq 0 ]]; then
      cogspace_cache_record_hit
      echo "$cached"
      return 0
    else
      cogspace_cache_record_miss
      return 1
    fi
  fi
}

#═══════════════════════════════════════════════════════════════════════════════
# CACHE WARMING
#═══════════════════════════════════════════════════════════════════════════════

cogspace_cache_warm() {
  if ! cogspace_cache_available; then
    return 1
  fi

  echo -e "${CYAN}🔥 Warming cache...${NC}"

  # Count warmed entries
  local warmed=0

  # Warm common technology detections
  if [[ -f "package.json" ]]; then
    local techs='["Node.js","JavaScript"]'
    cogspace_cache_readme_tech "$(pwd)" "$techs" "set" && ((warmed++))
  fi

  # Warm git template
  if [[ -d ".git" ]]; then
    local repo=$(basename "$(pwd)")
    local template="🧠 COGSPACE:"
    cogspace_cache_git_template "$repo" "$template" "set" && ((warmed++))
  fi

  if [[ $warmed -gt 0 ]]; then
    echo -e "${GREEN}✅ Warmed $warmed cache entries${NC}"
  else
    echo -e "${YELLOW}ℹ️  No entries to warm${NC}"
  fi

  return 0
}

#═══════════════════════════════════════════════════════════════════════════════
# CACHE MANAGEMENT COMMANDS
#═══════════════════════════════════════════════════════════════════════════════

cogspace_cache_info() {
  echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
  echo -e "${CYAN}   COGSPACE REVOLUTION v20.0 - CACHE MANAGER${NC}"
  echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
  echo ""

  if ! cogspace_cache_available; then
    echo -e "${RED}❌ Redis cache not available${NC}"
    echo -e "${YELLOW}   System will work without cache (slower performance)${NC}"
    echo ""
    echo -e "${BLUE}To enable caching:${NC}"
    echo -e "${BLUE}  1. Install Redis: brew install redis${NC}"
    echo -e "${BLUE}  2. Start Redis: brew services start redis${NC}"
    return 1
  fi

  echo -e "${GREEN}✅ Redis cache available${NC}"
  echo ""

  local stats=$(cogspace_cache_stats)
  local total_keys=$(echo "$stats" | jq -r '.totalKeys')
  local memory=$(echo "$stats" | jq -r '.memoryUsed')
  local hit_rate=$(echo "$stats" | jq -r '.hitRate')
  local hits=$(echo "$stats" | jq -r '.hits')
  local misses=$(echo "$stats" | jq -r '.misses')

  echo -e "${CYAN}Cache Statistics:${NC}"
  echo -e "${BLUE}  Total Keys:   $total_keys${NC}"
  echo -e "${BLUE}  Memory Used:  $memory${NC}"
  echo -e "${BLUE}  Hit Rate:     ${hit_rate}%${NC}"
  echo -e "${BLUE}  Hits:         $hits${NC}"
  echo -e "${BLUE}  Misses:       $misses${NC}"
  echo ""

  echo -e "${CYAN}Cache Domains:${NC}"
  echo -e "${BLUE}  • readme:tech:*       (Technology detection, 7 days TTL)${NC}"
  echo -e "${BLUE}  • git:commit:*        (Commit templates, 7 days TTL)${NC}"
  echo -e "${BLUE}  • research:*          (Research results, 30 days TTL)${NC}"
  echo -e "${BLUE}  • patterns:*          (Pattern library, 90 days TTL)${NC}"
  echo -e "${BLUE}  • session:*:context   (Session context, 24 hours TTL)${NC}"
  echo -e "${BLUE}  • devdiscover:*       (Feed cache, 7 days TTL)${NC}"
  echo ""

  echo -e "${CYAN}Management Commands:${NC}"
  echo -e "${BLUE}  cogspace_cache_stats          # Show statistics JSON${NC}"
  echo -e "${BLUE}  cogspace_cache_warm           # Warm cache with common data${NC}"
  echo -e "${BLUE}  cogspace_cache_flush [pattern] # Flush matching keys${NC}"
  echo -e "${BLUE}  cogspace_cache_info           # Show this information${NC}"
  echo ""
}

#═══════════════════════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
#═══════════════════════════════════════════════════════════════════════════════

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  # Script called directly
  case "${1:-info}" in
    stats)
      cogspace_cache_stats | jq .
      ;;
    warm)
      cogspace_cache_warm
      ;;
    flush)
      cogspace_cache_flush "${2:-*}"
      echo -e "${GREEN}✅ Cache flushed${NC}"
      ;;
    info|*)
      cogspace_cache_info
      ;;
  esac
fi


