#!/bin/bash
# COGSPACE v40.0.0
# COGSPACE v23.1.0 - GitHub Repository Setup Assistant
# Creates new GitHub repository using GitHub CLI with OAuth authentication

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
BOLD='\033[1m'
NC='\033[0m'

PROJECT_NAME=$(basename "$PWD")

echo -e "${CYAN}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║${NC}  ${BOLD}GitHub Repository Setup Assistant${NC}                         ${CYAN}║${NC}"
echo -e "${CYAN}╠═══════════════════════════════════════════════════════════════╣${NC}"
echo -e "${CYAN}║${NC}  Project: ${BOLD}${PROJECT_NAME}${NC}"
echo -e "${CYAN}╚═══════════════════════════════════════════════════════════════╝${NC}"
echo ""

#═══════════════════════════════════════════════════════════════════════════════
# Step 1: Check if already a git repository
#═══════════════════════════════════════════════════════════════════════════════

if [[ -d ".git" ]]; then
  echo -e "${YELLOW}⚠️  This project is already a git repository${NC}"
  echo ""

  # Check if has remote
  REMOTE=$(git remote get-url origin 2>/dev/null)
  if [[ -n "$REMOTE" ]]; then
    echo -e "${GREEN}✅ Remote already configured:${NC}"
    echo -e "   ${REMOTE}"
    echo ""
    echo -e "${BLUE}Current branch:${NC} $(git branch --show-current)"
    echo -e "${BLUE}Last commit:${NC} $(git log -1 --pretty="%h - %s" 2>/dev/null || echo "No commits")"
    echo ""
    echo -e "${CYAN}Your repository is already set up! No action needed.${NC}"
    exit 0
  else
    echo -e "${YELLOW}Repository exists locally but has no remote backup.${NC}"
    echo -e "${CYAN}I'll help you add a GitHub remote...${NC}"
    echo ""
  fi
else
  echo -e "${BLUE}Initializing git repository...${NC}"
  git init
  echo -e "${GREEN}✅ Git repository initialized${NC}"
  echo ""
fi

#═══════════════════════════════════════════════════════════════════════════════
# Step 2: Check for GitHub CLI
#═══════════════════════════════════════════════════════════════════════════════

if ! command -v gh &> /dev/null; then
  echo -e "${RED}❌ GitHub CLI (gh) is not installed${NC}"
  echo ""
  echo -e "${CYAN}GitHub CLI is needed to create repositories easily.${NC}"
  echo ""
  echo -e "${BOLD}Installation Options:${NC}"
  echo ""

  # Detect OS and provide appropriate installation instructions
  if [[ "$OSTYPE" == "darwin"* ]]; then
    echo -e "${YELLOW}macOS:${NC}"
    echo -e "  ${GREEN}brew install gh${NC}"
    echo ""

    # Check if Homebrew is installed
    if command -v brew &> /dev/null; then
      read -p "Would you like me to install it now using Homebrew? (y/n) " -n 1 -r
      echo ""
      if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${CYAN}Installing GitHub CLI...${NC}"
        brew install gh
        echo -e "${GREEN}✅ GitHub CLI installed${NC}"
        echo ""
      else
        echo -e "${YELLOW}Please install GitHub CLI manually and run this command again.${NC}"
        exit 1
      fi
    else
      echo -e "${YELLOW}Homebrew not found. Please install from: https://brew.sh${NC}"
      exit 1
    fi
  elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo -e "${YELLOW}Linux:${NC}"
    echo -e "  ${GREEN}sudo apt install gh${NC}     # Debian/Ubuntu"
    echo -e "  ${GREEN}sudo dnf install gh${NC}     # Fedora/RHEL"
    echo ""
    echo -e "${YELLOW}Please install and run this command again.${NC}"
    exit 1
  else
    echo -e "${YELLOW}Visit: ${BLUE}https://cli.github.com/${NC}"
    echo ""
    echo -e "${YELLOW}Please install and run this command again.${NC}"
    exit 1
  fi
fi

echo -e "${GREEN}✅ GitHub CLI (gh) is installed${NC}"
echo ""

#═══════════════════════════════════════════════════════════════════════════════
# Step 3: Check GitHub authentication
#═══════════════════════════════════════════════════════════════════════════════

echo -e "${BLUE}Checking GitHub authentication...${NC}"

if ! gh auth status &> /dev/null; then
  echo -e "${YELLOW}⚠️  Not authenticated with GitHub${NC}"
  echo ""
  echo -e "${CYAN}I'll open your browser to authenticate with GitHub...${NC}"
  echo -e "${CYAN}This uses OAuth for secure authentication.${NC}"
  echo ""

  # Authenticate with GitHub
  gh auth login

  # Check if authentication was successful
  if ! gh auth status &> /dev/null; then
    echo ""
    echo -e "${RED}❌ Authentication failed${NC}"
    echo -e "${YELLOW}Please try again or check your internet connection.${NC}"
    exit 1
  fi
fi

echo -e "${GREEN}✅ Authenticated with GitHub${NC}"
GH_USER=$(gh api user -q .login)
echo -e "${CYAN}   Logged in as: ${BOLD}${GH_USER}${NC}"
echo ""

#═══════════════════════════════════════════════════════════════════════════════
# Step 4: Confirm repository details
#═══════════════════════════════════════════════════════════════════════════════

echo -e "${BOLD}Repository Configuration:${NC}"
echo -e "  ${BLUE}Name:${NC} ${PROJECT_NAME}"
echo -e "  ${BLUE}Owner:${NC} ${GH_USER}"
echo -e "  ${BLUE}Visibility:${NC} Private (recommended)"
echo -e "  ${BLUE}URL:${NC} https://github.com/${GH_USER}/${PROJECT_NAME}"
echo ""

read -p "Create this repository? (y/n) " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
  echo -e "${YELLOW}Repository creation cancelled.${NC}"
  exit 0
fi

#═══════════════════════════════════════════════════════════════════════════════
# Step 5: Create GitHub repository
#═══════════════════════════════════════════════════════════════════════════════

echo ""
echo -e "${CYAN}Creating GitHub repository...${NC}"

# Create repository (private by default)
if gh repo create "$PROJECT_NAME" --private --source=. --remote=origin; then
  echo -e "${GREEN}✅ Repository created successfully!${NC}"
  echo ""

  # Get repository URL
  REPO_URL=$(gh repo view --json url -q .url)

  echo -e "${BOLD}Repository Details:${NC}"
  echo -e "  ${BLUE}URL:${NC} ${REPO_URL}"
  echo -e "  ${BLUE}Remote:${NC} origin"
  echo ""

  # Check if there are files to commit
  if [[ -n "$(ls -A)" ]]; then
    echo -e "${CYAN}Setting up initial commit...${NC}"
    echo ""

    # Create .gitignore if it doesn't exist
    if [[ ! -f ".gitignore" ]]; then
      cat > .gitignore << 'GITIGNORE_EOF'
# COGSPACE
.DS_Store
node_modules/
*.log
.env
.env.local

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
Thumbs.db
GITIGNORE_EOF
      echo -e "${GREEN}✅ Created .gitignore${NC}"
    fi

    # Stage all files
    git add .

    # Show what will be committed
    FILE_COUNT=$(git diff --cached --name-only | wc -l | tr -d ' ')
    echo -e "${BLUE}Files to commit: ${FILE_COUNT}${NC}"
    echo ""

    # Create initial commit
    git commit -m "Initial commit: ${PROJECT_NAME}

🤖 Generated with COGSPACE v22.1.2
Repository created via add-new-repo command

Co-Authored-By: Claude <noreply@anthropic.com>"

    echo -e "${GREEN}✅ Initial commit created${NC}"
    echo ""

    # Push to GitHub
    echo -e "${CYAN}Pushing to GitHub...${NC}"
    if git push -u origin main 2>/dev/null || git push -u origin master 2>/dev/null; then
      echo -e "${GREEN}✅ Code pushed to GitHub successfully!${NC}"
      echo ""
      echo -e "${CYAN}╔═══════════════════════════════════════════════════════════════╗${NC}"
      echo -e "${CYAN}║${NC}  ${BOLD}${GREEN}✅ Repository Setup Complete!${NC}                             ${CYAN}║${NC}"
      echo -e "${CYAN}╠═══════════════════════════════════════════════════════════════╣${NC}"
      echo -e "${CYAN}║${NC}                                                               ${CYAN}║${NC}"
      echo -e "${CYAN}║${NC}  ${BLUE}View your repository:${NC}                                      ${CYAN}║${NC}"
      echo -e "${CYAN}║${NC}  ${REPO_URL}                                                    "
      echo -e "${CYAN}║${NC}                                                               ${CYAN}║${NC}"
      echo -e "${CYAN}║${NC}  ${BOLD}Next Steps:${NC}                                                ${CYAN}║${NC}"
      echo -e "${CYAN}║${NC}  ${GREEN}•${NC} Your work is now backed up to GitHub                    ${CYAN}║${NC}"
      echo -e "${CYAN}║${NC}  ${GREEN}•${NC} COGSPACE will automatically sync on sleep              ${CYAN}║${NC}"
      echo -e "${CYAN}║${NC}  ${GREEN}•${NC} Share the URL with your team for collaboration        ${CYAN}║${NC}"
      echo -e "${CYAN}║${NC}                                                               ${CYAN}║${NC}"
      echo -e "${CYAN}╚═══════════════════════════════════════════════════════════════╝${NC}"
    else
      echo -e "${YELLOW}⚠️  Push failed - but repository was created${NC}"
      echo -e "${CYAN}You can push manually later with: ${BOLD}git push -u origin main${NC}"
    fi
  else
    echo -e "${YELLOW}⚠️  No files to commit yet${NC}"
    echo -e "${CYAN}Repository created and connected.${NC}"
    echo -e "${CYAN}Add files and commit when ready.${NC}"
  fi
else
  echo ""
  echo -e "${RED}❌ Failed to create repository${NC}"
  echo ""
  echo -e "${YELLOW}Possible reasons:${NC}"
  echo -e "  • Repository name already exists"
  echo -e "  • Network connection issues"
  echo -e "  • Insufficient permissions"
  echo ""
  echo -e "${CYAN}Try a different repository name or check GitHub:${NC}"
  echo -e "  ${BLUE}https://github.com/${GH_USER}${NC}"
  exit 1
fi


