# Lesson Learned: Never Hardcode Version Strings

**Date**: 2025-12-13
**Category**: Code Quality / Maintainability
**Severity**: High
**Version**: v55.0.0

---

## The Problem

During the v55.0.0 release, a hardcoded version string "v21.1.5" was discovered at line 1032 in `cogspace-diagnostics.sh`. When updating to v55.0.0, the fix initially replaced one hardcoded string with another ("v55.0.0") - perpetuating the anti-pattern instead of fixing the root cause.

**Symptom**: Diagnostics banner displayed wrong version (v21.1.5) when actual version was v55.0.0
**Location**: `cogspace/src/cogspace-diagnostics.sh:1032`

---

## Why This Happens

1. **Copy-paste coding**: Quick fixes that hardcode values seem faster
2. **Oversight during reviews**: Easy to miss string literals in large files
3. **Inconsistent patterns**: When some values are dynamic and others aren't
4. **Time pressure**: "I'll fix it properly later" syndrome

---

## The Solution

**Always use dynamic reads from the single source of truth.**

### Correct Pattern (v55.0.0 fix):
```bash
# v55.0.0: Dynamic version from cogspace-version.json (never hardcode!)
local diag_version=$(get_current_version)
echo -e "${CYAN}COGSPACE DIAGNOSTICS v${diag_version}${NC}"
```

### Anti-Patterns to Avoid:
```bash
# BAD: Hardcoded version
echo -e "${CYAN}COGSPACE DIAGNOSTICS v21.1.5${NC}"

# BAD: Replacing one hardcode with another
echo -e "${CYAN}COGSPACE DIAGNOSTICS v55.0.0${NC}"

# BAD: Environment variable that might not be set
echo -e "${CYAN}COGSPACE DIAGNOSTICS v${VERSION}${NC}"
```

### Correct Patterns:
```bash
# GOOD: Read from version file using existing helper
local version=$(get_current_version)
echo "Version: v${version}"

# GOOD: Use lib/version.cjs in Node.js contexts
const { getVersion } = require('./lib/version.cjs');
console.log(`Version: ${getVersion()}`);

# GOOD: Read directly from JSON when helper unavailable
local version=$(jq -r '.version' cogspace/cogspace-version.json)
```

---

## The Rule

> **If a value CAN change, it WILL change. Use dynamic reads from a single source of truth.**

### Checklist for Version References:
- [ ] Is this value read dynamically from cogspace-version.json?
- [ ] Does the helper function/tool already exist?
- [ ] Would a future version bump require editing this line?
- [ ] Is this the ONLY place this value appears, or is it duplicated?

---

## Impact

- **Files affected**: cogspace-diagnostics.sh, any script displaying version info
- **Time cost**: 45+ minutes debugging "wrong version displayed" issues
- **User confusion**: Dashboard and CLI showing different versions
- **Trust erosion**: Users lose confidence when versions don't match

---

## Prevention

1. **Use grep to find hardcoded versions**: `grep -rn "v[0-9]\+\.[0-9]\+\.[0-9]\+" cogspace/`
2. **Add pre-commit checks**: Lint for version string patterns
3. **Code review focus**: Any version string should trigger review
4. **Single source of truth**: `cogspace-version.json` is the ONLY version authority

---

## Related Files

- `cogspace/cogspace-version.json` - Single source of truth
- `cogspace/lib/version.cjs` - Node.js version helper
- `cogspace/src/cogspace-diagnostics.sh` - Uses `get_current_version()` function

---

*Lesson documented by Clarity Engineer during v55.0.0 "Complete Healing" release*
