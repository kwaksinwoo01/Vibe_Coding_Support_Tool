"""
Document models for the 6-tier task orchestration system.

**Single Responsibility**: Represent document structures (WPD, PRD, results).
This module is changed only when document structures change.

**Responsibility**: Document data models (WPD, PRD, results, status)
**Reason to Change**: When document structures or result models change

Models:
- StatusPad: Structured status representation
- WPDDocument: Work Plan Document model (all grades L0-L3)
- PRDDocument: Product Requirements Document model
- UpdateResult: Document update result model
- TemplateInstance: Template metadata instance

Note: Formatting, conversion, and serialization are in separate modules:
- Formatting: formatters/markdown_formatter.py
- Conversion: converters/document_converters.py
- Serialization: serializers/document_serializer.py
- Template definitions: templates.py
"""

from dataclasses import dataclass, field, asdict
from typing import List, Optional, Literal, Dict, Any, Tuple
from datetime import datetime


# ============================================================================
# Shared Status Model
# ============================================================================

@dataclass
class StatusPad:
    """Structured status representation.
    
    Used by all document and result models for consistent status tracking.
    
    **Responsibility**: Encapsulate status information
    **Reason to Change**: When status structure needs modification
    
    Attributes:
        state: Status state (pending, in_progress, complete, failed)
        success: Operation success flag (None if not applicable)
        source: Status source information (module name, file path, etc.)
    """
    state: str
    success: Optional[bool] = None
    source: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StatusPad":
        """Create from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ============================================================================
# WPD Document Model
# ============================================================================

@dataclass
class WPDDocument:
    """
    Unified WPD Document Model for all grades (L0-L3).
    
    Represents a Work Plan Document at any hierarchical level.
    Combines service-layer document management with content representation.
    
    **Responsibility**: Encapsulate WPD document data (not format, convert, or serialize)
    **Reason to Change**: When WPD document structure changes
    
    Attributes (Identification):
        Part_N: Hierarchical step number (e.g., "5", "5.2", "5.2.1")
        wpd_grade: Document grade/level (L0, L1, L2, L3)
        title: Document title
        
    Attributes (Content):
        description: Detailed description
        action: List of action items
        files_to_update: Files that need updating
        checklist: Checklist items
        goal: Main goal description (optional)
        success_criteria: List of success criteria (optional)
        implementation_plan: Implementation details (optional)
        test_results: Test results summary (optional)
        problem_statement: Problem description (optional)
        priority: Priority level (optional)
        
    Attributes (Metadata):
        version: Version in N1.N2.N3 format
        status: Status string with emoji prefix or StatusPad
        document_type: WPD or PRD
        timestamp: Creation timestamp
        
    Attributes (Hierarchy):
        parent_document: Path to parent document
        child_documents: Paths to child documents
        reference_documents: Related documents
        
    Attributes (Context):
        test_module: Path to test module (L2/L3)
        code_modifications: Code changes (L3)
        files_to_create: New files to create (L3)
        
    Attributes (Results):
        results_report: PRD document path
        prd_reference: Alternative PRD reference
        execution_summary: Summary from Tier B
    """
    
    # Hierarchical identification
    Part_N: str
    wpd_grade: Literal["L0", "L1", "L2", "L3"]
    title: str
    
    # Content (all grades)
    description: str = ""
    action: List[str] = field(default_factory=list)
    files_to_update: List[str] = field(default_factory=list)
    checklist: List[str] = field(default_factory=list)
    
    # Extended content (optional, from WPDContent)
    goal: str = ""
    success_criteria: List[str] = field(default_factory=list)
    implementation_plan: str = ""
    test_results: str = ""
    problem_statement: str = ""
    priority: str = ""
    
    # Metadata
    version: str = "1.0.0"
    status: str = "📋 PENDING"  # Can be StatusPad or string
    document_type: Literal["WPD", "PRD"] = "WPD"
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    # Hierarchy
    parent_document: Optional[str] = None
    child_documents: List[str] = field(default_factory=list)
    reference_documents: List[str] = field(default_factory=list)
    
    # Content context
    test_module: str = ""
    code_modifications: List[str] = field(default_factory=list)
    files_to_create: List[str] = field(default_factory=list)
    
    # Results Report integration
    results_report: Optional[str] = None
    prd_reference: Optional[str] = None
    prd_path: Optional[str] = None  # backward-compatible alias
    execution_summary: str = ""

    def __post_init__(self):
        # Ensure prd_path mirrors results_report or prd_reference if provided
        if self.prd_path is None:
            if self.results_report:
                self.prd_path = self.results_report
            elif self.prd_reference:
                self.prd_path = self.prd_reference
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WPDDocument":
        """Create from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
    
    def get_prd_path(self) -> Optional[str]:
        """Get PRD path, preferring results_report over prd_reference."""
        return self.results_report or self.prd_reference
    
    def set_prd_path(self, path: str) -> "WPDDocument":
        """Set PRD path."""
        self.results_report = path
        return self
    
    def is_complete(self) -> bool:
        """Check if document is marked as complete."""
        if isinstance(self.status, str):
            return "✅" in self.status or "COMPLETE" in self.status.upper()
        return False


# ============================================================================
# PRD Document Model
# ============================================================================

@dataclass
class PRDDocument:
    """PRD (Product Requirements Document) model.
    
    Represents a Product Requirements Document generated from WPD execution.
    
    **Responsibility**: Encapsulate PRD document data
    **Reason to Change**: When PRD document structure changes
    
    Attributes:
        title: Document title
        content: Generated PRD content
        wpd_source: Source WPD document path
        status: Generation status (StatusPad or string)
        version: Document version
        timestamp: Creation timestamp
        warnings: List of warning messages
    """
    title: str
    content: str = ""
    wpd_source: Optional[str] = None
    status: str = "📋 PENDING"  # Can be StatusPad or string
    version: str = "1.0.0"
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PRDDocument":
        """Create from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ============================================================================
# Result Models
# ============================================================================

@dataclass
class UpdateResult:
    """Document update operation result model.
    
    Represents the result of updating document content.
    
    **Responsibility**: Encapsulate update operation results
    **Reason to Change**: When update result structure changes
    
    Attributes:
        status: Operation status (StatusPad or string)
        message: Result message or description
        content_list: Updated content as list of tuples (optional)
        updated_files: List of updated file paths (optional)
    """
    status: str  # Can be StatusPad or string
    message: str
    content_list: Optional[List[Tuple[str, str]]] = None
    updated_files: Optional[List[str]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UpdateResult":
        """Create from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class TemplateInstance:
    """Template metadata instance for document generation.
    
    Represents an instance of a template with metadata.
    Different from template definitions in templates.py.
    
    **Responsibility**: Encapsulate template instance metadata
    **Reason to Change**: When template instance structure changes
    
    Attributes:
        project_number: Project identifier
        description: Template description
        wpd_grade: WPD grade level (L0-L3)
        version: Template version
        status: Template status
        created_date: Creation date
    """
    project_number: str
    description: str
    wpd_grade: Optional[Literal["L0", "L1", "L2", "L3"]] = None
    version: str = "1.0.0"
    status: str = "📋 PENDING"
    created_date: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TemplateInstance":
        """Create from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


__all__ = [
    "StatusPad",
    "WPDDocument",
    "PRDDocument",
    "UpdateResult",
    "TemplateInstance",
]
