When updating the Persona Registry JSON (PERSONA_REGISTRY_V7.json), the COGSPACE database does NOT automatically sync. The import script only INSERTs new records and skips existing ones.

CRITICAL: After editing a persona in the JSON:
1. If only changing metadata (title, achievements, etc.) - manual SQL UPDATE required
2. If changing persona_id - requires: INSERT new record, UPDATE foreign keys, DELETE old record
3. Always verify with: sqlite3 .cogspace/cogspace.db "SELECT persona_id, title, registry_version FROM personas;"

LESSON FROM: Trouble Report cogspace-updates-20251214-155930-8834
The Clarity Engineering Director promotion (Dec 14, 2025) was not reflected in database for 24 hours because re-running import-persona-registry.py just skipped existing records.

FUTURE: Consider adding --force flag or version-aware upsert to import script if this becomes a recurring issue.