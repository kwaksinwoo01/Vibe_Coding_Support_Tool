"""
AgentState model for workflow orchestration.

**Single Responsibility**: Represent the execution state and results of a tier.
This module is changed only when the agent state structure itself needs modification.

**Responsibility**: AgentState data model
**Reason to Change**: When the core state structure (tier, status, payload) needs modification

Note: Serialization, factory methods, and tier conversion are in separate modules:
- Serialization: serializers/agent_state_serializer.py
- Factory methods: builders/agent_state_builder.py
- Tier conversion: converters/tier_converters.py
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any, List, Literal
from datetime import datetime, timezone

from .types import StatusType, TierType


@dataclass
class AgentState:
    """
    Unified state and result model for all orchestration tiers (A-F).
    
    This dataclass represents the execution state of a single tier and is passed
    to the next tier for chaining. Each tier module returns an AgentState instance
    which is emitted to stdout in JSON format for the orchestrator to process.
    
    **Responsibility**: Represent the execution state (not serialize, build, or convert)
    
    **Architecture - Field Organization**:
    - Common fields (used by ALL tiers): tier, status, logic_summary, next_node, 
      payload, execution_log, wpd_grade, wpd_source_path, execution_time_ms, 
      errors, warnings, timestamp
    - Tier-specific fields: Stored in payload dict, managed by TierXState classes
    - Nested dataclasses (metadata, hierarchy, sources): Only in TierXState, 
      serialized into payload
    
    Attributes:
        tier: Current executing tier (A, B, C, D, E, F)
        status: Execution result (SUCCESS, FAILED, PENDING, RETRY, PARTIAL)
        logic_summary: Human-readable execution summary for the orchestrator
        next_node: Next tier to execute (None if chain ends)
        
        # Payload and context
        payload: Tier-specific execution data (generic Dict)
                 Contains tier-specific state serialized from TierXState.to_payload()
                 - TierAState: Document creation state and results
                 - TierBState: Plan execution state and phase results
                 - TierCState: Document modification state and changes
                 - TierDState: Issue analysis state and suggested fixes
                 - TierEState: Document management state and operations
                 - TierFState: Classification state and routing information
        
        # Common tier fields (shared across ALL tiers)
        execution_log: Execution log messages
        wpd_grade: WPD grade level (L0, L1, L2, L3)
        wpd_source_path: Source WPD document path
        
        # Metadata
        execution_time_ms: Time spent in this tier (milliseconds)
        errors: List of error messages
        warnings: List of warning messages
        timestamp: Execution timestamp (ISO 8601)
        
        # Debugging and decision tracking
        decision_trace: Decision-making trace for debugging
        confidence: Routing confidence (0.0-1.0)
        retry_count: Number of retry attempts
    """
    
    tier: Literal["A", "B", "C", "D", "E", "F"]
    status: Literal["SUCCESS", "FAILED", "PENDING", "RETRY", "PARTIAL"]
    logic_summary: str = ""
    next_node: Optional[str] = None
    
    # Payload and context (tier-specific data)
    payload: Dict[str, Any] = field(default_factory=dict)
    
    # Common tier fields (shared across ALL tiers)
    execution_log: List[str] = field(default_factory=list)
    wpd_grade: str = "L1"  # WPD grade level (L0, L1, L2, L3)
    wpd_source_path: str = ""  # Source WPD document path
    
    # Execution metadata
    execution_time_ms: float = 0.0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    
    # Decision tracking (for automated decision rules)
    confidence: float = 0.5  # Routing confidence (0.0-1.0)
    decision_trace: List[Dict[str, Any]] = field(default_factory=list)
    retry_count: int = 0
    
    def add_error(self, error_msg: str) -> "AgentState":
        """Add an error message to the errors list."""
        self.errors.append(error_msg)
        return self
    
    def add_warning(self, warning_msg: str) -> "AgentState":
        """Add a warning message to the warnings list."""
        self.warnings.append(warning_msg)
        return self
    
    def set_next_node(self, next_tier: Optional[str], reason: str = "") -> "AgentState":
        """Set the next tier to execute."""
        self.next_node = next_tier
        if reason:
            self.add_decision("routing", {"next_tier": next_tier, "reason": reason})
        return self
    
    def set_execution_time(self, elapsed_ms: float) -> "AgentState":
        """Set the execution time in milliseconds."""
        self.execution_time_ms = elapsed_ms
        return self
    
    def add_decision(self, decision_type: str, details: Dict[str, Any]) -> "AgentState":
        """
        Add decision to trace for audit and debugging.
        
        Args:
            decision_type: Type of decision (e.g., "routing", "retry", "human_approval")
            details: Decision details and reasoning
        
        Returns:
            Self for chaining
        """
        decision_entry = {
            "type": decision_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "details": details
        }
        self.decision_trace.append(decision_entry)
        return self
    
    def set_confidence(self, confidence: float) -> "AgentState":
        """
        Set routing confidence score.
        
        Args:
            confidence: Confidence score (0.0 - 1.0)
        
        Returns:
            Self for chaining
        """
        self.confidence = max(0.0, min(1.0, confidence))
        return self
    
    def increment_retry(self) -> "AgentState":
        """
        Increment retry count.
        
        Returns:
            Self for chaining
        """
        self.retry_count += 1
        return self
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        return data
    
    @property
    def is_success(self) -> bool:
        """Check if execution was successful."""
        return self.status == StatusType.SUCCESS.value
    
    @property
    def is_failed(self) -> bool:
        """Check if execution failed."""
        return self.status == StatusType.FAILED.value
    
    @property
    def has_errors(self) -> bool:
        """Check if there are any errors."""
        return len(self.errors) > 0
    
    @property
    def has_warnings(self) -> bool:
        """Check if there are any warnings."""
        return len(self.warnings) > 0
    
    @classmethod
    def create_failure(cls, tier: str, error_msg: str, logic_summary: str = "") -> "AgentState":
        """
        Create a failed AgentState with an error message.
        
        Args:
            tier: Tier identifier
            error_msg: Error message
            logic_summary: Optional summary of what failed
        
        Returns:
            AgentState with FAILED status
        """
        return cls(
            tier=tier,
            status="FAILED",
            logic_summary=logic_summary or f"Error in tier {tier}",
            errors=[error_msg]
        )
    
    @classmethod
    def create_success(cls, tier: str, logic_summary: str = "", 
                      payload: Optional[Dict[str, Any]] = None,
                      next_node: Optional[str] = None) -> "AgentState":
        """
        Create a successful AgentState.
        
        Args:
            tier: Tier identifier
            logic_summary: Summary of what was accomplished
            payload: Tier-specific data payload
            next_node: Next tier to execute (for chaining)
        
        Returns:
            AgentState with SUCCESS status
        """
        return cls(
            tier=tier,
            status="SUCCESS",
            logic_summary=logic_summary or f"Tier {tier} completed successfully",
            payload=payload or {},
            next_node=next_node
        )
    
    def emit(self):
        """
        Emit AgentState as JSON to stdout for orchestrator consumption.
        Prints formatted JSON with marker for parsing.
        """
        import json
        print("\n---AGENT_STATE_DATA---")
        print(json.dumps({"data": self.to_dict()}, indent=2))

@dataclass
class AgentLog:
    """
    Execution log for agent operations.
    
    Used across all 6 tiers to track execution steps and decisions.
    
    **Responsibility**: Centralized execution logging
    **Reason to Change**: When logging structure needs modification
    
    Attributes:
        execution_log: List of timestamped log messages
        changes_made: List of change records with metadata
    """
    execution_log: List[str] = field(default_factory=list)
    changes_made: List[Dict[str, Any]] = field(default_factory=list)
    
    def add_entry(self, message: str, timestamp: Optional[str] = None) -> None:
        """Add log entry with timestamp."""
        from datetime import datetime
        ts = timestamp or datetime.now().strftime("%H:%M:%S")
        log_msg = f"[{ts}] {message}"
        self.execution_log.append(log_msg)
        self.changes_made.append({"timestamp": ts, "message": message})
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentLog":
        """Create from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

__all__ = ["AgentState", "AgentLog"]
