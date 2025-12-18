#!/usr/bin/env python3
"""
COGSPACE Pre-DNA Documentation Audit Tool

Checks that all operational documentation is current before pushing to DNA.
This prevents the v56→v59 gap where code advanced but docs fell behind.

Usage:
    python3 pre-dna-audit.py [--verbose]

Exit codes:
    0 = All docs current, safe to push
    1 = Docs out of sync, update required

Author: Clarity Engineering Director
Version: Reads from cogspace-version.json (single source of truth)
"""

import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional


def parse_version(v: str) -> Tuple[int, int, int]:
    """Parse version string to tuple for comparison."""
    try:
        parts = v.split('.')
        return (int(parts[0]), int(parts[1]), int(parts[2]) if len(parts) > 2 else 0)
    except (ValueError, IndexError):
        return (0, 0, 0)

# Paths
SCRIPT_DIR = Path(__file__).parent.parent  # Points to cogspace/
DOCS_DIR = Path("/Volumes/FOUR-TB/crystal-palace/operations/cogspace/current")

# Documents to audit (filename -> description)
OPERATIONAL_DOCS = {
    "cogspace-database-operations.md": "Database tables, migrations, CLI tools",
    "cogspace-directory-structure.md": "Files, folders, scripts",
    "cogspace-how-to-create-new-project.md": "Project setup workflow",
    "cogspace-how-to-update.md": "Update workflow",
    "cogspace-system-requirements.md": "Dependencies",
    "cogspace-readme.md": "Feature overview",
}


def get_cogspace_version() -> str:
    """Get COGSPACE version from cogspace-version.json (single source of truth)."""
    version_file = SCRIPT_DIR / "cogspace-version.json"
    try:
        with open(version_file) as f:
            data = json.load(f)
            return data.get('version', 'unknown')
    except (FileNotFoundError, json.JSONDecodeError):
        return 'unknown'


def extract_version_from_doc(filepath: Path) -> Optional[str]:
    """Extract version number from document header.

    Looks for patterns like:
    - v56.0.0
    - Version: 56.0.0
    - COGSPACE Version: 56.0.0
    - **COGSPACE Version:** 56.0.0
    """
    try:
        with open(filepath, 'r') as f:
            # Only check first 30 lines for version
            for i, line in enumerate(f):
                if i > 30:
                    break

                # Pattern 1: v56.0.0 style
                match = re.search(r'v(\d+\.\d+\.\d+)', line, re.IGNORECASE)
                if match:
                    return match.group(1)

                # Pattern 2: Version: 56.0.0 style
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
            # Extract version from filename
            match = re.search(r'RELEASE-NOTES-(\d+\.\d+\.\d+)\.md', f.name)
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
        # (allows for minor doc lag within same major)
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
    current_version = get_cogspace_version()
    results = []
    all_current = True

    # Check release notes
    latest_rn_file, latest_rn_version = find_latest_release_notes(DOCS_DIR)

    expected_rn = f"RELEASE-NOTES-{current_version}.md"
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
║  COGSPACE Pre-DNA Documentation Audit                            ║
╚══════════════════════════════════════════════════════════════════╝
""")

    print(f"📋 Current COGSPACE Version: {current_version}")
    print(f"📂 Docs Location: {DOCS_DIR}")
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
        version_str = f"v{r['doc_version']}" if r['doc_version'] not in ('MISSING', 'NO VERSION', 'NONE') else r['doc_version']

        print(f"  {icon} {r['file']:<40} {version_str:<10} {label}")

    print("─" * 68)
    print()

    if all_current:
        print("✅ ALL DOCUMENTATION CURRENT - Safe to push to DNA")
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
                print(f"   Current: v{r['doc_version']} → Needed: v{current_version}")
                print(f"   Review: {r['description']}")
            print()

        if check:
            print("REVIEW NEEDED (may be fine):")
            for r in check:
                print(f"  ⚠️  {r['file']} - {r['description']}")
            print()

        print("DO NOT push to DNA until ALL documents are current.")

    print()


def main():
    """Main function."""
    import argparse

    parser = argparse.ArgumentParser(description="COGSPACE Pre-DNA Documentation Audit")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show verbose output")
    args = parser.parse_args()

    # Check if docs directory exists
    if not DOCS_DIR.exists():
        print(f"⚠️  Documentation directory not found: {DOCS_DIR}")
        print("   This is expected on non-Crystal Palace systems.")
        print("   Skipping documentation audit.")
        return 0

    current_version = get_cogspace_version()
    all_current, results = audit_documentation(args.verbose)

    print_report(current_version, results, all_current)

    return 0 if all_current else 1


if __name__ == '__main__':
    sys.exit(main())
