# REQUIRED: Pre-DNA Documentation Audit

**Priority**: MANDATORY before ANY push to COGSPACE DNA
**Created**: 2025-12-14
**Author**: Clarity Engineering Director

---

## Overview

Before pushing ANY changes to COGSPACE DNA (GitHub remote), you MUST ensure documentation parity. This prevents the regression where code advances but documentation falls behind.

---

## Audit Workflow

### Step 1: Run the Audit Script

```bash
python3 cogspace/commands/pre-dna-audit.py
```

This script automatically:
- Reads the current COGSPACE version from `cogspace-version.json`
- Scans ALL operational documents in `/Volumes/FOUR-TB/crystal-palace/operations/cogspace/current/`
- Extracts version numbers from document headers
- Reports which documents are outdated or missing

### Step 2: Address Any Issues

If the script reports ❌ OUTDATED or MISSING documents:

1. **Create missing release notes**:
   - Location: `/Volumes/FOUR-TB/crystal-palace/operations/cogspace/current/`
   - Filename: `RELEASE-NOTES-{VERSION}.md`
   - Include: Overview, Key Changes, Files Modified, Migration Notes, Testing

2. **Update operational docs as needed**:
   - `cogspace-database-operations.md` - New tables, migrations, tools
   - `cogspace-directory-structure.md` - New files, folders, scripts
   - `cogspace-how-to-create-new-project.md` - Setup workflow changes
   - `cogspace-how-to-update.md` - Update workflow changes
   - `cogspace-system-requirements.md` - New dependencies
   - `cogspace-readme.md` - New features

3. **Update version headers** in each document to match current COGSPACE version

### Step 3: Re-run and Confirm

```bash
python3 cogspace/commands/pre-dna-audit.py
```

Only proceed with DNA push when ALL documents show ✅ CURRENT.

---

## Document Checklist

| Document | Update When |
|----------|-------------|
| `RELEASE-NOTES-{VERSION}.md` | Every version bump |
| `cogspace-database-operations.md` | New tables, migrations, CLI tools |
| `cogspace-directory-structure.md` | New files, folders, scripts added |
| `cogspace-how-to-create-new-project.md` | Setup workflow changes |
| `cogspace-how-to-update.md` | Update workflow changes |
| `cogspace-system-requirements.md` | New dependencies |
| `cogspace-readme.md` | New features added |

---

## Why This Matters

- **v56.0.0 → v59.2.0 gap**: We shipped 7 versions without updating operational docs
- **Operators need current docs**: They can't use features they don't know exist
- **Code without docs is incomplete**: Documentation IS part of the release

---

## Quick Reference

```bash
# Check documentation status
python3 cogspace/commands/pre-dna-audit.py

# Docs location
/Volumes/FOUR-TB/crystal-palace/operations/cogspace/current/

# Version source of truth
cogspace/cogspace-version.json
```

---

**DO NOT push to DNA until documentation is current.**

*"Maintain parity going forward"* 🏰⚡
