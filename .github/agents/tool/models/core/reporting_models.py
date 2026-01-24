"""
Core data models for the entire system (Reporting + Analysis).

**Single Responsibility**: Define all core data structures.
This module is changed only when data structure needs modification.

**Responsibility**:
- Reporting data models (ValidationIssue, SyncResult, FileMetadata)
- Analysis data models (IssueClassification, RootCauseAnalysis, ResolutionStrategy, RoutingInfo)

**Reason to Change**: When data structure requirements change

Migrated from:
- doc_management/mp/reporting.py (reporting models)
- analysis/error/data_models.py (analysis models)

Architecture:
- Minimal, focused dataclasses
- No business logic (moved to formatters/reporters/analyzers)
- Simple helper methods (to_dict/from_dict)
- Type annotations for all fields
- Supports serialization/deserialization
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any, List
from datetime import datetime


@dataclass
class ValidationIssue:
    """
    Validation issue data.

    Represents a single validation issue found during document validation.

    Attributes:
        file_path: Path to the file containing the issue
        severity: Issue severity level ('error', 'warning', 'info')
        message: Human-readable issue description
        line_number: Optional line number where issue occurs
    """

    file_path: str
    severity: str  # error, warning, info
    message: str
    line_number: Optional[int] = None

    def is_error(self) -> bool:
        """Check if this is an error severity issue."""
        return self.severity == "error"

    def is_warning(self) -> bool:
        """Check if this is a warning severity issue."""
        return self.severity == "warning"

    def is_blocking(self) -> bool:
        """Check if this issue is blocking (errors are blocking)."""
        return self.severity == "error"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ValidationIssue":
        """Create from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class SyncResult:
    """
    Synchronization result data.

    Represents the result of a file synchronization operation.

    Attributes:
        file_path: Path to the synchronized file
        status: Sync status ('synced', 'skipped', 'failed')
        details: Additional details about the sync operation
        changes_count: Number of changes applied during sync
    """

    file_path: str
    status: str  # synced, skipped, failed
    details: str = ""
    changes_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SyncResult":
        """Create from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class FileMetadata:
    """
    File metadata information.

    Represents metadata for a document file in the system.

    Attributes:
        file_path: Path to the file
        purpose: Purpose/role of the file
        scope: Scope of the file (project, module, etc.)
        current_line: Current line count in the file
        related_project: Related project name (optional)
    """

    file_path: str
    purpose: str
    scope: str
    current_line: int
    related_project: str = ""

    def is_oversized(self, limit: int = 500) -> bool:
        """
        Check if file exceeds line limit.

        Args:
            limit: Line count limit (default: 500)

        Returns:
            True if file exceeds limit, False otherwise
        """
        return self.current_line > limit

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FileMetadata":
        """Create from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class IssueClassification:
    """
    이슈 분류 결과

    Examples:
        classification = IssueClassification(
            issue_type="bug",
            severity="high",
            confidence_score=0.95,
            keywords=["error", "exception", "ValueError"],
            category="implementation_error"
        )
    """

    issue_type: str = ""  # bug, design_flaw, implementation, documentation, unknown
    severity: str = "medium"  # critical, high, medium, low
    confidence_score: float = 0.0  # 0.0 ~ 1.0
    keywords: List[str] = field(default_factory=list)
    category: str = ""  # 세부 카테고리

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "IssueClassification":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class RootCauseAnalysis:
    """
    근본원인 분석 결과

    Examples:
        analysis = RootCauseAnalysis(
            root_cause="Missing type check in the new implementation",
            affected_components=["module_x.py", "util.py"],
            error_context={"line": 42, "function": "process_data"},
            evidence=["TypeError at line 42", "No validation before use"],
            confidence_level="high"
        )
    """

    root_cause: str = ""
    affected_components: List[str] = field(default_factory=list)
    error_context: Dict[str, Any] = field(default_factory=dict)
    evidence: List[str] = field(default_factory=list)
    confidence_level: str = "medium"  # high, medium, low
    analysis_timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RootCauseAnalysis":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class ResolutionStrategy:
    """
    해결 전략

    Examples:
        strategy = ResolutionStrategy(
            approach="fix_implementation",
            estimated_effort="medium",
            target_tier="C",
            wpd_grade="L1",
            priority=3,
            dependencies=["test_review"],
            rollback_plan="Revert to previous commit",
            auto_resolve_flag=True
        )

    Field Nesting Rules Compliance:
        - auto_resolve_flag: New field for automatic resolution capability
        - No role overlap with existing fields (unique purpose: automation decision)
        - Different from target_tier (which is destination, not automation flag)
        - Different from approach (which is method, not automation capability)
    """

    approach: str = ""  # fix_implementation, refactor, redesign, document, investigate
    estimated_effort: str = "medium"  # low, medium, high
    target_tier: str = ""  # A, B, C, E, F
    wpd_grade: str = "L0"  # L0, L1, L2, L3
    priority: int = 5  # 1~10 (높을수록 우선)
    dependencies: List[str] = field(default_factory=list)
    rollback_plan: str = ""
    estimated_duration_hours: float = 0.0

    # New field for automatic resolution chain (Proposal 1)
    auto_resolve_flag: bool = (
        False  # True if issue can be auto-resolved via D → C → B chain
    )

    # New fields for enhanced routing context (Proposal 2)
    # Following nesting rules: same destination, different types → combined into list
    routing_contexts: List[Dict[str, Any]] = field(
        default_factory=list
    )  # Multiple contexts for same destination
    message_type: str = (
        ""  # Single field: message categorization (e.g., "error", "warning", "info")
    )
    confidence_thresholds: Dict[str, float] = field(
        default_factory=lambda: {"auto_resolve": 0.85}
    )  # Configurable thresholds

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ResolutionStrategy":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class RoutingInfo:
    """
    라우팅 결정 정보 (Tier D의 최종 결정)

    Examples:
        routing = RoutingInfo(
            target_tier="C",
            routing_reason="Implementation error in existing code - requires modification",
            routing_confidence=0.95,
            requires_clarification=False,
            metadata={"analysis_steps": 3, "processing_time_ms": 245}
        )
    """

    target_tier: str = ""  # A, B, C, E, F
    routing_reason: str = ""  # 라우팅 이유
    routing_confidence: float = 0.0  # 0.0 ~ 1.0
    requires_clarification: bool = False
    clarification_questions: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    routing_timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RoutingInfo":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


__all__ = [
    # Reporting models
    "ValidationIssue",
    "SyncResult",
    "FileMetadata",
    # Analysis models
    "IssueClassification",
    "RootCauseAnalysis",
    "ResolutionStrategy",
    "RoutingInfo",
]
