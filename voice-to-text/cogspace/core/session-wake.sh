#!/bin/bash
# COGSPACE v52.0.0
# ENHANCED SESSION-WAKE: Complete Cognitive Context Restoration
# Revolutionary session initialization with FULL context display
# Database is PRIMARY source of truth | Multi-environment support
# Version: 4.0.0 - Distributed Consciousness Preservation
# - v52.0.0: Multi-file session capture (main + agent JSONL files)
# - v52.0.0: Session manifest with wake/sleep timestamp-based timeframe

set -eu

# ============================================================================
# VERBOSE MODE SUPPORT
# ============================================================================
# Usage: ./hi -v or ./hi --verbose
VERBOSE=false
for arg in "$@"; do
    case "$arg" in
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
    esac
done

# Verbose logging function
vlog() {
    if [[ "$VERBOSE" == "true" ]]; then
        echo -e "\033[0;36m[VERBOSE]\033[0m $*"
    fi
}

vlog "Verbose mode enabled"
vlog "Arguments: $*"

# ============================================================================
# VERSION CHECK AND AUTO-UPGRADE WITH RE-EXEC
# ============================================================================
# Check version FIRST and upgrade immediately, then re-exec with new version

# COGSPACE DNA Resolution - GitHub is Source of Truth
# Tiered fallback: Local cache → GitHub → Bundled
COGSPACE_DNA_REPO="howeirdo/cogspace-remote-dna"
COGSPACE_DNA_CACHE="$HOME/.cogspace/dna"
COGSPACE_MODE="unknown"
DNA_SOURCE=""

resolve_dna_source() {
    vlog "Resolving DNA source..."

    # Tier 1: Crystal Palace Local (legacy - for transition period)
    if [[ -d "/Volumes/FOUR-TB/cogspace-dna-source/current" ]]; then
        vlog "  Tier 1: Found Crystal Palace local DNA"
        DNA_SOURCE="/Volumes/FOUR-TB/cogspace-dna-source/current"
        COGSPACE_MODE="crystal-palace"
        return 0
    fi
    vlog "  Tier 1: Crystal Palace not available"

    # Tier 2: Update from GitHub if possible, then use cache
    # v59.3.0: FIXED - Separated gh requirement (clone) from git requirement (pull)
    # Previously, git pull was gated behind gh check, preventing updates on systems
    # with osxkeychain but no gh installed (John's MacBook issue)
    # Fixes: John's MacBook stuck at v50.0.0 (Dec 2025)
    mkdir -p "$COGSPACE_DNA_CACHE"

    # Tier 2a: Fresh clone requires gh (no existing git credentials in cache)
    if [[ ! -d "$COGSPACE_DNA_CACHE/.git" ]]; then
        if command -v gh &>/dev/null && gh auth status &>/dev/null 2>&1; then
            vlog "  Tier 2a: Fresh clone via GitHub CLI"
            gh repo clone "$COGSPACE_DNA_REPO" "$COGSPACE_DNA_CACHE" --depth 1 2>/dev/null || true
        else
            vlog "  Tier 2a: No gh available, cannot fresh clone (need existing cache or standalone)"
        fi
    fi

    # Tier 2b: Update existing cache - git pull works with osxkeychain, no gh needed!
    if [[ -d "$COGSPACE_DNA_CACHE/.git" ]]; then
        vlog "  Tier 2b: Updating existing DNA cache..."
        (
            cd "$COGSPACE_DNA_CACHE"
            # Stash any local changes (from previous COGSPACE operations)
            git stash --all --quiet 2>/dev/null || true

            # Try gh repo sync first if available (handles auth best)
            if command -v gh &>/dev/null && gh auth status &>/dev/null 2>&1; then
                if gh repo sync --force 2>/dev/null; then
                    vlog "  Tier 2b: gh repo sync succeeded"
                else
                    vlog "  Tier 2b: gh repo sync failed, trying git pull"
                    GIT_TERMINAL_PROMPT=0 git pull --quiet 2>/dev/null || true
                fi
            else
                # v59.3.0: git pull works with osxkeychain even without gh!
                # This is the KEY FIX - previously this branch was never reached
                vlog "  Tier 2b: No gh, trying git pull (osxkeychain/credential helper)"
                GIT_TERMINAL_PROMPT=0 git pull --quiet 2>/dev/null || true
            fi

            # Drop stashed changes (don't pollute DNA cache with project artifacts)
            git stash drop --quiet 2>/dev/null || true
        ) 2>/dev/null || true
    fi

    # Tier 3: Use cached DNA (whether just updated or from previous session)
    # v40.0.0: Single version source - cogspace-version.json
    if [[ -f "$COGSPACE_DNA_CACHE/cogspace/cogspace-version.json" ]]; then
        vlog "  Tier 3: Using cached DNA at $COGSPACE_DNA_CACHE"
        DNA_SOURCE="$COGSPACE_DNA_CACHE"
        COGSPACE_MODE="portable"
        return 0
    fi
    vlog "  Tier 3: No cached DNA found"

    # Tier 4: No DNA available - standalone mode
    vlog "  Tier 4: No DNA source - standalone mode"
    DNA_SOURCE=""
    COGSPACE_MODE="standalone"
    return 1
}

# Resolve DNA source (v51.2.0: Call directly, no subshell - fixes COGSPACE_MODE propagation)
vlog "Starting DNA source resolution..."
resolve_dna_source || true
vlog "DNA_SOURCE resolved to: ${DNA_SOURCE:-'(none)'}"
vlog "COGSPACE_MODE: $COGSPACE_MODE"

# v40.0.0: Single version source - cogspace/cogspace-version.json only
# Removed .version and cogspace/.cogspace-version (legacy artifacts)
vlog "Reading version from cogspace/cogspace-version.json..."
CURRENT_VERSION=""
if [[ -f "cogspace/cogspace-version.json" ]]; then
    CURRENT_VERSION=$(jq -r '.version // "0.0.0"' cogspace/cogspace-version.json 2>/dev/null | tr -d '\n')
    vlog "CURRENT_VERSION: $CURRENT_VERSION"
else
    vlog "Warning: cogspace/cogspace-version.json not found"
fi

DNA_VERSION=""
if [[ -n "$DNA_SOURCE" && -f "$DNA_SOURCE/cogspace/cogspace-version.json" ]]; then
    DNA_VERSION=$(jq -r '.version // "0.0.0"' "$DNA_SOURCE/cogspace/cogspace-version.json" 2>/dev/null | tr -d '\n')
    vlog "DNA_VERSION: $DNA_VERSION"
else
    vlog "Warning: DNA version file not found or DNA_SOURCE empty"
fi

# Check for auto-heal disable marker (v51.6.0: for cogspace-updates development project)
AUTOHEAL_DISABLED=false
if [[ -f ".cogspace-autoheal-disabled" ]]; then
    AUTOHEAL_DISABLED=true
    vlog "Auto-heal DISABLED - .cogspace-autoheal-disabled marker found"
    echo "⚠️  Auto-heal disabled (development mode)"
fi

# If version mismatch, heal and re-exec (unless disabled)
vlog "Version comparison: CURRENT=$CURRENT_VERSION vs DNA=$DNA_VERSION"
if [[ "$AUTOHEAL_DISABLED" == "false" ]] && [[ "$CURRENT_VERSION" != "$DNA_VERSION" ]] && [[ -n "$DNA_VERSION" ]]; then
    vlog "Version mismatch detected - triggering auto-heal"
    echo "🔄 COGSPACE upgrade detected: v$CURRENT_VERSION → v$DNA_VERSION"
    echo "⚡ Auto-healing and restarting wake cycle..."

    # Run diagnostics healing
    if [[ -x "./cogspace/src/cogspace-diagnostics.sh" ]]; then
        ./cogspace/src/cogspace-diagnostics.sh --silent-fix
    fi

    # Clean old dashboard artifacts (v32.1.5: new path)
    if [[ -d "session-management/dashboard" ]]; then
        find session-management/dashboard -name "dashboard-*.html" -mtime +7 -delete 2>/dev/null || true
        echo "✅ Cleaned old dashboard files"
    fi
    # Clean legacy dashboard directory if it exists
    if [[ -d "dashboard" ]]; then
        find dashboard -name "dashboard-*.html" -mtime +7 -delete 2>/dev/null || true
    fi

    # v40.0.0: Update version in cogspace-version.json to prevent infinite loop on re-exec
    if [[ -f "cogspace/cogspace-version.json" ]]; then
        # Use jq to update version in place
        jq --arg v "$DNA_VERSION" '.version = $v' cogspace/cogspace-version.json > cogspace/cogspace-version.json.tmp && \
        mv cogspace/cogspace-version.json.tmp cogspace/cogspace-version.json
    fi
    echo "✅ Updated local version to v$DNA_VERSION"

    # RE-EXEC with new version
    echo "🔄 Re-executing wake with v$DNA_VERSION..."
    exec "$0" "$@"
    exit 0  # Should never reach here
fi

# ============================================================================
# FORCED RSYNC - SYNC COGSPACE FROM DNA SOURCE (v40.2.1 HOTFIX)
# ============================================================================
# This ensures file CONTENTS are always current, not just version numbers.
# Fixes issue where version matches but files differ (e.g., generate-simple.cjs)
# Phase 2 (future): Manifest-based cleanup to remove deprecated files
# v56.0.0: SKIP rsync when autoheal is disabled (development mode)
if [[ "$AUTOHEAL_DISABLED" == "true" ]]; then
    vlog "Rsync SKIPPED (autoheal disabled - development mode)"
elif [[ -n "$DNA_SOURCE" && -d "$DNA_SOURCE/cogspace" ]]; then
    RSYNC_START=$(date +%s)
    rsync -av --quiet \
          --exclude="*.BROKEN-OLLAMA-BACKUP" \
          --exclude="cogspace-backup-*" \
          --exclude=".DS_Store" \
          "$DNA_SOURCE/cogspace/" "./cogspace/" 2>/dev/null || true

    # Also sync root-level scripts
    for script in wake.sh sleep.sh save.sh hi bye save; do
        if [[ -f "$DNA_SOURCE/$script" ]]; then
            cp -P "$DNA_SOURCE/$script" "./$script" 2>/dev/null || true
            chmod +x "./$script" 2>/dev/null || true
        fi
    done

    RSYNC_END=$(date +%s)
    RSYNC_DURATION=$((RSYNC_END - RSYNC_START))
    echo -e "\033[0;32m✅ COGSPACE sync complete (${RSYNC_DURATION}s)\033[0m"
    vlog "Forced rsync completed in ${RSYNC_DURATION}s"

    # =============================================================================
    # 🔄 DATABASE MIGRATION (after script upgrade)
    # =============================================================================
    # v59.2.1: Run database migrations after script upgrade to ensure schema is current
    # Fixes: TR-T3-20251215-000119-1478 (Iris's first trouble report)
    echo ""
    echo -e "\033[0;36m🔄 Checking database schema...\033[0m"
    vlog "Checking database schema after COGSPACE sync..."

    if [[ -f ".cogspace/cogspace.db" ]]; then
        MIGRATE_SCRIPT="${PROJECT_ROOT:-$(pwd)}/cogspace/db/migrate-schema.py"
        if [[ -f "$MIGRATE_SCRIPT" ]]; then
            vlog "Running database migration: $MIGRATE_SCRIPT"
            if python3 "$MIGRATE_SCRIPT"; then
                vlog "Database migration completed successfully"
            else
                echo -e "\033[1;33m⚠️  Database migration warnings - session will use JSON fallback\033[0m"
                vlog "Database migration had issues (continuing)"
            fi
        else
            vlog "Migration script not found: $MIGRATE_SCRIPT"
            echo -e "\033[1;33mℹ️  Migration script not found - database may need manual update\033[0m"
        fi
    else
        vlog "No database yet - will be created on first save"
        echo -e "\033[0;36mℹ️  No database yet - will be created on first save\033[0m"
    fi
else
    vlog "DNA_SOURCE not available for rsync: ${DNA_SOURCE:-'(none)'}"
fi

# Normal silent healing for same-version fixes (handles directory creation, cleanup, etc.)
# v56.0.0: SKIP diagnostics when autoheal is disabled (development mode)
if [[ "$AUTOHEAL_DISABLED" != "true" ]]; then
    vlog "Running silent diagnostics healing..."
    if [[ -x "./cogspace/src/cogspace-diagnostics.sh" ]]; then
        ./cogspace/src/cogspace-diagnostics.sh --silent-fix
        vlog "Diagnostics healing completed"
    else
        vlog "Diagnostics script not found or not executable"
    fi
else
    vlog "Diagnostics SKIPPED (autoheal disabled - development mode)"
fi

# Color definitions for enhanced UX
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Configuration
# Smart directory detection - works in both source and deployed structures
vlog "Detecting project structure..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
vlog "SCRIPT_DIR: $SCRIPT_DIR"
if [[ "$(basename "$SCRIPT_DIR")" == "cogspace" ]]; then
    # We're in a cogspace subdirectory, go up one level to project root
    PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
    vlog "Detected cogspace subdirectory, PROJECT_ROOT set to parent"
else
    # We're already in project root
    PROJECT_ROOT="$SCRIPT_DIR"
    vlog "Already in project root"
fi
PROJECT_NAME=$(basename "$PROJECT_ROOT")
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%S.%3NZ")
WAKE_SESSION_ID=$(date +%s)-$(openssl rand -hex 2)
vlog "PROJECT_ROOT: $PROJECT_ROOT"
vlog "PROJECT_NAME: $PROJECT_NAME"
vlog "WAKE_SESSION_ID: $WAKE_SESSION_ID"

# v32.1.5: Session metadata now in session-management/
mkdir -p "$PROJECT_ROOT/session-management"
echo "$(date +%s)" > "$PROJECT_ROOT/session-management/.session-start-time"
echo "$WAKE_SESSION_ID" > "$PROJECT_ROOT/session-management/.session-id"

# v35.0.0: Display COGSPACE mode indicator
# v40.0.0: Updated to use cogspace-version.json as single source
display_cogspace_mode() {
    local version
    if [[ "$AUTOHEAL_DISABLED" == "true" ]]; then
        # Development mode: use LOCAL version, not DNA
        version=$(jq -r '.version // "unknown"' cogspace/cogspace-version.json 2>/dev/null || echo 'unknown')
    else
        # Normal mode: prefer DNA_VERSION, fallback to local
        version="${DNA_VERSION:-$(jq -r '.version // "unknown"' cogspace/cogspace-version.json 2>/dev/null || echo 'unknown')}"
    fi
    case "$COGSPACE_MODE" in
        "crystal-palace")
            echo -e "${MAGENTA}🏰 COGSPACE v$version | Crystal Palace Mode${NC}"
            ;;
        "portable")
            echo -e "${CYAN}📱 COGSPACE v$version | Portable Mode (GitHub DNA)${NC}"
            ;;
        "standalone")
            echo -e "${YELLOW}⚠️  COGSPACE v$version | Standalone Mode (No DNA Source)${NC}"
            ;;
        *)
            echo -e "${BLUE}🔧 COGSPACE v$version | Mode: $COGSPACE_MODE${NC}"
            ;;
    esac
}

# Ensure we're in the correct working directory
cd "$PROJECT_ROOT"

# ============================================================================
# SMART FIRST-TIME GITHUB AUTO-SYNC PROMPT (v32.1.4 Feature)
# ============================================================================
# Only prompt if:
# 1. Git repo exists
# 2. Remote is configured (GitHub detected)
# 3. No .cogspace-git-config.json exists yet
if [[ -d ".git" ]] && [[ ! -f ".cogspace-git-config.json" ]]; then
  REMOTE_URL=$(git remote get-url origin 2>/dev/null || echo "")

  if [[ -n "$REMOTE_URL" ]] && [[ "$REMOTE_URL" == *"github.com"* ]]; then
    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}   🚀 COGSPACE GitHub Auto-Sync Setup${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "${BLUE}Detected GitHub remote:${NC} $REMOTE_URL"
    echo ""
    echo -e "${GREEN}COGSPACE can automatically sync your work with GitHub:${NC}"
    echo -e "  ✅ ${CYAN}Wake (./hi):${NC} Auto-pull latest changes (prevents working on stale code)"
    echo -e "  ✅ ${CYAN}Sleep (./bye):${NC} Auto-commit and push all changes (ensures cloud backup)"
    echo ""
    echo -e "${YELLOW}Benefits:${NC}"
    echo -e "  • Never lose work - automatic cloud backup on every sleep"
    echo -e "  • Never work on stale code - automatic sync on every wake"
    echo -e "  • Seamless collaboration - team always has latest changes"
    echo -e "  • Maintains comprehensive context - code AND context preserved"
    echo ""
    echo -e "${BLUE}This is RECOMMENDED for all projects.${NC}"
    echo ""
    echo -e "${GREEN}Enable GitHub Auto-Sync? (Y/n):${NC}"
    read -r enable_autosync

    # Default to YES (any response except explicit 'n' or 'N')
    if [[ ! "$enable_autosync" =~ ^[Nn]$ ]]; then
      # Create .cogspace-git-config.json with auto-sync enabled
      cat > .cogspace-git-config.json << 'EOF'
{
  "autoSync": {
    "wake": true,
    "sleep": true
  },
  "commitPrefix": "🤖 COGSPACE",
  "setupComplete": true,
  "setupDate": "SETUP_DATE_PLACEHOLDER"
}
EOF

      # Update setup date
      SETUP_DATE=$(date -u +%Y-%m-%dT%H:%M:%SZ)
      if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' "s/SETUP_DATE_PLACEHOLDER/$SETUP_DATE/" .cogspace-git-config.json
      else
        sed -i "s/SETUP_DATE_PLACEHOLDER/$SETUP_DATE/" .cogspace-git-config.json
      fi

      echo ""
      echo -e "${GREEN}✅ GitHub Auto-Sync enabled!${NC}"
      echo -e "${BLUE}   Wake will auto-pull, Sleep will auto-commit/push${NC}"
      echo -e "${BLUE}   You can disable anytime with:${NC}"
      echo -e "${CYAN}     git config cogspace.autoSync.wake false${NC}"
      echo -e "${CYAN}     git config cogspace.autoSync.sleep false${NC}"

      # Add to .gitignore if not already there
      if [[ -f ".gitignore" ]] && ! grep -q ".cogspace-git-config.json" .gitignore; then
        echo ".cogspace-git-config.json" >> .gitignore
        echo -e "${GREEN}   Added .cogspace-git-config.json to .gitignore${NC}"
      fi
    else
      # User declined - create config with auto-sync disabled
      cat > .cogspace-git-config.json << 'EOF'
{
  "autoSync": {
    "wake": false,
    "sleep": false
  },
  "commitPrefix": "🤖 COGSPACE",
  "setupComplete": true,
  "setupDate": "SETUP_DATE_PLACEHOLDER",
  "userDeclined": true
}
EOF

      # Update setup date
      SETUP_DATE=$(date -u +%Y-%m-%dT%H:%M:%SZ)
      if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' "s/SETUP_DATE_PLACEHOLDER/$SETUP_DATE/" .cogspace-git-config.json
      else
        sed -i "s/SETUP_DATE_PLACEHOLDER/$SETUP_DATE/" .cogspace-git-config.json
      fi

      echo ""
      echo -e "${YELLOW}ℹ️  GitHub Auto-Sync disabled${NC}"
      echo -e "${YELLOW}   ⚠️  Your code changes will NOT be automatically backed up${NC}"
      echo -e "${BLUE}   You can enable later with:${NC}"
      echo -e "${CYAN}     git config cogspace.autoSync.wake true${NC}"
      echo -e "${CYAN}     git config cogspace.autoSync.sleep true${NC}"

      # Add to .gitignore
      if [[ -f ".gitignore" ]] && ! grep -q ".cogspace-git-config.json" .gitignore; then
        echo ".cogspace-git-config.json" >> .gitignore
      fi
    fi

    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
    echo ""
  fi
fi

# ============================================================================
# GITHUB SYNC - AUTO-PULL LATEST CHANGES (v32.1.4 - Default ON)
# ============================================================================
# Auto-pull is now DEFAULT to prevent working on stale code
# Disable with: git config cogspace.autoSync.wake false
if [[ -f "cogspace/cogspace-git-helpers.sh" ]] && [[ -d ".git" ]]; then
  source cogspace/cogspace-git-helpers.sh

  # Default to ON, allow explicit opt-out
  AUTO_SYNC_WAKE=$(cogspace_git_config 'autoSync.wake')
  if [[ "$AUTO_SYNC_WAKE" != "false" ]]; then
    echo -e "${CYAN}🔄 Auto-Pull: Syncing latest changes from remote...${NC}"
    echo -e "${CYAN}   (Disable: git config cogspace.autoSync.wake false)${NC}"

    PULL_START=$(date +%s)
    if cogspace_git_pull; then
      PULL_END=$(date +%s)
      PULL_DURATION=$((PULL_END - PULL_START))
      echo -e "${GREEN}✅ Auto-pull successful (${PULL_DURATION}s)${NC}"

      # Log to session file for dashboard tracking
      if [[ ! -d "session-management/cognitive-context" ]]; then
        mkdir -p session-management/cognitive-context
      fi
      echo "{\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"operation\":\"git-auto-pull\",\"status\":\"success\",\"duration\":${PULL_DURATION}}" >> session-management/cognitive-context/git-operations.jsonl
    else
      echo -e "${YELLOW}⚠️  Auto-pull failed - continuing with local version${NC}"
      echo -e "${YELLOW}   Check network connection or run 'git pull' manually${NC}"

      # Log failure
      echo "{\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"operation\":\"git-auto-pull\",\"status\":\"failed\"}" >> session-management/cognitive-context/git-operations.jsonl
    fi
    echo ""
  else
    echo -e "${YELLOW}ℹ️  Auto-pull disabled by user configuration${NC}"
    echo ""
  fi
fi

# ============================================================================
# GIT REPOSITORY VERIFICATION (v32.1 Feature)
# ============================================================================
if [[ ! -d ".git" ]]; then
    echo -e "${YELLOW}⚠️  No git repository detected${NC}"
    echo -e "${CYAN}Git provides:${NC}"
    echo -e "  • Version control and history"
    echo -e "  • Enhanced v32 git-diff-analyzer (enhanced fidelity)"
    echo -e "  • Automatic backup and collaboration"
    echo ""
    echo -e "${YELLOW}Initialize git repository? (Y/n):${NC}"
    read -r init_git

    if [[ ! "$init_git" =~ ^[Nn]$ ]]; then
        git init
        git add .gitignore README.md .project-metadata.json
        git commit -m "Initial commit: COGSPACE project

🤖 Auto-initialized by COGSPACE wake cycle
"
        echo -e "${GREEN}✅ Git repository initialized${NC}"
    fi
    echo ""
fi

# ============================================================================
# README.md CREATION (v32.1.4 Feature)
# ============================================================================
# Create default README.md if it doesn't exist (for old projects or manual setup)
if [[ ! -f "README.md" ]]; then
    echo -e "${YELLOW}📄 No README.md found - creating default project README${NC}"

    # Get user name for suggestion
    USER_NAME=$(git config user.name 2>/dev/null || echo "Developer")

    cat > "README.md" << EOF
# ${PROJECT_NAME}

**Created:** $(date -u +"%Y-%m-%d")
**COGSPACE Version:** $(jq -r '.version // "40.0.0"' "${DNA_SOURCE:-./cogspace}/cogspace/cogspace-version.json" 2>/dev/null || echo "40.0.0")

## Description

[Project description here - customize this README to describe your project]

## Getting Started

### Session Management Commands

\`\`\`bash
# Start development session with cognitive restoration
./hi

# Save context during development (crash protection)
./save "checkpoint message"

# End session with complete preservation
./bye "session summary"
\`\`\`

### View Dashboard

\`\`\`bash
# Dashboard opens automatically on ./hi
# Or generate manually:
node cogspace/dashboard/generate-simple.cjs
\`\`\`

## COGSPACE Features

- ✅ comprehensive session preservation
- ✅ Git auto-sync (automatic pull on wake, push on sleep)
- ✅ Hardware failure protection
- ✅ Multi-environment compatibility
- ✅ Interactive dashboard visualization
- ✅ Smart GitHub integration

## Development

[Add your development workflow, build instructions, testing, etc.]

---

**Powered by COGSPACE** - Cognitive workspace serialization for seamless development continuity
EOF

    echo -e "${GREEN}✅ Default README.md created${NC}"
    echo -e "${CYAN}💡 Suggestion for ${USER_NAME}:${NC}"
    echo -e "${YELLOW}   Consider customizing README.md with your project details!${NC}"
    echo -e "${YELLOW}   You can ask your AI assistant to help update it.${NC}"
    echo ""
fi

echo -e "${CYAN}🌅 ENHANCED SESSION-WAKE: Complete Cognitive Context Restoration${NC}"
echo -e "${BLUE}Project: ${PROJECT_NAME}${NC}"
echo -e "${BLUE}Wake Timestamp: ${TIMESTAMP}${NC}"
echo -e "${BLUE}Wake Session ID: ${WAKE_SESSION_ID}${NC}"

# Validate Node.js availability
if ! command -v node &> /dev/null; then
    echo -e "${RED}❌ ERROR: Node.js required for cognitive restoration${NC}"
    exit 1
fi

# Validate cognitive serializer
if [[ ! -f "${PROJECT_ROOT}/cogspace/analyzers/serializer.cjs" ]]; then
    echo -e "${RED}❌ ERROR: Cognitive serializer not found${NC}"
    echo -e "${YELLOW}Expected location: ${PROJECT_ROOT}/cogspace/analyzers/serializer.cjs${NC}"
    echo -e "${YELLOW}Current working directory: $(pwd)${NC}"
    echo -e "${YELLOW}Script location: ${SCRIPT_DIR}${NC}"
    exit 1
fi

# Multi-environment compatibility check
echo -e "${MAGENTA}🌍 MULTI-ENVIRONMENT COMPATIBILITY CHECK${NC}"
echo -e "${BLUE}Platform: $(uname -s)${NC}"
echo -e "${BLUE}Architecture: $(uname -m)${NC}"
echo -e "${BLUE}Hostname: $(hostname)${NC}"
echo -e "${BLUE}User: $(whoami)${NC}"
echo -e "${BLUE}Working Directory: ${PROJECT_ROOT}${NC}"

# Detect IDE/Editor environment
IDE_ENVIRONMENT="unknown"
if [[ -n "${VSCODE_PID:-}" ]] || [[ -n "${TERM_PROGRAM:-}" && "${TERM_PROGRAM}" == "vscode" ]]; then
    IDE_ENVIRONMENT="vscode"
elif [[ -n "${CURSOR:-}" ]] || [[ "${PWD}" =~ cursor ]]; then
    IDE_ENVIRONMENT="cursor"
elif [[ -n "${CLAUDE_CODE:-}" ]] || [[ "${0}" =~ claude ]]; then
    IDE_ENVIRONMENT="claude-code"
fi

echo -e "${BLUE}IDE Environment: ${IDE_ENVIRONMENT}${NC}"
echo ""

# ============================================================================
# COGSPACE DNA VERSION CHECK (v20 Feature)
# ============================================================================
if [[ -f "cogspace/cogspace-git-helpers.sh" ]]; then
  source cogspace/cogspace-git-helpers.sh

  # Check DNA version and display update banner if outdated
  if ! cogspace_check_dna_version; then
    cogspace_display_dna_update
  fi
fi

# ============================================================================
# COGSPACE REVOLUTION - INTELLIGENCE ACTIVATION
# ============================================================================

# v21.5.0: Dual-system version detection with auto-migration
# Priority: cogspace-version.json (new) > .cogspace-version (legacy) > .session-dna-version (root)
if [ -f "cogspace/cogspace-version.json" ]; then
    # Primary version file exists - use it
    COGSPACE_VERSION=$(jq -r '.version' cogspace/cogspace-version.json 2>/dev/null || echo "21.1.5")
else
    # Legacy system - read from old files and trigger migration
    COGSPACE_VERSION=$(cat cogspace/.cogspace-version 2>/dev/null || cat .session-dna-version 2>/dev/null || echo "21.1.5")

    # Auto-migrate to new version system (silent, non-blocking)
    if [ -f "cogspace/src/migrate-to-single-version.sh" ]; then
        cogspace/src/migrate-to-single-version.sh "$(pwd)/cogspace" >/dev/null 2>&1 || true
    fi
fi
echo ""
echo -e "${MAGENTA}═══════════════════════════════════════════════════════════${NC}"
echo -e "${MAGENTA}   🚀 COGSPACE REVOLUTION v${COGSPACE_VERSION} - INTELLIGENCE ACTIVE${NC}"
display_cogspace_mode
echo -e "${MAGENTA}═══════════════════════════════════════════════════════════${NC}"

# DevDiscover Intelligence Summary
if [[ -f "cogspace/devdiscover-agent.sh" ]]; then
  source cogspace/devdiscover-agent.sh
  cogspace_devdiscover_display_summary
fi

# Cache Warm
if [[ -f "cogspace/cache-manager.sh" ]]; then
  source cogspace/cache-manager.sh
  if cogspace_cache_available; then
    cogspace_cache_warm >/dev/null 2>&1
    stats=$(cogspace_cache_stats 2>/dev/null)
    hit_rate=$(echo "$stats" | jq -r '.hitRate // 0' 2>/dev/null || echo "0")
    echo -e "${CYAN}💾 Cache: ${hit_rate}% hit rate${NC}"
  fi
fi

# Ollama Specialists Ready
if [[ -f "cogspace/ollama-integration.sh" ]]; then
  source cogspace/ollama-integration.sh
  specialists=$(cogspace_ollama_list_specialists)
  if [[ -n "$specialists" ]]; then
    echo -e "${CYAN}🤖 Specialists: $specialists${NC}"
  fi
fi

# Knowledge Library Stats
if [[ -f "cogspace/knowledge-library.json" ]]; then
  pattern_count=$(jq -r '.metadata.totalPatterns // 0' cogspace/knowledge-library.json 2>/dev/null || echo "0")
  echo -e "${CYAN}📚 Knowledge Library: $pattern_count patterns${NC}"
fi

echo -e "${GREEN}✅ Revolutionary intelligence systems ready${NC}"
echo -e "${MAGENTA}═══════════════════════════════════════════════════════════${NC}"
echo ""

# Parse command line arguments
TARGET_SESSION_ID="${1:-}"
RESTORE_MODE="${2:-full}"

# Validate session ID format if provided
if [[ -n "$TARGET_SESSION_ID" ]]; then
    # Check if it looks like a session ID (timestamp-hex format)
    if [[ ! "$TARGET_SESSION_ID" =~ ^[0-9]+-[a-f0-9]+$ ]]; then
        echo -e "${RED}❌ ERROR: Invalid session ID format: ${TARGET_SESSION_ID}${NC}"
        echo -e "${YELLOW}Session IDs should be in format: timestamp-hex (e.g., 1755010435160-450d3ee6)${NC}"
        echo -e "${YELLOW}Usage: $0 [session-id] [restore-mode]${NC}"
        echo -e "${YELLOW}Or run without arguments to use the latest session${NC}"
        exit 1
    fi
fi

# Discover available cognitive contexts
echo -e "${CYAN}🔍 DISCOVERING COGNITIVE CONTEXTS${NC}"
vlog "Looking for cognitive contexts..."

COGNITIVE_CONTEXT_DIR="${PROJECT_ROOT}/session-management/cognitive-context"
vlog "COGNITIVE_CONTEXT_DIR: $COGNITIVE_CONTEXT_DIR"
if [[ ! -d "$COGNITIVE_CONTEXT_DIR" ]]; then
    vlog "No cognitive context directory found, initializing..."
    echo -e "${YELLOW}⚠️ No cognitive context directory found - initializing new workspace${NC}"
    mkdir -p "$COGNITIVE_CONTEXT_DIR"/{mental-models,work-narratives,decision-archaeology,performance-deltas,executable-continuity,guidelines,lessons,notes,backups}

    # Copy default welcome note if it exists in cogspace
    if [[ -f "${SCRIPT_DIR}/default-notes/notes-COGSPACE-dev-radio-2025-10-27T00-00-00.md" ]]; then
        cp "${SCRIPT_DIR}/default-notes/notes-COGSPACE-dev-radio-2025-10-27T00-00-00.md" "$COGNITIVE_CONTEXT_DIR/notes/" 2>/dev/null || true
        echo -e "${CYAN}📝 Default welcome note added${NC}"
    fi

    echo -e "${GREEN}✅ Cognitive workspace initialized${NC}"
fi

# Find available contexts in session-management
vlog "Searching for complete-context-*.json files..."
AVAILABLE_CONTEXTS=$(find "$COGNITIVE_CONTEXT_DIR" -name "complete-context-*.json" -type f 2>/dev/null | sort -u)
CONTEXT_COUNT=$(echo "$AVAILABLE_CONTEXTS" | grep -v "^$" | wc -l | tr -d ' ')
vlog "Found $CONTEXT_COUNT context files"

echo -e "${BLUE}Available contexts: ${CONTEXT_COUNT}${NC}"

if [[ $CONTEXT_COUNT -eq 0 ]]; then
    echo -e "${YELLOW}⚠️ No previous cognitive contexts found${NC}"
    echo -e "${CYAN}🚀 Creating welcome context for first-time experience${NC}"

    # Create welcome context from default template (v23.1.3 - pre-generated with bye logic)
    if [[ -f "cogspace/templates/default-welcome-context.json" ]]; then
        WELCOME_SESSION_ID="welcome-$(date +%s)"

        # Ensure cognitive context directory exists
        mkdir -p "$COGNITIVE_CONTEXT_DIR"

        # Copy default template to cognitive context directory
        WELCOME_CONTEXT="$COGNITIVE_CONTEXT_DIR/complete-context-${WELCOME_SESSION_ID}.json"
        cp "cogspace/templates/default-welcome-context.json" "$WELCOME_CONTEXT"

        # Update session ID and timestamp in the context
        node -e "
        const fs = require('fs');
        const context = JSON.parse(fs.readFileSync('$WELCOME_CONTEXT', 'utf8'));
        context.sessionId = '${WELCOME_SESSION_ID}';
        context.timestamp = new Date().toISOString();
        context.projectName = '$(basename "$PWD")';
        if (context.serializedComponents && context.serializedComponents.mentalModel) {
            context.serializedComponents.mentalModel.sessionId = '${WELCOME_SESSION_ID}';
            context.serializedComponents.mentalModel.timestamp = context.timestamp;
            context.serializedComponents.mentalModel.projectName = context.projectName;
        }
        fs.writeFileSync('$WELCOME_CONTEXT', JSON.stringify(context, null, 2));
        "

        echo -e "${GREEN}✅ Welcome context created: ${WELCOME_SESSION_ID}${NC}"
        echo -e "${CYAN}🎉 COGSPACE will now restore your welcome message${NC}"

        # Set this as the context to restore
        RESTORE_SESSION_ID="$WELCOME_SESSION_ID"
        FRESH_WORKSPACE=false
    else
        echo -e "${YELLOW}⚠️ Welcome template not found, initializing fresh workspace${NC}"
        FRESH_WORKSPACE=true
    fi
else
    FRESH_WORKSPACE=false
fi

# Only attempt context restoration if not a fresh workspace
if [[ "$FRESH_WORKSPACE" = false ]]; then

# Initialize RESTORE_SESSION_ID if not already set (for set -u compatibility)
RESTORE_SESSION_ID="${RESTORE_SESSION_ID:-}"

# Determine which context to restore (may already be set for welcome context)
vlog "Determining which context to restore..."
if [[ -z "$RESTORE_SESSION_ID" ]]; then
    if [[ -n "$TARGET_SESSION_ID" ]]; then
        vlog "User specified target session: $TARGET_SESSION_ID"
        # Check if specified session exists
        TARGET_CONTEXT="$COGNITIVE_CONTEXT_DIR/complete-context-${TARGET_SESSION_ID}.json"
        if [[ -f "$TARGET_CONTEXT" ]]; then
            RESTORE_SESSION_ID="$TARGET_SESSION_ID"
            vlog "Target session file found"
            echo -e "${GREEN}✅ Target session found: ${TARGET_SESSION_ID}${NC}"
        else
            vlog "Target session file NOT found: $TARGET_CONTEXT"
            echo -e "${RED}❌ ERROR: Specified session not found: ${TARGET_SESSION_ID}${NC}"
            exit 1
        fi
    else
        vlog "No target specified, finding most recent context..."
        # Find most recent context in session-management
        LATEST_CONTEXT=$(find "$COGNITIVE_CONTEXT_DIR" -name "complete-context-*.json" -type f 2>/dev/null | xargs ls -t 2>/dev/null | head -1)
        if [[ -n "$LATEST_CONTEXT" ]]; then
            RESTORE_SESSION_ID=$(basename "$LATEST_CONTEXT" | sed 's/complete-context-//' | sed 's/.json//')
            vlog "Using latest context: $RESTORE_SESSION_ID"
            echo -e "${GREEN}✅ Using latest session: ${RESTORE_SESSION_ID}${NC}"
        else
            vlog "No context files found"
        fi
    fi
else
    vlog "RESTORE_SESSION_ID already set: $RESTORE_SESSION_ID"
fi

if [[ -z "$RESTORE_SESSION_ID" ]]; then
    echo -e "${RED}❌ ERROR: No session to restore${NC}"
    exit 1
fi

echo ""
echo -e "${CYAN}🔄 RESTORING COGNITIVE CONTEXT${NC}"
echo -e "${BLUE}Session ID: ${RESTORE_SESSION_ID}${NC}"
echo -e "${BLUE}Restore Mode: ${RESTORE_MODE}${NC}"

# Execute cognitive context restoration
RESTORATION_RESULT=""
if ! RESTORATION_RESULT=$(node -e "
                const CognitiveWorkspaceSerializer = require('./cogspace/analyzers/serializer.cjs');
        const serializer = new CognitiveWorkspaceSerializer();

(async () => {
  try {
    console.log('🔄 Restoring cognitive workspace context...');
    const restored = await serializer.restoreWorkspaceContext('${RESTORE_SESSION_ID}');
    
    if (!restored) {
      console.error('❌ Context restoration failed - invalid or corrupted context');
      process.exit(1);
    }
    
    const context = restored.context;
    const continuityScore = restored.continuityScore;
    
    console.log(\`✅ Cognitive context restored successfully\`);
    console.log(\`🎯 Continuity Score: \${continuityScore}%\`);
    
    if (continuityScore >= 0) {
      console.log('🎯 TARGET ACHIEVED: context preservation');
    } else {
      console.log(\`⚠️ Below target: \${continuityScore}% below target\`);
    }
    
    // v21.9.0 - Dual format support: Handle both nested (serializedComponents) and flat formats
    const hasNested = context.serializedComponents && typeof context.serializedComponents === 'object';
    const formatType = hasNested ? 'nested' : 'flat';
    console.log(\`📦 Context Format: \${formatType}\`);

    // Helper function to get data from either format
    const getData = (nestedKey, flatKey) => {
      if (hasNested && context.serializedComponents[nestedKey]) {
        return context.serializedComponents[nestedKey];
      }
      if (context[flatKey || nestedKey]) {
        return context[flatKey || nestedKey];
      }
      return null;
    };

    // Display restored context summary
    console.log('');
    console.log('📋 RESTORED WORK CONTEXT:');

    const mental = getData('mentalModel');
    if (mental) {
      console.log('🧠 MENTAL MODEL:');
      console.log(\`   Work: \${mental.workDescription || 'N/A'}\`);
      console.log(\`   Focus: \${mental.currentFocus || 'N/A'}\`);
      if (mental.blockingIssues && mental.blockingIssues.length > 0) {
        console.log(\`   Blocking: \${mental.blockingIssues.join(', ')}\`);
      }
      if (mental.nextActions && mental.nextActions.length > 0) {
        console.log(\`   Next: \${mental.nextActions.join(', ')}\`);
      }
    }

    const narrative = getData('workNarrative');
    if (narrative) {
      console.log('');
      console.log('📖 WORK NARRATIVE:');
      console.log(\`   Story: \${narrative.sessionStory || 'N/A'}\`);
      console.log(\`   Current: \${narrative.currentChapter || 'N/A'}\`);
      console.log(\`   Next: \${narrative.nextChapter || 'N/A'}\`);
      if (narrative.achievements && narrative.achievements.length > 0) {
        console.log(\`   Achievements: \${narrative.achievements.length} items\`);
      }
    }

    const decisions = getData('decisionContext');
    if (decisions) {
      console.log('');
      console.log('🧠 DECISION CONTEXT:');
      if (decisions.chosenPaths && decisions.chosenPaths.length > 0) {
        decisions.chosenPaths.forEach((path, i) => {
          console.log(\`   \${i+1}. \${path.approach}: \${path.rationale}\`);
        });
      }
    }

    const perf = getData('performanceDeltas');
    if (perf) {
      console.log('');
      console.log('📊 PERFORMANCE METRICS:');
      if (perf.improvements && perf.improvements.length > 0) {
        perf.improvements.forEach(imp => {
          console.log(\`   ✅ \${imp.metric}: \${imp.improvement}\`);
        });
      }
    }

    const continuity = getData('executableContinuity');
    if (continuity) {
      console.log('');
      console.log('⚡ IMMEDIATE ACTIONS:');
      if (continuity.immediateActions && continuity.immediateActions.length > 0) {
        continuity.immediateActions.forEach((action, i) => {
          console.log(\`   \${i+1}. \${action.description}\`);
        });
      }
    }

    // Output structured data for shell processing
    console.log('');
    console.log('RESTORATION_DATA_START');
    console.log(JSON.stringify({
      sessionId: '${RESTORE_SESSION_ID}',
      continuityScore: continuityScore,
      restoredAt: '${TIMESTAMP}',
      projectName: context.projectName,
      formatType: formatType,
      mentalModel: mental || null,
      immediateActions: continuity?.immediateActions || []
    }));
    console.log('RESTORATION_DATA_END');
    
    process.exit(0);
  } catch (error) {
    console.error('❌ Cognitive restoration failed:', error.message);
    process.exit(1);
  }
})();
"); then
    echo -e "${RED}❌ COGNITIVE RESTORATION FAILED${NC}"
    echo -e "${YELLOW}⚠️  Continuing with error dashboard generation...${NC}"
    RESTORATION_FAILED=true
    RESTORATION_DATA="{\"error\": \"Context restoration failed\", \"sessionId\": \"${RESTORE_SESSION_ID}\", \"timestamp\": \"${TIMESTAMP}\"}"
else
    RESTORATION_FAILED=false
fi

# Extract restoration data for further processing
RESTORATION_DATA=$(echo "$RESTORATION_RESULT" | sed -n '/RESTORATION_DATA_START/,/RESTORATION_DATA_END/p' | grep -v 'RESTORATION_DATA_')

# Display restored context to user
if [[ -n "$RESTORATION_DATA" ]]; then
    echo ""
    echo -e "${MAGENTA}═══════════════════════════════════════════════════════${NC}"
    echo -e "${MAGENTA}   📖 RESTORED SESSION CONTEXT${NC}"
    echo -e "${MAGENTA}═══════════════════════════════════════════════════════${NC}"

    # Extract and display data
    WORK_DESC=$(echo "$RESTORATION_DATA" | jq -r '.mentalModel.workDescription // "No description"' 2>/dev/null)
    SESSION_STORY=$(echo "$RESTORATION_DATA" | jq -r '.workNarrative.sessionStory // "No story"' 2>/dev/null)
    CURRENT_CHAPTER=$(echo "$RESTORATION_DATA" | jq -r '.workNarrative.currentChapter // empty' 2>/dev/null)
    NEXT_CHAPTER=$(echo "$RESTORATION_DATA" | jq -r '.workNarrative.nextChapter // empty' 2>/dev/null)

    echo ""
    echo -e "${CYAN}📝 WHAT WE DID LAST SESSION:${NC}"
    echo -e "${WHITE}   $WORK_DESC${NC}"
    if [[ -n "$CURRENT_CHAPTER" ]]; then
        echo -e "${WHITE}   Chapter: $CURRENT_CHAPTER${NC}"
    fi
    echo ""

    # Achievements
    ACHIEVEMENTS=$(echo "$RESTORATION_DATA" | jq -r '.workNarrative.achievements[]?.achievement // empty' 2>/dev/null)
    if [[ -n "$ACHIEVEMENTS" ]]; then
        echo -e "${GREEN}✅ ACHIEVEMENTS:${NC}"
        while IFS= read -r achievement; do
            [[ -n "$achievement" ]] && echo -e "${GREEN}   • $achievement${NC}"
        done <<< "$ACHIEVEMENTS"
        echo ""
    fi

    # Challenges
    CHALLENGES=$(echo "$RESTORATION_DATA" | jq -r '.workNarrative.challenges[]?.challenge // empty' 2>/dev/null)
    if [[ -n "$CHALLENGES" ]]; then
        echo -e "${YELLOW}⚠️  REMAINING CHALLENGES:${NC}"
        while IFS= read -r challenge; do
            [[ -n "$challenge" ]] && echo -e "${YELLOW}   • $challenge${NC}"
        done <<< "$CHALLENGES"
        echo ""
    fi

    # Next Actions
    NEXT_ACTIONS=$(echo "$RESTORATION_DATA" | jq -r '.mentalModel.nextActions[]? // empty' 2>/dev/null)
    if [[ -n "$NEXT_ACTIONS" ]]; then
        echo -e "${CYAN}🎯 WHAT WE PLANNED FOR THIS SESSION:${NC}"
        while IFS= read -r action; do
            [[ -n "$action" ]] && echo -e "${CYAN}   • $action${NC}"
        done <<< "$NEXT_ACTIONS"
        if [[ -n "$NEXT_CHAPTER" ]]; then
            echo -e "${CYAN}   Next Chapter: $NEXT_CHAPTER${NC}"
        fi
        echo ""
    fi

    # Session Story
    if [[ "$SESSION_STORY" != "No story" && -n "$SESSION_STORY" ]]; then
        echo -e "${BLUE}📚 SESSION NARRATIVE:${NC}"
        echo -e "${WHITE}   $SESSION_STORY${NC}"
        echo ""
    fi

    # Developer Notes (v21.3.1: Always show with empty state message)
    echo -e "${CYAN}📝 RECENT DEVELOPER NOTES:${NC}"
    NOTES_DIR="$COGNITIVE_CONTEXT_DIR/notes"
    NOTES_DISPLAYED=false
    if [[ -d "$NOTES_DIR" ]]; then
        # Find recent notes (last 5, sorted by modification time)
        # FIX 2025-10-31: Use find instead of ls to avoid exit on no match with set -e
        RECENT_NOTES=$(find "$NOTES_DIR" -name "notes-*.md" -type f 2>/dev/null | xargs ls -t 2>/dev/null | head -5)
        if [[ -n "$RECENT_NOTES" ]]; then
            while IFS= read -r note_file; do
                if [[ -f "$note_file" ]]; then
                    # Extract developer name from filename: notes-{NAME}-{PROJECT}-{TIMESTAMP}.md
                    DEV_NAME=$(basename "$note_file" | sed 's/notes-\([^-]*\)-.*/\1/')
                    # Extract timestamp from filename
                    NOTE_TIMESTAMP=$(basename "$note_file" | sed 's/.*-\([0-9T-]*\)\.md/\1/' | sed 's/-/:/g' | sed 's/T/ /')
                    # Read note content (skip header lines, get actual note)
                    NOTE_CONTENT=$(sed -n '/^## Note Content/,/^---/p' "$note_file" | sed '1d;$d' | sed '/^$/d' | head -3)

                    if [[ -n "$NOTE_CONTENT" ]]; then
                        echo -e "${YELLOW}   👤 $DEV_NAME${NC} ${WHITE}($NOTE_TIMESTAMP)${NC}"
                        echo "$NOTE_CONTENT" | while IFS= read -r line; do
                            echo -e "${WHITE}      $line${NC}"
                        done
                        echo ""
                        NOTES_DISPLAYED=true
                    fi
                fi
            done <<< "$RECENT_NOTES"
        fi
    fi

    # Show empty state message if no notes found
    if [[ "$NOTES_DISPLAYED" == "false" ]]; then
        echo -e "${WHITE}   ...your notes will show here as you create them!${NC}"
        echo -e "${WHITE}   Tip: Use 'note \"YourName\" \"Your message\"' to add notes${NC}"
        echo ""
    fi

    # Continuity Score
    CONTINUITY_SCORE=$(echo "$RESTORATION_DATA" | jq -r '.continuityScore // empty' 2>/dev/null)
    if [[ -n "$CONTINUITY_SCORE" ]]; then
        echo -e "${MAGENTA}📊 Continuity Score: ${CONTINUITY_SCORE}%${NC}"
    fi

    echo -e "${MAGENTA}═══════════════════════════════════════════════════════${NC}"
    echo ""
fi

# Check for immediate action scripts
IMMEDIATE_ACTION_SCRIPT="next-immediate-action-${RESTORE_SESSION_ID}.sh"
if [[ -f "$IMMEDIATE_ACTION_SCRIPT" ]]; then
    echo ""
    echo -e "${YELLOW}🚀 IMMEDIATE ACTION SCRIPT FOUND${NC}"
    echo -e "${CYAN}Execute: ./${IMMEDIATE_ACTION_SCRIPT}${NC}"
    
    # Auto-execute immediate action script (non-interactive)
    echo -e "${BLUE}Auto-executing immediate action script (non-interactive mode)${NC}"
    echo -e "${CYAN}🚀 Executing immediate action script...${NC}"
    ./"$IMMEDIATE_ACTION_SCRIPT"
fi

# v39.0.0: Removed duplicate quick access commands creation
# Full commands are now deployed to cogspace/commands/ by deploy-cogspace.sh
# Commands available: guidelines, lessons, note, new-project, progress-report, trouble-report, update-readme
echo ""
echo -e "${MAGENTA}📚 COGSPACE COMMANDS${NC}"
echo -e "${GREEN}✅ Commands available in cogspace/commands/${NC}"
echo -e "${CYAN}   ./cogspace/commands/guidelines, lessons, note, etc.${NC}"

# Environment-specific setup
echo ""
echo -e "${MAGENTA}🌍 ENVIRONMENT-SPECIFIC SETUP${NC}"

case "$IDE_ENVIRONMENT" in
    "vscode")
        echo -e "${BLUE}VS Code environment detected${NC}"
        echo -e "${CYAN}💡 Use Ctrl+Shift+P → 'Open Integrated Terminal' for optimal experience${NC}"
        ;;
    "cursor")
        echo -e "${BLUE}Cursor environment detected${NC}"
        echo -e "${CYAN}💡 Use Ctrl+backtick for terminal, Ctrl+L for chat integration${NC}"
        ;;
    "claude-code")
        echo -e "${BLUE}Claude Code environment detected${NC}"
        echo -e "${CYAN}💡 All cognitive context available for AI analysis${NC}"
        ;;
    *)
        echo -e "${BLUE}Generic terminal environment${NC}"
        echo -e "${CYAN}💡 All enhanced session commands available${NC}"
        ;;
esac

# Final wake summary
echo ""
echo -e "${GREEN}✅ ENHANCED SESSION-WAKE COMPLETE${NC}"
echo -e "${CYAN}🌅 COGNITIVE WORKSPACE FULLY RESTORED${NC}"
echo ""
echo -e "${BLUE}📊 RESTORATION FEATURES ACTIVE:${NC}"
echo -e "${BLUE}  ✅ context preservation${NC}"
echo -e "${BLUE}  ✅ Complete cognitive context restoration${NC}"
echo -e "${BLUE}  ✅ Multi-environment compatibility${NC}"
echo -e "${BLUE}  ✅ Executable continuity scripts${NC}"
echo -e "${BLUE}  ✅ Dynamic guidelines/lessons/notes system${NC}"
echo -e "${BLUE}  ✅ Hardware failure recovery${NC}"
echo -e "${BLUE}  ✅ Portable context preservation${NC}"
echo ""

# ============================================================================
# SKILLS INTEGRATION - Phase 1
# ============================================================================

# Skills repo: Crystal Palace local or user's home directory
if [[ -d "/Volumes/FOUR-TB/root/claude-skills" ]]; then
    SKILLS_REPO="/Volumes/FOUR-TB/root/claude-skills"
elif [[ -d "$HOME/claude-skills" ]]; then
    SKILLS_REPO="$HOME/claude-skills"
else
    SKILLS_REPO=""
fi
PROJECT_SKILLS_DIR="${PROJECT_ROOT}/.claude/skills"
LAST_WAKE_FILE="${PROJECT_ROOT}/.claude/.last-wake"

# Create .claude directory if it doesn't exist
mkdir -p "${PROJECT_ROOT}/.claude"

# Check if central skills repository exists
if [[ -n "$SKILLS_REPO" && -d "$SKILLS_REPO" ]]; then
    # Create skills directory
    mkdir -p "$PROJECT_SKILLS_DIR"

    # Track linking statistics
    LINKED_COUNT=0
    SKIPPED_COUNT=0

    # Store category stats in temporary file (Bash 3.2 compatible)
    STATS_TEMP="/tmp/cogspace-skills-stats-$$.txt"
    > "$STATS_TEMP"  # Clear temp file

    # Link each category from central repository
    for category_path in "$SKILLS_REPO"/*; do
        if [[ -d "$category_path" ]] && [[ $(basename "$category_path") != ".git" ]]; then
            CATEGORY_NAME=$(basename "$category_path")
            TARGET_LINK="$PROJECT_SKILLS_DIR/$CATEGORY_NAME"

            # Skip if link exists and is correct
            if [[ -L "$TARGET_LINK" ]] && [[ "$(readlink "$TARGET_LINK")" == "$category_path" ]]; then
                ((SKIPPED_COUNT++))
            else
                # Remove broken link if exists
                [[ -L "$TARGET_LINK" ]] && rm "$TARGET_LINK"

                # Create symlink
                ln -s "$category_path" "$TARGET_LINK"
                ((LINKED_COUNT++))
            fi

            # Count operational and pending skills in this category
            READY_COUNT=0
            PENDING_COUNT=0
            for skill_dir in "$category_path"/*; do
                if [[ -d "$skill_dir" ]]; then
                    # Check if skill has SKILL.md (operational) or PENDING.md (pending)
                    if [[ -f "$skill_dir/SKILL.md" ]]; then
                        ((READY_COUNT++))
                    elif [[ -f "$skill_dir/PENDING.md" ]] || [[ -f "$skill_dir/README.md" ]]; then
                        ((PENDING_COUNT++))
                    else
                        # Default to ready if has content
                        ((READY_COUNT++))
                    fi
                fi
            done

            # Store stats in temp file (category:ready:pending)
            echo "$CATEGORY_NAME:$READY_COUNT:$PENDING_COUNT" >> "$STATS_TEMP"
        fi
    done

    # Detect new skills since last wake
    NEW_SKILLS=()
    if [[ -f "$LAST_WAKE_FILE" ]]; then
        LAST_WAKE_TIME=$(cat "$LAST_WAKE_FILE")

        # Find skills modified after last wake
        while IFS= read -r -d '' skill_dir; do
            SKILL_NAME=$(basename "$(dirname "$skill_dir")")/$(basename "$skill_dir")
            NEW_SKILLS+=("$SKILL_NAME")
        done < <(find "$SKILLS_REPO" -mindepth 2 -maxdepth 2 -type d -newer "$LAST_WAKE_FILE" -print0 2>/dev/null)
    fi

    # Update last wake timestamp
    date +%s > "$LAST_WAKE_FILE"

    # Display Skills Integration Section
    echo ""
    echo -e "${MAGENTA}═══════════════════════════════════════════════════════════════════════${NC}"
    echo -e "${MAGENTA}🧠 SKILLS INTEGRATION - Claude Code Enhanced Capabilities${NC}"
    echo -e "${MAGENTA}═══════════════════════════════════════════════════════════════════════${NC}"
    echo ""

    # Show new skills alert if any
    if [[ ${#NEW_SKILLS[@]} -gt 0 ]]; then
        echo -e "${GREEN}✨ NEW SKILLS DETECTED: ${#NEW_SKILLS[@]} new skills available since last wake${NC}"
        for skill in "${NEW_SKILLS[@]}"; do
            echo -e "${CYAN}   🆕 $skill${NC}"
        done
        echo ""
    fi

    # Two-column skills summary
    printf "┌───────────────────────────────────┬───────────────────────────────────┐\n"
    printf "│ ${BLUE}📚 CATEGORY${NC}                       │ ${BLUE}STATUS${NC}                            │\n"
    printf "├───────────────────────────────────┼───────────────────────────────────┤\n"

    # Display each category with stats (read from temp file)
    for category in mathematics educational research sciences ai-integration; do
        # Look up stats for this category in temp file
        STATS_LINE=$(grep "^$category:" "$STATS_TEMP" 2>/dev/null)
        if [[ -n "$STATS_LINE" ]]; then
            IFS=':' read -r cat_name ready pending <<< "$STATS_LINE"

            # Category icons
            case "$category" in
                mathematics) icon="📚" ;;
                educational) icon="🎓" ;;
                research) icon="🔬" ;;
                sciences) icon="🧬" ;;
                ai-integration) icon="🤖" ;;
            esac

            printf "│ $icon %-27s│ ✅ %-2d ready, ⏳ %-2d pending        │\n" "$category ($((ready + pending)))" "$ready" "$pending"
        fi
    done

    # Clean up temp file
    rm -f "$STATS_TEMP"

    printf "└───────────────────────────────────┴───────────────────────────────────┘\n"
    echo ""

    # Quick access information
    echo -e "${CYAN}📍 Skills Location:${NC} .claude/skills/ (symlinked to central repository)"
    echo -e "${CYAN}🎯 Quick Access:${NC}"
    echo -e "   ${BLUE}• Use skill commands:${NC} wolfram, notebooklm, khan, semantic-scholar, etc."
    echo -e "   ${BLUE}• View skill details:${NC} cat .claude/skills/<category>/<skill>/SKILL.md"
    echo -e "   ${BLUE}• Central repository:${NC} $SKILLS_REPO"
    echo ""

    if [[ $LINKED_COUNT -gt 0 ]]; then
        echo -e "${GREEN}✅ Skills Integration: $LINKED_COUNT new categories linked${NC}"
    else
        echo -e "${GREEN}✅ Skills Integration: All categories current (${SKIPPED_COUNT} already linked)${NC}"
    fi

else
    echo ""
    echo -e "${YELLOW}⚠️  Central skills repository not found: $SKILLS_REPO${NC}"
    echo -e "${YELLOW}   Skills integration will be available after repository setup${NC}"
fi

echo ""
echo -e "${MAGENTA}🚀 AVAILABLE COMMANDS:${NC}"
echo -e "${CYAN}  • ./session-wake.sh \"message\" - Save context during session${NC}"
echo -e "${CYAN}  • ./session-wake.sh \"message\" - Complete session termination${NC}"
echo -e "${CYAN}  • ./cogspace/commands/trouble-report - Create trouble reports for issues and bugs${NC}"
echo -e "${CYAN}  • guidelines [list|add|get] - Manage project guidelines${NC}"
echo -e "${CYAN}  • lessons [list|add|get] - Manage lessons learned${NC}"
echo -e "${CYAN}  • note [dev-name] [content] - Add developer notes${NC}"
echo ""
echo -e "${GREEN}🎯 REVOLUTIONARY SESSION MANAGEMENT ACTIVE${NC}"
echo -e "${YELLOW}🚀 Ready for productive development with cognitive continuity${NC}"

# Generate Dev Cockpit Dashboard
echo ""
echo -e "${CYAN}🎛️ GENERATING IDEAPLACE DASHBOARD${NC}"

# Extract developer name from project configuration
DEVNAME=""
if [[ -f "${PROJECT_ROOT}/docs/package.json" ]]; then
    DEVNAME=$(jq -r '.author // empty' "${PROJECT_ROOT}/docs/package.json" 2>/dev/null || echo "")
fi
# Fallback to system username if not found
if [[ -z "$DEVNAME" ]]; then
    DEVNAME=$(whoami)
fi

fi  # End of: if [[ "$FRESH_WORKSPACE" = false ]]

# v51.5.0 FIX: Actually call the dashboard generator!
# (v51.0.0-51.4.0 had a bug where this was never called despite the message above)
DASHBOARD_GENERATOR="${PROJECT_ROOT}/cogspace/dashboard/generate.sh"
if [[ -f "$DASHBOARD_GENERATOR" ]]; then
    vlog "Calling dashboard generator: $DASHBOARD_GENERATOR"
    if bash "$DASHBOARD_GENERATOR" "$PROJECT_NAME" "$WAKE_SESSION_ID" "$TIMESTAMP" "$PROJECT_ROOT" 2>/dev/null; then
        vlog "Dashboard generation completed successfully"
    else
        vlog "Dashboard generation had issues (continuing)"
    fi
else
    vlog "Dashboard generator not found: $DASHBOARD_GENERATOR"
fi

# ============================================================================
# DATABASE CONTEXT RESTORATION (PRIMARY SOURCE)
# ============================================================================
# Database is now PRIMARY source of truth for session context.
# Full context display is DEFAULT behavior.

echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BOLD}${CYAN}📊 COGSPACE v${COGSPACE_VERSION} - FULL CONTEXT RESTORATION${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Find db-session-restore.py
DB_RESTORE_SCRIPT=""
if [[ -f "${SCRIPT_DIR}/db-session-restore.py" ]]; then
    DB_RESTORE_SCRIPT="${SCRIPT_DIR}/db-session-restore.py"
elif [[ -f "${PROJECT_ROOT}/cogspace/db-session-restore.py" ]]; then
    DB_RESTORE_SCRIPT="${PROJECT_ROOT}/cogspace/db-session-restore.py"
fi
vlog "DB restore script: ${DB_RESTORE_SCRIPT:-'(not found)'}"

# v59.1.0: Crash Recovery - Check for orphaned sessions before restore
CRASH_RECOVERY_SCRIPT="${PROJECT_ROOT}/cogspace/db/recover-crashed-session.py"
if [[ -f "$CRASH_RECOVERY_SCRIPT" ]] && [[ -f "${PROJECT_ROOT}/.cogspace/cogspace.db" ]]; then
    echo -e "${CYAN}🔍 Checking for crashed sessions to recover...${NC}"
    RECOVERY_OUTPUT=$(python3 "$CRASH_RECOVERY_SCRIPT" --recover-all --hours 72 2>&1)
    # Only show output if orphans were found
    if echo "$RECOVERY_OUTPUT" | grep -q "orphaned session\|Recovered session"; then
        echo "$RECOVERY_OUTPUT" | grep -E "🚨|✅ Recovered|📝|⏰" | head -15
        echo ""
    else
        vlog "No crashed sessions to recover"
    fi
fi

# Restore context from database (PRIMARY SOURCE)
if [[ -n "$DB_RESTORE_SCRIPT" ]] && [[ -f "${PROJECT_ROOT}/.cogspace/cogspace.db" ]]; then
    vlog "Restoring context from database..."
    # Get display level from config or default to 'full'
    DISPLAY_LEVEL="full"
    if [[ -f "${PROJECT_ROOT}/.cogspace/config" ]]; then
        source "${PROJECT_ROOT}/.cogspace/config" 2>/dev/null || true
        DISPLAY_LEVEL="${COGSPACE_DISPLAY_LEVEL:-full}"
    fi
    vlog "Display level: $DISPLAY_LEVEL"

    python3 "$DB_RESTORE_SCRIPT" "$PROJECT_NAME" --level="$DISPLAY_LEVEL" || {
        echo -e "${YELLOW}⚠️ Database restore encountered an issue (continuing)${NC}"
    }
else
    vlog "Database not found or restore script missing, using legacy display"
    # Legacy fallback: Show session summary from JSON
    if [[ -f "${PROJECT_ROOT}/session-management/cognitive-context/session-summary.json" ]]; then
        echo -e "${YELLOW}📝 Previous Session Summary (JSON fallback):${NC}"
        if command -v jq &>/dev/null; then
            jq -r '.sleepMessage // .summary // "No summary available"' \
                "${PROJECT_ROOT}/session-management/cognitive-context/session-summary.json" 2>/dev/null || true
        else
            cat "${PROJECT_ROOT}/session-management/cognitive-context/session-summary.json" 2>/dev/null | head -20 || true
        fi
        echo ""
    fi
fi

# ============================================================================
# Smart Dashboard Auto-Open (Same-Tab Support)
# ============================================================================

echo ""
echo "📊 Opening dashboard..."
vlog "Searching for dashboard HTML files..."

# v32.1.5: Check new path first, fall back to legacy path
LATEST_DASHBOARD=$(ls -t session-management/dashboard/dashboard-*.html 2>/dev/null | head -1)
vlog "Checked session-management/dashboard/: ${LATEST_DASHBOARD:-'(none)'}"
if [[ -z "$LATEST_DASHBOARD" ]]; then
    LATEST_DASHBOARD=$(ls -t dashboard/dashboard-*.html 2>/dev/null | head -1)
    vlog "Checked dashboard/ fallback: ${LATEST_DASHBOARD:-'(none)'}"
fi

if [[ -n "$LATEST_DASHBOARD" ]]; then
    vlog "Dashboard file: $LATEST_DASHBOARD"

    # v51.0.0: Check if auto-open is enabled (default: true)
    DASHBOARD_AUTO_OPEN="true"
    BROWSER_PREFERENCE="auto"
    if [[ -f "${PROJECT_ROOT}/.cogspace/config" ]]; then
        source "${PROJECT_ROOT}/.cogspace/config" 2>/dev/null || true
        DASHBOARD_AUTO_OPEN="${COGSPACE_DASHBOARD_AUTO_OPEN:-true}"
        BROWSER_PREFERENCE="${COGSPACE_BROWSER_PREFERENCE:-auto}"
    fi
    vlog "Dashboard auto-open: $DASHBOARD_AUTO_OPEN, Browser: $BROWSER_PREFERENCE"

    if [[ "$DASHBOARD_AUTO_OPEN" == "true" ]]; then
        # v51.0.0: Use smart browser integration for same-tab support
        BROWSER_INTEGRATION=""
        if [[ -f "${SCRIPT_DIR}/browser-integration.sh" ]]; then
            BROWSER_INTEGRATION="${SCRIPT_DIR}/browser-integration.sh"
        elif [[ -f "${PROJECT_ROOT}/cogspace/browser-integration.sh" ]]; then
            BROWSER_INTEGRATION="${PROJECT_ROOT}/cogspace/browser-integration.sh"
        fi

        if [[ -n "$BROWSER_INTEGRATION" ]] && [[ -x "$BROWSER_INTEGRATION" ]]; then
            vlog "Using smart browser integration: $BROWSER_INTEGRATION"
            "$BROWSER_INTEGRATION" "$LATEST_DASHBOARD" --browser="$BROWSER_PREFERENCE" 2>/dev/null || {
                vlog "Browser integration failed, using simple open"
                open "$LATEST_DASHBOARD"
            }
        else
            vlog "Browser integration not found, using simple open"
            open "$LATEST_DASHBOARD"
        fi
        echo "✓ Dashboard opened: $LATEST_DASHBOARD"
    else
        echo "ℹ️  Dashboard ready: $LATEST_DASHBOARD"
        echo "   Auto-open disabled. Run: open \"$LATEST_DASHBOARD\""
    fi
else
    vlog "No dashboard files found"
    echo "ℹ️  No dashboard yet (will generate after first session)"
fi

# ============================================================================
# CRYSTAL PALACE HOST INTEGRATION - Push project registration on wake
# ============================================================================
# v35.0.0: Push-based sync replaces pull-based cron job
# Works from LAN (192.168.50.58) or remotely via Tailscale
# DISABLED v40.0.1: Crystal Palace sync temporarily disabled pending infrastructure fixes
# To re-enable: remove the 'if false; then' wrapper and matching 'fi'

if false; then
CRYSTAL_PALACE_SYNC=""
if [[ -f "${SCRIPT_DIR}/skills/crystal-palace-sync.sh" ]]; then
    CRYSTAL_PALACE_SYNC="${SCRIPT_DIR}/skills/crystal-palace-sync.sh"
elif [[ -f "${PROJECT_ROOT}/cogspace/skills/crystal-palace-sync.sh" ]]; then
    CRYSTAL_PALACE_SYNC="${PROJECT_ROOT}/cogspace/skills/crystal-palace-sync.sh"
fi

if [[ -n "$CRYSTAL_PALACE_SYNC" ]]; then
    echo ""
    echo -e "${CYAN}🏰 CRYSTAL PALACE HOST SYNC${NC}"
    # Export variables for the sync script
    export PROJECT_ROOT PROJECT_NAME COGSPACE_MODE IDE_ENVIRONMENT
    # Run registration in background (non-blocking)
    (
        "$CRYSTAL_PALACE_SYNC" register wake "$WAKE_SESSION_ID" 2>/dev/null
        # Also check and display health status
        "$CRYSTAL_PALACE_SYNC" health 2>/dev/null
    ) &
fi
fi



