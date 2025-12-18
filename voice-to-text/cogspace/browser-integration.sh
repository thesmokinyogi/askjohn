#!/bin/bash
# ============================================================================
# COGSPACE Browser Integration v51.0.0
# ============================================================================
# Smart browser automation for dashboard display with same-tab reuse.
# Supports Safari and Chrome with auto-detection of default browser.
#
# Usage:
#   ./browser-integration.sh <dashboard_path> [--browser=auto|safari|chrome]
#
# Features:
#   - Auto-detects default browser
#   - Reuses existing COGSPACE dashboard tab if found
#   - Falls back to new tab if no existing tab
#   - Configurable via session_config table
#
# Part of: COGSPACE v51.0.0
# ============================================================================

set -e

# Colors
CYAN='\033[96m'
GREEN='\033[92m'
YELLOW='\033[93m'
RED='\033[91m'
NC='\033[0m'

DASHBOARD_PATH="${1:-}"
BROWSER_PREF="${2:-auto}"

# Parse --browser=X argument
for arg in "$@"; do
    case "$arg" in
        --browser=*)
            BROWSER_PREF="${arg#*=}"
            ;;
    esac
done

# ============================================================================
# Helper Functions
# ============================================================================

log_info() {
    echo -e "${CYAN}[BROWSER]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[BROWSER]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[BROWSER]${NC} $1"
}

log_error() {
    echo -e "${RED}[BROWSER]${NC} $1"
}

# ============================================================================
# Browser Detection
# ============================================================================

detect_default_browser() {
    # Get default browser from macOS
    local default_browser
    default_browser=$(defaults read com.apple.LaunchServices/com.apple.launchservices.secure LSHandlers 2>/dev/null | \
        grep -B1 'LSHandlerURLScheme = https' | \
        grep 'LSHandlerRoleAll' | \
        head -1 | \
        sed 's/.*= "\(.*\)";/\1/' || echo "")

    case "$default_browser" in
        *safari*)
            echo "safari"
            ;;
        *chrome*)
            echo "chrome"
            ;;
        *firefox*)
            echo "firefox"
            ;;
        *)
            # Fallback: check what's running
            if pgrep -x "Safari" > /dev/null 2>&1; then
                echo "safari"
            elif pgrep -x "Google Chrome" > /dev/null 2>&1; then
                echo "chrome"
            else
                # Default to Safari on macOS
                echo "safari"
            fi
            ;;
    esac
}

# ============================================================================
# Safari Functions
# ============================================================================

open_safari_same_tab() {
    local dashboard_url="$1"

    osascript <<EOF
    tell application "Safari"
        activate

        -- Look for existing COGSPACE dashboard tab
        set dashboardTabFound to false
        set dashboardWindow to missing value
        set dashboardTabIndex to 0

        repeat with w in windows
            set tabIndex to 1
            repeat with t in tabs of w
                set tabURL to URL of t
                if tabURL contains "dashboard-" and tabURL contains ".html" then
                    set dashboardTabFound to true
                    set dashboardWindow to w
                    set dashboardTabIndex to tabIndex
                    exit repeat
                end if
                set tabIndex to tabIndex + 1
            end repeat
            if dashboardTabFound then exit repeat
        end repeat

        if dashboardTabFound then
            -- Reuse existing tab
            set current tab of dashboardWindow to tab dashboardTabIndex of dashboardWindow
            set URL of current tab of dashboardWindow to "$dashboard_url"
            set index of dashboardWindow to 1
            return "reused"
        else
            -- Check if there's an empty/new tab page to use
            if (count of windows) > 0 then
                set frontWindow to front window
                if (count of tabs of frontWindow) > 0 then
                    set currentURL to URL of current tab of frontWindow
                    if currentURL is "" or currentURL is "favorites://" or currentURL contains "topsites" then
                        -- Use the empty tab
                        set URL of current tab of frontWindow to "$dashboard_url"
                        return "used_empty"
                    end if
                end if
                -- Create new tab
                make new tab at end of tabs of frontWindow with properties {URL:"$dashboard_url"}
                return "new_tab"
            else
                -- No windows, create new one
                make new document with properties {URL:"$dashboard_url"}
                return "new_window"
            end if
        end if
    end tell
EOF
}

# ============================================================================
# Chrome Functions
# ============================================================================

open_chrome_same_tab() {
    local dashboard_url="$1"

    osascript <<EOF
    tell application "Google Chrome"
        activate

        -- Look for existing COGSPACE dashboard tab
        set dashboardTabFound to false
        set dashboardWindow to missing value
        set dashboardTabIndex to 0

        repeat with w in windows
            set tabIndex to 1
            repeat with t in tabs of w
                set tabURL to URL of t
                if tabURL contains "dashboard-" and tabURL contains ".html" then
                    set dashboardTabFound to true
                    set dashboardWindow to w
                    set dashboardTabIndex to tabIndex
                    exit repeat
                end if
                set tabIndex to tabIndex + 1
            end repeat
            if dashboardTabFound then exit repeat
        end repeat

        if dashboardTabFound then
            -- Reuse existing tab
            set active tab index of dashboardWindow to dashboardTabIndex
            set URL of active tab of dashboardWindow to "$dashboard_url"
            set index of dashboardWindow to 1
            return "reused"
        else
            -- Check if there's a new tab page to use
            if (count of windows) > 0 then
                set frontWindow to front window
                if (count of tabs of frontWindow) > 0 then
                    set currentURL to URL of active tab of frontWindow
                    if currentURL is "chrome://newtab/" or currentURL is "" then
                        -- Use the new tab page
                        set URL of active tab of frontWindow to "$dashboard_url"
                        return "used_empty"
                    end if
                end if
                -- Create new tab
                make new tab at end of tabs of frontWindow with properties {URL:"$dashboard_url"}
                return "new_tab"
            else
                -- No windows, create new one
                make new window
                set URL of active tab of front window to "$dashboard_url"
                return "new_window"
            end if
        end if
    end tell
EOF
}

# ============================================================================
# Firefox Functions (basic support)
# ============================================================================

open_firefox() {
    local dashboard_url="$1"

    # Firefox doesn't support same-tab targeting as easily
    # Fall back to simple open
    open -a "Firefox" "$dashboard_url"
    echo "new_tab"
}

# ============================================================================
# Fallback: Simple Open
# ============================================================================

open_simple() {
    local dashboard_path="$1"
    open "$dashboard_path"
    echo "simple_open"
}

# ============================================================================
# Main Logic
# ============================================================================

main() {
    if [[ -z "$DASHBOARD_PATH" ]]; then
        log_error "Usage: browser-integration.sh <dashboard_path> [--browser=auto|safari|chrome]"
        exit 1
    fi

    # Convert to absolute path if relative
    if [[ ! "$DASHBOARD_PATH" = /* ]]; then
        DASHBOARD_PATH="$(pwd)/$DASHBOARD_PATH"
    fi

    # Convert to file:// URL
    local dashboard_url="file://$DASHBOARD_PATH"

    # Verify file exists
    if [[ ! -f "$DASHBOARD_PATH" ]]; then
        log_error "Dashboard file not found: $DASHBOARD_PATH"
        exit 1
    fi

    # Determine browser
    local browser
    if [[ "$BROWSER_PREF" == "auto" ]]; then
        browser=$(detect_default_browser)
        log_info "Auto-detected browser: $browser"
    else
        browser="$BROWSER_PREF"
    fi

    # Open in appropriate browser
    local result
    case "$browser" in
        safari)
            log_info "Opening in Safari (same-tab mode)..."
            result=$(open_safari_same_tab "$dashboard_url" 2>/dev/null || echo "error")
            ;;
        chrome)
            log_info "Opening in Chrome (same-tab mode)..."
            result=$(open_chrome_same_tab "$dashboard_url" 2>/dev/null || echo "error")
            ;;
        firefox)
            log_info "Opening in Firefox..."
            result=$(open_firefox "$dashboard_url" 2>/dev/null || echo "error")
            ;;
        *)
            log_warn "Unknown browser '$browser', using simple open"
            result=$(open_simple "$DASHBOARD_PATH" 2>/dev/null || echo "error")
            ;;
    esac

    # Report result
    case "$result" in
        reused)
            log_success "Dashboard refreshed in existing tab"
            ;;
        used_empty)
            log_success "Dashboard opened in empty tab"
            ;;
        new_tab)
            log_success "Dashboard opened in new tab"
            ;;
        new_window)
            log_success "Dashboard opened in new window"
            ;;
        simple_open)
            log_success "Dashboard opened"
            ;;
        error)
            log_warn "AppleScript failed, falling back to simple open"
            open_simple "$DASHBOARD_PATH"
            ;;
        *)
            log_success "Dashboard opened"
            ;;
    esac

    # Return the result for caller
    echo "$result"
}

# Run if executed directly (not sourced)
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
