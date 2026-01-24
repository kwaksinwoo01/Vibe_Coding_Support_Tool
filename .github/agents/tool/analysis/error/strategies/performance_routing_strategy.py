"""
Performance routing strategy.

Handles routing for performance-related issues (new strategy).
"""

from typing import Dict
from .base import RoutingStrategy
from models.core.reporting_models import (
    IssueClassification,
    ResolutionStrategy,
    RoutingInfo,
)


class PerformanceRoutingStrategy(RoutingStrategy):
    """
    Routing strategy for performance issues.

    New strategy following existing patterns:
    - optimization → C (code modification)
    - scaling → A (architectural change)
    - resource → B (re-execution with proper resources)
    """

    # Performance-specific routing rules (new)
    PERFORMANCE_ROUTING_RULES: Dict[str, str] = {
        "optimization": "C",  # Tier C: code optimization
        "scaling": "A",  # Tier A: architectural scaling plan
        "resource": "B",  # Tier B: re-execute with resources
    }

    def can_handle(self, issue_type: str) -> bool:
        """Check if this strategy handles performance issues."""
        return issue_type == "performance"

    def decide_routing(
        self, classification: IssueClassification, strategy: ResolutionStrategy
    ) -> RoutingInfo:
        """
        Decide routing for performance issues.

        Args:
            classification: Issue classification with performance type
            strategy: Resolution strategy

        Returns:
            RoutingInfo with target tier and metadata
        """
        category = classification.category or "optimization"

        # Apply performance routing rules
        target_tier = self.PERFORMANCE_ROUTING_RULES.get(category, "C")  # Default to C

        # Calculate confidence
        confidence = self._calculate_routing_confidence(
            classification.confidence_score, strategy
        )

        # Generate routing reason
        routing_reason = f"Performance issue ({category}). Optimization required."

        # Generate metadata
        metadata = self._generate_metadata(classification, strategy)

        return RoutingInfo(
            target_tier=target_tier,
            routing_reason=routing_reason,
            routing_confidence=confidence,
            requires_clarification=confidence < 0.7,
            clarification_questions=self._generate_clarification_questions(
                classification.issue_type, confidence
            ),
            metadata=metadata,
        )
