"""
Base routing strategy interface.

Defines the contract for all routing strategies in the system.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List
from models.core.reporting_models import (
    IssueClassification,
    ResolutionStrategy,
    RoutingInfo,
)


class RoutingStrategy(ABC):
    """
    Abstract base class for routing strategies.

    Each strategy implements routing logic for a specific issue type,
    reusing existing routing rules from TIER_D_ROUTING_RULES.

    Strategies follow the Strategy pattern to enable:
    - Easy addition of new routing logic
    - Testable, isolated routing decisions
    - Reuse of existing routing rules
    """

    @abstractmethod
    def can_handle(self, issue_type: str) -> bool:
        """
        Check if this strategy can handle the given issue type.

        Args:
            issue_type: Type of issue (bug, design_flaw, implementation, etc.)

        Returns:
            True if strategy can handle this issue type
        """
        pass

    @abstractmethod
    def decide_routing(
        self, classification: IssueClassification, strategy: ResolutionStrategy
    ) -> RoutingInfo:
        """
        Decide routing for the given classification and resolution strategy.

        Args:
            classification: Issue classification result
            strategy: Resolution strategy

        Returns:
            RoutingInfo with target tier and metadata
        """
        pass

    def _calculate_routing_confidence(
        self, classification_confidence: float, strategy: ResolutionStrategy
    ) -> float:
        """
        Calculate routing confidence based on classification and strategy.

        Reused from original RoutingEngine implementation.

        Args:
            classification_confidence: Confidence score from classification
            strategy: Resolution strategy

        Returns:
            Calculated routing confidence (0.0 - 1.0)
        """
        # Classification confidence * strategy confidence
        strategy_confidence = {
            "low": 0.95,
            "medium": 0.80,
            "high": 0.60,  # Higher effort → lower confidence
        }.get(strategy.estimated_effort, 0.80)

        return min(1.0, classification_confidence * strategy_confidence)

    def _generate_metadata(
        self, classification: IssueClassification, strategy: ResolutionStrategy
    ) -> Dict[str, Any]:
        """
        Generate routing metadata.

        Args:
            classification: Issue classification result
            strategy: Resolution strategy

        Returns:
            Metadata dictionary
        """
        return {
            "analysis_type": classification.issue_type,
            "approach": strategy.approach,
            "priority": strategy.priority,
            "estimated_effort": strategy.estimated_effort,
            "wpd_grade": strategy.wpd_grade,
            "category": classification.category,
        }

    def _generate_clarification_questions(
        self, issue_type: str, confidence: float
    ) -> List[str]:
        """
        Generate clarification questions based on issue type and confidence.

        Args:
            issue_type: Type of issue
            confidence: Routing confidence score

        Returns:
            List of clarification questions
        """
        if confidence > 0.7:
            return []

        questions = []

        if issue_type == "unknown":
            questions.append("Can you provide more specific error information?")
            questions.append("What is the context in which this issue occurred?")

        if confidence < 0.5:
            questions.append("Could you describe the expected vs actual behavior?")
            questions.append("When did this issue start occurring?")

        return questions
