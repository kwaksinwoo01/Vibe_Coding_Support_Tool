"""
Child and Subordinate Data Classes for Tier States

**Architecture Classification**:
This module contains child and subordinate data classes as defined in the system architecture:

**Child Data Classes** (used by single tier):
- DocumentMetadata: Document metadata fields (TierAState only, potential for expansion)
- DocumentHierarchy: Parent-child document relationships (TierAState only, potential for expansion)
- DocumentCreationContext: Document creation parameters (TierCState only)

**Subordinate Data Classes** (shared by 2+ tiers):
- DocumentSources: WPD sources and report paths (TierBState, TierEState)

**Distinction from Parent Data Classes**:
- Parent (AgentState): Fields required by ALL intermediate data classes
- Child: Fields used by only ONE intermediate data class
- Subordinate: Fields shared by 2+ intermediate data classes (but not all)

**Single Responsibility**: Group related fields into cohesive parameter objects.
**Reason to Change**: When parameter grouping structure or tier usage patterns change
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any, Literal, TYPE_CHECKING

if TYPE_CHECKING:
    from .documents import WPDDocument


@dataclass
class DocumentMetadata:
    """
    Child Data Class: Document metadata fields.
    
    **Classification**: Child data class (used by single tier, potential for expansion)
    **Currently Used in**: TierAState only
    **Future Expansion**: May be used by additional tiers as system evolves
    
    **Responsibility**: Encapsulate document metadata fields
    **Reason to Change**: When metadata structure changes
    """
    
    document_type: Literal["WPD", "PRD"] = "WPD"
    Part_N: str = ""  # e.g., "5", "5.2", "5.2.1"
    document_title: str = ""
    version: str = "1.0.0"  # N1.N2.N3 format
    status: str = "📋 PENDING"  # 📋 PENDING, 🔄 IN PROGRESS, ✅ COMPLETE
    timestamp: str = ""  # ISO 8601 format
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DocumentMetadata":
        """Create from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
    
    @classmethod
    def from_wpd_document(cls, wpd_doc: "WPDDocument") -> "DocumentMetadata":
        """Extract metadata from WPDDocument."""
        return cls(
            document_type=wpd_doc.document_type,
            Part_N=wpd_doc.Part_N,
            document_title=wpd_doc.title,
            version=wpd_doc.version,
            status=wpd_doc.status,
            timestamp=wpd_doc.timestamp,
        )


@dataclass
class DocumentHierarchy:
    """
    Child Data Class: Document hierarchy and relationships.
    
    **Classification**: Child data class (used by single tier, potential for expansion)
    **Currently Used in**: TierAState only
    **Future Expansion**: May be used by additional tiers as system evolves
    
    **Responsibility**: Encapsulate document hierarchy fields
    **Reason to Change**: When hierarchy structure changes
    """
    
    parent_document: Optional[str] = None
    child_documents: List[str] = field(default_factory=list)
    reference_documents: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DocumentHierarchy":
        """Create from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
    
    @classmethod
    def from_wpd_document(cls, wpd_doc: "WPDDocument") -> "DocumentHierarchy":
        """Extract hierarchy from WPDDocument."""
        return cls(
            parent_document=wpd_doc.parent_document,
            child_documents=wpd_doc.child_documents.copy(),
            reference_documents=wpd_doc.reference_documents.copy(),
        )


@dataclass
class DocumentSources:
    """
    Subordinate Data Class: Document sources and execution tracking.
    
    **Classification**: Subordinate data class (shared by multiple tiers)
    **Used in**: TierBState, TierEState
    
    **Responsibility**: Encapsulate document source, report paths, and execution tracking
    **Reason to Change**: When source/path structure or execution tracking changes
    
    **Expanded**: Now includes execution tracking fields from TierBState
    for comprehensive execution and document management.
    """
    
    # Original document tracking fields
    wpd_sources: List[str] = field(default_factory=list)  # Source WPD document paths
    prd_path: Optional[str] = None  # PRD (results report) path
    execution_report_path: Optional[str] = None  # Execution report path
    
    # Execution tracking fields (moved from TierBState)
    execution_results: Dict[str, Any] = field(default_factory=dict)  # Execution results by phase
    milestone_status: Dict[str, str] = field(default_factory=dict)  # Milestone completion status
    total_phases: int = 0  # Total number of phases in execution
    completed_phases: int = 0  # Number of completed phases
    failed_phases: int = 0  # Number of failed phases
    phase_results: List[Dict[str, Any]] = field(default_factory=list)  # Detailed phase results
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DocumentSources":
        """Create from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
    
    @classmethod
    def from_wpd_document(cls, wpd_doc: "WPDDocument") -> "DocumentSources":
        """Extract sources from WPDDocument."""
        # Derive wpd_sources from parent_document when available
        wpd_sources = []
        if getattr(wpd_doc, "parent_document", None):
            wpd_sources = [wpd_doc.parent_document]
        elif getattr(wpd_doc, "Part_N", None) and getattr(wpd_doc, "title", None):
            # Fallback heuristic
            wpd_sources = [f"docs_2/P{wpd_doc.Part_N}/{wpd_doc.Part_N}-{wpd_doc.title}.md"]

        prd_path = getattr(wpd_doc, "prd_path", None) or getattr(wpd_doc, "results_report", None) or getattr(wpd_doc, "prd_reference", None)
        execution_report_path = getattr(wpd_doc, "results_report", None)

        return cls(
            wpd_sources=wpd_sources,
            prd_path=prd_path,
            execution_report_path=execution_report_path,
        )


@dataclass
class DocumentCreationContext:
    """
    Child Data Class: Document creation parameters.
    
    **Classification**: Child data class (used by single tier)
    **Used in**: TierCState only
    
    **Responsibility**: Encapsulate document creation context
    **Reason to Change**: When document creation parameters change
    """
    
    documents_to_create: List[str] = field(default_factory=list)
    parent_document_path: Optional[str] = None
    creation_parameters: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DocumentCreationContext":
        """Create from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


__all__ = [
    "DocumentMetadata",
    "DocumentHierarchy",
    "DocumentSources",
    "DocumentCreationContext",
]
