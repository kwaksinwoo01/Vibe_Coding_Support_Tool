# Data Class Refactoring Plan

**Version**: 1.0.0  
**Date**: 2026-01-12  
**Status**: 🔄 Planning Phase  
**Breaking Changes**: ⚠️ YES - Non-compatible refactoring

---

## 📋 Executive Summary

This document outlines the comprehensive refactoring plan for the turbo-system agent data class architecture. The refactoring introduces a strict 4-tier hierarchy (Parent → Intermediate → Child → Service) and eliminates all circular dependencies and hierarchy violations.

**⚠️ CRITICAL**: This is a **breaking change** refactoring. Compatibility with existing code is **NOT** maintained. All consuming code must be updated to the new structure.

---

## 🎯 Refactoring Objectives

### Primary Goals
1. ✅ Establish clear 4-tier hierarchy with no circular dependencies
2. ✅ Move common fields from Intermediate to Parent tier (AgentState)
3. ✅ Eliminate upward dependencies (Child → Parent, Intermediate → Parent)
4. ✅ Ensure all Service classes are stateless and reusable
5. ✅ Achieve 100% type safety with mypy/pyright

### Non-Goals
- ❌ Incremental migration (all-or-nothing approach)
- ❌ Runtime compatibility checks

---

## 🔍 Current State Analysis

### Current Violations

#### Violation 1: Circular Import (context.py ↔ states.py)
**Location**: `.github/agents/tool/models/core/context.py`

```python
# context.py
from .states import AgentState  # Child importing Parent

@dataclass
class TaskContext:
    previous_state: Optional[AgentState]  # Composition
```

**Status**: ✅ ACCEPTABLE  
**Reason**: TaskContext is also a Parent-tier class, this is composition not behavioral dependency

**Action**: Document as exception in guidelines

#### Violation 2: Upward Import in tier_models.py
**Location**: `.github/agents/tool/models/core/tier_models.py`

```python
# tier_models.py (Child tier)
if TYPE_CHECKING:
    from .documents import WPDDocument  # Child → Child (OK)
```

**Status**: ✅ OK  
**Reason**: TYPE_CHECKING import for type hints only, no runtime dependency

**Action**: No change needed

#### Violation 3: execution_log Duplication
**Location**: Multiple tier states

**Current State**:
```python
# TierAState (before refactoring)
execution_log: List[str] = field(default_factory=list)

# TierBState (before refactoring)
execution_log: List[str] = field(default_factory=list)

# AgentState
execution_log: List[str] = field(default_factory=list)
```

**Status**: ✅ FIXED (already completed)  
**Action**: Removed from all Intermediate tier states

#### Violation 4: wpd_grade Duplication
**Location**: TierAState, TierBState, AgentState

**Status**: ✅ FIXED (already completed)  
**Action**: Removed from all Intermediate tier states, kept only in AgentState

###Violation 5: Missing Service Layer for Complex Operations
**Location**: Various tier states with embedded logic

**Current State**:
```python
# tier_states.py
class TierStateConverter:
    @staticmethod
    def c_to_a(tier_c: TierCState) -> TierAState:
        # Conversion logic embedded in tier module
        ...
```

**Status**: ⚠️ NEEDS RELOCATION  
**Reason**: Converter logic should be in Service tier, not Intermediate tier

**Action**: Move to `.github/agents/tool/models/converters/tier_converters.py`

---

## 📊 Field Optimization Plan

### Phase 1: AgentState Optimization

#### Fields Added to AgentState
```python
# Common tier fields (moved from Intermediate states)
execution_log: List[str] = field(default_factory=list)
wpd_grade: str = "L1"  # WPD grade level (L0, L1, L2, L3)
wpd_source_path: str = ""  # Source WPD document path

# Optional structured metadata (from Child tier as Dict)
metadata: Optional[Dict[str, Any]] = None  # DocumentMetadata.to_dict()
hierarchy: Optional[Dict[str, Any]] = None  # DocumentHierarchy.to_dict()
sources: Optional[Dict[str, Any]] = None  # DocumentSources.to_dict()
```

#### Fields Removed from Intermediate States
```python
# TierAState - REMOVED
# execution_log: List[str]  # Moved to AgentState
# wpd_grade: str  # Moved to AgentState

# TierBState - REMOVED
# execution_log: List[str]  # Moved to AgentState
# wpd_grade: str  # Moved to AgentState
# wpd_source_path: str  # Moved to AgentState
```

**Impact**:
- ✅ Reduces duplication across 6 tier states
- ✅ Centralizes common fields in Parent tier
- ⚠️ Requires updating all tier state serialization methods
- ⚠️ Requires updating A_Working_Document_Progress.py execute() method

**Migration**: Already completed in previous refactoring

### Phase 2: Intermediate Tier Optimization (Planned)

#### TierAState Optimization
**Current Fields** (After Phase 1):
```python
@dataclass
class TierAState:
    metadata: DocumentMetadata
    hierarchy: DocumentHierarchy
    created_documents: List[str]
    main_document_path: str
    current_step: str
    validation_results: Dict[str, bool]
```

**Proposed Changes**: 
- Replace `validation_results: Dict[str, bool]` with `validation: CCV` (Centralized Control Validation)
- CCV will manage all validation operations through a unified interface

**Proposed Optimized Fields**:
```python
@dataclass
class TierAState:
    metadata: DocumentMetadata
    hierarchy: DocumentHierarchy
    created_documents: List[str]
    main_document_path: str
    current_step: str
    validation: CCV  # Centralized validation control
    # Removed: validation_results → replaced by CCV
```

**Rationale**: 
- ✅ Centralizes validation logic in Service tier
- ✅ Provides unified validation interface for all tier states
- ✅ Enables validation function composition and reuse
- ✅ Reduces code duplication across tier states

#### TierBState Optimization
**Current Fields** (After Phase 1):
```python
@dataclass
class TierBState:
    sources: DocumentSources
    execution_results: Dict[str, Any]
    milestone_status: Dict[str, str]
    total_phases: int
    completed_phases: int
    failed_phases: int
    current_phase: str
    start_time: str
    end_time: str
    phase_results: List[Dict[str, Any]]
    execution_report_path: str
    total_duration_ms: float
```

**Proposed Changes**: 
- Move `total_duration_ms` to AgentState.execution_time_ms
- Move `start_time` and `end_time` to AgentState as new fields
- Move execution-related fields to DocumentSources:
  - `execution_report_path` (already exists)
  - `phase_results`
  - `failed_phases`
  - `completed_phases`
  - `total_phases`
  - `execution_results`
  - `milestone_status`

**Proposed Optimized Fields**:
```python
@dataclass
class TierBState:
    sources: DocumentSources  # Expanded with execution fields
    current_phase: str  # Only tier-specific field
    # Removed: total_duration_ms → AgentState.execution_time_ms
    # Removed: start_time → AgentState.start_time
    # Removed: end_time → AgentState.end_time
    # Removed: execution_results → DocumentSources.execution_results
    # Removed: milestone_status → DocumentSources.milestone_status
    # Removed: total_phases → DocumentSources.total_phases
    # Removed: completed_phases → DocumentSources.completed_phases
    # Removed: failed_phases → DocumentSources.failed_phases
    # Removed: phase_results → DocumentSources.phase_results
    # Removed: execution_report_path → DocumentSources.execution_report_path
```

**Expanded DocumentSources**:
```python
@dataclass
class DocumentSources:
    # Original fields
    wpd_sources: List[str] = field(default_factory=list)
    prd_path: Optional[str] = None
    execution_report_path: Optional[str] = None
    
    # New execution tracking fields
    execution_results: Dict[str, Any] = field(default_factory=dict)
    milestone_status: Dict[str, str] = field(default_factory=dict)
    total_phases: int = 0
    completed_phases: int = 0
    failed_phases: int = 0
    phase_results: List[Dict[str, Any]] = field(default_factory=list)
```

**AgentState Time Fields**:
```python
@dataclass
class AgentState:
    # ... existing fields ...
    execution_time_ms: float = 0.0  # Already exists
    start_time: str = ""  # NEW
    end_time: str = ""  # NEW
```

**Impact**:
- ✅ Reduces field duplication
- ⚠️ Requires updating B_Performing_Tasks.py
- ⚠️ May affect execution time tracking logic

#### TierCState Optimization
**Current Fields** (After Phase 1):
```python
@dataclass
class TierCState:
    wpd_path: str
    target_document: str  # Alias for wpd_path
    modification_type: str
    creation_context: DocumentCreationContext
    modified_documents: List[str]
    modifications: List[Dict[str, Any]]
    affected_sections: List[str]
    changes_made: List[Dict[str, Any]]
    validation_passed: bool
    agent_log: AgentLog
    temporary_content: str
    documents_to_remove: List[str]
    auto_log_entries: List[Dict[str, Any]]
```

**Proposed Changes**:
- ✅ Merge `wpd_path` and `target_document` into single `target_document` field
- Consider moving `agent_log.execution_log` to AgentState.execution_log
- Evaluate if `changes_made` and `modifications` can be unified
- Replace `validation_passed: bool` with `validation: CCV`

**Proposed Optimized Fields**:
```python
@dataclass
class TierCState:
    target_document: str  # Unified field (wpd_path removed)
    modification_type: str
    creation_context: DocumentCreationContext
    modified_documents: List[str]
    modifications: List[Dict[str, Any]]  # Unified with changes_made
    affected_sections: List[str]
    validation: CCV  # Centralized validation control
    temporary_content: str
    documents_to_remove: List[str]
    # Removed: wpd_path → merged into target_document
    # Removed: agent_log → execution log moved to AgentState
    # Removed: changes_made → merged into modifications
    # Removed: auto_log_entries → moved to modifications
    # Removed: validation_passed → replaced by CCV
```

**Impact**:
- ✅ Simplifies field structure
- ⚠️ Requires updating C_Modifying_Working_Document.py
- ⚠️ May affect change tracking logic

#### TierDState, TierEState, TierFState Optimization
**Status**: Already optimized, no common fields identified

**Action**: No changes needed

### Phase 3: Child Tier Optimization (Planned)

#### DocumentMetadata Optimization
**Current Fields**:
```python
@dataclass
class DocumentMetadata:
    document_type: Literal["WPD", "PRD"] = "WPD"
    Part_N: str = ""
    document_title: str = ""
    version: str = "1.0.0"
    status: str = "📋 PENDING"
    timestamp: str = ""
```

**Proposed Changes**: None (already minimal)

**Rationale**: All fields are essential metadata

#### DocumentHierarchy Optimization
**Current Fields**:
```python
@dataclass
class DocumentHierarchy:
    parent_document: Optional[str] = None
    child_documents: List[str] = field(default_factory=list)
    reference_documents: List[str] = field(default_factory=list)
```

**Proposed Changes**: None (already minimal)

**Rationale**: All fields are essential for document relationships

#### DocumentSources Optimization
**Current Fields**:
```python
@dataclass
class DocumentSources:
    wpd_sources: List[str] = field(default_factory=list)
    prd_path: Optional[str] = None
    execution_report_path: Optional[str] = None
```

**Proposed Changes**: 
- Expand to include execution tracking fields from TierBState
- Becomes comprehensive execution and document tracking model

**Proposed Optimized Fields**:
```python
@dataclass
class DocumentSources:
    # Original document tracking fields
    wpd_sources: List[str] = field(default_factory=list)
    prd_path: Optional[str] = None
    execution_report_path: Optional[str] = None
    
    # Execution tracking fields (from TierBState)
    execution_results: Dict[str, Any] = field(default_factory=dict)
    milestone_status: Dict[str, str] = field(default_factory=dict)
    total_phases: int = 0
    completed_phases: int = 0
    failed_phases: int = 0
    phase_results: List[Dict[str, Any]] = field(default_factory=list)
```

**Rationale**: 
- ✅ Groups all execution and document tracking in one place
- ✅ Reduces TierBState to only tier-specific logic
- ✅ Makes DocumentSources a comprehensive execution tracking model
- ✅ Enables reuse across TierBState and TierEState

#### DocumentCreationContext Optimization
**Current Fields**:
```python
@dataclass
class DocumentCreationContext:
    documents_to_create: List[str] = field(default_factory=list)
    parent_document_path: Optional[str] = None
    creation_parameters: Dict[str, Any] = field(default_factory=dict)
```

**Proposed Changes**: None (already minimal)

**Rationale**: All fields are essential for document creation

### Phase 4: Service Tier Refactoring (Planned)

#### Create Centralized Control Validation (CCV) System

**New Module**: `.github/agents/tool/models/validators/validation_control.py` (Service tier)

**Purpose**: Centralize all validation logic across tier states through a unified interface

**CCV Class Design**:
```python
from typing import Dict, List, Tuple, Callable, Any
from dataclasses import dataclass, field

@dataclass
class CCV:
    """
    Centralized Control Validation (CCV)
    
    Manages validation operations for all tier states through a unified interface.
    Composes multiple validation functions and tracks results.
    
    **Responsibility**: Orchestrate validation functions for tier states
    **Usage**: Replace validation_results: Dict[str, bool] in tier states
    """
    
    # Validation results
    is_valid: bool = True
    validation_results: Dict[str, bool] = field(default_factory=dict)
    validation_errors: List[str] = field(default_factory=list)
    validation_warnings: List[str] = field(default_factory=list)
    
    # Validation functions registry
    validators: List[Callable] = field(default_factory=list)
    
    def add_validator(self, name: str, validator_func: Callable) -> "CCV":
        """Add a validation function to the registry."""
        self.validators.append((name, validator_func))
        return self
    
    def validate(self, target: Any) -> Tuple[bool, Dict[str, Any]]:
        """
        Execute all registered validators on target.
        
        Returns:
            Tuple of (is_valid, validation_report)
        """
        self.validation_results.clear()
        self.validation_errors.clear()
        self.validation_warnings.clear()
        
        for name, validator_func in self.validators:
            try:
                is_valid, messages = validator_func(target)
                self.validation_results[name] = is_valid
                
                if not is_valid:
                    self.validation_errors.extend(messages)
            except Exception as e:
                self.validation_results[name] = False
                self.validation_errors.append(f"{name}: {str(e)}")
        
        self.is_valid = all(self.validation_results.values())
        
        return self.is_valid, {
            "is_valid": self.is_valid,
            "results": self.validation_results,
            "errors": self.validation_errors,
            "warnings": self.validation_warnings
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize validation state to dictionary."""
        return {
            "is_valid": self.is_valid,
            "validation_results": self.validation_results,
            "validation_errors": self.validation_errors,
            "validation_warnings": self.validation_warnings
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CCV":
        """Deserialize from dictionary."""
        return cls(
            is_valid=data.get("is_valid", True),
            validation_results=data.get("validation_results", {}),
            validation_errors=data.get("validation_errors", []),
            validation_warnings=data.get("validation_warnings", [])
        )
    
    @classmethod
    def for_tier_a(cls) -> "CCV":
        """Create CCV instance with TierA-specific validators."""
        from validators.tier_validators import (
            validate_wpd_document_structure,
            validate_document_metadata,
            validate_document_hierarchy
        )
        
        ccv = cls()
        ccv.add_validator("wpd_structure", validate_wpd_document_structure)
        ccv.add_validator("metadata", validate_document_metadata)
        ccv.add_validator("hierarchy", validate_document_hierarchy)
        return ccv
    
    @classmethod
    def for_tier_b(cls) -> "CCV":
        """Create CCV instance with TierB-specific validators."""
        from validators.tier_validators import (
            validate_execution_results,
            validate_phase_completion
        )
        
        ccv = cls()
        ccv.add_validator("execution_results", validate_execution_results)
        ccv.add_validator("phase_completion", validate_phase_completion)
        return ccv
    
    @classmethod
    def for_tier_c(cls) -> "CCV":
        """Create CCV instance with TierC-specific validators."""
        from validators.tier_validators import (
            validate_document_modifications,
            validate_affected_sections
        )
        
        ccv = cls()
        ccv.add_validator("modifications", validate_document_modifications)
        ccv.add_validator("sections", validate_affected_sections)
        return ccv
```

**Usage in Tier States**:
```python
# TierAState
@dataclass
class TierAState:
    metadata: DocumentMetadata
    hierarchy: DocumentHierarchy
    created_documents: List[str]
    validation: CCV = field(default_factory=CCV.for_tier_a)
    
    def validate_all(self) -> Tuple[bool, Dict]:
        \"\"\"Validate entire state.\"\"\"
        return self.validation.validate(self)

# TierCState
@dataclass
class TierCState:
    target_document: str
    modifications: List[Dict[str, Any]]
    validation: CCV = field(default_factory=CCV.for_tier_c)
    
    def validate_all(self) -> Tuple[bool, Dict]:
        \"\"\"Validate entire state.\"\"\"
        return self.validation.validate(self)
```

**Impact**:
- ✅ Centralizes validation logic in Service tier
- ✅ Enables validator composition and reuse
- ✅ Provides consistent validation interface
- ✅ Reduces code duplication across tier states
- ⚠️ Requires updating all tier state validation logic
- ⚠️ Requires creating tier-specific validator functions

**Migration Steps**:
1. Create `.github/agents/tool/models/validators/validation_control.py`
2. Implement CCV class with factory methods
3. Update tier_validators.py with specific validator functions
4. Replace validation_results in TierAState with validation: CCV
5. Replace validation_passed in TierCState with validation: CCV
6. Update to_payload() and from_payload() methods
7. Update all tier execution modules to use CCV

#### Move TierStateConverter to Service Tier

**Current Location**: `.github/agents/tool/models/core/tier_states.py` (Intermediate tier)

**Target Location**: `.github/agents/tool/models/converters/tier_converters.py` (Service tier)

**Changes**:
```python
# Before: tier_states.py (Intermediate tier)
class TierStateConverter:
    @staticmethod
    def c_to_a(tier_c: TierCState) -> TierAState:
        ...
    
    @staticmethod
    def a_to_c(tier_a: TierAState, original_c: TierCState) -> TierCState:
        ...

# After: converters/tier_converters.py (Service tier)
def convert_tier_c_to_tier_a(tier_c: TierCState) -> TierAState:
    """Convert TierCState to TierAState for creation workflows."""
    ...

def merge_tier_a_to_tier_c(tier_a: TierAState, original_c: TierCState) -> TierCState:
    """Merge TierA creation results into existing TierCState."""
    ...

def chain_tier_states(source_state: Any, target_tier: str) -> Any:
    """Generic chaining helper for tier state conversions."""
    ...
```

**Impact**:
- ✅ Moves converter logic to appropriate Service tier
- ✅ Reduces Intermediate tier responsibilities
- ⚠️ Requires updating all import statements in tier modules
- ⚠️ May affect existing tests

**Migration Steps**:
1. Create `.github/agents/tool/models/converters/tier_converters.py`
2. Move TierStateConverter methods to standalone functions
3. Update tier_states.py to remove TierStateConverter class
4. Update all imports across codebase
5. Update tests to use new function names

#### Create Missing Service Modules

**Planned Modules**:
```
.github/agents/tool/models/
├── builders/
│   ├── agent_state_builder.py ✅ (exists)
│   ├── document_builder.py ✅ (exists)
│   ├── mp_builder.py ✅ (exists)
│   ├── template_builder.py ✅ (exists)
│   └── tier_state_builder.py ✅ (exists)
├── converters/
│   ├── document_converters.py ✅ (exists)
│   ├── mp_converters.py ✅ (exists)
│   └── tier_converters.py ⚠️ (needs TierStateConverter migration)
├── serializers/
│   ├── agent_state_serializer.py ✅ (exists)
│   ├── document_serializer.py ✅ (exists)
│   ├── json_serializer.py ✅ (exists)
│   └── mp_serializer.py ✅ (exists)
└── validators/
    ├── document_validators.py ✅ (exists)
    ├── mp_validators.py ✅ (exists)
    ├── template_validators.py ✅ (exists)
    └── tier_validators.py ✅ (exists)
```

**Status**: All modules exist except tier_converters.py needs refactoring

---

## 🚦 Refactoring Execution Plan

### Pre-Refactoring Checklist
- [x] Analyze current dependencies and violations
- [x] Document all breaking changes
- [x] Create Agent_DataClass_Guidelines.md
- [x] Create detailed refactoring plan (this document)
- [ ] Review plan with team
- [ ] Create backup branch
- [ ] Prepare test suite for validation

### Execution Phases

#### Phase 1: AgentState Common Fields (✅ Completed)
**Duration**: 1 day  
**Status**: ✅ DONE

**Tasks Completed**:
- [x] Add execution_log, wpd_grade, wpd_source_path to AgentState
- [x] Add metadata, hierarchy, sources as Optional[Dict] to AgentState
- [x] Remove execution_log from TierAState, TierBState
- [x] Remove wpd_grade from TierAState, TierBState
- [x] Update to_payload() and from_payload() methods
- [x] Update A_Working_Document_Progress.py execute() method
- [x] Fix main_agent.py type errors
- [x] Validate all changes with mypy/pyright

**Breaking Changes**:
- TierAState.to_payload() no longer includes execution_log, wpd_grade
- TierBState.to_payload() no longer includes execution_log, wpd_grade, wpd_source_path
- A_Working_Document_Progress.py must set state.execution_log instead of tier_a.execution_log

#### Phase 2: Service Tier Refactoring (🔄 In Progress)
**Duration**: 2 days  
**Status**: 🔄 PLANNING

**Tasks**:
- [ ] Create converters/tier_converters.py
- [ ] Move TierStateConverter.c_to_a() → convert_tier_c_to_tier_a()
- [ ] Move TierStateConverter.a_to_c() → merge_tier_a_to_tier_c()
- [ ] Move TierStateConverter.chain_to_tier() → chain_tier_states()
- [ ] Remove TierStateConverter class from tier_states.py
- [ ] Update __all__ exports in tier_states.py
- [ ] Update all import statements across codebase
- [ ] Update tests to use new function names
- [ ] Validate with mypy/pyright

**Breaking Changes**:
- TierStateConverter class no longer exists
- All converter methods are now standalone functions
- Import path changes from `models.core.tier_states` to `models.converters.tier_converters`

**Files to Update**:
- `.github/agents/tool/C_Modifying_Working_Document.py` (uses TierStateConverter)
- Tests that use TierStateConverter
- Any other modules importing TierStateConverter

#### Phase 3: TierBState Optimization (⏳ Planned)
**Duration**: 1 day  
**Status**: ⏳ NOT STARTED

**Tasks**:
- [ ] Remove total_duration_ms from TierBState (use AgentState.execution_time_ms)
- [ ] Evaluate start_time/end_time removal
- [ ] Update B_Performing_Tasks.py to use AgentState fields
- [ ] Update to_payload() and from_payload() methods
- [ ] Validate with mypy/pyright
- [ ] Update tests

**Breaking Changes**:
- TierBState.total_duration_ms removed
- Execution duration tracked in AgentState.execution_time_ms
- May require changes to execution time tracking logic

**Files to Update**:
- `.github/agents/tool/B_Performing_Tasks.py`
- Tests for TierBState

#### Phase 4: TierCState Optimization (⏳ Planned)
**Duration**: 1 day  
**Status**: ⏳ NOT STARTED

**Tasks**:
- [ ] Remove wpd_path field (use target_document only)
- [ ] Remove agent_log.execution_log (use AgentState.execution_log)
- [ ] Unify changes_made and modifications fields
- [ ] Update C_Modifying_Working_Document.py
- [ ] Update to_payload() and from_payload() methods
- [ ] Validate with mypy/pyright
- [ ] Update tests

**Breaking Changes**:
- TierCState.wpd_path removed (use target_document)
- TierCState.agent_log removed
- TierCState.changes_made merged into modifications
- All change tracking must use modifications field

**Files to Update**:
- `.github/agents/tool/C_Modifying_Working_Document.py`
- Tests for TierCState

#### Phase 5: Documentation and Validation (⏳ Planned)
**Duration**: 1 day  
**Status**: ⏳ NOT STARTED

**Tasks**:
- [ ] Update Agent_DataClass_Guidelines.md with final structure
- [ ] Create migration guide for external consumers
- [ ] Run full test suite
- [ ] Run mypy/pyright on entire codebase
- [ ] Update API documentation
- [ ] Create changelog

**Deliverables**:
- Updated Agent_DataClass_Guidelines.md
- MIGRATION_GUIDE.md for consumers
- CHANGELOG.md with all breaking changes
- Clean mypy/pyright validation

---

## ⚠️ Breaking Changes Summary

### Import Path Changes
```python
# Before
from models.core.tier_states import TierStateConverter

# After
from models.converters.tier_converters import (
    convert_tier_c_to_tier_a,
    merge_tier_a_to_tier_c,
    chain_tier_states
)
```

### Method Name Changes
```python
# Before
tier_a = TierStateConverter.c_to_a(tier_c)
tier_c = TierStateConverter.a_to_c(tier_a, original_c)

# After
tier_a = convert_tier_c_to_tier_a(tier_c)
tier_c = merge_tier_a_to_tier_c(tier_a, original_c)
```

### Field Removals
```python
# TierAState - REMOVED
# execution_log: List[str]  # Now in AgentState
# wpd_grade: str  # Now in AgentState

# TierBState - REMOVED
# execution_log: List[str]  # Now in AgentState
# wpd_grade: str  # Now in AgentState
# wpd_source_path: str  # Now in AgentState
# total_duration_ms: float  # Now in AgentState.execution_time_ms (Phase 3)

# TierCState - REMOVED
# wpd_path: str  # Use target_document instead (Phase 4)
# agent_log: AgentLog  # Execution log now in AgentState (Phase 4)
# changes_made: List[Dict]  # Merged into modifications (Phase 4)
```

### Serialization Changes
```python
# Before
tier_a = TierAState()
tier_a.execution_log.append("Log entry")
tier_a.wpd_grade = "L2"

# After
tier_a = TierAState()
state = AgentState(tier="A", status="SUCCESS", payload=tier_a.to_payload())
state.execution_log.append("Log entry")
state.wpd_grade = "L2"
state.metadata = tier_a.metadata.to_dict()
```

---

## 🧪 Testing Strategy

### Unit Tests
Each phase must include unit tests for:
- Data class creation and initialization
- Serialization (to_payload, to_dict)
- Deserialization (from_payload, from_dict)
- Field validation
- Type correctness

### Integration Tests
After each phase:
- Test tier execution flow (A → B → E)
- Test state passing between tiers
- Test service function usage
- Test converter functions

### Regression Tests
Before and after full refactoring:
- Run complete test suite
- Validate no functional regressions
- Ensure all tier modules work correctly

### Type Checking
After each phase:
```bash
mypy .github/agents/tool/models/
pyright .github/agents/tool/models/
```

Must pass with zero errors.

---

## 📋 Rollback Plan

### If Critical Issues Arise
1. Revert to backup branch created pre-refactoring
2. Analyze failure mode and root cause
3. Update refactoring plan to address issues
4. Re-attempt with fixes

### Partial Rollback (Phase-by-Phase)
Each phase is independent and can be rolled back individually if needed.

**Phase 1**: ✅ Cannot rollback (already completed and validated)

**Phase 2-4**: Can be rolled back by:
1. Reverting commits for that specific phase
2. Restoring original file versions
3. Re-running tests to ensure stability

---

## 📊 Success Metrics

### Code Quality
- ✅ Zero circular dependencies
- ✅ 100% type safety (mypy/pyright passes)
- ✅ All tests passing
- ✅ No hierarchy violations

### Architecture
- ✅ Clear 4-tier hierarchy established
- ✅ Service tier properly isolated
- ✅ Child tier has no upward dependencies
- ✅ Intermediate tier optimized (minimal fields)

### Documentation
- ✅ Agent_DataClass_Guidelines.md complete
- ✅ Refactoring plan documented (this document)
- ✅ Migration guide created
- ✅ API documentation updated

---

## 📅 Timeline

**Total Estimated Duration**: 6 days

- Day 1: ✅ Phase 1 completed (AgentState common fields)
- Day 2-3: 🔄 Phase 2 (Service tier refactoring)
- Day 4: ⏳ Phase 3 (TierBState optimization)
- Day 5: ⏳ Phase 4 (TierCState optimization)
- Day 6: ⏳ Phase 5 (Documentation and validation)

**Current Status**: Day 1 completed, Day 2 in planning

---

## 🤝 Contributors

- GitHub Copilot Coding Agent (Primary)
- Architecture Review Team (TBD)

---

## 📝 Change Log

- **2026-01-12**: Created refactoring plan
- **2026-01-12**: Completed Phase 1 (AgentState common fields)
- **2026-01-12**: Started Phase 2 planning (Service tier refactoring)

---

## 📚 References

- [Agent_DataClass_Guidelines.md](./Agent_DataClass_Guidelines.md) - Architecture guidelines
- [6TIER_IMPLEMENTATION_REPORT.md](../.github/agents/tool/6TIER_IMPLEMENTATION_REPORT.md) - Original implementation
- [AUTOMATED_DECISION_RULES_PLAN.md](../.github/AUTOMATED_DECISION_RULES_PLAN.md) - Decision rules architecture

---

**Questions or Issues**: File an issue or contact the development team.
