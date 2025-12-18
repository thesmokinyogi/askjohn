# Injection Protocol - 🏗️ COGSPACE v40.0.0 "Unified Version"

## Overview
This document outlines the proper protocol for injecting COGSPACE into new projects, based on lessons learned from the benefits-bridge deployment and subsequent path adjustments.

## Critical Path Adjustments Required

### 1. Project Root Scripts (save.sh, sleep.sh, wake.sh)
**Issue**: Scripts expect a `current` subdirectory that doesn't exist  
**Solution**: Remove the `/current` path reference

**Required Changes**:
```bash
# OLD (incorrect)
cd "${SCRIPT_DIR}/current"

# NEW (correct)
cd "${SCRIPT_DIR}"
```

### 2. Cognitive Serializer Paths
**Issue**: Scripts expect cognitive-serializer.cjs in nested cogspace folder  
**Solution**: Update all paths to use direct reference when in cogspace folder

**Required Changes**:
```bash
# OLD (incorrect for cogspace folder deployment)
./cogspace/cognitive-serializer.cjs
${PROJECT_ROOT}/cogspace/cognitive-serializer.cjs

# NEW (correct for cogspace folder deployment)
./cognitive-serializer.cjs
${PROJECT_ROOT}/cognitive-serializer.cjs
```

### 3. Dynamic Context Analyzer Paths
**Issue**: Scripts expect dynamic-context-analyzer.sh in root cogspace folder  
**Solution**: Update paths to reflect actual location in docs/ subfolder

**Required Changes**:
```bash
# OLD (incorrect)
${PROJECT_ROOT}/dynamic-context-analyzer.sh

# NEW (correct)
${PROJECT_ROOT}/docs/dynamic-context-analyzer.sh
```

### 4. JavaScript Template Quoting
**Issue**: Shell variables in JSON templates cause syntax errors  
**Solution**: Properly quote shell variables in JSON context

**Required Changes**:
```bash
# OLD (causes syntax error)
"immediateActions": ${IMMEDIATE_ACTIONS_JSON},

# NEW (correct)
"immediateActions": '${IMMEDIATE_ACTIONS_JSON}',
```

### 5. AI Semantic File Organization Protection
**Issue**: AI semantic organization moves project root scripts to src/ directory  
**Solution**: Add project root scripts to ESSENTIAL_FILES array

**Required Changes**:
```bash
# OLD (scripts get moved)
ESSENTIAL_FILES=(
  "cognitive-serializer.cjs"
  "session-save-enhanced.sh"
  "session-wake-enhanced.sh"
  "session-sleep-enhanced.sh"
  "deploy-cogspace.sh"
  "normalize-permissions.sh"
)

# NEW (scripts protected)
ESSENTIAL_FILES=(
  "cognitive-serializer.cjs"
  "session-save-enhanced.sh"
  "session-wake-enhanced.sh"
  "session-sleep-enhanced.sh"
  "deploy-cogspace.sh"
  "normalize-permissions.sh"
  "save.sh"
  "wake.sh"
  "sleep.sh"
)
```

### 6. Sleep Script AI Semantic Organization Enhancement
**Issue**: Sleep script lacks AI semantic file organization functionality  
**Solution**: Add complete AI semantic organization to sleep script

**Required Changes**:
```bash
# Add to sleep script:
- FILE_ORGANIZATION_RULES array
- ai_semantic_analyze() function
- ai_organize_file() function
- ai_enhanced_session_organization() function
- Call ai_enhanced_session_organization() before final serialization
- Essential files protection including project root scripts
```

### 7. Dynamic Dashboard Template Generation
**Issue**: No automatic dashboard generation for developers  
**Solution**: Add dashboard template and generator to wake script

**Required Files**:
```bash
# New files to include:
- dashboard-template.html          # Template with ${PROJECT_NAME}, ${SESSION_ID}, ${TIMESTAMP} variables
- generate-dashboard.sh           # Template processing script
```

**Required Changes to Wake Script**:
```bash
# Add after session restoration in wake script:
echo -e "${CYAN}🎛️ GENERATING DEV COCKPIT DASHBOARD${NC}"

if [[ -f "${SCRIPT_DIR}/generate-dashboard.sh" ]]; then
    "${SCRIPT_DIR}/generate-dashboard.sh" \
        "$PROJECT_NAME" \
        "$WAKE_SESSION_ID" \
        "$TIMESTAMP" \
        "$PROJECT_ROOT"
    
    DASHBOARD_PATH="${PROJECT_ROOT}/dashboard/dashboard-${WAKE_SESSION_ID}.html"
    if [[ -f "$DASHBOARD_PATH" ]]; then
        echo -e "${GREEN}✅ Dev Cockpit Dashboard: $DASHBOARD_PATH${NC}"
        echo -e "${BLUE}🌐 Open in browser: file://$DASHBOARD_PATH${NC}"
    fi
fi
```

### 5. Smart Directory Detection
**Issue**: Scripts assume specific working directory  
**Solution**: Implement smart directory detection

**Required Changes**:
```bash
# OLD (assumes specific directory)
PROJECT_ROOT=$(pwd)

# NEW (smart detection)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ "$(basename "$SCRIPT_DIR")" == "cogspace" ]]; then
    PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
else
    PROJECT_ROOT="$SCRIPT_DIR"
fi
```

## Files Requiring Updates

### Project Root Scripts
1. **save.sh** - Line 12: Remove `/current` path
2. **sleep.sh** - Line 12: Remove `/current` path  
3. **wake.sh** - Line 12: Remove `/current` path

### Session Management Scripts
1. **session-wake-enhanced.sh**
   - Lines 42, 44: PROJECT_ROOT path fixes
   - Lines 109, 155: require() path fixes
   - Lines 294-308: node -e command path fixes
   - PROJECT_ROOT determination: Smart directory detection
   - Dashboard generation integration: Add after session restoration

2. **session-save-enhanced.sh**
   - Lines 168, 326, 385: Path fixes for cognitive serializer
   - PROJECT_ROOT determination: Smart directory detection

3. **session-sleep-enhanced.sh**
   - Line 52: Dynamic context analyzer path fix
   - Line 203: JavaScript template quoting fix
   - PROJECT_ROOT determination: Smart directory detection

## Injection Protocol Steps

### Step 1: Deploy COGSPACE Files
```bash
# Create cogspace folder in project root
mkdir cogspace

# Copy all COGSPACE files to cogspace folder
cp -r /path/to/cogspace/* ./cogspace/

# Copy project root scripts
cp save.sh sleep.sh wake.sh ./

# Ensure dashboard generator is executable
chmod +x cogspace/generate-dashboard.sh
```

### Step 2: Apply Path Fixes (Automated)
```bash
cd cogspace

# Fix cognitive serializer paths
sed -i '' 's|${PROJECT_ROOT}/cogspace/cognitive-serializer.cjs|${PROJECT_ROOT}/cognitive-serializer.cjs|g' session-*-enhanced.sh
sed -i '' 's|./cogspace/cognitive-serializer.cjs|./cognitive-serializer.cjs|g' session-*-enhanced.sh

# Fix dynamic context analyzer paths
sed -i '' 's|${PROJECT_ROOT}/dynamic-context-analyzer.sh|${PROJECT_ROOT}/docs/dynamic-context-analyzer.sh|g' session-*-enhanced.sh

# Fix JavaScript template quoting
sed -i '' 's/"immediateActions": ${IMMEDIATE_ACTIONS_JSON},/"immediateActions": '"'"'${IMMEDIATE_ACTIONS_JSON}'"'"',/g' session-sleep-enhanced.sh

# Fix project root scripts
cd ..
sed -i '' 's|cd "${SCRIPT_DIR}/current"|cd "${SCRIPT_DIR}"|g' save.sh sleep.sh wake.sh
```

### Step 3: Verify Script Functionality
```bash
# Test from project root
./save.sh "Test message"
./wake.sh
./sleep.sh "Test completion"

# Test from cogspace directory
cd cogspace
./session-save-enhanced.sh "Test message"
./session-wake-enhanced.sh
./session-sleep-enhanced.sh "Test completion"
```

## Validation Checklist

- [ ] All session scripts execute without path errors
- [ ] Cognitive serializer loads correctly
- [ ] Dynamic context analyzer functions properly
- [ ] JavaScript templates render without syntax errors
- [ ] Session save/restore functionality works
- [ ] AI semantic organization functions correctly
- [ ] Scripts work from both project root and cogspace directory

## Common Issues and Solutions

### Issue: "Cognitive serializer not found"
**Solution**: Verify cognitive-serializer.cjs exists and paths are correct

### Issue: "Dynamic context analyzer not found"
**Solution**: Check that docs/dynamic-context-analyzer.sh exists

### Issue: JavaScript syntax errors in sleep script
**Solution**: Ensure IMMEDIATE_ACTIONS_JSON is properly quoted in JSON templates

### Issue: "No such file or directory: current"
**Solution**: Fix project root scripts to remove `/current` path reference

### Issue: Session scripts not executable
**Solution**: Run `chmod +x session-*-enhanced.sh save.sh sleep.sh wake.sh`

## Version History

- **v9.0.0**: Initial protocol based on benefits-bridge deployment
- **v9.0.1**: Added project root script fixes and smart directory detection
- **v9.0.2**: Documented dynamic context analyzer path requirements
- **v9.0.3**: Added JavaScript template quoting fixes

## Future Improvements

1. **Automated Path Detection**: Scripts should auto-detect their location and adjust paths accordingly
2. **Template System**: Use a proper template system instead of sed replacements
3. **Validation Script**: Create automated validation script for injection verification
4. **Rollback Mechanism**: Implement rollback capability for failed injections
5. **Universal Compatibility**: Ensure scripts work from any directory structure

## Contact

For issues with COGSPACE injection, refer to the COGSPACE-DNA-UPDATE-LOG.md for detailed change history and troubleshooting.

