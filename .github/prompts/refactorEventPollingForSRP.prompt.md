---
name: refactorEventPollingForSRP
description: Analyze event polling logs, identify data synchronization issues, and create a comprehensive refactoring strategy adhering to SRP and clean code principles.
argument-hint: Provide the event polling log file and identify the specific modules (cursor adapter, poller, event validator) that need refactoring. Specify the target data model (e.g., UnifiedFileModel) and any constraints (backward compatibility not required).
---

# Event Polling Refactoring Strategy: SRP-Compliant Analysis & Refactoring Plan

## Context
You are analyzing a multi-module event polling system with reported data synchronization issues:
- **Problem**: Event logs show incomplete event capture, mismatched file_ids, and outdated filename states
- **Root Cause**: Events (especially rename operations) are not fully captured in polling sequences
- **Impact**: UI displays incorrect file names and misses critical state changes
- **Constraint**: Breaking changes allowed; prioritize SRP, clean architecture, and maintainability

## Task: Generate Comprehensive Refactoring Strategy

### Phase 1: Log Analysis & Problem Identification

1. **Examine the event polling log** (provided file) to identify:
   - Missing or out-of-sequence events (e.g., file_id 'M5y2b3RGsYYAAAAAAAQhxg' has multiple filename states)
   - Time gaps between related events (add, rename, rename...) suggesting event loss
   - Discrepancies between logged events and actual local file states
   - Duplicate or conflicting entries for the same file_id
   
2. **Categorize issues by root cause**:
   - **Event Capture**: Which event types are missing (rename, move, delete)?
   - **Polling Timing**: Are there consistent time gaps or race conditions?
   - **State Synchronization**: Is local file state aligned with Dropbox API state?
   - **Data Transformation**: Are filename/path fields correctly mapped in UnifiedFileModel?

3. **Document findings** in a structured format:
   - Issue Type (Capture Gap, Sync Mismatch, Transform Error, etc.)
   - Affected file_ids and event types
   - Time range and sequence
   - Expected vs. Actual state

### Phase 2: SRP-Based Module Analysis

Analyze each module to identify **single responsibility violations**:

1. **CursorAdapter** - Should be responsible for ONLY:
   - Cursor-based pagination logic (advance, resume)
   - Raw Dropbox API event retrieval
   - Time-range filtering
   - **NOT**: Data transformation, validation, or synchronization
   
   *Issues to identify*:
   - Does it mix API calls with data normalization?
   - Are validation concerns embedded in polling logic?
   - Does it handle local sync responsibility?

2. **DropboxPoller** - Should be responsible for ONLY:
   - Orchestrating polling cycles (start, stop, pause)
   - Publishing events to the event bus
   - Error handling and retry logic for API failures
   - **NOT**: Event validation, transformation, or persistence
   
   *Issues to identify*:
   - Is event filtering mixed with polling logic?
   - Does it transform data into UnifiedFileModel?
   - Are multiple concerns (polling, validation, publishing) intertwined?

3. **InstrumentedCursorAdapter** - Should be responsible for ONLY:
   - Data flow tracking and instrumentation
   - Logging and debugging support
   - Test data capture and replay
   - **NOT**: Production polling logic, business rules
   
   *Issues to identify*:
   - Is instrumentation bleeding into core adapter logic?
   - Does it assume the main adapter's behavior?

### Phase 3: Synchronization Strategy

Define the approach to fix event capture and state synchronization:

1. **Event Completeness**:
   - Add event deduplication per file_id to detect missing intermediates
   - Implement event sequence validation (add → rename → rename → current_state)
   - Add fallback mechanism: Query Dropbox API for latest file metadata if events are incomplete
   
2. **State Reconciliation**:
   - After polling cycle, perform consistency check: Compare polled events against Dropbox API's current file state
   - For mismatches, log detailed trace and either re-poll or query metadata service
   - Maintain audit trail of state changes per file_id

3. **Data Transformation Pipeline**:
   - Create separate **EventValidator** module: Validate events (check required fields, sequence logic)
   - Create separate **EventTransformer** module: Convert raw Dropbox events → UnifiedFileModel (with filename/path fallback logic)
   - Separate **SyncReconciler** module: Detect and fix state mismatches
   
   *Rationale*: Each concern becomes independently testable and reusable

### Phase 4: Clean Architecture Refactoring

1. **Layer separation**:
   ```
   API Layer (CursorAdapter)
        ↓
   Raw Event Stream
        ↓
   Validation Layer (EventValidator)
        ↓
   Validated Events
        ↓
   Transformation Layer (EventTransformer)
        ↓
   UnifiedFileModel Instances
        ↓
   Synchronization Layer (SyncReconciler)
        ↓
   Reconciled State
        ↓
   Publishing Layer (DropboxPoller)
        ↓
   Event Bus
   ```

2. **Module Responsibilities** (Refactored):
   - **cursor_adapter.py**: Raw event retrieval only (no transformation)
   - **event_validator.py**: Event validation and sequence checking
   - **event_transformer.py**: Event → UnifiedFileModel conversion
   - **sync_reconciler.py**: State consistency verification and conflict resolution
   - **dropbox_poller.py**: Orchestration and event bus publishing
   - **cursor_adapter_instrumented.py**: Removed or significantly simplified (instrumentation via decorator/middleware pattern)

3. **Interface contracts**:
   - Define clear input/output types for each module
   - Use UnifiedFileModel as the standard interchange format
   - Document assumptions (e.g., "Events assumed to be ordered by timestamp")

### Phase 5: Implementation Roadmap

1. **Step 1**: Create EventValidator module
   - Validate required fields (file_id, filename, timestamp)
   - Check event sequences (file must exist before rename)
   - Detect incomplete event chains

2. **Step 2**: Create EventTransformer module
   - Implement robust field mapping (legacy field names → UnifiedFileModel)
   - Add fallback logic for missing fields (extract filename from path)
   - Preserve all metadata in a structured format

3. **Step 3**: Create SyncReconciler module
   - Compare polled event state against Dropbox API metadata
   - Identify missing events or outdated filenames
   - Provide repair mechanism (re-fetch latest metadata)

4. **Step 4**: Refactor CursorAdapter
   - Remove all transformation logic
   - Keep only pagination and filtering
   - Return raw event dictionaries (no UnifiedFileModel)

5. **Step 5**: Refactor DropboxPoller
   - Use new modules in sequence (Validate → Transform → Reconcile → Publish)
   - Add error handling per layer
   - Add comprehensive logging for debugging

6. **Step 6**: Deprecate or simplify InstrumentedCursorAdapter
   - Move instrumentation to a separate middleware/decorator
   - Or remove entirely if not needed in production

### Phase 6: Testing Strategy

1. **Unit Tests** (per module):
   - EventValidator: Test invalid events, sequence violations, field missing
   - EventTransformer: Test all field name variants, fallback logic, edge cases
   - SyncReconciler: Test state matching, mismatch detection, reconciliation

2. **Integration Tests**:
   - Full pipeline: Raw event → Validated → Transformed → Reconciled → Published
   - Test with log data (replay mode) to verify all events are captured
   - Verify no duplicates or missing events

3. **Log Replay Testing**:
   - Use provided log file to replay events and verify state consistency
   - Assert final state matches expected local file names

## Deliverables

1. **Analysis Report**:
   - Summary of identified issues with file_ids and event sequences
   - Root cause analysis per issue
   - Data flow diagram showing where state diverges

2. **Refactored Modules**:
   - event_validator.py (new)
   - event_transformer.py (new)
   - sync_reconciler.py (new)
   - cursor_adapter.py (simplified)
   - dropbox_poller.py (refactored)
   - cursor_adapter_instrumented.py (simplified or deprecated)

3. **Test Suite**:
   - Unit tests for each module
   - Integration tests with log replay
   - Test fixtures from provided log data

4. **Documentation**:
   - Module responsibility matrix (who does what)
   - Data flow diagram (JSON → Validation → Transform → Sync → Event Bus)
   - API contracts and type hints per module
   - Example usage and error handling patterns

## Key Principles

- **Single Responsibility**: Each module has ONE reason to change
- **Testability**: Every layer can be tested in isolation
- **Traceability**: File_id and state changes are fully auditable
- **Robustness**: Fallback logic and reconciliation handle incomplete data
- **Maintainability**: Clear separation of concerns, minimal interdependencies
- **Observability**: Comprehensive logging at each transformation step
