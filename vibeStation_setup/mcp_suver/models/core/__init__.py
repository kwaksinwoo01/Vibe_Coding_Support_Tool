"""
Core data models for the 6-tier task orchestration system.

This package contains the fundamental data models that follow the Single Responsibility Principle.
Each module has a single, well-defined responsibility:

- types.py: Type definitions and enums
- states.py: AgentState model (workflow orchestration state)
- context.py: TaskContext model (task execution context)
- tier_states.py: 6 tier-specific state models (A-F)
- tier_models.py: Child and subordinate data classes for tier states
- documents.py: WPDDocument model (service layer document)
- mp_models.py: Separated MP data models
- templates.py: WPD template definitions (L0-L3)
- reporting_models.py: Reporting data models (ValidationIssue, SyncResult, FileMetadata)
- version.py: Version information model (VersionInfo)
"""

from .types import (
    TierType,
    StatusType,
    WPDGrade,
    TierTypeValue,
    StatusTypeValue,
    WPDGradeValue,
    DocumentTypeValue,
    STATUS_EMOJI_MAP,
    WPD_GRADE_HIERARCHY,
)
from .states import AgentState, AgentLog
from .context import TaskContext
from .tier_states import (
    TierAState,
    TierBState,
    TierCState,
    TierDState,
    TierEState,
    TierFState,
)
from .tier_models import (
    DocumentMetadata,
    DocumentHierarchy,
    DocumentSources,
    DocumentCreationContext,
)
from .documents import (
    StatusPad,
    WPDDocument,
    PRDDocument,
    UpdateResult,
    TemplateInstance,
)
from .mp_models import (
    MPMetadata,
    MPSection,
    MPFlow,
    MPValidation,
    MPDiff,
)
from ..document_format.templates import (
    wpd_0_template,
    wpd_1_template,
    wpd_2_template,
    wpd_3_template,
    WPD_TEMPLATES,
    get_template_for_grade,
    get_required_sections,
)
# Note: Template classes are also available in models.document_format for better organization
from .reporting_models import (
    ValidationIssue,
    SyncResult,
    FileMetadata,
)
from .version import VersionInfo

__all__ = [
    # Types
    "TierType",
    "StatusType",
    "WPDGrade",
    "TierTypeValue",
    "StatusTypeValue",
    "WPDGradeValue",
    "DocumentTypeValue",
    "STATUS_EMOJI_MAP",
    "WPD_GRADE_HIERARCHY",
    # States
    "AgentState",
    "AgentLog",
    # Context
    "TaskContext",
    # Tier States
    "TierAState",
    "TierBState",
    "TierCState",
    "TierDState",
    "TierEState",
    "TierFState",
    # Child and Subordinate Data Classes (tier_models)
    "DocumentMetadata",
    "DocumentHierarchy",
    "DocumentSources",
    "DocumentCreationContext",
    # Documents
    "StatusPad",
    "WPDDocument",
    "PRDDocument",
    "UpdateResult",
    "TemplateInstance",
    # MP Models
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
]
