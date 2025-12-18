#!/bin/bash
# COGSPACE v40.2.1
# COGSPACE GitHub Sync Setup Wizard

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║${NC}  ${BLUE}🔧 COGSPACE GitHub Integration Setup${NC}                  ${CYAN}║${NC}"
echo -e "${CYAN}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if git repo exists
if [[ ! -d ".git" ]]; then
  echo -e "${RED}❌ Not a git repository${NC}"
  echo ""
  echo -e "${YELLOW}Initialize git first:${NC}"
  echo "   git init"
  echo "   git remote add origin <your-github-url>"
  echo ""
  exit 1
fi

# Check if remote exists
if ! git remote get-url origin >/dev/null 2>&1; then
  echo -e "${RED}❌ No GitHub remote configured${NC}"
  echo ""
  echo -e "${YELLOW}Add a GitHub remote first:${NC}"
  echo "   git remote add origin <your-github-url>"
  echo ""
  exit 1
fi

REMOTE_URL=$(git remote get-url origin)
echo -e "${GREEN}✅ GitHub remote: ${BLUE}$REMOTE_URL${NC}"
echo ""

# Check if jq is available
if ! command -v jq &> /dev/null; then
  echo -e "${YELLOW}⚠️  jq is not installed (recommended for config management)${NC}"
  echo "   Install with: brew install jq"
  echo ""
  read -p "Continue anyway? [y/N]: " CONTINUE
  if [[ "$CONTINUE" != "y" ]]; then
    exit 1
  fi
fi

# Interactive configuration
echo -e "${CYAN}Configure GitHub sync behavior:${NC}"
echo ""

read -p "Enable GitHub sync? [y/N]: " ENABLE_SYNC
if [[ "$ENABLE_SYNC" != "y" ]]; then
  echo ""
  echo -e "${YELLOW}GitHub sync disabled${NC}"
  exit 0
fi

echo ""
echo -e "${CYAN}Auto-sync options:${NC}"
echo ""

read -p "Pull on wake? (recommended: y) [y/N]: " WAKE_SYNC
read -p "Commit on save? (recommended: n) [y/N]: " SAVE_SYNC
read -p "Push on sleep? (recommended: y) [y/N]: " SLEEP_SYNC

WAKE_BOOL="false"; [[ "$WAKE_SYNC" == "y" ]] && WAKE_BOOL="true"
SAVE_BOOL="false"; [[ "$SAVE_SYNC" == "y" ]] && SAVE_BOOL="true"
SLEEP_BOOL="false"; [[ "$SLEEP_SYNC" == "y" ]] && SLEEP_BOOL="true"

echo ""
echo -e "${CYAN}README enhancement:${NC}"
echo ""

read -p "Enable automatic README updates? [y/N]: " README_ENABLE
read -p "Interactive mode (show diffs)? [y/N]: " README_INTERACTIVE

README_ENABLED_BOOL="false"; [[ "$README_ENABLE" == "y" ]] && README_ENABLED_BOOL="true"
README_INTERACTIVE_BOOL="false"; [[ "$README_INTERACTIVE" == "y" ]] && README_INTERACTIVE_BOOL="true"

# Create configuration file
echo ""
echo -e "${CYAN}📝 Creating configuration file...${NC}"

cat > .cogspace-git-config.json <<EOF
{
  "enabled": true,
  "autoSync": {
    "wake": $WAKE_BOOL,
    "save": $SAVE_BOOL,
    "sleep": $SLEEP_BOOL
  },
  "commitPrefix": "🧠 COGSPACE:",
  "branchStrategy": "main",
  "conflictResolution": "stash-pull-pop",
  "readmeEnhancement": {
    "enabled": $README_ENABLED_BOOL,
    "interactive": $README_INTERACTIVE_BOOL,
    "autoUpdateSections": [
      "Last Updated",
      "Recent Changes",
      "Technologies"
    ],
    "preserveSections": [
      "License",
      "Credits",
      "Contributors"
    ]
  },
  "excludeFromCommit": [
    "session-management/cognitive-context/backups/",
    "quick-restore-*.sh",
    ".cogspace/temp/",
    "node_modules/",
    ".DS_Store",
    "*.log"
  ]
}
EOF

echo ""
echo -e "${GREEN}✅ Configuration saved to .cogspace-git-config.json${NC}"
echo ""

# Display summary
echo -e "${CYAN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║${NC}  ${WHITE}GitHub Sync Configuration Summary${NC}                     ${CYAN}║${NC}"
echo -e "${CYAN}╠═══════════════════════════════════════════════════════════╣${NC}"

if [[ "$WAKE_BOOL" == "true" ]]; then
  echo -e "${CYAN}║${NC}  ${GREEN}✓${NC} Pull on wake                                           ${CYAN}║${NC}"
else
  echo -e "${CYAN}║${NC}  ${RED}✗${NC} Pull on wake                                           ${CYAN}║${NC}"
fi

if [[ "$SAVE_BOOL" == "true" ]]; then
  echo -e "${CYAN}║${NC}  ${GREEN}✓${NC} Commit on save                                         ${CYAN}║${NC}"
else
  echo -e "${CYAN}║${NC}  ${RED}✗${NC} Commit on save                                         ${CYAN}║${NC}"
fi

if [[ "$SLEEP_BOOL" == "true" ]]; then
  echo -e "${CYAN}║${NC}  ${GREEN}✓${NC} Push on sleep                                          ${CYAN}║${NC}"
else
  echo -e "${CYAN}║${NC}  ${RED}✗${NC} Push on sleep                                          ${CYAN}║${NC}"
fi

if [[ "$README_ENABLED_BOOL" == "true" ]]; then
  echo -e "${CYAN}║${NC}  ${GREEN}✓${NC} README enhancement                                     ${CYAN}║${NC}"
  if [[ "$README_INTERACTIVE_BOOL" == "true" ]]; then
    echo -e "${CYAN}║${NC}    ${BLUE}→${NC} Interactive mode (shows diffs)                       ${CYAN}║${NC}"
  else
    echo -e "${CYAN}║${NC}    ${BLUE}→${NC} Auto-apply mode                                      ${CYAN}║${NC}"
  fi
else
  echo -e "${CYAN}║${NC}  ${RED}✗${NC} README enhancement                                     ${CYAN}║${NC}"
fi

echo -e "${CYAN}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""

# Test the setup
echo -e "${CYAN}🧪 Testing GitHub connection...${NC}"

if git fetch origin --dry-run 2>&1 | grep -q "fatal"; then
  echo -e "${RED}❌ GitHub connection failed${NC}"
  echo ""
  echo -e "${YELLOW}Check your authentication:${NC}"
  echo "   • GitHub Personal Access Token (PAT)"
  echo "   • SSH key setup"
  echo "   • Network connectivity"
  echo ""
  exit 1
else
  echo -e "${GREEN}✅ GitHub connection successful${NC}"
fi

echo ""
echo -e "${CYAN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║${NC}  ${GREEN}✅ Setup Complete!${NC}                                      ${CYAN}║${NC}"
echo -e "${CYAN}╠═══════════════════════════════════════════════════════════╣${NC}"
echo -e "${CYAN}║${NC}  ${WHITE}Try it:${NC}                                                  ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}                                                           ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}  ${BLUE}./wake.sh${NC}                                               ${CYAN}║${NC}"

if [[ "$WAKE_BOOL" == "true" ]]; then
  echo -e "${CYAN}║${NC}    → Will pull from GitHub                               ${CYAN}║${NC}"
fi

echo -e "${CYAN}║${NC}                                                           ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}  ${BLUE}./save.sh \"Progress checkpoint\"${NC}                       ${CYAN}║${NC}"

if [[ "$SAVE_BOOL" == "true" ]]; then
  echo -e "${CYAN}║${NC}    → Will create local commit                            ${CYAN}║${NC}"
fi

echo -e "${CYAN}║${NC}                                                           ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}  ${BLUE}./sleep.sh \"Session complete\"${NC}                         ${CYAN}║${NC}"

if [[ "$SLEEP_BOOL" == "true" ]]; then
  echo -e "${CYAN}║${NC}    → Will commit and push to GitHub                      ${CYAN}║${NC}"
fi

if [[ "$README_ENABLED_BOOL" == "true" ]]; then
  echo -e "${CYAN}║${NC}    → Will update README.md with session work             ${CYAN}║${NC}"
fi

echo -e "${CYAN}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""

# Optionally add config to .gitignore
if [[ ! -f ".gitignore" ]] || ! grep -q ".cogspace-git-config.json" .gitignore; then
  read -p "Add .cogspace-git-config.json to .gitignore? [y/N]: " GITIGNORE
  if [[ "$GITIGNORE" == "y" ]]; then
    echo ".cogspace-git-config.json" >> .gitignore
    echo -e "${GREEN}✅ Added to .gitignore${NC}"
  fi
fi

echo ""
echo -e "${BLUE}💡 To modify settings later:${NC}"
echo "   Edit .cogspace-git-config.json"
echo "   Or run: ./cogspace/setup-github-sync.sh"
echo ""


