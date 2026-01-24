"""
partial_success_handler.py

**Partial Success Handling Module**

Responsibility: Detect and handle partial success scenarios with progressive
enhancement routing to appropriate tiers for completion.

Architecture:
- PartialSuccessType: Classification of partial success scenarios
- PartialSuccessContext: Input context for partial success detection
- ProgressiveAction: Output action for handling partial success
- PartialSuccessHandler: Core detection and routing logic

**Service Layer Module**: MUST follow SRP
**Responsibility**: Partial success detection and progressive enhancement
**Internal Layers**: 2 (Detection, Action)
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any, List
from datetime import datetime


class PartialSuccessType(Enum):
    """Classification of partial success scenarios"""
    INCOMPLETE_DATA = "incomplete_data"           # Missing required data fields
    PARTIAL_EXECUTION = "partial_execution"       # Some steps completed, others failed
    DEGRADED_QUALITY = "degraded_quality"         # Output quality below threshold
    MISSING_VALIDATION = "missing_validation"     # Validation steps skipped
    INCOMPLETE_CHAIN = "incomplete_chain"         # Multi-step process interrupted
    TIMEOUT_PARTIAL = "timeout_partial"           # Partial completion due to timeout
    RESOURCE_CONSTRAINT = "resource_constraint"   # Limited by resources


@dataclass
class PartialSuccessContext:
    """
    Context information for partial success detection.
    
    Contains execution results, expected outcomes, and quality metrics.
    """
    
    # Execution state
    tier: str
    status: str
    payload: Dict[str, Any] = field(default_factory=dict)
    
    # Completion metrics
    completed_steps: List[str] = field(default_factory=list)
    expected_steps: List[str] = field(default_factory=list)
    completion_percentage: float = 0.0
    
    # Quality metrics
    quality_score: float = 1.0  # 0.0 - 1.0
    quality_threshold: float = 0.7
    
    # Validation status
    validation_passed: bool = False
    validation_errors: List[str] = field(default_factory=list)
    
    # Resource usage
    timeout_occurred: bool = False
    resource_exhausted: bool = False
    
    # Metadata
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProgressiveAction:
    """
    Output action for handling partial success.
    
    Specifies routing, retry, or augmentation actions to complete the task.
    """
    
    # Action type
    action_type: str  # "augment", "retry", "fallback", "accept"
    
    # Routing
    next_tier: Optional[str]
    augmentation_tier: Optional[str] = None  # Tier for progressive enhancement
    
    # Reasoning
    partial_type: PartialSuccessType
    reasoning: str
    completion_estimate: float = 0.0  # Estimated completion after action (0.0-1.0)
    
    # Instructions
    augmentation_instructions: str = ""
    preserve_context: bool = True  # Preserve existing payload
    
    # Metadata
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "action_type": self.action_type,
            "next_tier": self.next_tier,
            "augmentation_tier": self.augmentation_tier,
            "partial_type": self.partial_type.value,
            "reasoning": self.reasoning,
            "completion_estimate": self.completion_estimate,
            "augmentation_instructions": self.augmentation_instructions,
            "preserve_context": self.preserve_context,
            "timestamp": self.timestamp
        }


class PartialSuccessHandler:
    """
    Core handler for partial success detection and progressive enhancement.
    
    Detects partial success scenarios and determines optimal actions:
    - Progressive enhancement routing
    - Targeted retry with context preservation
    - Quality augmentation strategies
    - Validation completion routing
    
    Internal Architecture (2 layers):
    1. Detection Layer (detect_partial_success, classify_partial_type)
    2. Action Layer (determine_action, build_augmentation)
    """
    
    # Configuration constants
    DEFAULT_QUALITY_THRESHOLD = 0.7
    MIN_COMPLETION_PERCENTAGE = 0.3
    MAX_AUGMENTATION_ATTEMPTS = 2
    
    # Tier routing for augmentation
    AUGMENTATION_ROUTING = {
        "incomplete_data": "A",      # Re-plan with missing data
        "partial_execution": "B",    # Re-execute incomplete steps
        "degraded_quality": "C",     # Enhance quality
        "missing_validation": "E",   # Complete validation
        "incomplete_chain": "B",     # Resume chain
        "timeout_partial": "B",      # Retry with extended timeout
        "resource_constraint": "D"   # Analyze resource issues
    }
    
    def __init__(self, 
                 quality_threshold: float = DEFAULT_QUALITY_THRESHOLD,
                 min_completion: float = MIN_COMPLETION_PERCENTAGE):
        """
        Initialize partial success handler.
        
        Args:
            quality_threshold: Minimum quality score for acceptance
            min_completion: Minimum completion percentage to consider partial success
        """
        self.quality_threshold = quality_threshold
        self.min_completion = min_completion
        
        # Internal state
        self.augmentation_history: List[ProgressiveAction] = []
    
    # ========================================================================
    # Layer 1: Detection
    # ========================================================================
    
    def detect_partial_success(self, context: PartialSuccessContext) -> bool:
        """
        Detect if execution resulted in partial success.
        
        Partial success criteria:
        - Status is not complete failure
        - Some steps completed but not all
        - Quality below threshold but not zero
        - Validation incomplete
        
        Args:
            context: Partial success context
        
        Returns:
            True if partial success detected
        """
        # Check completion percentage
        if context.expected_steps:
            completion = len(context.completed_steps) / len(context.expected_steps)
        else:
            completion = context.completion_percentage
        
        # Partial if some but not all steps completed
        is_partially_complete = (
            self.min_completion <= completion < 1.0
        )
        
        # Partial if quality degraded
        is_quality_degraded = (
            0 < context.quality_score < self.quality_threshold
        )
        
        # Partial if validation incomplete
        is_validation_incomplete = (
            not context.validation_passed and
            len(context.validation_errors) > 0
        )
        
        # Partial if timeout with some progress
        is_timeout_partial = (
            context.timeout_occurred and completion > 0
        )
        
        return any([
            is_partially_complete,
            is_quality_degraded,
            is_validation_incomplete,
            is_timeout_partial
        ])
    
    def classify_partial_type(self, context: PartialSuccessContext) -> PartialSuccessType:
        """
        Classify the type of partial success.
        
        Args:
            context: Partial success context
        
        Returns:
            PartialSuccessType classification
        """
        # Check timeout
        if context.timeout_occurred:
            return PartialSuccessType.TIMEOUT_PARTIAL
        
        # Check resource constraint
        if context.resource_exhausted:
            return PartialSuccessType.RESOURCE_CONSTRAINT
        
        # Check validation
        if not context.validation_passed and context.validation_errors:
            return PartialSuccessType.MISSING_VALIDATION
        
        # Check quality
        if context.quality_score < self.quality_threshold:
            return PartialSuccessType.DEGRADED_QUALITY
        
        # Check completion
        if context.expected_steps:
            completion = len(context.completed_steps) / len(context.expected_steps)
            if completion < 1.0:
                # Check if it's a chain interruption
                if "next_step" in context.metadata:
                    return PartialSuccessType.INCOMPLETE_CHAIN
                return PartialSuccessType.PARTIAL_EXECUTION
        
        # Check data completeness
        if "missing_fields" in context.metadata:
            return PartialSuccessType.INCOMPLETE_DATA
        
        # Default to partial execution
        return PartialSuccessType.PARTIAL_EXECUTION
    
    # ========================================================================
    # Layer 2: Action Determination
    # ========================================================================
    
    def determine_action(self, context: PartialSuccessContext) -> ProgressiveAction:
        """
        Determine progressive action for partial success.
        
        Main action determination method that:
        1. Detects partial success
        2. Classifies partial type
        3. Determines augmentation strategy
        4. Builds action instructions
        
        Args:
            context: Partial success context
        
        Returns:
            ProgressiveAction with routing and instructions
        """
        # Detect partial success
        if not self.detect_partial_success(context):
            # Not partial - accept as is
            return self._create_accept_action(context)
        
        # Classify partial type
        partial_type = self.classify_partial_type(context)
        
        # Check augmentation attempts
        augmentation_count = self._count_augmentation_attempts(context)
        if augmentation_count >= self.MAX_AUGMENTATION_ATTEMPTS:
            # Too many attempts - fallback
            return self._create_fallback_action(context, partial_type)
        
        # Build augmentation action
        action = self._build_augmentation(context, partial_type)
        
        # Record action
        self.augmentation_history.append(action)
        
        return action
    
    def _build_augmentation(self, context: PartialSuccessContext,
                           partial_type: PartialSuccessType) -> ProgressiveAction:
        """
        Build augmentation action for progressive enhancement.
        
        Args:
            context: Partial success context
            partial_type: Classified partial success type
        
        Returns:
            ProgressiveAction with augmentation instructions
        """
        # Determine augmentation tier
        augmentation_tier = self.AUGMENTATION_ROUTING.get(
            partial_type.value,
            "D"  # Default to Issue Analysis
        )
        
        # Calculate completion estimate
        current_completion = self._calculate_completion(context)
        completion_estimate = min(1.0, current_completion + 0.3)  # Expect 30% improvement
        
        # Build instructions
        instructions = self._build_instructions(context, partial_type)
        
        # Build reasoning
        reasoning = self._build_reasoning(context, partial_type, augmentation_tier)
        
        return ProgressiveAction(
            action_type="augment",
            next_tier=augmentation_tier,
            augmentation_tier=augmentation_tier,
            partial_type=partial_type,
            reasoning=reasoning,
            completion_estimate=completion_estimate,
            augmentation_instructions=instructions,
            preserve_context=True
        )
    
    def _create_accept_action(self, context: PartialSuccessContext) -> ProgressiveAction:
        """Create accept action for sufficient completion"""
        return ProgressiveAction(
            action_type="accept",
            next_tier=None,
            partial_type=PartialSuccessType.PARTIAL_EXECUTION,
            reasoning="Sufficient completion achieved, accepting result",
            completion_estimate=1.0,
            preserve_context=True
        )
    
    def _create_fallback_action(self, context: PartialSuccessContext,
                                partial_type: PartialSuccessType) -> ProgressiveAction:
        """Create fallback action after max augmentation attempts"""
        return ProgressiveAction(
            action_type="fallback",
            next_tier="D",  # Route to Issue Analysis
            partial_type=partial_type,
            reasoning=f"Max augmentation attempts reached, routing to Issue Analysis",
            completion_estimate=self._calculate_completion(context),
            preserve_context=True
        )
    
    # ========================================================================
    # Helper Methods
    # ========================================================================
    
    def _calculate_completion(self, context: PartialSuccessContext) -> float:
        """Calculate overall completion percentage"""
        if context.expected_steps:
            return len(context.completed_steps) / len(context.expected_steps)
        return context.completion_percentage
    
    def _count_augmentation_attempts(self, context: PartialSuccessContext) -> int:
        """Count previous augmentation attempts for this task"""
        return context.metadata.get("augmentation_count", 0)
    
    def _build_instructions(self, context: PartialSuccessContext,
                           partial_type: PartialSuccessType) -> str:
        """Build augmentation instructions"""
        instructions = {
            PartialSuccessType.INCOMPLETE_DATA: "Complete missing data fields: " + 
                ", ".join(context.metadata.get("missing_fields", [])),
            PartialSuccessType.PARTIAL_EXECUTION: "Resume execution from step: " +
                str(len(context.completed_steps) + 1),
            PartialSuccessType.DEGRADED_QUALITY: f"Enhance quality from {context.quality_score:.2f} to {self.quality_threshold:.2f}",
            PartialSuccessType.MISSING_VALIDATION: "Complete validation for: " +
                ", ".join(context.validation_errors),
            PartialSuccessType.INCOMPLETE_CHAIN: "Resume chain from next step",
            PartialSuccessType.TIMEOUT_PARTIAL: "Retry with extended timeout and incremental execution",
            PartialSuccessType.RESOURCE_CONSTRAINT: "Analyze and optimize resource usage"
        }
        
        return instructions.get(partial_type, "Complete remaining tasks")
    
    def _build_reasoning(self, context: PartialSuccessContext,
                        partial_type: PartialSuccessType,
                        augmentation_tier: str) -> str:
        """Build human-readable reasoning"""
        completion = self._calculate_completion(context)
        
        return (
            f"Partial success detected ({partial_type.value}): "
            f"{completion*100:.1f}% complete, "
            f"quality {context.quality_score:.2f}. "
            f"Routing to Tier {augmentation_tier} for progressive enhancement."
        )
    
    def get_augmentation_history(self) -> List[Dict[str, Any]]:
        """Get augmentation history as serializable list"""
        return [a.to_dict() for a in self.augmentation_history]
    
    def clear_history(self):
        """Clear augmentation history"""
        self.augmentation_history.clear()


# ============================================================================
# Utility Functions
# ============================================================================

def create_partial_context(tier: str, status: str,
                          completed_steps: Optional[List[str]] = None,
                          expected_steps: Optional[List[str]] = None,
                          **kwargs) -> PartialSuccessContext:
    """
    Utility function to create PartialSuccessContext.
    
    Args:
        tier: Current tier
        status: Execution status
        completed_steps: List of completed steps
        expected_steps: List of expected steps
        **kwargs: Additional context fields
    
    Returns:
        PartialSuccessContext instance
    """
    return PartialSuccessContext(
        tier=tier,
        status=status,
        completed_steps=completed_steps or [],
        expected_steps=expected_steps or [],
        **kwargs
    )
