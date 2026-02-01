"""
Data models package for the 6-tier task orchestration system.

This package contains all data models following the Single Responsibility Principle (SRP).
Each module has a single, well-defined responsibility for clarity and maintainability.

**Architecture**:
- core/: Fundamental data models (types, states, documents, templates)
- validators/: Validation logic for each domain
- converters/: Model transformation logic
- serializers/: Serialization/deserialization (JSON, Markdown, etc.)
- formatters/: Formatting and rendering logic
- builders/: Factory/builder patterns for object creation

**SRP Compliance**:
Each module is changed for only ONE reason:
- types.py: New types/enums
- states.py: AgentState structure
- validators/*: Validation rules
- converters/*: Conversion logic
- serializers/*: Output format
- formatters/*: Presentation format
- builders/*: Creation policy

**Quick Start**:
```python
from models.core import AgentState, TierAState, WPDDocument
from models.builders import create_tier_a_state
from models.validators import validate_tier_a_state
from models.serializers import emit_agent_state

# Create and validate a state
tier_a = create_tier_a_state(wpd_grade="L1", Part_N="5", document_title="Task")
errors = validate_tier_a_state(tier_a)

# Emit result
state = AgentState(tier="A", status="SUCCESS", next_node="B")
emit_agent_state(state)
```
"""

# Import core models
from .core import (
    TierType,
    StatusType,
    WPDGrade,
    AgentState,
    TaskContext,  # Task execution context
    TierAState,
    TierBState,
    TierCState,
    TierDState,
    TierEState,
    TierFState,
    DocumentMetadata,
    DocumentHierarchy,
    DocumentSources,
    DocumentCreationContext,
    WPDDocument,
    MPMetadata,
    MPSection,
    MPFlow,
    MPValidation,
    MPDiff,
    wpd_0_template,
    wpd_1_template,
    wpd_2_template,
    wpd_3_template,
    WPD_TEMPLATES,
    get_template_for_grade,
    get_required_sections,
    ValidationIssue,
    SyncResult,
    FileMetadata,
    VersionInfo,
)

# Import validators
from .validators import (
    validate_tier_a_state,
    validate_tier_b_state,
    validate_tier_c_state,
    validate_tier_d_state,
    validate_tier_e_state,
    validate_tier_f_state,
    validate_wpd_document,
    validate_wpd_grade,
    validate_Part_N,
    validate_document_hierarchy,
    validate_template_structure,
    validate_required_sections,
)

# Import converters
from .converters import (
    tier_a_to_tier_b,
    tier_b_to_tier_e,
    tier_c_to_tier_e,
    tier_d_to_tier_c,
    wpd_document_to_tier_a,
    tier_a_to_wpd_document,
)

# Import serializers
from .serializers import (
    serialize_to_json,
    deserialize_from_json,
    emit_agent_state,
)

# Import formatters
from .formatters import (
    format_wpd_document_as_markdown,
    format_tier_a_state_as_markdown,
)

# Import builders
from .builders import (
    create_success_state,
    create_failure_state,
    create_pending_state,
    create_tier_a_state,
    create_tier_b_state,
    create_tier_c_state,
    create_tier_d_state,
    create_tier_e_state,
    create_tier_f_state,
)

# Legacy imports removed - these modules no longer exist
# from .agent_state import AgentState as LegacyAgentState
# from .doc_models import WPDDocument as LegacyWPDDocument
# from .document_models import DocumentModel
# from .mp_models import MPModel

__all__ = [
    # Types
    "TierType",
    "StatusType",
    "WPDGrade",
    
    # Core states and models
    "AgentState",
    "TaskContext",  # Task execution context
    "TierAState",
    "TierBState",
    "TierCState",
    "TierDState",
    "TierEState",
    "TierFState",
    
    # Nested models
    "DocumentMetadata",
    "DocumentHierarchy",
    "DocumentSources",
    "DocumentCreationContext",
    
    # Documents
    "WPDDocument",
    
    # MP Models (separated)
    "MPMetadata",
    "MPSection",
    "MPFlow",
    "MPValidation",
    "MPDiff",
    
    # Templates
    "wpd_0_template",
    "wpd_1_template",
    "wpd_2_template",
    "wpd_3_template",
    "WPD_TEMPLATES",
    "get_template_for_grade",
    "get_required_sections",
    
    # Reporting Models
    "ValidationIssue",
    "SyncResult",
    "FileMetadata",
    
    # Version
    "VersionInfo",
    
    # Validators
    "validate_tier_a_state",
    "validate_tier_b_state",
    "validate_tier_c_state",
    "validate_tier_d_state",
    "validate_tier_e_state",
    "validate_tier_f_state",
    "validate_wpd_document",
    "validate_wpd_grade",
    "validate_Part_N",
    "validate_document_hierarchy",
    "validate_template_structure",
    "validate_required_sections",
    
    # Converters
    "tier_a_to_tier_b",
    "tier_b_to_tier_e",
    "tier_c_to_tier_e",
    "tier_d_to_tier_c",
    "wpd_document_to_tier_a",
    "tier_a_to_wpd_document",
    
    # Serializers
    "serialize_to_json",
    "deserialize_from_json",
    "emit_agent_state",
    
    # Formatters
    "format_wpd_document_as_markdown",
    "format_tier_a_state_as_markdown",
    
    # Builders
    "create_success_state",
    "create_failure_state",
    "create_pending_state",
    "create_tier_a_state",
    "create_tier_b_state",
    "create_tier_c_state",
    "create_tier_d_state",
    "create_tier_e_state",
    "create_tier_f_state",
]

