"""
Separated tier-specific state models for the 6-tier orchestration system.

**Single Responsibility**: Define state models for individual tiers.
Each tier state is in a separate section for clarity and maintainability.

**Responsibility**: Tier-specific state data models
**Reason to Change**: When a specific tier's state structure changes

Note: Model validation, factory methods, and tier conversion are in separate modules:
- Validation: validators/tier_validators.py
- Factory methods: builders/tier_state_builder.py
- Tier conversion: converters/tier_converters.py

Architecture:
- TierAState: Work Plan Creation (WPD generation)
- TierBState: Plan Execution (Execute plans and generate results)
- TierCState: Plan Modification (Edit existing WPD documents)
- TierDState: Issue Analysis (Analyze errors and failures)
- TierEState: Document Management (Manage PRD files and synchronization)
- TierFState: Unknown Logic (Fallback for unclassified requests)
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any, List, TYPE_CHECKING

from .tier_models import (
    DocumentMetadata,
    DocumentHierarchy,
    DocumentSources,
    DocumentCreationContext,
)
from .documents import WPDDocument
from ..validators.validation_control import CCV

if TYPE_CHECKING:
    from .states import AgentLog


def _create_agent_log():
    """Factory function to create AgentLog, avoiding circular import."""
    from .states import AgentLog
    return AgentLog()


# ============================================================================
# Tier A: Work Plan Creation
# ============================================================================

@dataclass
class TierAState:
    """
    State model for Tier A: Work Plan Creation.

    Tier A processes user input and generates WPD (Work Plan Document) files.

    **Clean API - Use nested dataclass access**:
        tier_a.metadata.document_type  # Access metadata fields
        tier_a.metadata.Part_N
        tier_a.metadata.document_title
        tier_a.hierarchy.parent_document  # Access hierarchy fields
        tier_a.hierarchy.child_documents

    Attributes:
        metadata: Document metadata (type, version, status, etc.)
        hierarchy: Document hierarchy (parent, children, references)
        created_documents: List of created WPD document paths
        main_document_path: Path to main document (e.g., NextTask)
        current_step: Current step number as string
        validation_results: Validation result map for created documents
    
    Note: wpd_grade, execution_log are now in AgentState
    """

    metadata: DocumentMetadata = field(default_factory=DocumentMetadata)
    hierarchy: DocumentHierarchy = field(default_factory=DocumentHierarchy)

    # Tier A specific fields
    created_documents: List[str] = field(default_factory=list)

    # Added for conversion/test compatibility
    main_document_path: str = "docs_2/NextTask-2.md"  # Default main document (replaces NEXT_TASK constant)
    current_step: str = ""
    validation_results: Dict[str, bool] = field(default_factory=dict)

    def to_payload(self) -> Dict[str, Any]:
        """Convert to dictionary payload for AgentState."""
        payload = {
            "metadata": self.metadata.to_dict(),
            "hierarchy": self.hierarchy.to_dict(),
            "created_documents": self.created_documents,
            "main_document_path": self.main_document_path,
            "current_step": self.current_step,
            "validation_results": self.validation_results,
        }
        # Backward-compatible top-level fields
        if self.metadata and getattr(self.metadata, "Part_N", None):
            payload["Part_N"] = self.metadata.Part_N
        if self.metadata and getattr(self.metadata, "document_title", None):
            payload["document_title"] = self.metadata.document_title
        # Backward-compatible keys for parent document
        payload["parent_document"] = self.hierarchy.parent_document
        return payload

    @classmethod
    def from_payload(cls, payload: Dict[str, Any]) -> "TierAState":
        """Create TierAState from payload dictionary."""
        return cls(
            metadata=DocumentMetadata.from_dict(payload.get("metadata", {})),
            hierarchy=DocumentHierarchy.from_dict(payload.get("hierarchy", {})),
            created_documents=payload.get("created_documents", []),
            main_document_path=payload.get("main_document_path", ""),
            current_step=payload.get("current_step", ""),
            validation_results=payload.get("validation_results", {}),
        )

    @classmethod
    def from_wpd_document(cls, wpd_doc: "WPDDocument") -> "TierAState":
        """Create a TierAState pre-filled from a WPDDocument."""
        metadata = DocumentMetadata.from_wpd_document(wpd_doc)
        hierarchy = DocumentHierarchy.from_wpd_document(wpd_doc)

        tier_a = cls(
            metadata=metadata,
            hierarchy=hierarchy,
        )
        tier_a.main_document_path = getattr(wpd_doc, "parent_document", "")
        tier_a.current_step = getattr(wpd_doc, "Part_N", "")
        return tier_a

    def to_wpd_document(self, wpd_grade: str = "L1") -> "WPDDocument":
        """Convert TierAState to a WPDDocument instance.
        
        Args:
            wpd_grade: WPD grade level (default: L1), pass from AgentState
        """
        from .documents import WPDDocument

        wpd_doc = WPDDocument(
            Part_N=self.metadata.Part_N or self.current_step,
            wpd_grade=wpd_grade,
            title=self.metadata.document_title,
            description="",
            files_to_update=[],
            checklist=[],
            version=self.metadata.version,
            status=self.metadata.status,
            document_type=self.metadata.document_type,
            timestamp=self.metadata.timestamp,
            parent_document=self.hierarchy.parent_document,
            child_documents=self.hierarchy.child_documents,
        )
        return wpd_doc

# Tier B: Plan Execution
# ============================================================================

@dataclass
class TierBState:
    """
    State model for Tier B: Plan Execution.
    
    Tier B loads WPD documents and executes them, generating results reports.
    
    **Clean API - Use nested dataclass access**:
        tier_b.sources.prd_path  # Access sources fields
        tier_b.sources.wpd_sources
        tier_b.sources.execution_report_path
    
    Attributes:
        sources: Document sources and report paths
        execution_results: Results from plan execution
        milestone_status: Status of each milestone
        total_phases: Total number of phases
        completed_phases: Number of completed phases
        failed_phases: Number of failed phases
        current_phase: Current phase identifier
        start_time: Execution start time
        end_time: Execution end time
        phase_results: Results for each phase
        execution_report_path: Path to execution report
        total_duration_ms: Total execution duration
    
    Note: wpd_source_path, wpd_grade, execution_log are now in AgentState
    """
    
    sources: DocumentSources = field(default_factory=DocumentSources)
    
    # Tier B specific fields
    execution_results: Dict[str, Any] = field(default_factory=dict)
    milestone_status: Dict[str, str] = field(default_factory=dict)
    
    # Additional fields used in B_Performing_Tasks.py
    total_phases: int = 0
    completed_phases: int = 0
    failed_phases: int = 0
    current_phase: str = ""
    start_time: str = ""
    end_time: str = ""
    phase_results: List[Dict[str, Any]] = field(default_factory=list)
    execution_report_path: str = ""
    total_duration_ms: float = 0.0
    
    def to_payload(self) -> Dict[str, Any]:
        """Convert to dictionary payload for AgentState."""
        payload = {
            "sources": self.sources.to_dict(),
            "execution_results": self.execution_results,
            "milestone_status": self.milestone_status,
            "total_phases": self.total_phases,
            "completed_phases": self.completed_phases,
            "failed_phases": self.failed_phases,
            "current_phase": self.current_phase,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "phase_results": self.phase_results,
            "execution_report_path": self.execution_report_path,
            "total_duration_ms": self.total_duration_ms,
        }
        # Backward-compatible keys
        payload["prd_path"] = self.sources.prd_path
        payload["execution_report_path"] = self.sources.execution_report_path
        return payload
    
    @classmethod
    def from_payload(cls, payload: Dict[str, Any]) -> "TierBState":
        """Create TierBState from payload dictionary."""
        return cls(
            sources=DocumentSources.from_dict(payload.get("sources", {})),
            execution_results=payload.get("execution_results", {}),
            milestone_status=payload.get("milestone_status", {}),
            total_phases=payload.get("total_phases", 0),
            completed_phases=payload.get("completed_phases", 0),
            failed_phases=payload.get("failed_phases", 0),
            current_phase=payload.get("current_phase", ""),
            start_time=payload.get("start_time", ""),
            end_time=payload.get("end_time", ""),
            phase_results=payload.get("phase_results", []),
            execution_report_path=payload.get("execution_report_path", ""),
            total_duration_ms=payload.get("total_duration_ms", 0.0),
        )


# ============================================================================
# Tier C: Plan Modification
# ============================================================================

@dataclass
class TierCState:
    """
    State model for Tier C: Plan Modification.

    Tier C modifies existing WPD documents based on user requests.

    **Clean API - Use nested dataclass access**:
        tier_c.creation_context.documents_to_create  # Access creation context fields
        tier_c.creation_context.parent_document_path
        tier_c.creation_context.creation_parameters
        tier_c.agent_log.execution_log  # Access execution log
        tier_c.agent_log.add_entry("message")  # Add log entries

    Attributes:
        target_document: Path to the document being modified (alias for wpd_path)
        modification_type: Type of modification (e.g., 'add_phase')
        creation_context: Document creation context
        modified_documents: List of modified WPD document paths
        modifications: List of modifications applied
        affected_sections: List of affected sections
        changes_made: List of change records
        validation_passed: Whether validation passed after operations
        agent_log: Centralized execution log (replaces execution_log)
        temporary_content: Temporary document content during modifications
        documents_to_remove: List of documents to remove
        auto_log_entries: Auto-trigger log entries
    """

    # Backward-compatible field
    wpd_path: str = ""
    target_document: str = ""  # new alias
    modification_type: str = ""

    creation_context: DocumentCreationContext = field(default_factory=DocumentCreationContext)

    # Tier C specific fields
    modified_documents: List[str] = field(default_factory=list)
    modifications: List[Dict[str, Any]] = field(default_factory=list)

    # Added fields for conversion/tests
    affected_sections: List[str] = field(default_factory=list)
    changes_made: List[Dict[str, Any]] = field(default_factory=list)
    validation_passed: bool = True
    
    # Centralized execution log (replaces self.execution_log)
    agent_log: "AgentLog" = field(default_factory=_create_agent_log)
    
    # Document operation state
    temporary_content: str = ""  # Replaces self.temporary_doc_content
    documents_to_remove: List[str] = field(default_factory=list)  # Replaces self.remove_doc
    auto_log_entries: List[Dict[str, Any]] = field(default_factory=list)  # Replaces self.auto_log_doc

    def to_payload(self) -> Dict[str, Any]:
        """Convert to dictionary payload for AgentState."""
        payload = {
            "wpd_path": self.wpd_path,
            "target_document": self.target_document or self.wpd_path,
            "modification_type": self.modification_type,
            "creation_context": self.creation_context.to_dict(),
            "modified_documents": self.modified_documents,
            "modifications": self.modifications,
            "affected_sections": self.affected_sections,
            "changes_made": self.changes_made,
            "validation_passed": self.validation_passed,
            "agent_log": self.agent_log.to_dict(),
            "temporary_content": self.temporary_content,
            "documents_to_remove": self.documents_to_remove,
            "auto_log_entries": self.auto_log_entries,
        }
        # Backward-compatible top-level keys expected by tests
        payload["documents_to_create"] = self.creation_context.documents_to_create
        payload["parent_document_path"] = self.creation_context.parent_document_path
        payload["execution_log"] = self.agent_log.execution_log
        payload.update(self.creation_context.creation_parameters)
        return payload

    @classmethod
    def from_payload(cls, payload: Dict[str, Any]) -> "TierCState":
        """Create TierCState from payload dictionary."""
        # Import here to avoid circular import
        from .states import AgentLog
        
        instance = cls(
            wpd_path=payload.get("wpd_path", ""),
            target_document=payload.get("target_document", payload.get("wpd_path", "")),
            modification_type=payload.get("modification_type", ""),
            creation_context=DocumentCreationContext.from_dict(payload.get("creation_context", {})),
            modified_documents=payload.get("modified_documents", []),
            modifications=payload.get("modifications", []),
            agent_log=AgentLog.from_dict(payload.get("agent_log", {})),
            temporary_content=payload.get("temporary_content", ""),
            documents_to_remove=payload.get("documents_to_remove", []),
            auto_log_entries=payload.get("auto_log_entries", []),
        )
        instance.affected_sections = payload.get("affected_sections", [])
        instance.changes_made = payload.get("changes_made", [])
        instance.validation_passed = payload.get("validation_passed", True)
        return instance
# ============================================================================

@dataclass
class TierDState:
    """
    State model for Tier D: Issue Analysis.
    
    Tier D analyzes errors and failures, identifying root causes and routing decisions.
    
    **Clean API - Use nested dataclass access**:
        tier_d.issue_classification.issue_type
        tier_d.root_cause_analysis.root_cause
        tier_d.resolution_strategy.approach
        tier_d.routing_info.target_tier
    
    **특징**:
    - 각 분석 단계가 명시적으로 구조화됨
    - 라우팅 정보가 명확히 분리됨
    - 하위 데이터 클래스로 재사용성 향상
    
    Attributes:
        issue_description: Description of the issue
        error_details: Detailed error information
        issue_classification: Issue classification result (IssueClassification)
        root_cause_analysis: Root cause analysis result (RootCauseAnalysis)
        resolution_strategy: Resolution strategy (ResolutionStrategy)
        routing_info: Routing decision information (RoutingInfo)
        analysis_metadata: Additional analysis metadata
        analysis_timestamp: Timestamp of analysis
    """
    
    # 원본 데이터
    issue_description: str = ""
    error_details: Dict[str, Any] = field(default_factory=dict)
    
    # 하위 데이터 클래스 (구조화된 분석 결과) - REQUIRED, not optional
    issue_classification: Any = field(default=None)  # IssueClassification from analysis.error.data_models
    root_cause_analysis: Any = field(default=None)   # RootCauseAnalysis from analysis.error.data_models
    resolution_strategy: Any = field(default=None)   # ResolutionStrategy from analysis.error.data_models
    routing_info: Any = field(default=None)          # RoutingInfo from analysis.error.data_models
    
    # 추가 분석 결과 및 메타데이터
    analysis_metadata: Dict[str, Any] = field(default_factory=dict)
    analysis_timestamp: str = ""
    
    def __post_init__(self):
        """Validate that all required structured fields are present."""
        required_fields = {
            "issue_classification": self.issue_classification,
            "root_cause_analysis": self.root_cause_analysis,
            "resolution_strategy": self.resolution_strategy,
            "routing_info": self.routing_info,
        }
        
        none_fields = [name for name, value in required_fields.items() if value is None]
        if none_fields:
            raise ValueError(
                f"TierDState requires all structured fields to be non-None. "
                f"Missing: {', '.join(none_fields)}. "
                f"Backward compatibility is not supported - use structured analysis results."
            )
    
    def to_payload(self) -> Dict[str, Any]:
        """Convert to dictionary payload for AgentState."""
        payload = {
            "issue_description": self.issue_description,
            "error_details": self.error_details,
            "analysis_metadata": self.analysis_metadata,
            "analysis_timestamp": self.analysis_timestamp,
        }
        
        # 하위 데이터 클래스를 dict로 변환
        if self.issue_classification:
            payload["issue_classification"] = (
                self.issue_classification.to_dict() 
                if hasattr(self.issue_classification, 'to_dict')
                else self.issue_classification
            )
        
        if self.root_cause_analysis:
            payload["root_cause_analysis"] = (
                self.root_cause_analysis.to_dict()
                if hasattr(self.root_cause_analysis, 'to_dict')
                else self.root_cause_analysis
            )
        
        if self.resolution_strategy:
            payload["resolution_strategy"] = (
                self.resolution_strategy.to_dict()
                if hasattr(self.resolution_strategy, 'to_dict')
                else self.resolution_strategy
            )
        
        if self.routing_info:
            payload["routing_info"] = (
                self.routing_info.to_dict()
                if hasattr(self.routing_info, 'to_dict')
                else self.routing_info
            )
        
        return payload
    
    @classmethod
    def from_payload(cls, payload: Dict[str, Any]) -> "TierDState":
        """
        Create TierDState from payload dictionary.
        
        This is a DESTRUCTIVE refactor - backward compatibility is NOT maintained.
        All structured fields are REQUIRED and must be present in the payload.
        
        Raises:
            KeyError: If any required structured field is missing from payload
            ValueError: If payload structure is invalid
        """
        # Validate that all required structured fields are present
        required_fields = [
            "issue_classification",
            "root_cause_analysis", 
            "resolution_strategy",
            "routing_info"
        ]
        
        missing_fields = [field for field in required_fields if field not in payload]
        if missing_fields:
            raise KeyError(
                f"TierDState requires structured fields. Missing: {', '.join(missing_fields)}. "
                f"Old unstructured payloads are no longer supported."
            )
        
        # Validate that structured fields are not None
        none_fields = [field for field in required_fields if payload[field] is None]
        if none_fields:
            raise ValueError(
                f"TierDState structured fields cannot be None. Found None in: {', '.join(none_fields)}"
            )
        
        return cls(
            issue_description=payload["issue_description"],
            error_details=payload.get("error_details", {}),
            issue_classification=payload["issue_classification"],
            root_cause_analysis=payload["root_cause_analysis"],
            resolution_strategy=payload["resolution_strategy"],
            routing_info=payload["routing_info"],
            analysis_metadata=payload.get("analysis_metadata", {}),
            analysis_timestamp=payload.get("analysis_timestamp", ""),
        )


# ============================================================================
# Tier E: Document Management
# ============================================================================

@dataclass
class TierEState:
    """
    State model for Tier E: Document Management.
    
    Tier E manages PRD files, synchronization, and document linking.
    
    **Clean API - Use nested dataclass access**:
        tier_e.sources.prd_path  # Access sources fields
        tier_e.sources.wpd_sources
        tier_e.sources.execution_report_path
    
    Attributes:
        sources: Document sources and report paths
        prd_operations: PRD file operations (create, update, sync)
        sync_status: Synchronization status
        document_links: Document linking information
    """
    
    sources: DocumentSources = field(default_factory=DocumentSources)
    
    # Tier E specific fields
    prd_operations: List[Dict[str, Any]] = field(default_factory=list)
    sync_status: Dict[str, str] = field(default_factory=dict)
    document_links: Dict[str, List[str]] = field(default_factory=dict)
    
    def to_payload(self) -> Dict[str, Any]:
        """Convert to dictionary payload for AgentState."""
        return {
            "sources": self.sources.to_dict(),
            "prd_operations": self.prd_operations,
            "sync_status": self.sync_status,
            "document_links": self.document_links,
        }
    
    @classmethod
    def from_payload(cls, payload: Dict[str, Any]) -> "TierEState":
        """Create TierEState from payload dictionary."""
        return cls(
            sources=DocumentSources.from_dict(payload.get("sources", {})),
            prd_operations=payload.get("prd_operations", []),
            sync_status=payload.get("sync_status", {}),
            document_links=payload.get("document_links", {}),
        )


# ============================================================================
# Tier F: Unknown Logic (Fallback)
# ============================================================================

@dataclass
class TierFState:
    """
    State model for Tier F: Unknown Logic (Fallback).
    
    Tier F handles requests that don't fit into other tiers.
    It performs classification and routing to appropriate tiers.
    
    Attributes:
        user_request: Original user request
        classification_results: Results of request classification
        suggested_tier: Suggested tier for routing
        confidence_score: Confidence in the classification
        classification_reasoning: Explanation of classification decision
        routed_to_tier: Tier that request was routed to
        routing_successful: Whether routing succeeded
        requires_clarification: Whether user clarification is needed
        clarification_questions: Questions to ask user for clarification
        fallback_action: Action to take if classification fails
    """
    
    user_request: str = ""
    
    # Tier F specific fields
    classification_results: Dict[str, Any] = field(default_factory=dict)
    suggested_tier: Optional[str] = None
    confidence_score: float = 0.0
    classification_reasoning: str = ""
    routed_to_tier: Optional[str] = None
    routing_successful: bool = False
    requires_clarification: bool = False
    clarification_questions: List[str] = field(default_factory=list)
    fallback_action: str = ""
    
    def to_payload(self) -> Dict[str, Any]:
        """Convert to dictionary payload for AgentState."""
        return {
            "user_request": self.user_request,
            "classification_results": self.classification_results,
            "suggested_tier": self.suggested_tier,
            "confidence_score": self.confidence_score,
            "classification_reasoning": self.classification_reasoning,
            "routed_to_tier": self.routed_to_tier,
            "routing_successful": self.routing_successful,
            "requires_clarification": self.requires_clarification,
            "clarification_questions": self.clarification_questions,
            "fallback_action": self.fallback_action,
        }
    
    @classmethod
    def from_payload(cls, payload: Dict[str, Any]) -> "TierFState":
        """Create TierFState from payload dictionary."""
        return cls(
            user_request=payload.get("user_request", ""),
            classification_results=payload.get("classification_results", {}),
            suggested_tier=payload.get("suggested_tier"),
            confidence_score=payload.get("confidence_score", 0.0),
            classification_reasoning=payload.get("classification_reasoning", ""),
            routed_to_tier=payload.get("routed_to_tier"),
            routing_successful=payload.get("routing_successful", False),
            requires_clarification=payload.get("requires_clarification", False),
            clarification_questions=payload.get("clarification_questions", []),
            fallback_action=payload.get("fallback_action", ""),
        )


class TierStateConverter:
    """Utility class to convert and merge states between tiers.

    Provides minimal conversion helpers used by Tier modules and tests:
    - c_to_a: Convert TierCState -> TierAState for document creation
    - a_to_c: Merge TierA results back into TierCState
    - chain_to_tier: Generic chaining helper (supports C->A and A->C)
    """

    @staticmethod
    def c_to_a(tier_c: "TierCState") -> "TierAState":
        """Convert TierCState to TierAState for creation workflows."""
        Part_N = tier_c.creation_context.creation_parameters.get("Part_N") if tier_c.creation_context and tier_c.creation_context.creation_parameters else None
        parent_doc = tier_c.creation_context.parent_document_path or "docs_2/NextTask-2.md"
        title = tier_c.creation_context.documents_to_create[0] if tier_c.creation_context.documents_to_create else "New-Document"

        tier_a = TierAState()
        tier_a.hierarchy.parent_document = tier_c.target_document or tier_c.wpd_path
        tier_a.main_document_path = parent_doc
        tier_a.current_step = Part_N or ""
        tier_a.metadata.document_title = title
        if Part_N:
            tier_a.metadata.Part_N = str(Part_N)
            tier_a.current_step = str(Part_N)
        # Note: wpd_grade will be set in AgentState, not in tier_a
        return tier_a

    @staticmethod
    def a_to_c(tier_a: "TierAState", original_c: "TierCState") -> "TierCState":
        """Merge TierA creation results into an existing TierCState."""
        updated = original_c
        created = tier_a.created_documents or []

        # Record change
        change_record = {
            "type": "document_creation",
            "created_documents": created,
            "validation_results": getattr(tier_a, "validation_results", {}),
            "timestamp": tier_a.metadata.timestamp if hasattr(tier_a, "metadata") else ""
        }

        updated.changes_made.append(change_record)
        updated.modified_documents.extend(created)
        updated.creation_context.documents_to_create = []

        # Propagate validation status
        if any(not v for v in change_record.get("validation_results", {}).values()):
            updated.validation_passed = False

        return updated

    @staticmethod
    def chain_to_tier(obj, target_tier: str):
        """Generic chaining helper - supports C -> A conversions and a simple check for unsupported transitions."""
        if isinstance(obj, TierCState) and target_tier == "A":
            return TierStateConverter.c_to_a(obj)
        if isinstance(obj, TierAState) and target_tier == "C":
            raise ValueError("Unsupported tier transition: A → C")
        raise ValueError(f"Unsupported tier transition: {type(obj).__name__} → {target_tier}")


__all__ = [
    "TierAState",
    "TierBState",
    "TierCState",
    "TierDState",
    "TierEState",
    "TierFState",
    "TierStateConverter",
]
