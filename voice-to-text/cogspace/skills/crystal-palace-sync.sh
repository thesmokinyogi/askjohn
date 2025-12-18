#!/bin/bash
# COGSPACE v40.0.0
# =============================================================================
# COGSPACE Crystal Palace Sync Skill
# Push project registration and docs to Crystal Palace Host Server
# =============================================================================

# Configuration
# LAN IP and Tailscale IP for Crystal Palace Host
CRYSTAL_PALACE_LAN_IP="192.168.50.58"
CRYSTAL_PALACE_TAILSCALE_IP="${CRYSTAL_PALACE_TAILSCALE_IP:-100.64.0.1}"  # Update with actual Tailscale IP
CRYSTAL_PALACE_PORT="${CRYSTAL_PALACE_PORT:-8081}"

# Auto-detect best IP to use (LAN first, then Tailscale)
detect_crystal_palace_host() {
    # Try LAN first (faster if on local network)
    if ping -c 1 -W 1 "$CRYSTAL_PALACE_LAN_IP" > /dev/null 2>&1; then
        echo "$CRYSTAL_PALACE_LAN_IP"
        return 0
    fi

    # Try Tailscale IP
    if ping -c 1 -W 2 "$CRYSTAL_PALACE_TAILSCALE_IP" > /dev/null 2>&1; then
        echo "$CRYSTAL_PALACE_TAILSCALE_IP"
        return 0
    fi

    # Try to get Tailscale IP dynamically
    local ts_ip=$(tailscale status 2>/dev/null | grep -i "crystal-palace\|ubuntu" | awk '{print $1}' | head -1)
    if [[ -n "$ts_ip" ]] && ping -c 1 -W 2 "$ts_ip" > /dev/null 2>&1; then
        echo "$ts_ip"
        return 0
    fi

    # Fallback to LAN IP (will fail gracefully later)
    echo "$CRYSTAL_PALACE_LAN_IP"
    return 1
}

# Set the host (auto-detect or use override)
if [[ -n "${CRYSTAL_PALACE_HOST:-}" ]]; then
    # User override
    _CP_HOST="$CRYSTAL_PALACE_HOST"
else
    # Auto-detect
    _CP_HOST=$(detect_crystal_palace_host)
fi
CRYSTAL_PALACE_HOST="$_CP_HOST"
CRYSTAL_PALACE_API="http://${CRYSTAL_PALACE_HOST}:${CRYSTAL_PALACE_PORT}/api"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

# Get project root (caller should set this, or detect)
PROJECT_ROOT="${PROJECT_ROOT:-$(pwd)}"
PROJECT_NAME="${PROJECT_NAME:-$(basename "$PROJECT_ROOT")}"

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

log_info() { echo -e "${CYAN}🏰${NC} $1"; }
log_success() { echo -e "${GREEN}✅${NC} $1"; }
log_warning() { echo -e "${YELLOW}⚠️${NC} $1"; }
log_error() { echo -e "${RED}❌${NC} $1"; }

# Check if Crystal Palace Host is reachable
check_host_available() {
    local timeout="${1:-3}"
    curl -s --connect-timeout "$timeout" "${CRYSTAL_PALACE_API}/health" > /dev/null 2>&1
    return $?
}

# Extract Short Description from README
get_short_description() {
    local readme="$1"
    if [[ -f "$readme" ]]; then
        # Look for ## Short Description section
        local desc=$(sed -n '/^## Short Description/,/^##/p' "$readme" 2>/dev/null \
            | grep -v "^##" \
            | tr '\n' ' ' \
            | sed 's/^[[:space:]]*//' \
            | sed 's/[[:space:]]*$//' \
            | cut -c1-200)
        echo "$desc"
    fi
}

# Get git information
get_git_info() {
    local info_type="$1"
    case "$info_type" in
        remote)
            git -C "$PROJECT_ROOT" remote get-url origin 2>/dev/null || echo ""
            ;;
        branch)
            git -C "$PROJECT_ROOT" branch --show-current 2>/dev/null || echo "main"
            ;;
        last_commit)
            git -C "$PROJECT_ROOT" log -1 --format="%h %s" 2>/dev/null | cut -c1-80 || echo ""
            ;;
    esac
}

# Get COGSPACE version
get_cogspace_version() {
    if [[ -f "${PROJECT_ROOT}/cogspace/.cogspace-version" ]]; then
        cat "${PROJECT_ROOT}/cogspace/.cogspace-version"
    elif [[ -f "${PROJECT_ROOT}/cogspace/cogspace-version.json" ]]; then
        jq -r '.version // "unknown"' "${PROJECT_ROOT}/cogspace/cogspace-version.json" 2>/dev/null || echo "unknown"
    else
        echo "unknown"
    fi
}

# Get developer info from cogspace-version.json
get_developer_info() {
    local field="$1"
    local config="${PROJECT_ROOT}/cogspace/cogspace-version.json"
    if [[ -f "$config" ]]; then
        jq -r ".developers.${field} // empty" "$config" 2>/dev/null
    fi
}

# Count files by type
count_files() {
    local pattern="$1"
    find "$PROJECT_ROOT" -name "$pattern" -type f 2>/dev/null \
        | grep -v node_modules \
        | grep -v ".git" \
        | wc -l \
        | tr -d ' '
}

# =============================================================================
# MAIN FUNCTIONS
# =============================================================================

# Ensure README has Short Description (generate if needed)
ensure_short_description() {
    local readme="${PROJECT_ROOT}/README.md"

    if [[ ! -f "$readme" ]]; then
        log_warning "No README.md found"
        return 1
    fi

    if ! grep -q "^## Short Description" "$readme" 2>/dev/null; then
        log_info "README missing Short Description - generating..."

        # Try to run enhance-readme.cjs with AI generation
        local enhancer="${PROJECT_ROOT}/cogspace/enhance-readme.cjs"
        if [[ -f "$enhancer" ]]; then
            (cd "$PROJECT_ROOT" && node "$enhancer" --add-short-description 2>/dev/null)

            if grep -q "^## Short Description" "$readme" 2>/dev/null; then
                log_success "Short Description generated"
                return 0
            fi
        fi

        log_warning "Could not auto-generate Short Description"
        return 1
    fi

    return 0
}

# Register project with Crystal Palace Host
register_project() {
    local event="${1:-wake}"
    local session_id="${2:-$(date +%s)}"

    # Check host availability
    if ! check_host_available 3; then
        log_warning "Crystal Palace Host not reachable - skipping sync"
        return 1
    fi

    log_info "Registering with Crystal Palace Host..."

    # Ensure Short Description exists
    ensure_short_description

    # Gather project metadata
    local short_desc=$(get_short_description "${PROJECT_ROOT}/README.md")
    local cogspace_version=$(get_cogspace_version)
    local hostname=$(hostname -s 2>/dev/null || echo "unknown")
    local git_remote=$(get_git_info remote)
    local git_branch=$(get_git_info branch)
    local git_commit=$(get_git_info last_commit)
    local human_dev=$(get_developer_info human)
    local binary_dev=$(get_developer_info binary)
    local docs_count=$(count_files "*.md")
    local scripts_count=$(count_files "*.sh")
    local ide="${IDE_ENVIRONMENT:-unknown}"

    # Build JSON payload
    local payload=$(cat <<EOF
{
  "project": "${PROJECT_NAME}",
  "path": "${PROJECT_ROOT}",
  "host": "${hostname}",
  "cogspace_version": "${cogspace_version}",
  "mode": "${COGSPACE_MODE:-standalone}",
  "developers": {
    "human": "${human_dev:-Howard}",
    "binary": "${binary_dev:-Bob}"
  },
  "session": {
    "id": "${session_id}",
    "event": "${event}",
    "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
    "ide": "${ide}"
  },
  "git": {
    "remote": "${git_remote}",
    "branch": "${git_branch}",
    "last_commit": "${git_commit}"
  },
  "readme_summary": $(echo "$short_desc" | jq -Rs .),
  "stats": {
    "docs_count": ${docs_count:-0},
    "scripts_count": ${scripts_count:-0}
  }
}
EOF
)

    # Send registration
    local response=$(curl -s --connect-timeout 5 --max-time 10 \
        -X POST "${CRYSTAL_PALACE_API}/projects/register" \
        -H "Content-Type: application/json" \
        -d "$payload" 2>/dev/null)

    if [[ -n "$response" ]] && echo "$response" | jq -e '.success' > /dev/null 2>&1; then
        log_success "Registered: ${PROJECT_NAME} (${event})"
        return 0
    else
        log_warning "Registration response: $response"
        return 1
    fi
}

# Sync docs to Crystal Palace Host (delta sync)
sync_docs() {
    local timeout="${1:-60}"

    if ! check_host_available 3; then
        log_warning "Crystal Palace Host not reachable - skipping doc sync"
        return 1
    fi

    log_info "Syncing docs to Crystal Palace Host..."

    # Use rsync with timeout for delta sync
    local target_dir=$(echo "$PROJECT_NAME" | tr '[:upper:]' '[:lower:]' | tr ' ' '-')

    rsync -avz --timeout="$timeout" --delete \
        --include='*/' \
        --include='*.md' \
        --include='*.txt' \
        --include='*.json' \
        --include='*.html' \
        --include='*.sh' \
        --include='*.js' \
        --include='*.py' \
        --include='*.ts' \
        --include='README*' \
        --exclude='node_modules/' \
        --exclude='.git/' \
        --exclude='logs/' \
        --exclude='backups/' \
        --exclude='cogspace-backup-*/' \
        --exclude='google-drive-venv/' \
        --exclude='*.pyc' \
        --exclude='__pycache__/' \
        --exclude='*' \
        -e "sshpass -p wizard ssh -o StrictHostKeyChecking=no" \
        "${PROJECT_ROOT}/" \
        "wizard@${CRYSTAL_PALACE_HOST}:/home/wizard/crystal-palace-host/docs/${target_dir}/" \
        2>/dev/null

    if [[ $? -eq 0 ]]; then
        log_success "Docs synced to Crystal Palace Host"

        # Trigger reindex
        curl -s --connect-timeout 5 -X POST "${CRYSTAL_PALACE_API}/search/reindex" > /dev/null 2>&1
        return 0
    else
        log_warning "Doc sync failed or timed out"
        return 1
    fi
}

# Check Crystal Palace Host health
check_health() {
    if check_host_available 3; then
        local health=$(curl -s --connect-timeout 3 "${CRYSTAL_PALACE_API}/health" 2>/dev/null)
        if [[ -n "$health" ]]; then
            local projects=$(echo "$health" | jq -r '.projects // "?"')
            local scripts=$(echo "$health" | jq -r '.scripts // "?"')
            echo -e "${GREEN}✅${NC} Crystal Palace Host: Online (${projects} projects, ${scripts} scripts)"
            return 0
        fi
    fi
    echo -e "${RED}❌${NC} Crystal Palace Host: Offline"
    return 1
}

# =============================================================================
# COMMAND DISPATCH
# =============================================================================

case "${1:-}" in
    register)
        register_project "${2:-wake}" "${3:-}"
        ;;
    sync)
        sync_docs "${2:-60}"
        ;;
    health)
        check_health
        ;;
    ensure-short-desc)
        ensure_short_description
        ;;
    full)
        # Full sync: register + sync docs
        register_project "${2:-wake}" "${3:-}"
        sync_docs 60
        ;;
    *)
        echo "Usage: $0 {register|sync|health|ensure-short-desc|full} [event] [session_id]"
        echo ""
        echo "Commands:"
        echo "  register [event] [session_id]  - Register project with Crystal Palace Host"
        echo "  sync [timeout]                 - Sync docs to Crystal Palace Host"
        echo "  health                         - Check Crystal Palace Host status"
        echo "  ensure-short-desc              - Ensure README has Short Description"
        echo "  full [event] [session_id]      - Full sync (register + docs)"
        exit 1
        ;;
esac


