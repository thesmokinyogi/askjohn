# Cleanup Script Scheduling Options

## Requirements
- Run `scripts/cleanup_jobs.py --all` once per week
- Should be reliable and maintainable
- Should work even if app restarts

## Option 1: Cron Job (Recommended) ✅

**Pros:**
- ✅ Independent of app - runs even if app is down
- ✅ Simple, standard Unix tool
- ✅ Reliable - system-level scheduling
- ✅ No additional dependencies
- ✅ Easy to verify (check cron logs)

**Cons:**
- ⚠️ Need to ensure venv is activated
- ⚠️ Need to ensure correct working directory

**Implementation:**
```bash
# Add to crontab (crontab -e)
0 2 * * 0 cd /Users/johncarosella/Documents/GitHub/askjohn/voice-to-text && /Users/johncarosella/Documents/GitHub/askjohn/voice-to-text/venv/bin/python scripts/cleanup_jobs.py --all >> logs/cleanup.log 2>&1
```

**Schedule:** Every Sunday at 2 AM

**Location:** System crontab (`crontab -e`)

---

## Option 2: Background Task in FastAPI

**Pros:**
- ✅ Integrated with app
- ✅ Can use app's services directly (no imports needed)
- ✅ Runs only when app is running (saves resources)

**Cons:**
- ❌ Only runs when app is running
- ❌ Adds dependency (APScheduler)
- ❌ More complex setup

**Implementation:**
- Add APScheduler to requirements.txt
- Create background task in `app/main.py`
- Schedule weekly cleanup

**Location:** `app/main.py` (startup event)

---

## Option 3: Systemd Timer (Linux only)

**Pros:**
- ✅ System-level, very reliable
- ✅ Can run independently of app

**Cons:**
- ❌ Platform-specific (Linux/macOS with systemd)
- ❌ More complex setup
- ❌ Requires root/admin access

**Location:** `/etc/systemd/system/` (system service)

---

## Recommendation: Cron Job

**Why:**
1. **Simplicity:** Standard Unix tool, well-understood
2. **Reliability:** Runs independently of app
3. **No Dependencies:** Doesn't require additional Python packages
4. **Easy Maintenance:** Can check logs, modify schedule easily
5. **Platform Agnostic:** Works on macOS, Linux, any Unix

**Implementation Steps:**
1. Create wrapper script (handles venv activation)
2. Add to crontab
3. Test manually first
4. Monitor logs

---

## Alternative: Hybrid Approach

**Background Task + Cron Fallback:**
- Background task runs when app is running (more efficient)
- Cron job runs weekly as backup (catches missed runs if app was down)

**Best of both worlds:**
- Efficient when app is running
- Reliable even if app restarts

