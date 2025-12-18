#!/bin/bash
# COGSPACE v55.0.0
# COGSPACE DIAGNOSTICS v55.0.0 - Complete Healing
# Automatically detects and repairs COGSPACE integrity issues
# Version: 55.0.0 - Complete infrastructure cleanup & command symlinks
#
# v55.0.0 Changes:
#   - ENHANCED: Intelligent /src/ cleanup (preserves user code, removes COGSPACE scripts)
#   - ENHANCED: Intelligent /commands/ cleanup (removes old symlinks to /src/)
#   - ADDED: Command symlinks for all 7 commands (guidelines, lessons, note, etc.)
#   - ADDED: Symlink validation with auto-fix
#   - ADDED: Expanded DEPRECATED_ITEMS (templates, config, canvas-extract-test-01)
#   - ADDED: Safety guarantees for user code protection
#
# v50.0.0 Changes:
#   - MAJOR: Per-project SQLite database for session persistence
#   - Added cogspace/db/ module with auto-migration
#   - Added db-session-save.py and db-session-restore.py
#   - Aggressive cleanup: removes cogspace-backup-*, .diagnostics.*.log, .session-dna-updated
#   - Python3 now REQUIRED for database operations
#
# v40.0.0 Changes:
#   - BREAKING: Single version source - cogspace/cogspace-version.json only
#   - Removed .version and cogspace/.cogspace-version (legacy artifacts)
#   - All version reads now use jq to parse JSON
#
# v35.2.5 Changes:
#   - Cross-platform timeout: Uses gtimeout on macOS, timeout on Linux
#   - Graceful fallback: Works without timeout (with warning)
#
# v35.2.0 Changes:
#   - Dynamic DNA resolution (Crystal Palace → GitHub → Cache → Standalone)
#   - Portable mode: Works anywhere, not just Crystal Palace
#   - Mode indicators: 🏰 Crystal Palace / 📱 Portable / ⚠️ Standalone
#   - GitHub DNA: howeirdo/cogspace-remote-dna as source of truth

set -eu

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Get project info
# v38.2.1: Fixed path - script is at cogspace/src/, so need /../.. to reach project root
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PROJECT_NAME=$(basename "$PROJECT_ROOT")

# Get developer name
DEV_NAME="${USER:-wizard}"
if [[ -f "$PROJECT_ROOT/package.json" ]]; then
    DEV_NAME=$(jq -r '.author.name // .author // empty' "$PROJECT_ROOT/package.json" 2>/dev/null | head -1 || echo "${USER:-wizard}")
fi

# Cross-platform timeout command (v35.2.5)
# macOS doesn't have 'timeout' by default - uses 'gtimeout' from coreutils
# Linux has 'timeout' in coreutils
# Fallback: run without timeout if neither available
TIMEOUT_CMD=""
if command -v timeout &>/dev/null; then
    TIMEOUT_CMD="timeout"
elif command -v gtimeout &>/dev/null; then
    TIMEOUT_CMD="gtimeout"
fi

# Helper function: run command with timeout if available
run_with_timeout() {
    local seconds=$1
    shift
    if [[ -n "$TIMEOUT_CMD" ]]; then
        $TIMEOUT_CMD "$seconds" "$@"
    else
        "$@"
    fi
}

# DNA Source Resolution (v35.0.0+ architecture)
# Tiered fallback: Crystal Palace → GitHub → Cache → Standalone
COGSPACE_DNA_REPO="howeirdo/cogspace-remote-dna"
COGSPACE_DNA_CACHE="$HOME/.cogspace/dna"
COGSPACE_MODE="unknown"
DNA_SOURCE=""

resolve_dna_source() {
    # Tier 1: Crystal Palace Local (legacy - for transition period)
    if [[ -d "/Volumes/FOUR-TB/cogspace-dna-source/current" ]]; then
        DNA_SOURCE="/Volumes/FOUR-TB/cogspace-dna-source/current"
        COGSPACE_MODE="crystal-palace"
        return 0
    fi

    # Tier 2: Update from GitHub if possible, then use cache
    # v51.4.0: Use gh repo sync with stash to handle auth and local changes
    # Fixes: TR-tic-tac-toe-20251210-204806-0954 (silent sync failure)
    if command -v gh &>/dev/null && gh auth status &>/dev/null 2>&1; then
        mkdir -p "$COGSPACE_DNA_CACHE"
        if [[ -d "$COGSPACE_DNA_CACHE/.git" ]]; then
            # Update existing cache - sync latest from GitHub
            # v51.4.0: Use gh repo sync with stash (handles auth + local changes)
            (
                cd "$COGSPACE_DNA_CACHE"
                # Stash any local changes (from previous COGSPACE operations)
                git stash --all --quiet 2>/dev/null || true
                # Use gh repo sync (handles auth properly via gh credentials)
                if run_with_timeout 15 gh repo sync --force 2>/dev/null; then
                    : # Success
                else
                    # Fallback to git pull if gh repo sync fails
                    GIT_TERMINAL_PROMPT=0 run_with_timeout 10 git pull --quiet 2>/dev/null || true
                fi
                # Drop stashed changes (don't pollute DNA cache with project artifacts)
                git stash drop --quiet 2>/dev/null || true
            ) 2>/dev/null || true
        else
            # Fresh clone (30s timeout)
            run_with_timeout 30 gh repo clone "$COGSPACE_DNA_REPO" "$COGSPACE_DNA_CACHE" --depth 1 2>/dev/null || true
        fi
    fi

    # Tier 3: Use cached DNA (whether just updated or from previous session)
    # v40.0.0: Single version source - cogspace-version.json
    if [[ -f "$COGSPACE_DNA_CACHE/cogspace/cogspace-version.json" ]]; then
        DNA_SOURCE="$COGSPACE_DNA_CACHE"
        COGSPACE_MODE="portable"
        return 0
    fi

    # Tier 4: No DNA available - standalone mode (limited healing)
    DNA_SOURCE=""
    COGSPACE_MODE="standalone"
    return 1
}

# Resolve DNA source
resolve_dna_source || true

# Parse mode
MODE="${1:---interactive}"

# Required files for COGSPACE to be considered "perfect"
# v33.0.0: Clean Start - memories/ removed, dashboard relocated
# v50.0.0: Added database components
# v55.0.0: Added command symlinks
REQUIRED_FILES=(
    "cogspace/core/session-wake.sh"
    "cogspace/core/session-sleep.sh"
    "cogspace/core/session-save.sh"
    "cogspace/dashboard/generate-simple.cjs"
    "cogspace/dashboard/generate.sh"
    "cogspace/claude-code-context-extractor.cjs"
    "cogspace/generate-complete-context.cjs"
    "cogspace/analyzers/semantic-analyzer.cjs"
    "cogspace/analyzers/git-diff-analyzer.cjs"
    "cogspace/analyzers/user-context-analyzer.cjs"
    "cogspace/cogspace-version.json"
    # Core script symlinks
    "wake.sh"
    "sleep.sh"
    "save.sh"
    "hi"
    "bye"
    "save"
    # Command files in cogspace/commands/
    "cogspace/commands/trouble-report"
    "cogspace/commands/progress-report"
    "cogspace/commands/new-project"
    "cogspace/commands/guidelines"
    "cogspace/commands/lessons"
    "cogspace/commands/note"
    "cogspace/commands/update-readme"
    # v55.0.0: Root symlinks for commands
    "guidelines"
    "lessons"
    "note"
    "trouble-report"
    "progress-report"
    "new-project"
    "update-readme"
    # Diagnostics and database
    "cogspace/src/cogspace-diagnostics.sh"
    "cogspace/db/cogspace_db.py"
    "cogspace/db/schema_version.json"
    "cogspace/db-session-save.py"
    "cogspace/db-session-restore.py"
)

# v33.0.0: Required directories
REQUIRED_DIRS=(
    "session-management/cognitive-context"
    "session-management/dashboard"
    "session-management/system-state"
)

# v33.0.0: Deprecated files/directories (should NOT exist)
# v40.0.0: Added .version and cogspace/.cogspace-version as deprecated
# v50.0.0: Added cogspace-backup-*, .session-dna-updated, src/ (if empty)
# v55.0.0: Added templates, config, canvas-extract-test-01
DEPRECATED_ITEMS=(
    "memories"
    ".session-dna-version"
    "dashboard"
    ".version"
    "cogspace/.cogspace-version"
    ".session-dna-updated"
    # v55.0.0 deprecated - old infrastructure
    "templates"                    # Old AITCL templates
    "config"                       # Old cognitive-workspace-version.json
    "canvas-extract-test-01"       # Old test artifacts
)

# v55.0.0: Known old COGSPACE scripts that can be safely removed from /src/
OLD_COGSPACE_SCRIPTS=(
    "cogspace" "cogspace-diagnostics.sh" "cogspace-install-lib.sh"
    "create-project-bob" "help-me-bob" "new-project" "update-bob"
    "trouble-report" "progress-report" "project-list" "project-registry-enhanced.sh"
    "mass-heal-all-projects.sh" "dna-version-upgrade-system.sh"
    "migrate-to-single-version.sh" "validate-dna-version.sh"
    "deploy-group-1-core-infrastructure.sh" "deploy-group-2-crystal-palace.sh"
    "setup-cogspace-command.sh" "setup-global-commands.sh"
)

# v55.0.0: Command symlinks that should exist at project root
COMMAND_SYMLINKS=(
    "guidelines:cogspace/commands/guidelines"
    "lessons:cogspace/commands/lessons"
    "note:cogspace/commands/note"
    "trouble-report:cogspace/commands/trouble-report"
    "progress-report:cogspace/commands/progress-report"
    "new-project:cogspace/commands/new-project"
    "update-readme:cogspace/commands/update-readme"
)

# v55.0.0: Core script symlinks for validation
CORE_SYMLINKS=(
    "hi:cogspace/core/session-wake.sh"
    "bye:cogspace/core/session-sleep.sh"
    "save:cogspace/core/session-save.sh"
    "wake.sh:cogspace/core/session-wake.sh"
    "sleep.sh:cogspace/core/session-sleep.sh"
    "save.sh:cogspace/core/session-save.sh"
)

# Function: v55.0.0 - Cleanup deprecated infrastructure (with user code protection)
cleanup_deprecated_infrastructure() {
    # Handle /commands/ at root - ONLY if it contains symlinks to /src/
    if [[ -d "$PROJECT_ROOT/commands" ]]; then
        local is_old_infra=true
        local item_count=0
        for item in "$PROJECT_ROOT/commands"/*; do
            [[ -e "$item" ]] || continue  # Skip if glob didn't match
            ((item_count++))
            if [[ -L "$item" ]]; then
                local target=$(readlink "$item")
                if [[ "$target" != ../src/* ]]; then
                    is_old_infra=false
                    break
                fi
            elif [[ -f "$item" ]] || [[ -d "$item" ]]; then
                # Contains actual files/directories, not just symlinks
                is_old_infra=false
                break
            fi
        done

        if [[ "$is_old_infra" == true ]] && [[ $item_count -gt 0 ]]; then
            rm -rf "$PROJECT_ROOT/commands"
            echo "  🗑️  Removed deprecated commands/ (old symlinks to src/)"
        elif [[ $item_count -eq 0 ]]; then
            rm -rf "$PROJECT_ROOT/commands"
            echo "  🗑️  Removed empty commands/ directory"
        else
            echo "  ⚠️  commands/ contains user content - manual review needed"
        fi
    fi

    # Handle /src/ at root - detect if it's old COGSPACE scripts
    if [[ -d "$PROJECT_ROOT/src" ]]; then
        local cogspace_scripts=0
        local user_files=0

        for file in "$PROJECT_ROOT/src"/*; do
            [[ -e "$file" ]] || continue  # Skip if glob didn't match
            local basename=$(basename "$file")
            local is_cogspace=false
            for cs in "${OLD_COGSPACE_SCRIPTS[@]}"; do
                if [[ "$basename" == "$cs" ]]; then
                    is_cogspace=true
                    ((cogspace_scripts++))
                    break
                fi
            done
            if [[ "$is_cogspace" == false ]]; then
                ((user_files++))
            fi
        done

        if [[ $user_files -eq 0 ]] && [[ $cogspace_scripts -gt 0 ]]; then
            rm -rf "$PROJECT_ROOT/src"
            echo "  🗑️  Removed deprecated src/ ($cogspace_scripts old COGSPACE scripts)"
        elif [[ $cogspace_scripts -gt 0 ]]; then
            echo "  ⚠️  src/ has $cogspace_scripts COGSPACE scripts AND $user_files user files"
            echo "  ⚠️  Manual review needed - keeping directory intact"
        elif [[ $user_files -eq 0 ]] && [[ $cogspace_scripts -eq 0 ]]; then
            # Empty src/ directory - safe to remove
            if [[ -z "$(ls -A "$PROJECT_ROOT/src" 2>/dev/null)" ]]; then
                rm -rf "$PROJECT_ROOT/src"
                echo "  🗑️  Removed empty src/ directory"
            fi
        fi
    fi
}

# Function: v55.0.0 - Create all command symlinks
create_command_symlinks() {
    for entry in "${COMMAND_SYMLINKS[@]}"; do
        local name="${entry%%:*}"
        local target="${entry#*:}"

        # Only create if target exists in cogspace/commands/
        if [[ -f "$PROJECT_ROOT/$target" ]]; then
            # Remove old symlink or file if it exists
            if [[ -e "$PROJECT_ROOT/$name" ]] || [[ -L "$PROJECT_ROOT/$name" ]]; then
                rm -f "$PROJECT_ROOT/$name"
            fi
            ln -sf "$target" "$PROJECT_ROOT/$name"
            chmod +x "$PROJECT_ROOT/$name"
            echo "  ✅ Created symlink: $name → $target"
        fi
    done
}

# Function: v55.0.0 - Validate symlink targets
validate_symlinks() {
    local symlink_issues=()

    # Check core symlinks
    for entry in "${CORE_SYMLINKS[@]}"; do
        local name="${entry%%:*}"
        local expected_target="${entry#*:}"

        if [[ -L "$PROJECT_ROOT/$name" ]]; then
            local actual_target=$(readlink "$PROJECT_ROOT/$name")
            if [[ "$actual_target" != "$expected_target" ]]; then
                symlink_issues+=("$name points to '$actual_target' instead of '$expected_target'")
                # Auto-fix: recreate symlink with correct target
                rm -f "$PROJECT_ROOT/$name"
                ln -sf "$expected_target" "$PROJECT_ROOT/$name"
                chmod +x "$PROJECT_ROOT/$name"
                echo "  🔧 Fixed symlink: $name → $expected_target"
            fi
        elif [[ -f "$PROJECT_ROOT/$name" ]]; then
            # It's a file, not a symlink - acceptable but suboptimal
            :
        fi
    done

    # Check command symlinks
    for entry in "${COMMAND_SYMLINKS[@]}"; do
        local name="${entry%%:*}"
        local expected_target="${entry#*:}"

        if [[ -L "$PROJECT_ROOT/$name" ]]; then
            local actual_target=$(readlink "$PROJECT_ROOT/$name")
            if [[ "$actual_target" != "$expected_target" ]]; then
                symlink_issues+=("$name points to '$actual_target' instead of '$expected_target'")
                # Auto-fix: recreate symlink with correct target
                rm -f "$PROJECT_ROOT/$name"
                ln -sf "$expected_target" "$PROJECT_ROOT/$name"
                chmod +x "$PROJECT_ROOT/$name"
                echo "  🔧 Fixed symlink: $name → $expected_target"
            fi
        fi
    done

    # Return issues for logging (if any)
    if [[ ${#symlink_issues[@]} -gt 0 ]]; then
        for issue in "${symlink_issues[@]}"; do
            echo "SYMLINK_ISSUE: $issue"
        done
    fi
}

# Function: Get DNA version
# v40.0.0: Single version source - cogspace-version.json only
get_dna_version() {
    # Check if DNA source is available
    if [[ -z "$DNA_SOURCE" ]]; then
        echo "0.0.0"
        return
    fi

    # v40.0.0: Single source - cogspace-version.json only (jq required)
    if [[ -f "$DNA_SOURCE/cogspace/cogspace-version.json" ]] && command -v jq &> /dev/null; then
        jq -r '.version // "0.0.0"' "$DNA_SOURCE/cogspace/cogspace-version.json" 2>/dev/null | tr -d '\n' || echo "0.0.0"
    else
        echo "0.0.0"
    fi
}

# Function: Get current version
# v40.0.0: Single version source - cogspace-version.json only
get_current_version() {
    if [[ -f "$PROJECT_ROOT/cogspace/cogspace-version.json" ]] && command -v jq &> /dev/null; then
        jq -r '.version // "0.0.0"' "$PROJECT_ROOT/cogspace/cogspace-version.json" 2>/dev/null | tr -d '\n' || echo "0.0.0"
    else
        echo "0.0.0"
    fi
}

# Function: Check if system is perfect
check_system_health() {
    local is_perfect=true
    local issues=()

    # Check version
    local current_version=$(get_current_version)
    local dna_version=$(get_dna_version)

    if [[ "$current_version" == "missing" ]]; then
        is_perfect=false
        issues+=("Version file missing")
    elif [[ "$current_version" != "$dna_version" ]]; then
        is_perfect=false
        issues+=("Version mismatch: $current_version (current) vs $dna_version (expected)")
    fi

    # Check required files
    for file in "${REQUIRED_FILES[@]}"; do
        if [[ ! -f "$PROJECT_ROOT/$file" ]]; then
            is_perfect=false
            issues+=("Missing file: $file")
        fi
    done

    # v33.0.0: Check required directories
    for dir in "${REQUIRED_DIRS[@]}"; do
        if [[ ! -d "$PROJECT_ROOT/$dir" ]]; then
            is_perfect=false
            issues+=("Missing directory: $dir")
        fi
    done

    # v33.0.0: Check for deprecated items (should NOT exist)
    for item in "${DEPRECATED_ITEMS[@]}"; do
        if [[ -e "$PROJECT_ROOT/$item" ]]; then
            is_perfect=false
            issues+=("Deprecated item still present: $item (should be removed in v33.0.0)")
        fi
    done

    # Return results
    if [[ "$is_perfect" == true ]]; then
        echo "PERFECT"
    else
        echo "NOT_PERFECT"
        for issue in "${issues[@]}"; do
            echo "ISSUE: $issue"
        done
    fi
}

# Function: Create timestamped log
create_log() {
    local timestamp=$(date +%Y%m%d-%H%M%S)
    local log_file="$PROJECT_ROOT/cogspace/.diagnostics.${timestamp}.log"

    local current_version=$(get_current_version)
    local dna_version=$(get_dna_version)
    local hostname=$(hostname)
    local os_type=$(uname -s)
    local check_result="$1"

    # Create log directory if needed
    mkdir -p "$PROJECT_ROOT/cogspace"

    # Write comprehensive log
    {
        echo "======================================================================"
        echo "COGSPACE DIAGNOSTIC LOG"
        echo "======================================================================"
        echo ""
        echo "🕐 Timestamp:        $(date -Iseconds 2>/dev/null || date)"
        echo "📁 Project Root:     $PROJECT_ROOT"
        echo "📦 Project Name:     $PROJECT_NAME"
        echo "👤 Developer:        $DEV_NAME"
        echo "🔧 Current Version:  $current_version"
        echo "🎯 Expected Version: $dna_version"
        echo "📍 DNA Source:       $DNA_SOURCE"
        echo "💻 Hostname:         $hostname"
        echo "🖥️  OS:              $os_type"
        echo ""
        echo "======================================================================"
        echo "SYSTEM HEALTH CHECK"
        echo "======================================================================"
        echo ""

        if [[ "$check_result" == "PERFECT" ]]; then
            echo "✅ Status: PERFECT"
            echo "   All required files present"
            echo "   Version matches DNA source"
            echo "   No action required"
        else
            echo "⚠️  Status: NOT PERFECT"
            echo ""
            echo "Issues Detected:"
            while IFS= read -r line; do
                if [[ "$line" == ISSUE:* ]]; then
                    echo "   • ${line#ISSUE: }"
                fi
            done <<< "$check_result"
            echo ""
            echo "Action: Full re-injection from DNA source"
        fi

        echo ""
        echo "======================================================================"
        echo "FILE INVENTORY"
        echo "======================================================================"
        echo ""

        for file in "${REQUIRED_FILES[@]}"; do
            if [[ -f "$PROJECT_ROOT/$file" ]]; then
                echo "   ✅ $file"
            else
                echo "   ❌ $file (MISSING)"
            fi
        done

        echo ""
        echo "======================================================================"
        echo "END OF DIAGNOSTIC LOG"
        echo "======================================================================"
    } > "$log_file"

    echo "$log_file"
}

# Function: Perform full re-injection
perform_healing() {
    local dna_version=$(get_dna_version)

    # v39.0.0: Removed wasteful backup creation - DNA source IS the backup
    # All projects are in git, and cogspace/ can be re-synced from DNA anytime

    # CRITICAL FIX 2025-11-10: Remove Bob's broken Ollama context-synthesizer BEFORE rsync
    # This prevents rsync from being confused by the broken file
    if [[ -f "$PROJECT_ROOT/cogspace/skills/context-synthesizer.sh" ]]; then
        if grep -q "ollama run" "$PROJECT_ROOT/cogspace/skills/context-synthesizer.sh" 2>/dev/null; then
            mv "$PROJECT_ROOT/cogspace/skills/context-synthesizer.sh" \
               "$PROJECT_ROOT/cogspace/skills/context-synthesizer.sh.BROKEN-OLLAMA-BACKUP" 2>/dev/null || true
            echo "  ⚠️  Removed broken Ollama context-synthesizer before healing"
        fi
    fi

    # Full rsync from DNA source - preserves permissions, excludes backups
    mkdir -p "$PROJECT_ROOT/cogspace"
    rsync -av --quiet \
          --exclude="*.BROKEN-OLLAMA-BACKUP" \
          --exclude="cogspace-backup-*" \
          "$DNA_SOURCE/cogspace/" "$PROJECT_ROOT/cogspace/" 2>/dev/null || true

    echo "  ✅ Synced cogspace directory from DNA source"

    # Copy root-level scripts (wake.sh, sleep.sh, save.sh) - preserve symlinks
    for script in wake.sh sleep.sh save.sh hi bye save; do
        if [[ -L "$DNA_SOURCE/$script" ]]; then
            # Preserve symlink if source is a symlink
            cp -P "$DNA_SOURCE/$script" "$PROJECT_ROOT/$script"
            chmod +x "$PROJECT_ROOT/$script"
            echo "  ✅ Updated $script (symlink preserved)"
        elif [[ -f "$DNA_SOURCE/$script" ]]; then
            # Copy file if source is a file
            cp "$DNA_SOURCE/$script" "$PROJECT_ROOT/$script"
            chmod +x "$PROJECT_ROOT/$script"
            echo "  ✅ Updated $script"
        else
            # Create symlink if source doesn't exist (fallback)
            case "$script" in
                wake.sh|hi)
                    ln -sf "cogspace/core/session-wake.sh" "$PROJECT_ROOT/$script"
                    chmod +x "$PROJECT_ROOT/$script"
                    echo "  ✅ Created $script symlink"
                    ;;
                sleep.sh|bye)
                    ln -sf "cogspace/core/session-sleep.sh" "$PROJECT_ROOT/$script"
                    chmod +x "$PROJECT_ROOT/$script"
                    echo "  ✅ Created $script symlink"
                    ;;
                save.sh|save)
                    ln -sf "cogspace/core/session-save.sh" "$PROJECT_ROOT/$script"
                    chmod +x "$PROJECT_ROOT/$script"
                    echo "  ✅ Created $script symlink"
                    ;;
            esac
        fi
    done

    # Copy src-level scripts with diagnostics self-update
    # v40.2.1: Fixed path - was creating PROJECT_ROOT/src instead of cogspace/src
    mkdir -p "$PROJECT_ROOT/cogspace/src"
    for script in trouble-report cogspace-diagnostics.sh dna-version-upgrade-system.sh migrate-to-single-version.sh; do
        if [[ -f "$DNA_SOURCE/cogspace/src/$script" ]]; then
            cp "$DNA_SOURCE/cogspace/src/$script" "$PROJECT_ROOT/cogspace/src/$script"
            chmod +x "$PROJECT_ROOT/cogspace/src/$script"
        fi
    done
    echo "  ✅ Updated src scripts"

    # v40.0.0: Single version source - cogspace-version.json only
    # No more .version or cogspace/.cogspace-version files
    if [[ -f "$DNA_SOURCE/cogspace/cogspace-version.json" ]]; then
        cp "$DNA_SOURCE/cogspace/cogspace-version.json" "$PROJECT_ROOT/cogspace/cogspace-version.json"
        echo "  ✅ Updated cogspace-version.json to $dna_version"
    fi

    # v40.0.0: Remove legacy version files if they exist
    if [[ -f "$PROJECT_ROOT/.version" ]]; then
        rm -f "$PROJECT_ROOT/.version"
        echo "  🗑️  Removed deprecated .version file"
    fi
    if [[ -f "$PROJECT_ROOT/cogspace/.cogspace-version" ]]; then
        rm -f "$PROJECT_ROOT/cogspace/.cogspace-version"
        echo "  🗑️  Removed deprecated cogspace/.cogspace-version file"
    fi

    # Verify critical Node.js context files are present (rsync should have copied them)
    local verification_passed=true
    if [[ ! -f "$PROJECT_ROOT/cogspace/generate-complete-context.cjs" ]]; then
        echo "  ⚠️  Missing generate-complete-context.cjs after rsync"
        verification_passed=false
    fi
    if [[ ! -d "$PROJECT_ROOT/cogspace/analyzers" ]]; then
        echo "  ⚠️  Missing analyzers directory after rsync"
        verification_passed=false
    fi
    if [[ "$verification_passed" == "true" ]]; then
        echo "  ✅ Verified Node.js context generation system"
    fi

    # v33.0.0: Remove deprecated memories/ directory
    if [[ -d "$PROJECT_ROOT/memories" ]]; then
        echo "  🗑️  Removing deprecated memories/ directory..."
        rm -rf "$PROJECT_ROOT/memories"
        echo "  ✅ memories/ removed (deprecated in v33.0.0)"
    fi

    # v33.0.0: Remove deprecated .session-dna-version file
    if [[ -f "$PROJECT_ROOT/.session-dna-version" ]]; then
        echo "  🗑️  Removing deprecated .session-dna-version..."
        rm -f "$PROJECT_ROOT/.session-dna-version"
        echo "  ✅ .session-dna-version removed (v33.0.0 uses single .version)"
    fi

    # v33.0.0: Remove old root-level dashboard/ directory
    if [[ -d "$PROJECT_ROOT/dashboard" ]]; then
        echo "  🗑️  Removing old root-level dashboard/ directory..."
        rm -rf "$PROJECT_ROOT/dashboard"
        echo "  ✅ dashboard/ removed (v33.0.0 uses session-management/dashboard/)"
    fi

    # v33.0.0: Create required session-management directories
    mkdir -p "$PROJECT_ROOT/session-management/cognitive-context"
    mkdir -p "$PROJECT_ROOT/session-management/dashboard"
    mkdir -p "$PROJECT_ROOT/session-management/system-state"
    echo "  ✅ Created v33.0.0 directory structure"

    # v50.0.0: Install database components
    echo "  📦 Installing v50.0.0 database components..."
    mkdir -p "$PROJECT_ROOT/cogspace/db/migrations"
    mkdir -p "$PROJECT_ROOT/.cogspace"

    if [[ -d "$DNA_SOURCE/cogspace/db" ]]; then
        cp -r "$DNA_SOURCE/cogspace/db/"* "$PROJECT_ROOT/cogspace/db/" 2>/dev/null || true
        echo "  ✅ Installed cogspace/db/ module"
    fi

    if [[ -f "$DNA_SOURCE/cogspace/db-session-save.py" ]]; then
        cp "$DNA_SOURCE/cogspace/db-session-save.py" "$PROJECT_ROOT/cogspace/"
        chmod +x "$PROJECT_ROOT/cogspace/db-session-save.py"
        echo "  ✅ Installed db-session-save.py"
    fi

    if [[ -f "$DNA_SOURCE/cogspace/db-session-restore.py" ]]; then
        cp "$DNA_SOURCE/cogspace/db-session-restore.py" "$PROJECT_ROOT/cogspace/"
        chmod +x "$PROJECT_ROOT/cogspace/db-session-restore.py"
        echo "  ✅ Installed db-session-restore.py"
    fi

    # v50.0.0: Check Python3 availability
    if command -v python3 &> /dev/null; then
        echo "  ✅ Python3 available for database operations"
    else
        echo "  ⚠️  Python3 not found - database features will be limited"
        echo "  ⚠️  Install with: brew install python3"
    fi

    # v50.0.0: AGGRESSIVE CLEANUP - Remove all deprecated crap
    echo "  🧹 v50.0.0 aggressive cleanup..."

    # Remove cogspace-backup-* directories
    for backup_dir in "$PROJECT_ROOT"/cogspace-backup-*; do
        if [[ -d "$backup_dir" ]]; then
            rm -rf "$backup_dir"
            echo "  🗑️  Removed $(basename "$backup_dir")"
        fi
    done

    # Remove .diagnostics.*.log files
    find "$PROJECT_ROOT/cogspace" -name ".diagnostics.*.log" -type f -delete 2>/dev/null || true
    DIAG_COUNT=$(find "$PROJECT_ROOT/cogspace" -name ".diagnostics.*.log" -type f 2>/dev/null | wc -l | tr -d ' ')
    if [[ "$DIAG_COUNT" == "0" ]]; then
        echo "  ✅ Cleaned old diagnostic logs"
    fi

    # Remove .session-dna-updated
    if [[ -f "$PROJECT_ROOT/.session-dna-updated" ]]; then
        rm -f "$PROJECT_ROOT/.session-dna-updated"
        echo "  🗑️  Removed .session-dna-updated"
    fi

    # Remove empty src/ at root (if cogspace/src/ exists)
    if [[ -d "$PROJECT_ROOT/src" ]] && [[ -d "$PROJECT_ROOT/cogspace/src" ]]; then
        if [[ -z "$(ls -A "$PROJECT_ROOT/src" 2>/dev/null)" ]]; then
            rm -rf "$PROJECT_ROOT/src"
            echo "  🗑️  Removed empty src/ directory"
        fi
    fi

    echo "  ✅ v50.0.0 cleanup complete"

    # Clean old dashboard artifacts in new location (keep last 3)
    if [[ -d "$PROJECT_ROOT/session-management/dashboard" ]]; then
        DASHBOARD_COUNT=$(find "$PROJECT_ROOT/session-management/dashboard" -name "dashboard-*.html" -type f 2>/dev/null | wc -l | tr -d ' ')

        if [[ $DASHBOARD_COUNT -gt 3 ]]; then
            echo "  🧹 Cleaning old dashboards (keeping 3 most recent)..."

            # Keep 3 newest, delete the rest
            find "$PROJECT_ROOT/session-management/dashboard" -name "dashboard-*.html" -type f -print0 2>/dev/null | \
                xargs -0 ls -t | \
                tail -n +4 | \
                xargs rm -f 2>/dev/null || true

            echo "  ✅ Dashboard cleanup complete"
        fi
    fi

    # v50.0.0: Removed .session-dna-updated creation (deprecated)

    # v55.0.0: Complete infrastructure cleanup
    echo "  🧹 v55.0.0 complete infrastructure cleanup..."
    cleanup_deprecated_infrastructure

    # v55.0.0: Create command symlinks
    echo "  🔗 Creating command symlinks..."
    create_command_symlinks

    # v55.0.0: Validate and fix symlink targets
    echo "  🔍 Validating symlink targets..."
    validate_symlinks

    echo "  ✅ v55.0.0 healing complete"

    return 0
}

# Function: Get changelog entry for version
get_changelog_entry() {
    local version="$1"
    local changelog_file="$DNA_SOURCE/COGSPACE-DNA-CHANGELOG.json"

    if [[ ! -f "$changelog_file" ]]; then
        echo ""
        return 1
    fi

    # Extract changelog entry for this version
    jq -r --arg ver "$version" '.entries[] | select(.version == $ver)' "$changelog_file" 2>/dev/null || echo ""
}

# Function: Update README.md with new version (only on version change)
update_readme_version() {
    local old_version="$1"
    local new_version="$2"
    local readme="$PROJECT_ROOT/README.md"

    # Only update if version actually changed
    if [[ "$old_version" == "$new_version" ]]; then
        return 0
    fi

    # If no README, skip
    if [[ ! -f "$readme" ]]; then
        return 0
    fi

    # Get changelog entry
    local changelog_entry=$(get_changelog_entry "$new_version")
    if [[ -z "$changelog_entry" ]]; then
        # Fallback: just update version number
        sed -i.bak "s/\*\*COGSPACE Version:\*\* [0-9.]*/**COGSPACE Version:** $new_version/" "$readme" 2>/dev/null || true
        rm -f "$readme.bak" 2>/dev/null || true
        return 0
    fi

    # Extract changelog details
    local codename=$(echo "$changelog_entry" | jq -r '.codename // "Unknown"')
    local release_date=$(echo "$changelog_entry" | jq -r '.release_date // "Unknown"')
    local summary=$(echo "$changelog_entry" | jq -r '.summary // "Update"')
    local features=$(echo "$changelog_entry" | jq -r '.features[]' 2>/dev/null || echo "")

    # Check if README has COGSPACE DNA section
    if grep -q "## COGSPACE DNA" "$readme"; then
        # README already has DNA section, update it
        update_existing_dna_section "$readme" "$new_version" "$codename" "$release_date" "$summary" "$features"
    else
        # README doesn't have DNA section, add it
        add_dna_section_to_readme "$readme" "$new_version" "$codename" "$release_date" "$summary" "$features"
    fi

    # Update full history file
    update_cogspace_history "$old_version" "$new_version" "$changelog_entry"
}

# Function: Update existing DNA section in README
update_existing_dna_section() {
    local readme="$1"
    local version="$2"
    local codename="$3"
    local release_date="$4"
    local summary="$5"
    local features="$6"

    # Update current version line
    sed -i.bak "s/\*\*Current Version:\*\* v[0-9.]*.*/\*\*Current Version:\*\* v$version - $codename/" "$readme" 2>/dev/null || true
    sed -i.bak "s/\*\*Last Updated:\*\* .*/\*\*Last Updated:\*\* $(date -Iseconds 2>/dev/null || date)/" "$readme" 2>/dev/null || true

    # Add new entry to Recent Updates (keep last 5)
    # This is complex - we'll do a simpler approach: regenerate the section
    rm -f "$readme.bak" 2>/dev/null || true
}

# Function: Add DNA section to README (for projects that don't have it)
add_dna_section_to_readme() {
    local readme="$1"
    local version="$2"
    local codename="$3"
    local release_date="$4"
    local summary="$5"
    local features="$6"

    # Find insertion point (after project description, before "Features" or "Getting Started")
    local insert_line=$(grep -n "^## Features\|^## Getting Started" "$readme" | head -1 | cut -d: -f1)

    if [[ -z "$insert_line" ]]; then
        # No clear insertion point, append at end
        cat >> "$readme" << EOF

## COGSPACE DNA

**Current Version:** v$version - $codename
**Last Updated:** $(date -Iseconds 2>/dev/null || date)
**Auto-healing:** Enabled

### Recent Updates

#### v$version - $codename ($release_date)
$summary

EOF
        if [[ -n "$features" ]]; then
            echo "$features" | while IFS= read -r feature; do
                echo "- ✅ $feature" >> "$readme"
            done
        fi
        echo "" >> "$readme"
        echo "*[View complete changelog: .cogspace-history.md]*" >> "$readme"
        echo "" >> "$readme"
    else
        # Insert before Features/Getting Started section
        local temp_file=$(mktemp)
        head -n $((insert_line - 1)) "$readme" > "$temp_file"

        cat >> "$temp_file" << EOF

## COGSPACE DNA

**Current Version:** v$version - $codename
**Last Updated:** $(date -Iseconds 2>/dev/null || date)
**Auto-healing:** Enabled

### Recent Updates

#### v$version - $codename ($release_date)
$summary

EOF
        if [[ -n "$features" ]]; then
            echo "$features" | while IFS= read -r feature; do
                echo "- ✅ $feature" >> "$temp_file"
            done
        fi
        echo "" >> "$temp_file"
        echo "*[View complete changelog: .cogspace-history.md]*" >> "$temp_file"
        echo "" >> "$temp_file"

        tail -n +$insert_line "$readme" >> "$temp_file"
        mv "$temp_file" "$readme"
    fi
}

# Function: Update .cogspace-history.md with full changelog
update_cogspace_history() {
    local old_version="$1"
    local new_version="$2"
    local changelog_entry="$3"
    local history_file="$PROJECT_ROOT/.cogspace-history.md"

    # If history file doesn't exist, create it
    if [[ ! -f "$history_file" ]]; then
        cat > "$history_file" << 'EOF'
# COGSPACE DNA Update History

This file tracks all COGSPACE DNA updates applied to this project.

---

EOF
    fi

    # Extract details
    local codename=$(echo "$changelog_entry" | jq -r '.codename // "Unknown"')
    local release_date=$(echo "$changelog_entry" | jq -r '.release_date // "Unknown"')
    local summary=$(echo "$changelog_entry" | jq -r '.summary // "Update"')
    local features=$(echo "$changelog_entry" | jq -r '.features[]' 2>/dev/null || echo "")
    local breaking=$(echo "$changelog_entry" | jq -r '.breaking_changes[]' 2>/dev/null || echo "")
    local notes=$(echo "$changelog_entry" | jq -r '.upgrade_notes // ""')

    # Prepend new entry
    local temp_file=$(mktemp)
    cat > "$temp_file" << EOF
## v$new_version - $codename

**Release Date:** $release_date
**Applied:** $(date -Iseconds 2>/dev/null || date)
**Upgraded From:** v$old_version

### Summary
$summary

### Features Added
EOF

    if [[ -n "$features" ]]; then
        echo "$features" | while IFS= read -r feature; do
            echo "- ✅ $feature" >> "$temp_file"
        done
    fi

    if [[ -n "$breaking" ]]; then
        echo "" >> "$temp_file"
        echo "### Breaking Changes" >> "$temp_file"
        echo "$breaking" | while IFS= read -r change; do
            echo "- ⚠️ $change" >> "$temp_file"
        done
    fi

    if [[ -n "$notes" ]]; then
        echo "" >> "$temp_file"
        echo "### Upgrade Notes" >> "$temp_file"
        echo "$notes" >> "$temp_file"
    fi

    echo "" >> "$temp_file"
    echo "---" >> "$temp_file"
    echo "" >> "$temp_file"

    # Append existing history
    if [[ -f "$history_file" ]]; then
        tail -n +4 "$history_file" >> "$temp_file"  # Skip header
    fi

    mv "$temp_file" "$history_file"
}

# Main execution
main() {
    local check_result=$(check_system_health)
    local status=$(echo "$check_result" | head -1)

    case "$MODE" in
        --silent-fix)
            # Zero-touch auto-healing
            if [[ "$status" == "NOT_PERFECT" ]]; then
                echo "🔄 COGSPACE: Auto-healing required, in progress..." >&2

                local old_version=$(get_current_version)
                perform_healing
                local dna_version=$(get_dna_version)

                # Update README if version changed
                update_readme_version "$old_version" "$dna_version"

                echo "✅ COGSPACE: System restored to COGSPACE v$dna_version" >&2

                # Create log
                local log_file=$(create_log "$check_result")

                exit 0
            else
                # Silent success - no output
                create_log "$check_result" > /dev/null
                exit 0
            fi
            ;;

        --silent-verify)
            # Quick health check - no output, just exit code
            create_log "$check_result" > /dev/null
            if [[ "$status" == "PERFECT" ]]; then
                exit 0
            else
                exit 1
            fi
            ;;

        --interactive|*)
            # Interactive mode with full output
            # v55.0.0: Dynamic version from cogspace-version.json (never hardcode!)
            local diag_version=$(get_current_version)
            echo -e "${CYAN}🔍 COGSPACE DIAGNOSTICS v${diag_version}${NC}"
            echo -e "${BLUE}Project: $PROJECT_NAME${NC}"
            echo -e "${BLUE}Developer: $DEV_NAME${NC}"
            echo ""

            if [[ "$status" == "PERFECT" ]]; then
                echo -e "${GREEN}✅ System Status: PERFECT${NC}"
                echo "   All required files present"
                echo "   Version matches DNA source"
                echo ""
            else
                echo -e "${YELLOW}⚠️  System Status: NOT PERFECT${NC}"
                echo ""
                echo "Issues Detected:"
                while IFS= read -r line; do
                    if [[ "$line" == ISSUE:* ]]; then
                        echo -e "   ${RED}•${NC} ${line#ISSUE: }"
                    fi
                done <<< "$check_result"
                echo ""

                echo -e "${YELLOW}🔄 Performing full re-injection...${NC}"
                local old_version=$(get_current_version)
                perform_healing

                local dna_version=$(get_dna_version)

                # Update README if version changed
                update_readme_version "$old_version" "$dna_version"

                echo -e "${GREEN}✅ System restored to COGSPACE v$dna_version${NC}"
                echo ""
            fi

            # Create and show log location
            local log_file=$(create_log "$check_result")
            echo -e "${BLUE}📋 Diagnostic log: ${log_file#$PROJECT_ROOT/}${NC}"
            echo ""

            exit 0
            ;;
    esac
}

# Run main
main


