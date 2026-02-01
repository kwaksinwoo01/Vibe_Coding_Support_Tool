"""
Bug routing strategy.

Handles routing for bug-related issues, reusing TIER_D_ROUTING_RULES["bug"].
"""

from typing import Dict
from .base import RoutingStrategy
from models.core.reporting_models import (
    IssueClassification,
    ResolutionStrategy,
    RoutingInfo,
)


class BugRoutingStrategy(RoutingStrategy):
    """
    Routing strategy for bug-related issues.

    Reuses existing routing rules from TIER_D_ROUTING_RULES["bug"]:
    - implementation_error → C (code modification)
    - environment_error → B (re-execute in environment)
    - data_error → E (data management)
    """

    # Reuse existing routing rules
    BUG_ROUTING_RULES: Dict[str, str] = {
        "implementation_error": "C",  # Tier C: code modification
        "environment_error": "B",  # Tier B: re-execute in environment
        "data_error": "E",  # Tier E: data management
    }

    def can_handle(self, issue_type: str) -> bool:
        """Check if this strategy handles bug issues."""
        return issue_type == "bug"

    def decide_routing(
        self, classification: IssueClassification, strategy: ResolutionStrategy
    ) -> RoutingInfo:
        """
        Decide routing for bug issues.

        Args:
            classification: Issue classification with bug type
            strategy: Resolution strategy

        Returns:
            RoutingInfo with target tier and metadata
        """
        category = classification.category or "implementation_error"

        # Apply bug routing rules
        target_tier = self.BUG_ROUTING_RULES.get(category, "C")  # Default to C

        # Calculate confidence
        confidence = self._calculate_routing_confidence(
            classification.confidence_score, strategy
        )

        # Generate routing reason
        routing_reason = f"Bug detected ({category}). Approach: {strategy.approach}"

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
