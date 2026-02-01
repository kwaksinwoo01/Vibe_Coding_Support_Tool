"""
Design flaw routing strategy.

Handles routing for design-related issues, reusing TIER_D_ROUTING_RULES["design_flaw"].
"""

from typing import Dict
from .base import RoutingStrategy
from models.core.reporting_models import (
    IssueClassification,
    ResolutionStrategy,
    RoutingInfo,
)


class DesignFlawRoutingStrategy(RoutingStrategy):
    """
    Routing strategy for design flaw issues.

    Reuses existing routing rules from TIER_D_ROUTING_RULES["design_flaw"]:
    - architecture → A (new plan)
    - algorithm → C (modify existing plan)
    - interface → C (modify existing plan)
    """

    # Reuse existing routing rules
    DESIGN_FLAW_ROUTING_RULES: Dict[str, str] = {
        "architecture": "A",  # Tier A: new plan
        "algorithm": "C",  # Tier C: modify existing plan
        "interface": "C",  # Tier C: modify existing plan
    }

    def can_handle(self, issue_type: str) -> bool:
        """Check if this strategy handles design flaw issues."""
        return issue_type == "design_flaw"

    def decide_routing(
        self, classification: IssueClassification, strategy: ResolutionStrategy
    ) -> RoutingInfo:
        """
        Decide routing for design flaw issues.

        Args:
            classification: Issue classification with design flaw type
            strategy: Resolution strategy

        Returns:
            RoutingInfo with target tier and metadata
        """
        category = classification.category or "algorithm"

        # Apply design flaw routing rules
        target_tier = self.DESIGN_FLAW_ROUTING_RULES.get(category, "C")  # Default to C

        # Calculate confidence
        confidence = self._calculate_routing_confidence(
            classification.confidence_score, strategy
        )

        # Generate routing reason
        routing_reason = f"Design issue ({category}). Requires architectural review."

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
