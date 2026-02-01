"""
Type definitions and enums for the 6-tier task orchestration system.

**Single Responsibility**: Define all type enumerations used across the system.
This module is changed only when new tier types, status types, or WPD grades are added.

**Responsibility**: Type enumeration definitions
**Reason to Change**: When new tier types, status values, or WPD grades are introduced
"""

from enum import Enum
from typing import Literal


class TierType(str, Enum):
    """
    Enumeration of the 6 orchestration tiers.
    
    Tiers represent different types of tasks in the system:
    - A: Work Plan Creation (WPD generation from user requests)
    - B: Plan Execution (Execute plans and generate results)
    - C: Plan Modification (Edit existing WPD documents)
    - D: Issue Analysis (Analyze errors and failures)
    - E: Document Management (Manage PRD files and synchronization)
    - F: Unknown Logic (Fallback for unclassified requests)
    """
    A_PLAN_CREATION = "A"
    B_PLAN_EXECUTION = "B"
    C_PLAN_MODIFICATION = "C"
    D_ISSUE_ANALYSIS = "D"
    E_DOCUMENT_MANAGEMENT = "E"
    F_UNKNOWN_LOGIC = "F"


class StatusType(str, Enum):
    """
    Enumeration of execution status values.
    
    Represents the outcome or state of tier execution:
    - SUCCESS: Task completed successfully
    - FAILED: Task execution failed (errors occurred)
    - PENDING: Task is waiting for execution
    - RETRY: Task execution should be retried
    - PARTIAL: Task partially completed (some steps succeeded)
    """
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    PENDING = "PENDING"
    RETRY = "RETRY"
    PARTIAL = "PARTIAL"


class WPDGrade(str, Enum):
    """
    Enumeration of WPD (Work Plan Document) grades.
    
    Represents hierarchical levels of work plan documents:
    - L0: Main work plan (top-level task coordination)
    - L1: Executive level (high-level planning with phases)
    - L2: Phase level (detailed phase implementation)
    - L3: Subphase level (concrete implementation steps)
    """
    L0 = "L0"
    L1 = "L1"
    L2 = "L2"
    L3 = "L3"


# Type aliases for common literal types
TierTypeValue = Literal["A", "B", "C", "D", "E", "F"]
StatusTypeValue = Literal["SUCCESS", "FAILED", "PENDING", "RETRY", "PARTIAL"]
WPDGradeValue = Literal["L0", "L1", "L2", "L3"]

# Document type values
DocumentTypeValue = Literal["WPD", "PRD"]

# Status emoji mapping
STATUS_EMOJI_MAP = {
    "PENDING": "📋",
    "IN_PROGRESS": "🔄",
    "COMPLETE": "✅",
    "FAILED": "❌",
}

# WPD Grade hierarchy
WPD_GRADE_HIERARCHY = {
    "L0": 0,  # Main work plan
    "L1": 1,  # Executive level
    "L2": 2,  # Phase level
    "L3": 3,  # Subphase level
}


class EventType(str, Enum):
    """
    Enumeration of event types for the decision rules system.
    
    Decision Flow Events:
    - DECISION_REQUIRED: Low confidence or ambiguous routing
    - DECISION_PROVIDED: External decision input received
    - CONFIDENCE_LOW: Confidence below threshold
    - CONFIDENCE_HIGH: High confidence routing
    
    Retry and Failure Events:
    - RETRY_ATTEMPTED: Tier execution retry
    - RETRY_EXHAUSTED: Max retries reached
    - CIRCUIT_BREAKER_OPEN: Circuit breaker activated
    - CIRCUIT_BREAKER_CLOSED: Circuit breaker reset
    
    Partial Success Events:
    - PARTIAL_SUCCESS: Partial completion
    - PROGRESSIVE_ENHANCEMENT: Augmentation tier routing
    
    Policy and Routing Events:
    - POLICY_EVALUATED: Policy rule evaluated
    - ROUTE_OVERRIDE: Manual route override
    - COST_LIMIT_REACHED: Credit budget exceeded
    
    Tier Execution Events:
    - TIER_STARTED: Tier execution began
    - TIER_COMPLETED: Tier execution finished
    - TIER_FAILED: Tier execution failed
    """
    # Decision flow events
    DECISION_REQUIRED = "DECISION_REQUIRED"
    DECISION_PROVIDED = "DECISION_PROVIDED"
    CONFIDENCE_LOW = "CONFIDENCE_LOW"
    CONFIDENCE_HIGH = "CONFIDENCE_HIGH"
    
    # Retry and failure events
    RETRY_ATTEMPTED = "RETRY_ATTEMPTED"
    RETRY_EXHAUSTED = "RETRY_EXHAUSTED"
    CIRCUIT_BREAKER_OPEN = "CIRCUIT_BREAKER_OPEN"
    CIRCUIT_BREAKER_CLOSED = "CIRCUIT_BREAKER_CLOSED"
    
    # Partial success events
    PARTIAL_SUCCESS = "PARTIAL_SUCCESS"
    PROGRESSIVE_ENHANCEMENT = "PROGRESSIVE_ENHANCEMENT"
    
    # Policy and routing events
    POLICY_EVALUATED = "POLICY_EVALUATED"
    ROUTE_OVERRIDE = "ROUTE_OVERRIDE"
    COST_LIMIT_REACHED = "COST_LIMIT_REACHED"
    
    # Tier execution events
    TIER_STARTED = "TIER_STARTED"
    TIER_COMPLETED = "TIER_COMPLETED"
    TIER_FAILED = "TIER_FAILED"


__all__ = [
    "TierType",
    "StatusType",
    "WPDGrade",
    "EventType",
    "TierTypeValue",
    "StatusTypeValue",
    "WPDGradeValue",
    "DocumentTypeValue",
    "STATUS_EMOJI_MAP",
    "WPD_GRADE_HIERARCHY",
]
