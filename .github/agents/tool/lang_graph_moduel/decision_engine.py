"""
decision_engine.py

**Decision Engine Module**

Responsibility: Intelligent routing decisions based on multiple factors including
confidence, cost, failure history, and policy rules.

Architecture:
- ConfidenceLevel: Enumeration of confidence levels
- FailureType: Classification of failures (transient vs permanent)
- DecisionContext: Input context for decision making
- RoutingDecision: Decision output with confidence and reasoning
- DecisionEngine: Core decision evaluation logic

**Service Layer Module**: MUST follow SRP
**Responsibility**: Decision evaluation and routing recommendations
**Internal Layers**: 3 (Context, Decision, Engine)
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any, List
from datetime import datetime
import time


class ConfidenceLevel(Enum):
    """Confidence level classification for routing decisions"""
    VERY_LOW = 0.2   # Requires human approval
    LOW = 0.4        # May trigger additional validation
    MEDIUM = 0.6     # Standard confidence
    HIGH = 0.8       # High confidence automatic routing
    VERY_HIGH = 0.95 # Extremely high confidence
    
    @classmethod
    def from_score(cls, score: float) -> "ConfidenceLevel":
        """Convert confidence score to level"""
        if score >= 0.9:
            return cls.VERY_HIGH
        elif score >= 0.75:
            return cls.HIGH
        elif score >= 0.55:
            return cls.MEDIUM
        elif score >= 0.35:
            return cls.LOW
        else:
            return cls.VERY_LOW


class FailureType(Enum):
    """Classification of failure types for retry logic"""
    TRANSIENT = "transient"      # Retryable (network timeout, rate limit)
    PERMANENT = "permanent"       # Non-retryable (404, invalid input, logic error)
    UNKNOWN = "unknown"           # Unclassified - conservative retry
    CIRCUIT_OPEN = "circuit_open" # Circuit breaker is open


@dataclass
class DecisionContext:
    """
    Context information for decision making.
    
    Contains all relevant information needed to make routing decisions including
    current state, history, costs, and constraints.
    """
    
    # Current state
    tier: str
    status: str
    user_input: str
    payload: Dict[str, Any] = field(default_factory=dict)
    
    # History and performance
    retry_count: int = 0
    previous_failures: List[str] = field(default_factory=list)
    execution_time_ms: float = 0.0
    
    # Cost and resources
    estimated_cost: float = 0.0
    available_credit: float = float('inf')
    
    # Policies and constraints
    max_retries: int = 3
    confidence_threshold: float = 0.5
    require_human_approval: bool = False
    
    # Additional metadata
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RoutingDecision:
    """
    Output of decision evaluation.
    
    Contains the routing decision, confidence level, reasoning, and any
    special handling instructions (retry, human approval, etc.)
    """
    
    # Core decision
    next_tier: Optional[str]
    confidence: float
    confidence_level: ConfidenceLevel
    
    # Reasoning
    reasoning: str
    decision_factors: Dict[str, Any] = field(default_factory=dict)
    
    # Special handling
    requires_human_approval: bool = False
    requires_retry: bool = False
    retry_delay_ms: int = 0
    
    # Failure handling
    failure_type: Optional[FailureType] = None
    fallback_tier: Optional[str] = None
    
    # Cost and resources
    estimated_cost: float = 0.0
    
    # Metadata
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "next_tier": self.next_tier,
            "confidence": self.confidence,
            "confidence_level": self.confidence_level.name,
            "reasoning": self.reasoning,
            "decision_factors": self.decision_factors,
            "requires_human_approval": self.requires_human_approval,
            "requires_retry": self.requires_retry,
            "retry_delay_ms": self.retry_delay_ms,
            "failure_type": self.failure_type.value if self.failure_type else None,
            "fallback_tier": self.fallback_tier,
            "estimated_cost": self.estimated_cost,
            "timestamp": self.timestamp
        }


class DecisionEngine:
    """
    Core decision engine for intelligent tier routing.
    
    Evaluates multiple factors to make optimal routing decisions:
    - Routing confidence from state and context
    - Failure type classification for retry logic
    - Cost-aware routing and budget constraints
    - Policy-based decision rules
    - Circuit breaker integration
    
    Internal Architecture (3 layers):
    1. Context Analysis (analyze_context)
    2. Decision Evaluation (evaluate_routing, classify_failure)
    3. Decision Assembly (assemble_decision)
    """
    
    # Configuration constants
    DEFAULT_CONFIDENCE_THRESHOLD = 0.5
    HUMAN_APPROVAL_THRESHOLD = 0.4
    MAX_RETRIES = 3
    BASE_RETRY_DELAY_MS = 1000  # 1 second
    
    # Failure pattern database
    TRANSIENT_ERROR_PATTERNS = [
        "timeout", "connection", "network", "503", "504", "429",
        "rate limit", "temporary", "unavailable", "retry"
    ]
    
    PERMANENT_ERROR_PATTERNS = [
        "404", "400", "401", "403", "invalid", "not found",
        "unauthorized", "forbidden", "bad request", "validation"
    ]
    
    def __init__(self, 
                 confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
                 max_retries: int = MAX_RETRIES,
                 base_retry_delay_ms: int = BASE_RETRY_DELAY_MS):
        """
        Initialize decision engine.
        
        Args:
            confidence_threshold: Minimum confidence for automatic routing
            max_retries: Maximum retry attempts for transient failures
            base_retry_delay_ms: Base delay for exponential backoff
        """
        self.confidence_threshold = confidence_threshold
        self.max_retries = max_retries
        self.base_retry_delay_ms = base_retry_delay_ms
        
        # Internal state
        self.decision_history: List[RoutingDecision] = []
        
    # ========================================================================
    # Layer 1: Context Analysis
    # ========================================================================
    
    def analyze_context(self, context: DecisionContext) -> Dict[str, Any]:
        """
        Analyze decision context and extract relevant factors.
        
        Returns:
            Dictionary of analyzed factors
        """
        factors = {
            "has_retry_capacity": context.retry_count < context.max_retries,
            "within_budget": context.estimated_cost <= context.available_credit,
            "has_failures": len(context.previous_failures) > 0,
            "execution_slow": context.execution_time_ms > 5000,  # 5 seconds
            "status_success": context.status == "SUCCESS",
            "status_failed": context.status == "FAILED",
            "status_partial": context.status == "PARTIAL"
        }
        
        return factors
    
    # ========================================================================
    # Layer 2: Decision Evaluation
    # ========================================================================
    
    def calculate_confidence(self, context: DecisionContext, 
                            factors: Dict[str, Any]) -> float:
        """
        Calculate routing confidence based on context and factors.
        
        Confidence factors:
        - Status success/failure
        - Retry history
        - Execution performance
        - Previous failures
        
        Returns:
            Confidence score (0.0 - 1.0)
        """
        confidence = 0.5  # Base confidence
        
        # Status-based adjustments
        if factors["status_success"]:
            confidence += 0.3
        elif factors["status_failed"]:
            confidence -= 0.3
        elif factors["status_partial"]:
            confidence += 0.1
        
        # Retry history penalty
        if context.retry_count > 0:
            confidence -= 0.1 * context.retry_count
        
        # Failure history penalty
        if factors["has_failures"]:
            confidence -= 0.05 * len(context.previous_failures)
        
        # Performance penalty
        if factors["execution_slow"]:
            confidence -= 0.1
        
        # Clamp to valid range
        return max(0.0, min(1.0, confidence))
    
    def classify_failure(self, error_message: str) -> FailureType:
        """
        Classify failure type from error message.
        
        Args:
            error_message: Error message to analyze
        
        Returns:
            FailureType classification
        """
        error_lower = error_message.lower()
        
        # Check transient patterns
        if any(pattern in error_lower for pattern in self.TRANSIENT_ERROR_PATTERNS):
            return FailureType.TRANSIENT
        
        # Check permanent patterns
        if any(pattern in error_lower for pattern in self.PERMANENT_ERROR_PATTERNS):
            return FailureType.PERMANENT
        
        # Conservative default - allow retry for unknown errors
        return FailureType.UNKNOWN
    
    def determine_retry_eligibility(self, context: DecisionContext,
                                   failure_type: FailureType) -> bool:
        """
        Determine if retry should be attempted.
        
        Args:
            context: Decision context
            failure_type: Classified failure type
        
        Returns:
            True if retry should be attempted
        """
        # No retry if max retries reached
        if context.retry_count >= context.max_retries:
            return False
        
        # No retry for permanent failures
        if failure_type == FailureType.PERMANENT:
            return False
        
        # No retry if circuit breaker open
        if failure_type == FailureType.CIRCUIT_OPEN:
            return False
        
        # Retry for transient and unknown failures
        return failure_type in (FailureType.TRANSIENT, FailureType.UNKNOWN)
    
    def calculate_backoff_delay(self, retry_count: int) -> int:
        """
        Calculate exponential backoff delay.
        
        Formula: base_delay * (2 ^ retry_count)
        
        Args:
            retry_count: Current retry attempt number
        
        Returns:
            Delay in milliseconds
        """
        return int(self.base_retry_delay_ms * (2 ** retry_count))
    
    # ========================================================================
    # Layer 3: Decision Assembly
    # ========================================================================
    
    def evaluate_routing(self, context: DecisionContext) -> RoutingDecision:
        """
        Evaluate routing decision based on context.
        
        Main decision evaluation method that:
        1. Analyzes context
        2. Calculates confidence
        3. Determines routing
        4. Assembles final decision
        
        Args:
            context: Decision context
        
        Returns:
            RoutingDecision with next tier and metadata
        """
        # Layer 1: Analyze context
        factors = self.analyze_context(context)
        
        # Layer 2: Calculate confidence
        confidence = self.calculate_confidence(context, factors)
        confidence_level = ConfidenceLevel.from_score(confidence)
        
        # Determine next tier based on payload or default routing
        next_tier = self._determine_next_tier(context, factors)
        
        # Check if human approval required
        requires_human = (
            confidence < self.HUMAN_APPROVAL_THRESHOLD or
            context.require_human_approval
        )
        
        # Build reasoning
        reasoning = self._build_reasoning(context, factors, confidence)
        
        # Assemble decision
        decision = RoutingDecision(
            next_tier=next_tier,
            confidence=confidence,
            confidence_level=confidence_level,
            reasoning=reasoning,
            decision_factors=factors,
            requires_human_approval=requires_human,
            estimated_cost=context.estimated_cost
        )
        
        # Record decision
        self.decision_history.append(decision)
        
        return decision
    
    def evaluate_failure(self, context: DecisionContext,
                        error_message: str) -> RoutingDecision:
        """
        Evaluate failure and determine retry or fallback routing.
        
        Args:
            context: Decision context
            error_message: Error message from failure
        
        Returns:
            RoutingDecision with retry or fallback instructions
        """
        # Classify failure
        failure_type = self.classify_failure(error_message)
        
        # Check retry eligibility
        should_retry = self.determine_retry_eligibility(context, failure_type)
        
        # Calculate backoff if retry
        retry_delay = 0
        if should_retry:
            retry_delay = self.calculate_backoff_delay(context.retry_count)
        
        # Determine routing
        if should_retry:
            next_tier = context.tier  # Retry same tier
            reasoning = f"Transient failure detected, retrying (attempt {context.retry_count + 1}/{self.max_retries})"
        else:
            next_tier = "D"  # Route to Issue Analysis
            reasoning = f"Permanent or max retries reached, routing to Issue Analysis"
        
        # Build decision
        decision = RoutingDecision(
            next_tier=next_tier,
            confidence=0.3,  # Low confidence on failure
            confidence_level=ConfidenceLevel.LOW,
            reasoning=reasoning,
            decision_factors={"failure_type": failure_type.value},
            requires_retry=should_retry,
            retry_delay_ms=retry_delay,
            failure_type=failure_type,
            fallback_tier="D"
        )
        
        self.decision_history.append(decision)
        
        return decision
    
    # ========================================================================
    # Helper Methods
    # ========================================================================
    
    def _determine_next_tier(self, context: DecisionContext,
                            factors: Dict[str, Any]) -> Optional[str]:
        """Determine next tier from context or default routing"""
        # Check if next_node specified in payload
        if "next_node" in context.payload:
            return context.payload["next_node"]
        
        # Default routing based on current tier and status
        if context.tier == "A" and factors["status_success"]:
            return "B"  # Create Plan → Execute Plan
        elif context.tier == "B" and factors["status_success"]:
            return "E"  # Execute Plan → Document Management
        elif context.tier == "C" and factors["status_success"]:
            return "E"  # Modify Plan → Document Management
        elif factors["status_failed"]:
            return "D"  # Any failure → Issue Analysis
        
        return None  # End of chain
    
    def _build_reasoning(self, context: DecisionContext,
                        factors: Dict[str, Any],
                        confidence: float) -> str:
        """Build human-readable reasoning for decision"""
        reasons = []
        
        if factors["status_success"]:
            reasons.append("successful execution")
        elif factors["status_failed"]:
            reasons.append("execution failed")
        elif factors["status_partial"]:
            reasons.append("partial success")
        
        if context.retry_count > 0:
            reasons.append(f"retry attempt {context.retry_count}")
        
        if factors["has_failures"]:
            reasons.append(f"{len(context.previous_failures)} previous failures")
        
        if confidence < self.confidence_threshold:
            reasons.append("low confidence")
        
        return f"Routing decision based on: {', '.join(reasons)}"
    
    def get_decision_history(self) -> List[Dict[str, Any]]:
        """Get decision history as serializable list"""
        return [d.to_dict() for d in self.decision_history]
    
    def clear_history(self):
        """Clear decision history"""
        self.decision_history.clear()


# ============================================================================
# Utility Functions
# ============================================================================

def create_decision_context(tier: str, status: str, user_input: str,
                           payload: Optional[Dict[str, Any]] = None,
                           **kwargs) -> DecisionContext:
    """
    Utility function to create DecisionContext.
    
    Args:
        tier: Current tier
        status: Execution status
        user_input: User input text
        payload: Optional payload dictionary
        **kwargs: Additional context fields
    
    Returns:
        DecisionContext instance
    """
    return DecisionContext(
        tier=tier,
        status=status,
        user_input=user_input,
        payload=payload or {},
        **kwargs
    )
