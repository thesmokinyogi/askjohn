# Refactored System Testing Plan

## Overview

This document outlines comprehensive testing for the refactored system. The refactoring introduced:
- New `/api/v1/` endpoints (15 routes)
- `TranscriptionOrchestrator` service
- Pydantic models for validation
- Standardized error handling
- Configuration management
- Cost calculation service

## Test Categories

### 0. Unit Testing (Architectural Boundaries)
### 1. API Endpoint Testing
### 2. End-to-End Workflow Testing
### 3. Error Handling Testing
### 4. Backward Compatibility Testing
### 5. UI Integration Testing
### 6. Service Integration Testing
### 7. Server Startup & Initialization Testing
### 8. Performance Testing

---

## 0. Unit Testing (Architectural Boundaries)

### 0.1 Pydantic Model Testing

**Purpose:** Test request/response models independently to verify validation boundaries.

#### Request Models (`app/models/requests.py`)

**Test Cases:**
- [ ] `TranscribeRequest` with valid model → Accepts
- [ ] `TranscribeRequest` with invalid model → Rejects with validation error
- [ ] `TranscribeRequest` with None model → Accepts (optional)
- [ ] `EstimateCostRequest` with valid data → Accepts
- [ ] `EstimateCostRequest` with negative duration → Rejects
- [ ] `EstimateCostRequest` with zero duration → Rejects
- [ ] `EstimateProcessingTimeRequest` with valid data → Accepts
- [ ] `EstimateProcessingTimeRequest` with invalid model → Rejects

**Test Commands:**
```python
# Example test
from app.models.requests import TranscribeRequest
from pydantic import ValidationError

# Valid
req = TranscribeRequest(model="chirp_batch")

# Invalid
try:
    req = TranscribeRequest(model="invalid_model")
except ValidationError as e:
    # Verify error structure
    pass
```

#### Response Models (`app/models/responses.py`)

**Test Cases:**
- [ ] `TranscriptionJobResponse` serialization → Valid JSON
- [ ] `JobStatusResponse` with all fields → Valid JSON
- [ ] `JobStatusResponse` with None fields → Valid JSON
- [ ] `BudgetSummaryResponse` with multiple providers → Valid JSON
- [ ] `ErrorResponse` structure → Valid error format
- [ ] `SuccessResponse` structure → Valid success format

#### Job Domain Model (`app/models/job.py`)

**Test Cases:**
- [ ] `JobModel` with all required fields → Accepts
- [ ] `JobModel` with optional fields → Accepts
- [ ] `JobStatus` enum values → Valid
- [ ] `JobModel` with invalid status → Rejects
- [ ] `JobModel` serialization → Valid JSON

**Test Script:**
```bash
python -m pytest tests/test_models.py -v
```

---

### 0.2 Orchestrator Method Testing

**Purpose:** Test TranscriptionOrchestrator methods directly to verify business logic boundaries.

#### `map_model_name()` Method

**Test Cases:**
- [ ] `chirp_batch` → Returns `('chirp', 'chirp_batch', 'batch')`
- [ ] `chirp_standard` → Returns `('chirp', 'chirp_standard', 'standard')`
- [ ] `long_batch` → Returns `('long', 'long_batch', 'batch')`
- [ ] `long_standard` → Returns `('long', 'long_standard', 'standard')`
- [ ] `None` → Uses default model
- [ ] Unknown model → Falls back to default

#### `validate_file()` Method

**Test Cases:**
- [ ] Valid file extension → Accepts
- [ ] Invalid file extension → Raises ValueError
- [ ] File too large → Raises ValueError
- [ ] File within size limit → Accepts

#### `submit_transcription()` Method

**Test Cases:**
- [ ] Valid file → Creates job, returns job_id
- [ ] Invalid file → Raises ValueError
- [ ] File upload failure → Handles error correctly
- [ ] Cost estimation → Calculates correctly
- [ ] Job submission → Returns operation
- [ ] Tier extraction → Stores tier correctly

#### `check_job_status()` Method

**Test Cases:**
- [ ] Queued job → Returns queued status
- [ ] Processing job → Sets processing_started_at
- [ ] Complete job → Calculates costs, updates budget, adds to library
- [ ] Failed job → Handles error correctly
- [ ] Invalid job_id → Handles error correctly

#### Factory Pattern Testing

**Test Cases:**
- [ ] Factory creates correct service type
- [ ] Factory with different models → Creates appropriate service
- [ ] Factory with different locations → Creates appropriate service
- [ ] Factory service has correct configuration

**Test Script:**
```bash
python -m pytest tests/test_orchestrator.py -v
```

---

### 0.3 Cost Calculation Service Testing

**Purpose:** Test CostCalculationService independently to verify cost calculation boundary.

#### `calculate_actual_cost()` Method

**Test Cases:**
- [ ] All free (duration < free_remaining) → $0.00 cost
- [ ] Part free, part paid → Correct split
- [ ] All paid (free exhausted) → Full cost
- [ ] Zero free remaining → All billable
- [ ] Different models → Uses correct rate
- [ ] Missing billed_duration → Falls back to estimated
- [ ] Missing pricing → Uses estimated cost
- [ ] Negative cost calculation → Handles gracefully

**Test Scenarios:**
```python
# Scenario 1: All free
result = cost_service.calculate_actual_cost(
    provider="google",
    model="chirp_batch",
    billed_duration_minutes=2.0,
    estimated_duration_minutes=2.0
)
# Expected: actual_cost=0.0, actual_free_minutes_used=2.0

# Scenario 2: Transition (part free, part paid)
result = cost_service.calculate_actual_cost(
    provider="google",
    model="chirp_batch",
    billed_duration_minutes=5.0,
    estimated_duration_minutes=5.0
)
# With 3.82 free remaining:
# Expected: actual_cost=0.0047, actual_free_minutes_used=3.82, actual_billable_minutes=1.18

# Scenario 3: All paid
result = cost_service.calculate_actual_cost(
    provider="google",
    model="chirp_batch",
    billed_duration_minutes=5.0,
    estimated_duration_minutes=5.0
)
# With 0 free remaining:
# Expected: actual_cost=0.02, actual_free_minutes_used=0.0, actual_billable_minutes=5.0
```

**Test Script:**
```bash
python tests/test_free_tier_transition.py  # Already exists
python -m pytest tests/test_cost_calculation.py -v
```

---

### 0.4 Configuration Management Testing

**Purpose:** Test Config class to verify configuration boundary and fail-fast behavior.

#### Config Initialization

**Test Cases:**
- [ ] Config loads from environment variables → All properties accessible
- [ ] Config with all required fields → Initializes successfully
- [ ] Config with missing required field → Raises error (fail-fast)
- [ ] Config with invalid value → Raises error (fail-fast)
- [ ] Config with optional fields missing → Uses defaults
- [ ] `get_config()` returns singleton → Same instance

#### Config Properties

**Test Cases:**
- [ ] `stt_provider` → Returns correct value
- [ ] `google_model` → Returns correct value
- [ ] `gcs_bucket_name` → Returns correct value
- [ ] `google_cloud_project` → Returns correct value
- [ ] `monthly_budget` → Returns correct value
- [ ] `max_file_size_mb` → Returns correct value
- [ ] `test_mode_skip_upload` → Returns correct value

#### Config Validation

**Test Cases:**
- [ ] Invalid provider → Raises ValueError
- [ ] Invalid model → Raises ValueError (if validated)
- [ ] Missing GCS bucket → Raises ValueError
- [ ] Missing project ID → Raises ValueError
- [ ] Invalid budget → Raises ValueError (if validated)

#### Config Methods

**Test Cases:**
- [ ] `validate()` method → Validates all required fields
- [ ] `validate()` with missing fields → Raises ValueError
- [ ] `validate()` with invalid values → Raises ValueError
- [ ] `to_dict()` method → Returns dict with all properties
- [ ] `to_dict()` serialization → Valid JSON structure

#### Config in Dependency Injection

**Test Cases:**
- [ ] `get_app_config()` used in dependencies → Works correctly
- [ ] Config passed to services → Services initialized correctly
- [ ] Config changes don't affect existing services → Services use initial config
- [ ] `reset_config()` function → Resets singleton (for testing)

**Test Script:**
```bash
python -m pytest tests/test_config.py -v
```

**Manual Test:**
```bash
# Test fail-fast behavior
unset GOOGLE_CLOUD_PROJECT
uvicorn app.main:app
# Should fail immediately with clear error

# Test validate() method
python -c "
from app.config import Config, get_config
config = get_config()
config.validate()  # Should not raise if valid
"
```

---

## 1. API Endpoint Testing

### 1.1 Transcription Endpoints (`/api/v1/transcription`)

#### POST `/api/v1/transcribe`
**Test Cases:**
- [ ] Submit valid audio file → Returns job_id, status "queued"
- [ ] Submit with model parameter → Uses specified model
- [ ] Submit without model → Uses default model
- [ ] Submit invalid file type → Returns 400 error
- [ ] Submit file too large → Returns 400 error
- [ ] Verify tier is extracted and stored correctly

**Test Command:**
```bash
curl -X POST http://localhost:8000/api/v1/transcribe \
  -F "file=@test_audio.mp3" \
  -F "model=chirp_batch" | jq
```

#### POST `/api/v1/detect-duration`
**Test Cases:**
- [ ] Valid audio file → Returns duration, format, metadata
- [ ] Invalid file → Returns 400 error
- [ ] Unsupported format → Returns appropriate error

**Test Command:**
```bash
curl -X POST http://localhost:8000/api/v1/detect-duration \
  -F "file=@test_audio.mp3" | jq
```

### 1.2 Jobs Endpoints (`/api/v1/jobs`)

#### GET `/api/v1/jobs`
**Test Cases:**
- [ ] List all jobs → Returns job list with stats
- [ ] Filter by status → Returns filtered jobs
- [ ] Limit parameter → Respects limit
- [ ] Verify tier field included in response

**Test Command:**
```bash
curl http://localhost:8000/api/v1/jobs | jq '.jobs[] | {job_id, model, tier, status}'
```

#### GET `/api/v1/jobs/{job_id}/status`
**Test Cases:**
- [ ] Valid job_id → Returns job status
- [ ] Queued job → Returns "queued" status
- [ ] Processing job → Returns "processing" status
- [ ] Complete job → Returns transcript, confidence, cost
- [ ] Failed job → Returns error message
- [ ] Invalid job_id → Returns 404 error

**Test Command:**
```bash
curl http://localhost:8000/api/v1/jobs/PROJECT_ID/locations/LOCATION/operations/OP_ID/status | jq
```

#### DELETE `/api/v1/jobs/{job_id}`
**Test Cases:**
- [ ] Valid job_id → Deletes job, returns success
- [ ] Invalid job_id → Returns 404 error
- [ ] Verify job removed from list

**Test Command:**
```bash
curl -X DELETE http://localhost:8000/api/v1/jobs/PROJECT_ID/locations/LOCATION/operations/OP_ID | jq
```

### 1.3 Library Endpoints (`/api/v1/library`)

#### GET `/api/v1/library`
**Test Cases:**
- [ ] List all entries → Returns library entries
- [ ] Verify transcript and words included
- [ ] Verify metadata included

**Test Command:**
```bash
curl http://localhost:8000/api/v1/library | jq '.entries[0] | {library_id, filename, transcript, words}'
```

#### GET `/api/v1/library/{library_id}`
**Test Cases:**
- [ ] Valid library_id → Returns entry details
- [ ] Invalid library_id → Returns 404 error

#### GET `/api/v1/library/{library_id}/download/text`
**Test Cases:**
- [ ] Valid library_id → Returns transcript as text
- [ ] Invalid library_id → Returns 404 error

#### GET `/api/v1/library/{library_id}/download/json`
**Test Cases:**
- [ ] Valid library_id → Returns transcript as JSON
- [ ] Invalid library_id → Returns 404 error

#### DELETE `/api/v1/library/{library_id}`
**Test Cases:**
- [ ] Valid library_id → Deletes entry
- [ ] Invalid library_id → Returns 404 error

### 1.4 Budget Endpoints (`/api/v1/budget`)

#### GET `/api/v1/budget`
**Test Cases:**
- [ ] Returns budget summary for all providers
- [ ] Includes free tier info for Google
- [ ] Includes credit info for Whisper
- [ ] Shows correct totals and counts

**Test Command:**
```bash
curl http://localhost:8000/api/v1/budget | jq '.providers.google'
```

#### GET `/api/v1/pricing`
**Test Cases:**
- [ ] Returns pricing for all providers
- [ ] Includes model details, rates, features

#### GET `/api/v1/pricing/{provider}`
**Test Cases:**
- [ ] Valid provider → Returns provider pricing
- [ ] Invalid provider → Returns 404 error

#### POST `/api/v1/estimate-cost`
**Test Cases:**
- [ ] Valid request → Returns cost estimate
- [ ] With free tier remaining → Shows free/billable breakdown
- [ ] Without free tier → Shows all billable
- [ ] Invalid model → Returns 400 error

**Test Command:**
```bash
curl -X POST http://localhost:8000/api/v1/estimate-cost \
  -H "Content-Type: application/json" \
  -d '{"provider": "google", "model": "chirp_batch", "duration_minutes": 5.0}' | jq
```

#### GET `/api/v1/estimate-processing-time`
**Test Cases:**
- [ ] Valid model and duration → Returns time estimate
- [ ] Invalid model → Returns 400 error
- [ ] Returns confidence, R², sample count

**Test Command:**
```bash
curl "http://localhost:8000/api/v1/estimate-processing-time?model=chirp_batch&duration_minutes=5.0" | jq
```

---

## 2. End-to-End Workflow Testing

### 2.1 Complete Transcription Workflow

**Test Sequence:**
1. [ ] **Detect Duration**
   ```bash
   curl -X POST http://localhost:8000/api/v1/detect-duration -F "file=@test.mp3"
   ```

2. [ ] **Estimate Cost**
   ```bash
   curl -X POST http://localhost:8000/api/v1/estimate-cost \
     -H "Content-Type: application/json" \
     -d '{"provider": "google", "model": "chirp_batch", "duration_minutes": 5.0}'
   ```

3. [ ] **Submit Transcription**
   ```bash
   curl -X POST http://localhost:8000/api/v1/transcribe \
     -F "file=@test.mp3" \
     -F "model=chirp_batch"
   ```
   - Verify job_id returned
   - Verify tier stored correctly

4. [ ] **Check Status** (poll until complete)
   ```bash
   curl http://localhost:8000/api/v1/jobs/{job_id}/status
   ```
   - Verify status transitions: queued → processing → complete
   - Verify processing_started_at is set
   - Verify actual_cost calculated correctly
   - Verify free tier updated correctly

5. [ ] **Verify in Jobs List**
   ```bash
   curl http://localhost:8000/api/v1/jobs
   ```
   - Verify job appears in list
   - Verify tier field present
   - Verify cost, confidence, status correct

6. [ ] **Verify in Library**
   ```bash
   curl http://localhost:8000/api/v1/library
   ```
   - Verify entry added to library
   - Verify transcript and words included
   - Verify metadata correct

7. [ ] **Verify Budget Updated**
   ```bash
   curl http://localhost:8000/api/v1/budget
   ```
   - Verify free tier decremented (if applicable)
   - Verify total_cost increased
   - Verify transcription_count increased

### 2.2 Multiple Models Workflow

**Test with different models:**
- [ ] `chirp_batch` → Verify tier="batch", correct pricing
- [ ] `chirp_standard` → Verify tier="standard", correct pricing
- [ ] `long_batch` → Verify tier="batch", correct pricing
- [ ] `long_standard` → Verify tier="standard", correct pricing

---

## 3. Error Handling Testing

### 3.1 Validation Errors

**Test Cases:**
- [ ] Invalid file type → Returns 400 with error details
- [ ] File too large → Returns 400 with error details
- [ ] Missing required fields → Returns 422 validation error
- [ ] Invalid model name → Returns 400/422 error
- [ ] Invalid job_id format → Returns 404 error

**Verify:**
- Error response includes `error` object
- Error includes `code`, `message`, `details`
- Error includes `request_id` for tracking

### 3.2 Service Errors

**Test Cases:**
- [ ] GCS upload failure → Returns appropriate error
- [ ] Transcription service error → Returns error with details
- [ ] Budget service error → Returns error with details
- [ ] Storage service error → Returns error with details

### 3.3 Standardized Error Format

**Verify all errors return:**
```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable message",
    "details": {},
    "request_id": "req_..."
  }
}
```

### 3.4 Error Handler Integration Testing

**Purpose:** Test that errors flow through handlers correctly and handlers are properly registered.

#### Error Handler Registration

**Test Cases:**
- [ ] Error handlers registered with FastAPI app → Verify in app setup
- [ ] HTTPException handler registered → Test with HTTPException
- [ ] ValidationException handler registered → Test with Pydantic validation error
- [ ] GeneralException handler registered → Test with unexpected exception

#### Error Flow Testing

**Test Cases:**
- [ ] HTTPException raised → Caught by `http_exception_handler`
  ```bash
  # Trigger 404 error
  curl http://localhost:8000/api/v1/jobs/invalid-id/status
  # Verify: Error response has standardized format
  ```
- [ ] Pydantic ValidationError → Caught by `validation_exception_handler`
  ```bash
  # Send invalid request
  curl -X POST http://localhost:8000/api/v1/estimate-cost \
    -H "Content-Type: application/json" \
    -d '{"invalid": "data"}'
  # Verify: Error response has standardized format with validation details
  ```
- [ ] Unexpected exception → Caught by `general_exception_handler`
  ```bash
  # This would require simulating a service failure
  # Verify: Error response has standardized format, doesn't expose internals
  ```

#### Request ID Generation

**Test Cases:**
- [ ] Each error includes unique request_id → Verify uniqueness
- [ ] Request ID format correct → Verify format (e.g., "req_...")
- [ ] Request ID in logs → Verify correlation between error and logs

#### Error Code Mapping

**Test Cases:**
- [ ] 400 Bad Request → Error code "BAD_REQUEST"
- [ ] 404 Not Found → Error code "NOT_FOUND"
- [ ] 422 Validation Error → Error code "VALIDATION_ERROR"
- [ ] 500 Internal Error → Error code "INTERNAL_ERROR"

**Test Script:**
```bash
# Test error handler registration
python -c "from app.main import app; print([h.__name__ for h in app.exception_handlers.values()])"

# Test error responses
curl -X POST http://localhost:8000/api/v1/estimate-cost \
  -H "Content-Type: application/json" \
  -d '{}' | jq '.error'
```

---

## 4. Backward Compatibility Testing

### 4.1 Old Endpoints Still Work

**Test old `/api/` endpoints:**
- [ ] `POST /api/transcribe` → Still works
- [ ] `GET /api/jobs` → Still works
- [ ] `GET /api/jobs/{job_id}/status` → Still works
- [ ] `GET /api/budget` → Still works
- [ ] `GET /api/config` → Still works

**Verify:**
- Old endpoints return same format
- Old endpoints still functional
- No breaking changes

### 4.2 Frontend Compatibility

**Test UI pages:**
- [ ] `/static/index.html` → Transcription page works
- [ ] `/static/jobs.html` → Jobs page works
- [ ] `/static/library.html` → Library page works

**Verify:**
- UI can submit transcriptions
- UI can check job status
- UI displays jobs correctly
- UI displays library correctly
- UI displays budget correctly

---

## 5. UI Integration Testing

### 5.1 Transcription Page (`/static/index.html`)

**Test Cases:**
- [ ] File upload works
- [ ] Model selection works
- [ ] Cost estimation displays correctly
- [ ] Submit transcription works
- [ ] Status polling works
- [ ] Results display correctly
- [ ] Confidence displays correctly (including N/A for Chirp)
- [ ] Budget display shows correct info
- [ ] Processing time estimate displays

### 5.2 Jobs Page (`/static/jobs.html`)

**Test Cases:**
- [ ] Jobs list loads
- [ ] Status filtering works
- [ ] Job details display correctly
- [ ] Confidence displays (including N/A)
- [ ] Delete job works
- [ ] Processing time estimate displays

### 5.3 Library Page (`/static/library.html`)

**Test Cases:**
- [ ] Library list loads
- [ ] Entry details display correctly
- [ ] Download text works
- [ ] Download JSON works
- [ ] Delete entry works
- [ ] Refresh button works
- [ ] Filename wrapping works

---

## 6. Service Integration Testing

### 6.1 Orchestrator Service

**Test Cases:**
- [ ] `submit_transcription()` → Creates job correctly
- [ ] `check_job_status()` → Updates status correctly
- [ ] `check_job_status()` → Sets processing_started_at
- [ ] `check_job_status()` → Handles completion correctly
- [ ] `check_job_status()` → Calculates costs correctly
- [ ] `check_job_status()` → Updates budget correctly
- [ ] `check_job_status()` → Adds to library correctly

**Service Coordination Testing:**
- [ ] Orchestrator coordinates storage service → Upload works
- [ ] Orchestrator coordinates pricing service → Cost estimation works
- [ ] Orchestrator coordinates budget service → Budget updates work
- [ ] Orchestrator coordinates job storage → Job records created
- [ ] Orchestrator coordinates library service → Library entries added
- [ ] Orchestrator coordinates processing time service → Time tracking works
- [ ] Orchestrator coordinates cost calculation service → Costs calculated correctly

**Factory Pattern Testing:**
- [ ] Transcription service factory creates correct service type
- [ ] Factory with different models → Creates appropriate service
- [ ] Factory service initialized with correct parameters
- [ ] Factory service can be used for transcription

### 6.2 Cost Calculation Service

**Test Cases:**
- [ ] Calculates free tier correctly
- [ ] Calculates billable minutes correctly
- [ ] Uses correct pricing rate
- [ ] Handles edge cases (zero free, all free, etc.)

**Service Integration Testing:**
- [ ] CostCalculationService uses PricingService → Gets correct rates
- [ ] CostCalculationService uses BudgetService → Gets free tier info
- [ ] Service handles missing pricing gracefully → Falls back to estimated
- [ ] Service handles missing budget info gracefully → Handles error

**Test Script:**
```bash
# Run comprehensive cost calculation tests
python tests/test_free_tier_transition.py
python tests/test_transition_all_models.py
```

### 6.3 Dependency Injection

**Test Cases:**
- [ ] Services are singletons
- [ ] Services initialized correctly
- [ ] Config loaded correctly
- [ ] Dependencies resolved correctly

**Singleton Pattern Testing:**
- [ ] `get_orchestrator()` called multiple times → Returns same instance
- [ ] `get_storage_service()` called multiple times → Returns same instance
- [ ] `get_app_config()` called multiple times → Returns same instance
- [ ] `get_budget_service()` called multiple times → Returns same instance

**Service Initialization Testing:**
- [ ] Services initialize on first use → Not created until needed
- [ ] Service initialization order correct → Dependencies available
- [ ] Service initialization doesn't block → Fast startup
- [ ] Service initialization errors handled → Clear error messages

**Dependency Resolution Testing:**
- [ ] FastAPI dependency injection works → Routes get services
- [ ] Dependencies injected into routes correctly → Services accessible
- [ ] Dependency functions called correctly → Proper initialization
- [ ] Dependency errors handled → Clear error messages

**Test Script:**
```python
# Test singleton pattern
from app.dependencies import get_orchestrator, get_storage_service

orchestrator1 = get_orchestrator()
orchestrator2 = get_orchestrator()
assert orchestrator1 is orchestrator2  # Same instance

storage1 = get_storage_service()
storage2 = get_storage_service()
assert storage1 is storage2  # Same instance
```

### 6.4 Configuration Management Integration

**Test Cases:**
- [ ] Config used in dependency injection → Services get config
- [ ] Config passed to orchestrator → Orchestrator initialized correctly
- [ ] Config used in route dependencies → Routes work correctly
- [ ] Config changes require restart → Services use initial config

**Test Script:**
```bash
# Test config in dependencies
python -c "
from app.dependencies import get_app_config
config = get_app_config()
print(f'Provider: {config.stt_provider}')
print(f'Model: {config.google_model}')
print(f'Bucket: {config.gcs_bucket_name}')
"
```

### 6.5 Storage Adapter Interface Testing

**Purpose:** Verify that current implementations conform to Protocol interfaces.

**Test Cases:**
- [ ] `JobStorageService` conforms to `JobStorageAdapter` Protocol
  - [ ] Implements all required methods
  - [ ] Method signatures match Protocol
  - [ ] Return types match Protocol
- [ ] `LibraryService` conforms to `LibraryStorageAdapter` Protocol
  - [ ] Implements all required methods
  - [ ] Method signatures match Protocol
  - [ ] Return types match Protocol
- [ ] `JobStorageService` transcript methods conform to `TranscriptStorageAdapter` Protocol
  - [ ] Implements all required methods
  - [ ] Method signatures match Protocol

**Test Script:**
```python
# Test Protocol compliance
from app.services.storage_adapters.adapter import (
    JobStorageAdapter,
    LibraryStorageAdapter,
    TranscriptStorageAdapter
)
from app.services.jobs import JobStorageService
from app.services.library import LibraryService

# Verify JobStorageService conforms
job_storage = JobStorageService()
assert isinstance(job_storage, JobStorageAdapter)  # Runtime check

# Verify LibraryService conforms
library_service = LibraryService()
assert isinstance(library_service, LibraryStorageAdapter)  # Runtime check
```

**Note:** Protocol compliance is primarily checked at type-checking time (mypy), but runtime checks verify actual implementation.

---

## 7. Server Startup & Initialization Testing

### 7.1 Server Startup Testing

**Test Cases:**
- [ ] Server starts without errors → `uvicorn app.main:app` succeeds
- [ ] All routes registered → Verify route count (40 routes expected)
- [ ] API v1 routes registered → Verify 15 v1 routes
- [ ] Old routes still registered → Verify backward compatibility
- [ ] Error handlers registered → Verify 3 error handlers
- [ ] Static files mounted → Verify `/static/` accessible

**Test Commands:**
```bash
# Start server
uvicorn app.main:app --reload

# Check routes
curl http://localhost:8000/docs  # OpenAPI docs should show all routes

# Check server logs for initialization
# Should see: "TranscriptionOrchestrator initialized"
# Should see: "Loaded pricing config version..."
# Should see: "Loaded budget data from..."
```

### 7.2 Service Initialization Testing

**Test Cases:**
- [ ] All services initialize on startup → No errors in logs
- [ ] Config service initializes → Config loaded
- [ ] Storage service initializes → GCS client created
- [ ] Pricing service initializes → Pricing config loaded
- [ ] Budget service initializes → Budget data loaded
- [ ] Job storage initializes → Jobs data loaded
- [ ] Library service initializes → Library data loaded
- [ ] Processing time service initializes → Processing time data loaded
- [ ] Orchestrator initializes → All dependencies available

**Test Script:**
```bash
# Check service initialization in logs
uvicorn app.main:app 2>&1 | grep -i "initialized\|loaded\|error"
```

### 7.3 Configuration Validation Testing

**Test Cases:**
- [ ] Valid configuration → Server starts successfully
- [ ] Missing required config → Server fails with clear error
- [ ] Invalid config value → Server fails with clear error
- [ ] Config validation happens early → Fail-fast behavior

**Test Commands:**
```bash
# Test with missing config
unset GOOGLE_CLOUD_PROJECT
uvicorn app.main:app
# Expected: Fails immediately with clear error about missing GOOGLE_CLOUD_PROJECT

# Test with invalid config
export STT_PROVIDER=invalid_provider
uvicorn app.main:app
# Expected: Fails immediately with clear error about invalid provider
```

### 7.4 Dependency Injection Initialization

**Test Cases:**
- [ ] Dependencies initialize in correct order → No circular dependencies
- [ ] Dependencies available when needed → Services can access dependencies
- [ ] Dependency initialization errors handled → Clear error messages
- [ ] Dependency initialization doesn't block → Fast startup

**Test Script:**
```python
# Test dependency initialization order
import logging
logging.basicConfig(level=logging.INFO)

from app.dependencies import get_orchestrator

# This should initialize all dependencies in correct order
orchestrator = get_orchestrator()
# Check logs for initialization order
```

---

## 8. Performance Testing

### 8.1 Response Times

**Test Cases:**
- [ ] Endpoint response times reasonable
- [ ] No significant slowdown from refactoring
- [ ] Concurrent requests handled correctly

### 8.2 Resource Usage

**Test Cases:**
- [ ] Memory usage reasonable
- [ ] No memory leaks
- [ ] Service initialization doesn't block

---

## Quick Test Checklist

### Critical Path (Must Work)
- [ ] Server starts without errors
- [ ] All services initialize correctly
- [ ] Config validation works (fail-fast)
- [ ] Submit transcription job
- [ ] Check job status
- [ ] Job completes successfully
- [ ] Results appear in library
- [ ] Budget updates correctly
- [ ] UI pages load and work

### Important Features
- [ ] Tier tracking works
- [ ] Free tier transition works
- [ ] Cost calculation correct
- [ ] Error handling works
- [ ] Error handlers registered and working
- [ ] Old endpoints still work
- [ ] Dependency injection works (singletons)
- [ ] Orchestrator coordinates services correctly

### Architectural Boundaries
- [ ] Pydantic models validate correctly
- [ ] Orchestrator methods work correctly
- [ ] Cost calculation service works independently
- [ ] Config class validates and fails fast
- [ ] Storage adapters conform to Protocols
- [ ] Dependency injection creates singletons

### Nice to Have
- [ ] All endpoints tested
- [ ] All error cases tested
- [ ] All unit tests pass
- [ ] Performance verified

---

## Running Tests

### Manual Testing
1. Start server: `uvicorn app.main:app --reload`
2. Test endpoints using curl commands above
3. Test UI in browser
4. Verify logs for errors

### Automated Testing (Future)
- Create pytest test suite
- Test all endpoints programmatically
- Test error cases
- Test edge cases

---

## Success Criteria

✅ **All critical paths work**
✅ **No regressions from refactoring**
✅ **Error handling works correctly**
✅ **Backward compatibility maintained**
✅ **UI still functional**
✅ **Performance acceptable**

---

## Issues Found

(Record any issues discovered during testing)

---

## Next Steps After Testing

1. Fix any issues found
2. Update documentation if needed
3. Consider removing old endpoints (if desired)
4. Add automated tests
5. Performance optimization if needed

