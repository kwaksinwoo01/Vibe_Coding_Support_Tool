"""
Fallback routing strategy.

Handles unknown or unclassified issues, reusing TIER_D_ROUTING_RULES fallback logic.
"""

from .base import RoutingStrategy
from models.core.reporting_models import (
    IssueClassification,
    ResolutionStrategy,
    RoutingInfo,
)


class FallbackRoutingStrategy(RoutingStrategy):
    """
    Fallback routing strategy for unknown or unhandled issue types.

    Routes to:
    - implementation → C (plan modification)
    - documentation → E (document management)
    - unknown → F (re-classification)
    """

    def can_handle(self, issue_type: str) -> bool:
        """This strategy handles all unhandled issue types (fallback)."""
        return True  # Fallback handles everything

    def decide_routing(
        self, classification: IssueClassification, strategy: ResolutionStrategy
    ) -> RoutingInfo:
        """
        Decide routing for unknown/fallback issues.

        Args:
            classification: Issue classification
            strategy: Resolution strategy

        Returns:
            RoutingInfo with target tier and metadata
        """
        issue_type = classification.issue_type

        # Apply fallback routing logic
        if issue_type == "implementation":
            target_tier = "C"
            routing_reason = "Implementation improvement needed."
        elif issue_type == "documentation":
            target_tier = "E"
            routing_reason = "Documentation update required."
        else:  # unknown or unhandled
            target_tier = "F"
            routing_reason = "Issue requires further analysis and classification."

        # Calculate confidence
        confidence = self._calculate_routing_confidence(
            classification.confidence_score, strategy
        )

        # Generate metadata
        metadata = self._generate_metadata(classification, strategy)

        return RoutingInfo(
            target_tier=target_tier,
            routing_reason=routing_reason,
            routing_confidence=confidence,
            requires_clarification=confidence < 0.7,
            clarification_questions=self._generate_clarification_questions(
                issue_type, confidence
            ),
            metadata=metadata,
        )
