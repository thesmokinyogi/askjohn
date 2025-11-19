# ProcessingStrategy Explanation

## What We Know

### From Google's Official Examples
- Google's official Python examples **always include** `processing_strategy`
- The value used is: `cloud_speech.BatchRecognizeRequest.ProcessingStrategy.DYNAMIC_BATCHING`
- It's part of the `BatchRecognizeRequest` object

### What It Controls
Based on documentation and naming:

**`processing_strategy`** determines **how Google processes your batch recognition request**:
- **Order of processing** (which files get processed first)
- **Resource allocation** (how compute resources are distributed)
- **Batching behavior** (how files are grouped for processing)
- **Cost optimization** (potentially affects pricing)

## Available Options (Inferred)

Based on Google Cloud API patterns and the name `DYNAMIC_BATCHING`:

1. **`DYNAMIC_BATCHING`** (what Google's examples use)
   - Likely: Optimizes processing based on file sizes, queue length, resource availability
   - May: Group files intelligently for cost/performance optimization
   - May: Adjust processing order based on system load

2. **`STATIC_BATCHING`** (likely exists)
   - Likely: Process files in submission order
   - May: Fixed resource allocation per file
   - May: Simpler, more predictable processing

3. **`PROCESSING_STRATEGY_UNSPECIFIED`** (default if omitted)
   - Likely: Google chooses the strategy automatically
   - May: Defaults to `DYNAMIC_BATCHING` or system default

## Why It Matters

### The Critical Question
**Is `processing_strategy` required, or just recommended?**

- **If required:** Our missing field could be why transcripts are empty
- **If optional:** It might affect performance/cost but not correctness

### Evidence
1. ✅ **Google's official examples always include it**
2. ❓ **We were missing it** - and getting empty transcripts
3. ❓ **No clear documentation** on whether it's required

## What We Changed

We added:
```python
processing_strategy=cloud_speech.BatchRecognizeRequest.ProcessingStrategy.DYNAMIC_BATCHING,
```

To our `BatchRecognizeRequest` in `submit_job()`.

## Testing Hypothesis

**If `processing_strategy` was required:**
- Adding it should fix the empty transcript issue
- Jobs should now produce transcript text

**If `processing_strategy` is optional:**
- Adding it shouldn't hurt
- It might improve performance/cost
- We still need to find the real root cause

## Next Steps

1. **Test with the new field** - see if transcripts appear
2. **If still empty** - the issue is elsewhere (config, parsing, etc.)
3. **If it works** - we found the root cause!

## References

- Google's official Python examples (from web search)
- `docs/OFFICIAL_EXAMPLE_COMPARISON.md` - Our comparison document
- `app/services/transcribe_v2.py:837` - Where we added it

