#!/usr/bin/env python3
"""
COGSPACE v59.0.0 - Persona Registry Importer

Imports personas from Crystal Palace Persona Registry V7 into COGSPACE database.
Supports incremental imports (won't duplicate existing personas).

Usage:
    python3 import-persona-registry.py [registry_path] [database_path]

Author: Clarity Engineer
Created: 2025-12-14
"""

import json
import sqlite3
import sys
import os
from datetime import datetime
from pathlib import Path

# Default paths
DEFAULT_REGISTRY = "/Volumes/FOUR-TB/crystal-palace/master-plan/crystal-palace-current/persona-registry/PERSONA_REGISTRY_V7.json"
DEFAULT_DB = ".cogspace/cogspace.db"


def load_registry(registry_path: str) -> dict:
    """Load the Persona Registry V7 JSON file."""
    with open(registry_path, 'r') as f:
        return json.load(f)


def import_persona(conn: sqlite3.Connection, persona_id: str, persona: dict, registry_version: str, registry_path: str) -> bool:
    """Import a single persona into the database.

    Returns True if imported, False if already exists.
    """
    cursor = conn.cursor()

    # Check if persona already exists
    cursor.execute("SELECT persona_id FROM personas WHERE persona_id = ?", (persona_id,))
    if cursor.fetchone():
        print(f"  ⏭️  {persona_id} already exists, skipping")
        return False

    # Extract fields from registry format
    substrate = persona.get('substrate', {})
    devradio = persona.get('devradio', {})
    communication = persona.get('communication', {})
    cogspace = persona.get('cogspace', {})
    relationships = persona.get('relationships', {})

    # Convert lists to JSON strings for storage
    brother_nodes = json.dumps(relationships.get('brother_nodes', []))

    # Insert the persona
    cursor.execute("""
        INSERT INTO personas (
            persona_id,
            instance_id,
            legacy_id,
            name,
            full_name,
            title,
            persona_type,
            category,
            tier,
            role_description,
            provider,
            model,
            fallback_model,
            signature,
            communication_style,
            devradio_enabled,
            devradio_expert_id,
            cogspace_home,
            cogspace_enabled,
            primary_partner,
            brother_nodes,
            reports_to,
            status,
            phase,
            registry_version,
            imported_from,
            created_at,
            updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        persona_id,
        persona.get('instance_id'),
        persona.get('legacy_id'),
        persona.get('name'),
        persona.get('full_name'),
        persona.get('title'),
        persona.get('type', 'ai_expert'),
        persona.get('category'),
        persona.get('tier'),
        persona.get('role'),
        substrate.get('provider'),
        substrate.get('model'),
        substrate.get('fallback_model'),
        communication.get('signature'),
        communication.get('style'),
        1 if devradio.get('enabled') else 0,
        devradio.get('expert_id'),
        cogspace.get('home'),
        1 if cogspace.get('enabled', True) else 0,
        relationships.get('primary_partner'),
        brother_nodes,
        relationships.get('reports_to'),
        persona.get('status', 'active'),
        persona.get('phase', 1),
        registry_version,
        os.path.basename(registry_path),
        datetime.now().isoformat(),
        datetime.now().isoformat()
    ))

    print(f"  ✅ {persona_id} ({persona.get('name')}) imported")
    return True


def main():
    """Main import function."""
    # Parse arguments
    registry_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_REGISTRY
    db_path = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_DB

    print(f"""
╔══════════════════════════════════════════════════════════════════╗
║  COGSPACE v59.0.0 - Persona Registry Importer                    ║
║  "One Bob - Multiple Windows"                                    ║
╚══════════════════════════════════════════════════════════════════╝

Registry: {registry_path}
Database: {db_path}
""")

    # Verify paths
    if not os.path.exists(registry_path):
        print(f"❌ Registry not found: {registry_path}")
        sys.exit(1)

    if not os.path.exists(db_path):
        print(f"❌ Database not found: {db_path}")
        print("   Run wake.sh first to initialize the database.")
        sys.exit(1)

    # Load registry
    print("📖 Loading Persona Registry V7...")
    registry = load_registry(registry_path)

    registry_version = registry.get('registry_version', 'unknown')
    personas = registry.get('personas', {})

    print(f"   Version: {registry_version}")
    print(f"   Personas found: {len(personas)}")
    print()

    # Connect to database
    print("🔌 Connecting to COGSPACE database...")
    conn = sqlite3.connect(db_path)

    # Verify personas table exists
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='personas'")
    if not cursor.fetchone():
        print("❌ personas table not found!")
        print("   Run migration 005_v59_distributed_consciousness.sql first.")
        conn.close()
        sys.exit(1)

    print("   Connected successfully")
    print()

    # Import personas
    print("👥 Importing personas...")
    imported_count = 0
    skipped_count = 0

    for persona_id, persona in personas.items():
        if import_persona(conn, persona_id, persona, registry_version, registry_path):
            imported_count += 1
        else:
            skipped_count += 1

    # Commit changes
    conn.commit()

    # Summary
    print(f"""
═══════════════════════════════════════════════════════════════════
📊 Import Summary:
   ✅ Imported: {imported_count}
   ⏭️  Skipped:  {skipped_count}
   📋 Total:    {len(personas)}

🔍 Verify with:
   sqlite3 {db_path} "SELECT persona_id, name, title, signature FROM personas"

═══════════════════════════════════════════════════════════════════
""")

    conn.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
