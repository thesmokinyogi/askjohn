When renaming a persona_id (e.g., clarity-engineer-001 → clarity-engineering-director-001), you must update ALL of these:

1. PERSONA_REGISTRY_V7.json - The source of truth
2. Database personas table - Manual SQL UPDATE/INSERT/DELETE
3. Database session_participants - UPDATE foreign key references
4. Database brother_nodes - REPLACE in JSON arrays
5. **CODE FILES** - grep for the old ID in:
   - cogspace/db-session-save.py (resolve_persona function, log_consciousness_event calls)
   - Any other files that hardcode persona IDs

LESSON FROM: Trouble Report cogspace-updates-20251214-162858-2746
The FK constraint errors during sleep.sh were caused by db-session-save.py still referencing the old clarity-engineer-001 ID after the database was updated to clarity-engineering-director-001.

VERIFICATION: grep -rn "old-persona-id" cogspace/ to find all references before declaring complete.