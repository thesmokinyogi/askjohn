# Voice-to-Text Transcription Service - Architecture Document

**Version:** 2.0
**Last Updated:** 2025-11-09
**Status:** Living Document

---

## Purpose of This Document

This document defines the **strategic architectural principles** for the Voice-to-Text transcription service. It guides implementation decisions and helps distinguish between:

- **STRATEGIC elements** - Core principles that should not change without architectural discussion
- **TACTICAL elements** - Implementation details that can evolve

**Use this document to:**
- Make design decisions
- Evaluate proposed changes
- Onboard new contributors (including AI)
- Prevent architectural drift

---

## 1. Core Design Principles (STRATEGIC)

### 1.1 Provider Agnosticism

**Principle:** The system must support multiple transcription providers without core architectural changes.

**Why:**
- Technology landscape evolves (today: Google, tomorrow: Whisper, future: unknown)
- Cost optimization requires ability to switch providers
- Quality comparison requires testing multiple providers
- Vendor lock-in creates strategic risk

**Implementation Requirements:**
- `STT_PROVIDER` is the top-level architectural switch
- Provider-specific code isolated in separate services
- Common interface across all providers
- Configuration clearly separates provider selection from provider-specific settings

**Prohibited:**
- Hard-coding provider assumptions into core application logic
- Mixing provider-specific configuration with strategic configuration
- Removing `STT_PROVIDER` without architectural redesign

**Test:** Can we add a new provider (e.g., AssemblyAI) by:
1. Creating a new service file
2. Adding provider-specific config
3. Adding routing logic in main.py
4. WITHOUT touching core business logic?

---

### 1.2 Cost Transparency & Control

**Principle:** Users must understand, predict, and control transcription costs.

**Why:**
- Transcription is usage-based (not fixed cost)
- User has budget constraints ($250/month initially)
- Different models have different cost/quality tradeoffs
- Cost awareness influences user behavior (batch vs real-time, model selection)

**Implementation Requirements:**
- Cost estimation before transcription
- Budget tracking and alerting
- Model selection exposes cost implications
- Usage history and reporting
- Admin controls for budget limits

**Prohibited:**
- Hidden costs or surprise billing
- Obscuring model pricing differences
- Automatic escalation to expensive models without user consent

**Test:** Can a user answer these questions?
1. "How much will this 45-minute recording cost?"
2. "How much of my budget remains?"
3. "What's the cost difference between models?"
4. "What did I spend last month?"

---

### 1.3 Modular, Layered Architecture

**Principle:** Clear separation of concerns with well-defined boundaries.

**Layers:**
```
┌─────────────────────────────────────┐
│  Presentation Layer (UI)            │  User interaction
├─────────────────────────────────────┤
│  API Layer (FastAPI routes)         │  HTTP interface
├─────────────────────────────────────┤
│  Business Logic Layer               │  Transcription orchestration
├─────────────────────────────────────┤
│  Service Layer (Provider adapters)  │  Provider-specific implementations
├─────────────────────────────────────┤
│  Infrastructure Layer               │  Storage, auth, logging
└─────────────────────────────────────┘
```

**Why:**
- Testability (mock layers independently)
- Maintainability (change one layer without affecting others)
- Understandability (clear responsibilities)

**Implementation Requirements:**
- No UI logic in services
- No provider-specific code in API routes
- Business logic doesn't know about HTTP
- Services don't know about each other (dependency injection)

**Prohibited:**
- Skipping layers (UI directly calling provider)
- Mixing concerns (storage logic in transcription service)
- Circular dependencies

---

### 1.4 Extensibility Over Premature Optimization

**Principle:** Design for future capabilities without building them now.

**Why:**
- Requirements evolve (today: transcription, tomorrow: speaker ID, analysis)
- Building everything upfront wastes time
- But refactoring architectural choices is expensive
- "Hooks" enable future features without breaking changes

**Implementation Approach:**
- Design interfaces for future capabilities
- Stub out extension points
- Document where features will go
- Keep implementation simple, architecture flexible

**Examples:**
- Post-processing pipeline hook (for future audio analysis)
- Metadata extension points (for future speaker ID, sentiment, etc.)
- Provider capability negotiation (some providers have features others don't)

**Prohibited:**
- Building features "because we might need them"
- Architectural decisions that prevent known future requirements
- Ignoring stated future needs (e.g., "I'll want Whisper eventually")

---

### 1.5 Simple But Robust

**Principle:** Minimize complexity while maintaining production quality.

**Why:**
- User is product-minded, not dev-operations expert
- Fewer moving parts = fewer failure modes
- Debugging is easier with simpler systems
- But simple doesn't mean fragile

**Balanced Approach:**
- Simple: Single server, file-based config, local deployment
- Robust: Proper error handling, logging, recovery, monitoring

**Implementation:**
- Avoid microservices, distributed systems, complex orchestration
- Use well-tested libraries and patterns
- Comprehensive logging for debugging
- Graceful degradation (continue working when non-critical components fail)

**Prohibited:**
- Over-engineering for scale we don't have
- Sacrificing reliability for simplicity
- Ignoring edge cases and error handling

---

## 2. Layered Architecture Details

### 2.1 Configuration Layer

**Strategic Configuration** (defines what we use):
- `STT_PROVIDER` - Which transcription provider (google, whisper, etc.)

**Tactical Configuration** (how provider works):
- `GOOGLE_MODEL` - Which Google model (long, chirp_3, short)
- `GOOGLE_CLOUD_PROJECT` - Google project ID
- `GCS_BUCKET_NAME` - Cloud Storage bucket
- `GOOGLE_APPLICATION_CREDENTIALS` - Auth file path

**Naming Convention:**
- Strategic: `<CAPABILITY>_<SETTING>` (e.g., STT_PROVIDER)
- Tactical: `<PROVIDER>_<SETTING>` (e.g., GOOGLE_MODEL, WHISPER_DEVICE)

**Why This Matters:**
- Clearly distinguishes architectural choices from implementation details
- Prevents accidental removal of strategic config
- Makes provider-specific settings obvious

---

### 2.2 Service Layer Architecture

**Interface Contract** (all providers must implement):
```python
class TranscriptionService:
    """Base interface for all transcription providers."""

    def transcribe(self, audio: AudioInput) -> TranscriptionResult:
        """
        Transcribe audio to text.

        Returns standardized result regardless of provider.
        """
        pass
```

**Provider Implementations:**
- `GoogleSpeechV2Service` - Google Cloud Speech-to-Text V2
- `WhisperService` - OpenAI Whisper (future)
- `AssemblyAIService` - AssemblyAI (future)

**Why:**
- Swappable providers without changing business logic
- Consistent interface regardless of provider differences
- Easy to add new providers

**Provider-Specific Optimizations:**
Some providers have unique capabilities (speaker diarization, emotion detection, etc.). Handle via:
- Optional result fields (present only if provider supports them)
- Capability negotiation (query what provider supports)
- Feature flags in config

---

### 2.3 Data Flow

**Upload → Process → Return:**

```
User uploads file (UI)
    ↓
API validates file (main.py)
    ↓
Route to provider (based on STT_PROVIDER)
    ↓
Provider-specific processing:
  - Google: Upload to GCS → Batch recognize → Cleanup
  - Whisper: Direct transcription (future)
    ↓
Standardized result returned
    ↓
UI displays transcript
```

**Cost Estimation Flow:**

```
User selects file (UI)
    ↓
Detect duration (audio analyzer)
    ↓
Calculate cost (budget service)
    ↓
Display estimate (UI)
    ↓
User confirms
    ↓
Transcription proceeds
```

---

## 3. Provider-Specific Architectures

### 3.1 Google Cloud Speech-to-Text

**API Choice:** V2 Batch Recognition (not V1 synchronous)

**Why V2:**
- No 60-second limit (user has 75-minute classes)
- Better models (Chirp 3, Long Audio optimized)
- Speaker diarization support (future podcasts)
- V1 offers no advantages for this use case

**V1 Status:**
- Kept in codebase (app/services/transcribe_v1.py)
- Not exposed as user choice
- Available for emergency fallback or dev testing
- NOT part of the strategic architecture

**Implementation Pattern:**
```
Audio file → Cloud Storage → Batch API → Poll for results → Retrieve → Cleanup
```

**Dependencies:**
- Google Cloud Storage (for audio staging)
- Service account with Speech + Storage permissions
- GCS bucket in same project

**Cost Model (2025 Pricing):**
- **Standard Tier:** $0.016/min (all models including Chirp, Long, Short)
- **Dynamic Batch:** $0.004/min (75% discount, up to 24hr processing time)
- **Free Tier:** 60 min/month (shared across all models and tiers)

**Model Options:**
- **Long** (default) - Optimized for recordings >30 min (yoga classes, lectures)
- **Chirp** - Best accuracy, included at standard price (no premium)
- **Short** - Optimized for clips <30 sec
- All models available in Standard or Dynamic Batch pricing

---

### 3.2 Whisper (OpenAI API)

**Implementation Pattern:**
```
Audio file → OpenAI API → Return
```

**Cost Model (2025 Pricing):**
- **Whisper:** $0.006/min (flat rate)
- **GPT-4o Mini Transcribe:** $0.003/min (cost-sensitive option)
- **Free Tier:** $5 credit one-time (expires after 3 months, ~833 minutes at standard rate)

**Pricing Structure:**
- One-time credit (not monthly recurring like Google)
- After credit exhausted, pay full price forever
- No volume discounts
- Simpler model selection (fewer options than Google)

**When to implement:**
- User wants cost comparison
- After Google free tier exhausted (Whisper might be cheaper: $0.006 vs $0.016)
- Quality/accuracy testing
- Preference for OpenAI ecosystem

---

## 4. Cost Management Architecture

### 4.1 Budget Service (Phase 1B)

**Responsibilities:**
- Track usage against budget
- Calculate cost estimates
- Monitor free tier consumption
- Alert on thresholds
- Block when budget exceeded (optional)

**Storage:**
- JSON file (simple, single-user) - Phase 1B
- SQLite (multi-user, better queries) - Future
- Not cloud database (complexity not justified)

**Calculations:**
```
gross_cost = duration_minutes × model_rate
free_tier_credit = min(free_tier_remaining, gross_cost)
net_cost = gross_cost - free_tier_credit
```

**Alert Thresholds:**
- 80% of budget → Warning
- 100% of budget → Critical alert
- Optional: Block transcription when exceeded

---

### 4.2 Model Selection (Phase 1B)

**UI Component:**
- Radio buttons for model + pricing tier selection
- Cost per minute displayed (provider-specific)
- Estimated total cost for current file
- Budget remaining shown
- Free tier status (varies by provider)
- Default: Google Long Standard (recommended for user's use case)

**Provider Configurations:**
```python
PROVIDER_CONFIGS = {
    "google": {
        "name": "Google Cloud Speech-to-Text V2",
        "free_tier": {
            "type": "monthly_minutes",
            "amount": 60,
            "shared": True
        },
        "models": {
            "long_standard": {
                "name": "Long Audio (Standard)",
                "cost_per_min": 0.016,
                "processing_time": "~1-3 minutes",
                "recommended_for": ["yoga classes", "lectures", "long recordings"],
                "features": ["optimized_long_audio", "automatic_punctuation"]
            },
            "long_batch": {
                "name": "Long Audio (Dynamic Batch)",
                "cost_per_min": 0.004,
                "processing_time": "up to 24 hours",
                "recommended_for": ["non-urgent transcription", "cost optimization"],
                "features": ["optimized_long_audio", "75% cost savings"]
            },
            "chirp_standard": {
                "name": "Chirp (Standard)",
                "cost_per_min": 0.016,
                "processing_time": "~1-3 minutes",
                "recommended_for": ["best accuracy", "multi-speaker", "podcasts"],
                "features": ["best_accuracy", "speaker_diarization", "multilingual"]
            },
            "chirp_batch": {
                "name": "Chirp (Dynamic Batch)",
                "cost_per_min": 0.004,
                "processing_time": "up to 24 hours",
                "recommended_for": ["best accuracy with cost savings"],
                "features": ["best_accuracy", "speaker_diarization", "75% savings"]
            },
            "short_standard": {
                "name": "Short Audio (Standard)",
                "cost_per_min": 0.016,
                "processing_time": "~1-2 minutes",
                "recommended_for": ["clips under 30 seconds", "voice memos"],
                "features": ["optimized_short_clips"]
            }
        }
    },
    "whisper": {
        "name": "OpenAI Whisper",
        "free_tier": {
            "type": "dollar_credit",
            "amount": 5.00,
            "expires_days": 90
        },
        "models": {
            "whisper_standard": {
                "name": "Whisper",
                "cost_per_min": 0.006,
                "processing_time": "~30-60 seconds",
                "recommended_for": ["general transcription", "cost-effective"],
                "features": ["good_accuracy", "fast_processing"]
            },
            "gpt4o_mini": {
                "name": "GPT-4o Mini Transcribe",
                "cost_per_min": 0.003,
                "processing_time": "~30-60 seconds",
                "recommended_for": ["cost-sensitive applications"],
                "features": ["budget_friendly", "decent_accuracy"]
            }
        }
    }
}
```

---

## 5. Future Extensibility

### 5.1 Post-Processing Pipeline

**Current:** Transcription only

**Future:** Audio analysis, song recognition, mood detection, etc.

**Architecture Hook:**
```python
class PostProcessor:
    """Extension point for future audio analysis."""

    def process(self, audio: bytes, transcript: Transcript) -> Metadata:
        """Run additional analysis on audio."""
        pass

# In transcription flow:
result = transcription_service.transcribe(audio)
if ENABLE_POST_PROCESSING:
    metadata = post_processor.process(audio, result)
    result.metadata.update(metadata)
```

**Examples:**
- Speaker identification and separation
- Song/music detection (for workout classes)
- Ambient sound classification
- Sentiment/energy level detection
- Timestamp-based chapter detection

**Not Implemented Yet:** But architecture accommodates it.

---

### 5.2 Content Cockpit Integration

**Current Scope:** Standalone transcription service

**Future Scope:** Part of larger Content Cockpit

**Integration Points:**
- Library storage (where transcripts go)
- Semantic search (indexing transcripts)
- Content repurposing (clip extraction based on timestamps)
- Metadata enrichment (tags, categories from content)

**Design Requirement:** Transcription service should work standalone OR as component.

**Avoid:**
- Tight coupling to Content Cockpit
- Assuming Content Cockpit exists
- Preventing standalone use

---

### 5.3 Multi-User Support (Future)

**Current:** Single user (John)

**Future:** Potentially multi-user (other instructors?)

**Preparation:**
- Budget tracking per user
- Usage quotas
- Authentication/authorization
- Isolated storage

**Not Building Now:** But not making architectural choices that prevent it.

---

## 6. Decision-Making Framework

### 6.1 Before Removing Anything

**Ask:**
1. **Why was this here?** What architectural principle does it serve?
2. **What breaks if removed?** Not just now, but future capabilities?
3. **Is this strategic or tactical?** Strategic requires discussion, tactical can change.
4. **Did user explicitly mention this?** (e.g., "I'll want Whisper eventually")

**Example: STT_PROVIDER**
1. Why: Provider abstraction for flexibility
2. Breaks: Can't swap to Whisper without refactoring
3. Strategic (defines what we use)
4. User mentioned Whisper, cost concerns → needs flexibility

**Conclusion: Don't remove**

---

### 6.2 Before Adding Complexity

**Ask:**
1. **Is this needed now?** Or speculative future-proofing?
2. **Does it serve a stated requirement?** Or "might be nice"?
3. **Can we stub it instead?** Extension point vs full implementation?
4. **What's the maintenance cost?** More code = more to maintain

**Example: V1 vs V2 switching**
1. Not needed (user will never choose V1)
2. No requirement for it
3. Keep V1 file, don't expose as choice
4. Less code, simpler UX

**Conclusion: Don't expose V1 as user-facing option**

---

### 6.3 Strategic vs Tactical Checklist

| Element | Type | Can Change Without Discussion? |
|---------|------|-------------------------------|
| STT_PROVIDER | Strategic | ❌ No - defines provider abstraction |
| GOOGLE_MODEL | Tactical | ✅ Yes - Google implementation detail |
| Layered architecture | Strategic | ❌ No - core design principle |
| GCS bucket name | Tactical | ✅ Yes - infrastructure detail |
| Cost transparency | Strategic | ❌ No - user requirement |
| Model selection UI | Tactical | ✅ Yes - UX implementation |
| Provider interface | Strategic | ❌ No - enables swappability |
| Logging format | Tactical | ✅ Yes - operational detail |

---

## 7. Technology Choices (Current)

### 7.1 Backend

- **Framework:** FastAPI
  - Why: Modern, async, good docs, type hints
  - Tactical choice (could swap to Flask, Django)

- **Server:** Uvicorn
  - Why: ASGI server for FastAPI
  - Tactical choice

- **Python Version:** 3.12
  - Why: Modern features, long support
  - Tactical choice

### 7.2 Frontend

- **Technology:** Vanilla HTML/CSS/JavaScript
  - Why: Simple, no build step, no dependencies
  - Tactical choice (could add React later)

- **Design:** Single-page, drag-and-drop upload
  - Why: Simple UX, self-contained
  - Tactical choice

### 7.3 Infrastructure

- **Deployment:** Local (user's Mac)
  - Why: Simple, no hosting costs, good for single user
  - Strategic choice (aligns with "simple but robust")

- **Database:** None currently; JSON files for Phase 1B
  - Why: Avoid complexity, sufficient for single user
  - Tactical choice (can upgrade to SQLite later)

- **Authentication:** None (local-only, trusted user)
  - Why: Not needed for single-user local deployment
  - Tactical choice (required if exposing to network)

---

## 8. Quality Attributes

### 8.1 Accuracy (Primary)

**Target:** >95% word accuracy for yoga classes

**Approach:**
- Use best models available (Chirp 3 when budget allows)
- Custom vocabulary hints (Sanskrit terms, pose names)
- Compare providers (Google vs Whisper eventually)

**Measurement:**
- Manual review of sample transcripts
- Error rate tracking
- Vocabulary-specific accuracy (yoga terms)

---

### 8.2 Cost Efficiency (Primary)

**Target:** Stay within $250/month budget

**Approach:**
- Default to cheaper models (long vs chirp_3)
- Cost estimation before transcription
- Budget monitoring and alerts
- Provider comparison for cost/quality

**Measurement:**
- Monthly spend tracking
- Cost per minute by model
- Budget utilization percentage

---

### 8.3 Reliability (Secondary)

**Target:** >99% successful transcription (no data loss)

**Approach:**
- Comprehensive error handling
- Automatic retry with exponential backoff
- Cleanup on failure (no orphaned files)
- Detailed logging for debugging

**Measurement:**
- Success rate tracking
- Error type analysis
- Recovery time from failures

---

### 8.4 Performance (Secondary)

**Target:** <5 minutes processing time for 60-minute audio

**Approach:**
- Batch API (async processing)
- Progress indication in UI
- Efficient polling strategy

**Note:** Real-time not required (batch workflow expected)

---

## 9. Non-Functional Requirements

### 9.1 Security

**Current Posture:**
- Local deployment (not exposed to internet)
- Credentials in .env file (gitignored)
- Temporary files cleaned up after processing

**Future Considerations:**
- If multi-user: Add authentication
- If cloud-deployed: Add HTTPS, rate limiting, input sanitization

---

### 9.2 Privacy

**Approach:**
- Audio files deleted after transcription
- No persistent storage of audio (only transcripts)
- Cloud storage temporary (files deleted after processing)

**User Control:**
- User owns Google Cloud project (data residency)
- Can delete GCS bucket anytime
- Transcripts stored locally only

---

### 9.3 Maintainability

**Practices:**
- Type hints throughout
- Comprehensive docstrings
- Architectural documentation (this document)
- Clear separation of concerns
- Logging for observability

---

## 10. Open Questions & Future Decisions

### 10.1 Pending Decisions

1. **Multi-user support?**
   - When/if needed
   - Authentication approach
   - Budget allocation per user

2. **Whisper integration timeline?**
   - When to implement
   - Cost/quality comparison methodology
   - Migration strategy

3. **Cloud deployment?**
   - When/if needed (currently local)
   - Security implications
   - Hosting costs

4. **Advanced features priority?**
   - Speaker diarization (podcasts)
   - Audio analysis (song recognition)
   - Semantic search integration

### 10.2 Known Limitations

1. **Single user only** - No multi-tenancy
2. **Local deployment** - No remote access
3. **Manual budget tracking** - No automatic enforcement initially
4. **English only** - Though Chirp supports multilingual

---

## 11. Revision History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2025-11-08 | Initial architecture (V1 implementation) | Claude |
| 2.0 | 2025-11-09 | V2 upgrade, provider abstraction clarified | Claude + John |

---

## 12. How to Use This Document

### For Implementation Decisions:

1. **Before making changes:** Check if it affects strategic principles
2. **Proposing new features:** Map to architecture layers
3. **Choosing technologies:** Verify alignment with quality attributes
4. **Refactoring:** Ensure layered architecture maintained

### For Code Reviews:

1. **Does this change violate strategic principles?**
2. **Is separation of concerns maintained?**
3. **Are provider-specific details properly isolated?**
4. **Is cost transparency preserved?**

### For Onboarding (Human or AI):

1. **Read Core Design Principles first** (Section 1)
2. **Understand strategic vs tactical** (Section 6.3)
3. **Review decision-making framework** (Section 6)
4. **Check current implementation** (code + this doc)

---

## Appendix A: Configuration Quick Reference

### Your Current .env File Should Have:

```bash
# STRATEGIC
STT_PROVIDER=google

# TACTICAL (Google-specific)
GOOGLE_APPLICATION_CREDENTIALS=/Users/johncarosella/Documents/GitHub/credentials/google-cloud-key.json
GOOGLE_CLOUD_PROJECT=voice-to-text-dev
GCS_BUCKET_NAME=voice-to-text-audio-jc
GOOGLE_MODEL=long
```

### Don't Have (Removed):
- ~~STT_API_VERSION~~ - Not a strategic choice (user won't pick V1)
- ~~STT_MODEL~~ - Renamed to GOOGLE_MODEL (provider-specific)

---

**End of Architecture Document**

*This is a living document. Update as architectural decisions evolve.*
