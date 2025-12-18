#!/usr/bin/env python3
"""
Crystal Palace Persona Registry Pre-Update Documentation Audit Tool

Checks that all operational documentation is current before pushing registry updates.
Mirrors the COGSPACE pre-dna-audit.py workflow.

Usage:
    python3 pre-persona-registry-audit.py [--verbose]

Exit codes:
    0 = All docs current, safe to update
    1 = Docs out of sync, update required

Author: Clarity Engineering Director
"""

import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional


def parse_version(v: str) -> Tuple[int, int, int]:
    """Parse version string to tuple for comparison.

    Handles both "7.1.0" and "V7.1.0" formats.
    """
    try:
        # Remove leading 'V' or 'v' if present
        v = v.lstrip('Vv')
        parts = v.split('.')
        return (int(parts[0]), int(parts[1]), int(parts[2]) if len(parts) > 2 else 0)
    except (ValueError, IndexError):
        return (0, 0, 0)


# Paths
REGISTRY_FILE = Path("/Volumes/FOUR-TB/crystal-palace/master-plan/crystal-palace-current/persona-registry/PERSONA_REGISTRY_V7.json")
DOCS_DIR = Path("/Volumes/FOUR-TB/crystal-palace/operations/persona-registry/current")

# Documents to audit (filename -> description)
OPERATIONAL_DOCS = {
    "persona-registry-readme.md": "Overview, philosophy, quick start",
    "persona-registry-operations.md": "How to add, edit, update personas",
    "persona-registry-architecture.md": "JSON schema, file structure, identity system",
}


def get_registry_version() -> str:
    """Get Persona Registry version from JSON file."""
    try:
        with open(REGISTRY_FILE) as f:
            data = json.load(f)
            return data.get('registry_version', 'unknown')
    except (FileNotFoundError, json.JSONDecodeError):
        return 'unknown'


def extract_version_from_doc(filepath: Path) -> Optional[str]:
    """Extract version number from document header.

    Looks for patterns like:
    - V7.1.0 or v7.1.0
    - Version: 7.1.0
    - **Version**: V7.1.0
    """
    try:
        with open(filepath, 'r') as f:
            # Only check first 30 lines for version
            for i, line in enumerate(f):
                if i > 30:
                    break

                # Pattern 1: V7.1.0 or v7.1.0 style
                match = re.search(r'[Vv](\d+\.\d+\.\d+)', line)
                if match:
                    return match.group(1)

                # Pattern 2: Version: 7.1.0 style
                match = re.search(r'version[:\s]+(\d+\.\d+\.\d+)', line, re.IGNORECASE)
                if match:
                    return match.group(1)

    except Exception:
        pass

    return None


def find_latest_release_notes(docs_dir: Path) -> Tuple[Optional[str], Optional[str]]:
    """Find the latest RELEASE-NOTES file and its version.

    Returns: (filename, version) or (None, None)
    """
    release_notes = []

    if not docs_dir.exists():
        return None, None

    for f in docs_dir.iterdir():
        if f.name.startswith("RELEASE-NOTES-") and f.name.endswith(".md"):
            # Extract version from filename (e.g., RELEASE-NOTES-V7.1.0.md)
            match = re.search(r'RELEASE-NOTES-[Vv]?(\d+\.\d+\.\d+)\.md', f.name)
            if match:
                release_notes.append((f.name, match.group(1)))

    if not release_notes:
        return None, None

    # Sort by version (descending)
    release_notes.sort(key=lambda x: parse_version(x[1]), reverse=True)
    return release_notes[0]


def compare_versions(doc_version: str, current_version: str) -> str:
    """Compare versions and return status.

    Returns: 'current', 'outdated', 'check', or 'unknown'
    """
    try:
        doc_v = parse_version(doc_version)
        curr_v = parse_version(current_version)

        # Consider "current" if major version matches
        if doc_v[0] == curr_v[0] and doc_v[1] >= curr_v[1] - 1:
            if doc_v >= curr_v:
                return 'current'
            else:
                return 'check'  # Close enough, but review

        if doc_v < curr_v:
            return 'outdated'

        return 'current'
    except Exception:
        return 'unknown'


def audit_documentation(verbose: bool = False) -> Tuple[bool, List[Dict]]:
    """Run full documentation audit.

    Returns: (all_current, results_list)
    """
    current_version = get_registry_version()
    results = []
    all_current = True

    # Check release notes
    latest_rn_file, latest_rn_version = find_latest_release_notes(DOCS_DIR)

    expected_rn = f"RELEASE-NOTES-V{current_version}.md"
    rn_exists = (DOCS_DIR / expected_rn).exists() if DOCS_DIR.exists() else False

    if rn_exists:
        results.append({
            'file': expected_rn,
            'doc_version': current_version,
            'status': 'current',
            'description': 'Release notes for current version'
        })
    else:
        all_current = False
        results.append({
            'file': expected_rn,
            'doc_version': latest_rn_version or 'NONE',
            'status': 'missing',
            'description': f'Release notes (latest: {latest_rn_file or "none"})'
        })

    # Check operational docs
    for doc_name, description in OPERATIONAL_DOCS.items():
        doc_path = DOCS_DIR / doc_name

        if not doc_path.exists():
            all_current = False
            results.append({
                'file': doc_name,
                'doc_version': 'MISSING',
                'status': 'missing',
                'description': description
            })
            continue

        doc_version = extract_version_from_doc(doc_path)

        if not doc_version:
            results.append({
                'file': doc_name,
                'doc_version': 'NO VERSION',
                'status': 'check',
                'description': description
            })
            continue

        status = compare_versions(doc_version, current_version)

        if status == 'outdated':
            all_current = False

        results.append({
            'file': doc_name,
            'doc_version': doc_version,
            'status': status,
            'description': description
        })

    return all_current, results


def print_report(current_version: str, results: List[Dict], all_current: bool):
    """Print formatted audit report."""

    print("""
╔══════════════════════════════════════════════════════════════════╗
║  Crystal Palace Persona Registry Documentation Audit             ║
╚══════════════════════════════════════════════════════════════════╝
""")

    print(f"📋 Current Registry Version: V{current_version}")
    print(f"📂 Docs Location: {DOCS_DIR}")
    print(f"📄 Registry File: {REGISTRY_FILE}")
    print()

    print("DOCUMENT STATUS:")
    print("─" * 68)

    status_icons = {
        'current': '✅',
        'check': '⚠️ ',
        'outdated': '❌',
        'missing': '❌',
        'unknown': '❓'
    }

    status_labels = {
        'current': 'CURRENT',
        'check': 'CHECK NEEDED',
        'outdated': 'OUTDATED',
        'missing': 'MISSING',
        'unknown': 'UNKNOWN'
    }

    for r in results:
        icon = status_icons.get(r['status'], '❓')
        label = status_labels.get(r['status'], 'UNKNOWN')
        version_str = f"V{r['doc_version']}" if r['doc_version'] not in ('MISSING', 'NO VERSION', 'NONE') else r['doc_version']

        print(f"  {icon} {r['file']:<40} {version_str:<10} {label}")

    print("─" * 68)
    print()

    if all_current:
        print("✅ ALL DOCUMENTATION CURRENT - Safe to update registry")
    else:
        outdated = [r for r in results if r['status'] in ('outdated', 'missing')]
        check = [r for r in results if r['status'] == 'check']

        print(f"❌ DOCUMENTATION OUT OF SYNC - {len(outdated)} doc(s) need updates")
        print()
        print("ACTION REQUIRED:")
        print()

        for i, r in enumerate(outdated, 1):
            if r['status'] == 'missing' and 'RELEASE-NOTES' in r['file']:
                print(f"{i}. CREATE: {r['file']}")
                print("   Sections: Overview, Key Changes, Files Modified, Migration Notes, Testing")
            elif r['status'] == 'missing':
                print(f"{i}. CREATE: {r['file']}")
                print(f"   Content: {r['description']}")
            else:
                print(f"{i}. UPDATE: {r['file']}")
                print(f"   Current: V{r['doc_version']} → Needed: V{current_version}")
                print(f"   Review: {r['description']}")
            print()

        if check:
            print("REVIEW NEEDED (may be fine):")
            for r in check:
                print(f"  ⚠️  {r['file']} - {r['description']}")
            print()

        print("DO NOT update registry until ALL documents are current.")

    print()


def main():
    """Main function."""
    import argparse

    parser = argparse.ArgumentParser(description="Crystal Palace Persona Registry Documentation Audit")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show verbose output")
    args = parser.parse_args()

    # Check if registry file exists
    if not REGISTRY_FILE.exists():
        print(f"⚠️  Registry file not found: {REGISTRY_FILE}")
        print("   This is expected on non-Crystal Palace systems.")
        print("   Skipping documentation audit.")
        return 0

    # Check if docs directory exists
    if not DOCS_DIR.exists():
        print(f"⚠️  Documentation directory not found: {DOCS_DIR}")
        print("   Creating directory structure...")
        DOCS_DIR.mkdir(parents=True, exist_ok=True)

    current_version = get_registry_version()
    all_current, results = audit_documentation(args.verbose)

    print_report(current_version, results, all_current)

    return 0 if all_current else 1


if __name__ == '__main__':
    sys.exit(main())
