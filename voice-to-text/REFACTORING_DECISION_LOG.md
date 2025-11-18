# Refactoring Decision Log
**Date:** 2025-11-17  
**Status:** In Progress  
**Approach:** Proceeding with approved recommendations, documenting all decisions and uncertainties

---

## Overview

This document tracks all architectural decisions, implementation choices, and uncertainties encountered during the refactoring process. All decisions are made assuming recommendations have been approved, but marked for review upon return.

---

## Completed Phases

### Phase 1: Pydantic Models ✅
**Status:** Complete and tested

**Decisions Made:**
- Created comprehensive Pydantic models for all request/response types
- Used Pydantic V2 syntax (`json_schema_extra` instead of `schema_extra`)
- Models include validation, type hints, and documentation
- Separated into logical modules: `requests.py`, `responses.py`, `job.py`

**Files Created:**
- `app/models/__init__.py`
- `app/models/requests.py`
- `app/models/responses.py`
- `app/models/job.py`

**Testing:**
- ✅ All model validation tests pass
- ✅ Type checking works correctly
- ✅ Invalid data properly rejected

**Uncertainties:**
- None - models are straightforward data structures

---

### Phase 2: TranscriptionOrchestrator ✅
**Status:** Complete and tested (structure)

**Decisions Made:**
- Extracted all business logic from `main.py` endpoints into `TranscriptionOrchestrator`
- Orchestrator handles: validation, upload, cost estimation, job submission, status checking, completion handling
- Uses factory pattern for transcription service creation (supports different models)
- Allowed file extensions and model mapping moved to class constants

**Files Created:**
- `app/services/orchestrator.py`

**Testing:**
- ✅ Structure tests pass
- ✅ Imports correctly
- ⚠️ Full functionality not tested (requires running server and services)

**Uncertainties:**
1. **Transcription Service Factory:** Currently requires passing `project_id` and `location` to factory. This means orchestrator needs these values. Is this the right abstraction, or should factory be pre-configured?
   - **Decision:** Pass factory function that takes all three params (project_id, model, location)
   - **Rationale:** More flexible, allows different models per request
   - **Review Needed:** Verify this doesn't create unnecessary service instances

2. **Test Mode Handling:** Orchestrator accepts test mode flags. Should this be in orchestrator or handled at a higher level?
   - **Decision:** Include in orchestrator for now (matches current pattern)
   - **Rationale:** Keeps test mode logic isolated
   - **Review Needed:** Consider if test mode should be a separate test orchestrator

3. **Error Handling:** Orchestrator raises `ValueError` for validation errors. Should these be custom exceptions?
   - **Decision:** Use `ValueError` for now (standard Python)
   - **Rationale:** Simple, clear, can be caught by API layer
   - **Review Needed:** Consider custom exceptions for better error categorization

---

## Completed Phases (Continued)

### Phase 3: Split main.py into Route Modules ✅
**Status:** Complete (structure created, integration pending)

**Decisions Made:**
- Created `/api/v1/` route structure with separate modules:
  - `jobs.py` - Job endpoints (list, status, delete)
  - `library.py` - Library endpoints (list, get, download, delete)
  - `budget.py` - Budget and pricing endpoints
  - `transcription.py` - Transcription submission and metadata detection
  - `errors.py` - Standardized error handlers
- Used FastAPI `APIRouter` for route organization
- All routes use Pydantic models for request/response validation

**Files Created:**
- `app/api/__init__.py`
- `app/api/v1/__init__.py`
- `app/api/v1/jobs.py`
- `app/api/v1/library.py`
- `app/api/v1/budget.py`
- `app/api/v1/transcription.py`
- `app/api/v1/errors.py`

**Testing:**
- ✅ Routes import successfully (15 routes registered)
- ⚠️ Full integration pending (orchestrator dependency injection)

**Uncertainties:**
1. **Orchestrator Dependency Injection:** How to properly inject orchestrator into routes?
   - **Decision:** Create dependency function in main.py that builds orchestrator with all services
   - **Rationale:** Centralized service initialization, clear dependencies
   - **Review Needed:** Verify this pattern works with FastAPI's dependency system

2. **Transcription/Status Endpoints:** Currently marked as `NotImplementedError` in route modules
   - **Decision:** Keep old implementation in main.py until orchestrator integration complete
   - **Rationale:** Don't break existing functionality during refactoring
   - **Review Needed:** Complete integration before removing old endpoints

---

### Phase 4: Standardized Error Response Format ✅
**Status:** Complete

**Decisions Made:**
- Created `ErrorResponse` Pydantic model
- Implemented three error handlers:
  - `http_exception_handler` - For HTTPException
  - `validation_exception_handler` - For Pydantic validation errors
  - `general_exception_handler` - For unexpected exceptions
- All errors include request_id for tracking
- Error codes mapped from HTTP status codes

**Files Created:**
- `app/api/v1/errors.py` (already created in Phase 3)

**Testing:**
- ✅ Error handlers import successfully
- ⚠️ Not yet registered with app (will be done in integration)

**Uncertainties:**
- None - error handling is straightforward

---

### Phase 5: Configuration Management ✅
**Status:** Complete and tested

**Decisions Made:**
- Created `Config` class with properties for all configuration
- Validates configuration on startup (fail fast)
- Separates strategic (provider) from tactical (provider-specific settings)
- Includes test mode configuration

**Files Created:**
- `app/config.py`

**Testing:**
- ✅ Config loads and validates successfully
- ✅ Properties work correctly

**Uncertainties:**
- None - configuration is straightforward

---

### Phase 6: Cost Calculation Service ✅
**Status:** Complete and tested

**Decisions Made:**
- Extracted cost calculation logic from main.py
- Service uses PricingService and BudgetService
- Handles billed duration, free tier, and fallbacks
- Returns structured cost breakdown

**Files Created:**
- `app/services/cost_calculation.py`

**Testing:**
- ✅ Service loads successfully
- ⚠️ Full functionality not tested (requires actual job completion)

**Uncertainties:**
- None - service is straightforward extraction

---

### Phase 7: Storage Adapter Interface ✅
**Status:** Complete

**Decisions Made:**
- Created Protocol-based interfaces (structural typing)
- Defined three adapters:
  - `JobStorageAdapter` - Job operations
  - `LibraryStorageAdapter` - Library operations
  - `TranscriptStorageAdapter` - Transcript file operations
- Current services (JobStorageService, LibraryService) can implement these protocols
- No changes to existing services required (they already match the interface)

**Files Created:**
- `app/services/storage/__init__.py`
- `app/services/storage/adapter.py`

**Testing:**
- ✅ Interfaces import successfully
- ⚠️ Not yet enforced (services don't explicitly implement protocols yet)

**Uncertainties:**
1. **Protocol Enforcement:** Should we make services explicitly implement protocols?
   - **Decision:** Not required - structural typing works without explicit implementation
   - **Rationale:** Less code, same type safety
   - **Review Needed:** Verify mypy/pyright can check protocol conformance

---

## In Progress

### Phase 8: Integration into main.py
**Status:** Partially Complete

**Decisions Made:**
- Created `app/dependencies.py` with dependency injection functions
- Updated route modules to use orchestrator via dependencies
- Routes are ready but not yet integrated into main.py

**Files Created:**
- `app/dependencies.py` - Dependency injection functions

**Files Modified:**
- `app/api/v1/jobs.py` - Uses orchestrator for status checking
- `app/api/v1/transcription.py` - Uses orchestrator for submission

**Testing:**
- ✅ Dependencies import successfully
- ✅ Routes import successfully
- ⚠️ Not yet integrated into main.py

**Uncertainties:**
1. **Backward Compatibility:** Should we keep old endpoints or update frontend?
   - **Decision:** Keep old endpoints working for now (smooth transition)
   - **Rationale:** Don't break existing functionality
   - **Review Needed:** Decide when to remove old endpoints

2. **API Path Migration:** How to handle `/api/` vs `/api/v1/`?
   - **Decision:** Keep both paths working initially
   - **Rationale:** Allows gradual migration
   - **Review Needed:** Plan for removing old paths

**Remaining Work:**
1. Integrate API router into main.py
2. Register error handlers
3. Update main.py to use Config class
4. Test server startup
5. Test all endpoints

**Planned Structure:**
```
app/
  api/
    v1/
      __init__.py
      jobs.py          # Job endpoints
      library.py       # Library endpoints
      budget.py        # Budget endpoints
      transcription.py  # Transcription endpoints
      errors.py        # Error handlers
  main.py              # FastAPI app setup only
```

**Decisions to Make:**
1. **API Versioning:** Use `/api/v1/` prefix for all API endpoints?
   - **Decision:** Yes - standardizes API, allows future v2
   - **Rationale:** Best practice, enables versioning
   - **Review Needed:** Confirm this doesn't break existing UI/frontend

2. **UI Routes:** Keep `/`, `/jobs`, `/library` as separate routes or move to `/static/`?
   - **Decision:** Keep as routes in main.py (they're just serving HTML)
   - **Rationale:** Simple, no need to change
   - **Review Needed:** None - this is fine

3. **Route Organization:** Group by resource (jobs, library) or by operation (get, post)?
   - **Decision:** Group by resource (RESTful)
   - **Rationale:** More intuitive, easier to find endpoints
   - **Review Needed:** None - standard REST pattern

**Uncertainties:**
1. **Dependency Injection:** How to pass orchestrator/services to route handlers?
   - **Decision:** Use FastAPI `Depends()` for dependency injection
   - **Rationale:** FastAPI best practice, testable
   - **Review Needed:** Verify this works with our service initialization pattern

2. **Service Initialization:** Where should services be initialized? In main.py startup or in dependency functions?
   - **Decision:** Initialize in main.py startup, pass via dependencies
   - **Rationale:** Single initialization point, clear lifecycle
   - **Review Needed:** Verify this doesn't cause issues with async/threading

---

### Phase 4: Standardized Error Response Format
**Status:** Planned

**Decisions to Make:**
1. **Error Format:** Use the ErrorResponse model we created?
   - **Decision:** Yes - consistent with Pydantic models
   - **Rationale:** Type-safe, documented, consistent
   - **Review Needed:** Verify error codes match what frontend expects

2. **Error Middleware:** Use FastAPI exception handlers or custom middleware?
   - **Decision:** Use exception handlers (simpler, more explicit)
   - **Rationale:** FastAPI built-in, easier to understand
   - **Review Needed:** None - standard approach

**Uncertainties:**
1. **Request ID:** How to generate request IDs? UUID? Sequential?
   - **Decision:** Use UUID for now
   - **Rationale:** Unique, no coordination needed
   - **Review Needed:** Consider if sequential IDs would be better for debugging

2. **Error Logging:** Should all errors be logged in middleware or in handlers?
   - **Decision:** Log in handlers (more context)
   - **Rationale:** Handlers have more context about what failed
   - **Review Needed:** Consider if middleware logging would catch unhandled errors better

---

### Phase 5: Configuration Management
**Status:** Planned

**Decisions to Make:**
1. **Config Class:** Single Config class or separate classes per concern?
   - **Decision:** Single Config class with sections
   - **Rationale:** Simpler, all config in one place
   - **Review Needed:** Consider if separate classes would be clearer

2. **Validation:** Validate all config on startup or lazy validation?
   - **Decision:** Validate on startup (fail fast)
   - **Rationale:** Catch errors early, before serving requests
   - **Review Needed:** None - this is correct

**Uncertainties:**
1. **Test Mode:** Should test mode config be in main Config class or separate?
   - **Decision:** Include in main Config but clearly marked
   - **Rationale:** Keeps all config together
   - **Review Needed:** Consider if test config should be completely separate

2. **Provider Config:** Should provider-specific config be nested or flat?
   - **Decision:** Nested (e.g., `config.google.bucket_name`)
   - **Rationale:** Clearer organization, easier to extend
   - **Review Needed:** Verify this doesn't complicate access patterns

---

### Phase 6: Cost Calculation Service
**Status:** Planned

**Decisions to Make:**
1. **Service Location:** New service or method in existing service?
   - **Decision:** New `CostCalculationService`
   - **Rationale:** Single responsibility, testable
   - **Review Needed:** Verify this doesn't duplicate logic with PricingService

2. **Method Signature:** What should the service calculate?
   - **Decision:** Calculate actual cost from billed duration, free tier, model
   - **Rationale:** Matches current logic in main.py
   - **Review Needed:** Verify this matches business requirements

**Uncertainties:**
1. **Service Dependencies:** Does CostCalculationService need PricingService and BudgetService?
   - **Decision:** Yes - needs pricing for rates, budget for free tier
   - **Rationale:** Clear dependencies
   - **Review Needed:** Consider if this creates circular dependencies

---

### Phase 7: Storage Adapter Interface
**Status:** Planned

**Decisions to Make:**
1. **Interface Type:** Protocol or ABC?
   - **Decision:** Use `Protocol` (structural typing)
   - **Rationale:** More flexible, no inheritance required
   - **Review Needed:** Verify this works with existing services

2. **Migration Strategy:** Implement adapter now or just define interface?
   - **Decision:** Define interface, implement JSON adapter (current implementation)
   - **Rationale:** Prepares for future DB migration without breaking current code
   - **Review Needed:** Verify this doesn't add unnecessary abstraction

**Uncertainties:**
1. **Service Refactoring:** Should existing services implement adapter or wrap?
   - **Decision:** Services implement adapter interface
   - **Rationale:** Cleaner, no wrapper layer
   - **Review Needed:** Verify this doesn't require major refactoring of JobStorage/LibraryService

---

## Testing Strategy

### What I Can Test
- ✅ Pydantic model validation
- ✅ Import/export structure
- ✅ Type checking (can run mypy)
- ✅ Basic syntax/import errors

### What Requires Your Testing
- ⚠️ Full API endpoint functionality
- ⚠️ Service integration
- ⚠️ End-to-end workflows
- ⚠️ Error handling in real scenarios
- ⚠️ UI functionality

### Test Files Created
- `tests/test_refactoring_models.py` - Model validation tests
- `tests/test_refactoring_orchestrator.py` - Orchestrator structure tests

---

## Architecture Decisions

### Decision: API Versioning
**Choice:** Use `/api/v1/` prefix for all API endpoints  
**Rationale:** Standard practice, enables future versioning  
**Impact:** May require frontend updates  
**Review Needed:** Verify UI can handle new paths

### Decision: Route Organization
**Choice:** Group by resource (RESTful)  
**Rationale:** Intuitive, standard pattern  
**Impact:** None - internal organization  
**Review Needed:** None

### Decision: Dependency Injection
**Choice:** Use FastAPI `Depends()`  
**Rationale:** FastAPI best practice, testable  
**Impact:** Changes how services are passed to handlers  
**Review Needed:** Verify this works with our service pattern

### Decision: Error Handling
**Choice:** Exception handlers + ErrorResponse model  
**Rationale:** Consistent, type-safe  
**Impact:** All errors return same format  
**Review Needed:** Verify error codes match frontend expectations

---

## Uncertainties & Questions for Review

### High Priority
1. **API Path Changes:** Moving to `/api/v1/` may break frontend. Should we:
   - Keep old paths and redirect?
   - Update frontend simultaneously?
   - Use feature flag?

2. **Service Initialization:** Current services use module-level singletons. With dependency injection:
   - Should we keep singletons?
   - Or create new instances per request?
   - Or use FastAPI's dependency system?

3. **Orchestrator Factory:** Transcription service factory pattern - is this the right abstraction?
   - Current: Factory takes (project_id, model, location)
   - Alternative: Pre-configured factory with project_id/location
   - Which is better for our use case?

### Medium Priority
4. **Test Mode:** Should test mode be in orchestrator or separate test orchestrator?
5. **Error Codes:** What error codes should we use? Standardize with frontend?
6. **Request IDs:** UUID vs sequential - which is better for debugging?

### Low Priority
7. **Config Organization:** Single class vs separate classes?
8. **Storage Adapter:** Implement now or just define interface?

---

## Implementation Notes

### Code Quality
- All code follows existing patterns
- Type hints throughout
- Comprehensive docstrings
- Error handling included

### Backward Compatibility
- ⚠️ API path changes may break frontend (needs testing)
- ✅ Models are additive (don't break existing code)
- ✅ Orchestrator is new (doesn't affect existing code yet)

### Performance
- No performance impact expected
- Models add minimal overhead (<1ms per request)
- Orchestrator adds one function call layer

---

## Next Steps

1. Continue with Phase 3 (Route modules)
2. Implement Phase 4 (Error handling)
3. Create Phase 5 (Configuration)
4. Extract Phase 6 (Cost calculation)
5. Define Phase 7 (Storage adapter)
6. Integrate everything into main.py
7. Create comprehensive test script for user
8. Document all changes

---

## Review Checklist for Return

- [ ] Review all decisions marked "Review Needed"
- [ ] Test API path changes with frontend
- [ ] Verify service initialization pattern
- [ ] Test full end-to-end workflow
- [ ] Check error handling in real scenarios
- [ ] Verify performance is acceptable
- [ ] Review code quality and organization
- [ ] Check for any breaking changes

---

**Last Updated:** 2025-11-17  
**Next Update:** After each phase completion

