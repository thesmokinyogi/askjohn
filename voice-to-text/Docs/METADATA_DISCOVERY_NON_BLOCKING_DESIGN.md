# Design: Non-Blocking Metadata Discovery

## Problem
`initialize_metadata_cache()` is synchronous and can block for up to ~7 seconds (with retries). It's called in the async `startup_event`, which blocks the event loop and delays server startup.

## Observation
- `initialize_metadata_cache()` is sync, uses `time.sleep()`, makes REST API calls
- Service already has fallback mechanisms (`_CACHE_LOADED` flag, hardcoded fallback config)
- Service gracefully degrades when cache isn't loaded
- FastAPI won't accept requests until `startup_event` completes

## Research Findings
FastAPI recommends:
1. **`lifespan` context manager** (newer, preferred)
2. **`asyncio.create_task()` in startup_event** (works but deprecated in favor of lifespan)

Since `initialize_metadata_cache()` is sync, we need to run it in a thread pool executor to avoid blocking the event loop.

## Design Options

### Option A: Thread Pool Executor (Recommended)
- Run sync `initialize_metadata_cache()` in `asyncio.to_thread()` or `executor.submit()`
- Start task in `startup_event` using `asyncio.create_task()`
- Server starts immediately, discovery happens in background
- **Pros**: Minimal changes, preserves existing sync code
- **Cons**: Uses thread pool (acceptable for I/O-bound operation)

### Option B: Convert to Async
- Convert `initialize_metadata_cache()` to async
- Replace `time.sleep()` with `asyncio.sleep()`
- Use async HTTP client
- **Pros**: Fully async, no thread pool
- **Cons**: Larger refactor, need to change `discover_speech_metadata()` too

## Chosen Approach: Option A
- Minimal changes
- Preserves existing code structure
- Thread pool is fine for I/O-bound REST API calls
- Server starts immediately with fallback, upgrades when discovery completes

## Implementation Plan
1. Create async wrapper function that runs sync `initialize_metadata_cache()` in thread pool
2. Start background task in `startup_event` using `asyncio.create_task()`
3. Log clearly that server is ready while discovery happens in background
4. Service uses fallback until discovery completes, then automatically upgrades

## Edge Cases
- Discovery fails: Service continues with fallback (already handled)
- Server restarts during discovery: Discovery restarts (acceptable)
- Request arrives before discovery completes: Uses fallback (acceptable, already supported)

