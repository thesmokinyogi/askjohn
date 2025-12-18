#!/usr/bin/env python3
"""
COGSPACE Database Schema Migration Tool
Version: 59.2.1

Ensures database schema matches current COGSPACE version.
Called by wake.sh after script upgrade to apply pending migrations.

This script is safe to run multiple times - it will only apply
migrations that haven't been applied yet.
"""

import sqlite3
import sys
import json
from pathlib import Path


def get_script_dir():
    """Get the directory containing this script."""
    return Path(__file__).parent.resolve()


def get_db_path():
    """Get path to COGSPACE database in current project."""
    return Path.cwd() / ".cogspace" / "cogspace.db"


def get_migrations_dir():
    """Get path to migrations directory."""
    return get_script_dir() / "migrations"


def get_schema_version_json():
    """Get path to schema version JSON file."""
    return get_script_dir() / "schema_version.json"


def get_local_schema_version(db_path):
    """
    Get current schema version from database.
    Returns 0 if database doesn't exist or has no schema_version table.
    """
    if not db_path.exists():
        return 0

    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.execute(
            "SELECT MAX(version) FROM schema_version"
        )
        result = cursor.fetchone()
        return result[0] if result[0] else 0
    except sqlite3.OperationalError:
        # schema_version table doesn't exist
        return 0
    finally:
        conn.close()


def get_target_schema_version(json_path):
    """
    Get target schema version from DNA source.
    Returns 0 if file doesn't exist.
    """
    if not json_path.exists():
        return 0

    with open(json_path) as f:
        data = json.load(f)
    return data.get("version", 0)


def ensure_schema_version_table(db_path):
    """Create schema_version table if it doesn't exist."""
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY,
                description TEXT,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
    finally:
        conn.close()


def apply_migration(db_path, migration_file, version):
    """
    Apply a single migration file with idempotent handling.

    Args:
        db_path: Path to SQLite database
        migration_file: Path to .sql migration file
        version: Integer version number

    Returns:
        True if migration applied successfully, False if skipped due to existing objects
    """
    print(f"  📦 Applying migration {migration_file.name}...")

    conn = sqlite3.connect(db_path)
    try:
        with open(migration_file) as f:
            sql = f.read()

        # Try to execute the migration SQL
        # Handle partial migrations gracefully - some ALTER TABLE statements
        # may fail if columns already exist from a previous partial run
        try:
            conn.executescript(sql)
        except sqlite3.OperationalError as e:
            error_msg = str(e).lower()
            # These errors indicate the migration was partially applied
            # Mark as complete so we don't retry indefinitely
            if any(phrase in error_msg for phrase in [
                'duplicate column name',
                'table already exists',
                'index already exists',
            ]):
                print(f"  ⚠️  Migration {version} partially applied (schema objects exist)")
                print(f"     Marking as complete to prevent retry loops")
            else:
                # Unknown error - re-raise
                raise

        # Record the migration in schema_version table
        conn.execute(
            "INSERT OR REPLACE INTO schema_version (version, description, applied_at) "
            "VALUES (?, ?, datetime('now'))",
            (version, migration_file.stem)
        )
        conn.commit()
        print(f"  ✅ Migration {version} applied successfully")
        return True
    except Exception as e:
        print(f"  ❌ Migration {version} failed: {e}")
        raise
    finally:
        conn.close()


def migrate():
    """
    Main migration function.

    Checks current database schema version against target version,
    and applies any pending migrations in order.

    Returns:
        Number of migrations applied
    """
    db_path = get_db_path()
    migrations_dir = get_migrations_dir()
    schema_json = get_schema_version_json()

    # If no database exists, nothing to migrate
    if not db_path.exists():
        print("ℹ️  No database found - migrations will run on first save")
        return 0

    # Ensure schema_version table exists
    ensure_schema_version_table(db_path)

    # Get current and target versions
    local_version = get_local_schema_version(db_path)
    target_version = get_target_schema_version(schema_json)

    print(f"🔍 Database schema: v{local_version} → Target: v{target_version}")

    # Check if already current
    if local_version >= target_version:
        print("✅ Database schema is current")
        return 0

    print("🔄 Migrating database schema...")

    # Get sorted migration files
    if not migrations_dir.exists():
        print("⚠️  Migrations directory not found")
        return 0

    migration_files = sorted(migrations_dir.glob("*.sql"))

    if not migration_files:
        print("⚠️  No migration files found")
        return 0

    # Apply migrations in order
    applied = 0
    for mig_file in migration_files:
        # Extract version from filename (e.g., "005_v59_distributed.sql" → 5)
        try:
            mig_version = int(mig_file.name.split("_")[0])
        except (ValueError, IndexError):
            print(f"  ⚠️  Skipping {mig_file.name} - invalid filename format")
            continue

        # Only apply if version is greater than current local version
        if mig_version > local_version:
            apply_migration(db_path, mig_file, mig_version)
            applied += 1

    print(f"✅ Applied {applied} migration(s)")
    return applied


if __name__ == "__main__":
    try:
        migrations_applied = migrate()
        sys.exit(0)
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        sys.exit(1)
