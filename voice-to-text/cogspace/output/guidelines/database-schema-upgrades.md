# Database & Schema Upgrade Guideline

When making changes that affect COGSPACE database or Persona Registry:

## Persona Registry Updates (JSON → Database)

### Adding New Persona
1. Edit PERSONA_REGISTRY_V7.json
2. Run: python3 cogspace/db/import-persona-registry.py
3. Verify: sqlite3 .cogspace/cogspace.db "SELECT persona_id FROM personas;"

### Editing Existing Persona (metadata only)
1. Edit PERSONA_REGISTRY_V7.json
2. MANUAL SQL REQUIRED - import script skips existing records:
   UPDATE personas SET title="...", registry_version="..." WHERE persona_id="...";
3. Bump registry_version in JSON

### Changing Persona ID (rename)
1. Edit PERSONA_REGISTRY_V7.json with new ID
2. MANUAL SQL REQUIRED:
   - INSERT new record from old data
   - UPDATE session_participants SET persona_id="new" WHERE persona_id="old"
   - UPDATE brother_nodes references in other personas
   - DELETE old record
3. Bump registry_version in JSON

## Database Schema Migrations

### Adding New Tables
1. Create migration: cogspace/db/migrations/XXX_description.sql
2. Test: sqlite3 .cogspace/cogspace.db < migration.sql
3. Update cogspace-version.json

### Modifying Existing Tables
1. SQLite limitations: Cannot ALTER COLUMN, must recreate table
2. Use CREATE TABLE new_table AS SELECT... pattern
3. Always backup first: cp .cogspace/cogspace.db .cogspace/cogspace.db.bak

## Verification Checklist
- [ ] JSON validates: python3 -c "import json; json.load(open(\"...\"))"
- [ ] Database query returns expected data
- [ ] Foreign key references updated
- [ ] Version numbers bumped
- [ ] Release notes created if needed

Reference: Trouble Report cogspace-updates-20251214-155930-8834