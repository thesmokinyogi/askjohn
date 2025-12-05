# Setting Up Weekly Cleanup with Cron

## Quick Setup

### Step 1: Test the Wrapper Script

```bash
# Test manually first
./scripts/run_cleanup.sh --dry-run
```

### Step 2: Add to Crontab

```bash
# Open crontab editor
crontab -e

# Add this line (runs every Sunday at 2 AM):
0 2 * * 0 /Users/johncarosella/Documents/GitHub/askjohn/voice-to-text/scripts/run_cleanup.sh >> /Users/johncarosella/Documents/GitHub/askjohn/voice-to-text/logs/cleanup.log 2>&1
```

### Step 3: Verify

```bash
# List your cron jobs
crontab -l

# Check logs after it runs
tail -f logs/cleanup.log
```

## Cron Schedule Format

```
* * * * *
│ │ │ │ │
│ │ │ │ └─── Day of week (0-7, 0 and 7 = Sunday)
│ │ │ └───── Month (1-12)
│ │ └─────── Day of month (1-31)
│ └───────── Hour (0-23)
└─────────── Minute (0-59)
```

**Examples:**
- `0 2 * * 0` - Every Sunday at 2:00 AM
- `0 3 * * 1` - Every Monday at 3:00 AM
- `0 0 1 * *` - First day of every month at midnight

## Alternative: Background Task in FastAPI

If you prefer to run it as part of the app, we can add APScheduler:

```python
# In app/main.py startup_event
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()
scheduler.add_job(
    run_cleanup_task,
    'cron',
    day_of_week='sun',
    hour=2,
    minute=0
)
scheduler.start()
```

**Tradeoff:** Only runs when app is running, but more integrated.

