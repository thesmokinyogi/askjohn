# Migration Guide - 🏗️ COGSPACE v40.0.0 "Unified Version"

## Upgrading to v38.1.0 (Unified & Portable)

### Prerequisites

1. **Full backup**: Ensure you have backups of all projects
2. **Node.js**: Ensure Node.js is installed (`node --version`)
3. **npm**: Package manager (`npm --version`)

### Migration Steps

#### Option A: Fresh v23 Project (Recommended)

```bash
# 1. Create new v23 project
cd /Volumes/FOUR-TB/cogspace-dna-source/v23/src
./new-project my-project-v23 "owner" "developer" "type" "description"

# 2. Copy session data from v22
cp -r /path/to/old-project/session-management/cognitive-context/* \
      /path/to/new-project/memories/

# 3. Copy custom notes
cp -r /path/to/old-project/session-management/cognitive-context/notes/* \
      /path/to/new-project/memories/notes/
```

#### Option B: In-Place Upgrade (Advanced)

**WARNING**: This modifies your existing project. Backup first!

```bash
# 1. Run auto-upgrade script (coming soon)
./cogspace/migrate-to-v23.sh
```

### What Changes

| v22.x | v23.1.x |
|-------|---------|
| `session-management/` | `memories/` |
| `session-wake-enhanced.sh` | `cogspace/core/session-wake.sh` |
| `src/trouble-report` | `cogspace/commands/trouble-report` |
| Dynamic wrappers | Static commands |
| File-based dashboard | Server-based dashboard |

### Post-Migration

```bash
# 1. Install dependencies
npm install

# 2. Test wake
./wake.sh

# 3. Verify dashboard
open http://localhost:8765/dashboard.html

# 4. Test commands
./cogspace/commands/trouble-report
./cogspace/commands/guidelines list

# 5. Test save/sleep
./save.sh "Migration test"
./sleep.sh "Migration complete"
```

### Troubleshooting

**Server won't start**: Check Node.js installation and port 8765 availability
**Dashboard won't load**: Run `npm install` and restart wake.sh
**Commands not found**: Verify `/cogspace/commands/` exists and scripts are executable

### Rollback

If migration fails:

```bash
# Restore from backup
rm -rf /path/to/project
cp -r /path/to/backup /path/to/project
```

## Support

For issues, check the [v23 deployment log](v23-deployment-*.log)

