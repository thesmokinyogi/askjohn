# REQUIRED: Pre-Persona-Registry Documentation Audit

**Priority**: MANDATORY before ANY updates to Persona Registry
**Created**: 2025-12-14
**Author**: Clarity Engineering Director

---

## Overview

Before updating the Crystal Palace Persona Registry (PERSONA_REGISTRY_V7.json), you MUST ensure documentation parity. This prevents code/config advancing while documentation falls behind.

---

## Audit Workflow

### Step 1: Run the Audit Script

```bash
python3 cogspace/commands/pre-persona-registry-audit.py
```

This script automatically:
- Reads the current registry version from `PERSONA_REGISTRY_V7.json`
- Scans ALL operational documents in `/Volumes/FOUR-TB/crystal-palace/operations/persona-registry/current/`
- Extracts version numbers from document headers
- Reports which documents are outdated or missing

### Step 2: Address Any Issues

If the script reports OUTDATED or MISSING documents:

1. **Create missing release notes**:
   - Location: `/Volumes/FOUR-TB/crystal-palace/operations/persona-registry/current/`
   - Filename: `RELEASE-NOTES-V{VERSION}.md`
   - Include: Overview, Key Changes, Files Modified, Migration Notes, Testing

2. **Update operational docs as needed**:
   - `persona-registry-readme.md` - Overview, philosophy, quick start
   - `persona-registry-operations.md` - How to add, edit, update personas
   - `persona-registry-architecture.md` - JSON schema, file structure

3. **Update version headers** in each document to match current registry version

### Step 3: Re-run and Confirm

```bash
python3 cogspace/commands/pre-persona-registry-audit.py
```

Only proceed with registry updates when ALL documents show CURRENT.

---

## Document Checklist

| Document | Update When |
|----------|-------------|
| `RELEASE-NOTES-V{VERSION}.md` | Every version bump |
| `persona-registry-readme.md` | Philosophy changes, new quick start steps |
| `persona-registry-operations.md` | Workflow changes, new procedures |
| `persona-registry-architecture.md` | Schema changes, new fields |

---

## Why This Matters

- **Documentation gap**: Config can advance but docs fall behind
- **Operators need current docs**: They can't use features they don't know exist
- **Registry changes without docs are incomplete**: Documentation IS part of the release

---

## Quick Reference

```bash
# Check documentation status
python3 cogspace/commands/pre-persona-registry-audit.py

# Docs location
/Volumes/FOUR-TB/crystal-palace/operations/persona-registry/current/

# Registry source of truth
/Volumes/FOUR-TB/crystal-palace/master-plan/crystal-palace-current/persona-registry/PERSONA_REGISTRY_V7.json
```

---

**DO NOT update registry until documentation is current.**

*"No persona left undocumented"* 🏰⚡
