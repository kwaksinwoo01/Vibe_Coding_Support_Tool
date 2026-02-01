"""
Routing Engine - 라우팅 결정 및 검증

책임:
- Tier D의 초기 라우팅 결정 (Rule 1) - Strategy Pattern 기반
- 다른 Tier의 라우팅 검증 (Rule 2)
- 라우팅 규칙 정의 및 관리
- Strategy 등록 및 선택

Architecture:
- Strategy Pattern for routing decisions
- Registration-based strategy selection
- Reuses existing TIER_D_ROUTING_RULES via strategies
"""

from typing import Dict, List, Any
from models.core.reporting_models import (
    IssueClassification,
    ResolutionStrategy,
    RoutingInfo,
)

# Import routing strategies
from .strategies import (
    RoutingStrategy,
    BugRoutingStrategy,
    DesignFlawRoutingStrategy,
    PerformanceRoutingStrategy,
    FallbackRoutingStrategy,
)


class RoutingEngine:
    """라우팅 규칙 및 결정 엔진 (Strategy Pattern)"""

    def __init__(self):
        """Initialize routing engine with strategies."""
        # Register routing strategies
        self._strategies: List[RoutingStrategy] = [
            BugRoutingStrategy(),
            DesignFlawRoutingStrategy(),
            PerformanceRoutingStrategy(),
            # FallbackRoutingStrategy must be last (handles all types)
            FallbackRoutingStrategy(),
        ]

    # Rule 1: Tier D의 초기 라우팅 규칙 (PRESERVED for backward compatibility)
    TIER_D_ROUTING_RULES = {
        "bug": {
            "implementation_error": "C",  # Tier C: 코드 수정
            "environment_error": "B",  # Tier B: 환경 재실행
            "data_error": "E",  # Tier E: 데이터 관리
        },
        "design_flaw": {
            "architecture": "A",  # Tier A: 새 계획 수립
            "algorithm": "C",  # Tier C: 기존 계획 수정
            "interface": "C",  # Tier C: 기존 계획 수정
        },
        "implementation": "C",  # Tier C: 계획 수정
        "documentation": "E",  # Tier E: 문서 관리
        "unknown": "F",  # Tier F: 재분류
    }

    # Rule 2: 각 Tier의 가능한 다음 라우팅
    VALID_NEXT_ROUTINGS = {
        "A": ["B", "C", "E", None],  # 계획 생성 후: 실행 또는 수정 또는 문서 또는 종료
        "B": ["E", "C", None],  # 실행 후: 문서 또는 수정 또는 종료
        "C": ["B", "E", None],  # 수정 후: 실행 또는 문서 또는 종료
        "E": [None],  # 문서 관리 후: 종료만
        "F": ["A", "B", "C", "D", "E", None],  # 재분류 후: 어디든지 가능
    }

    # Rule 2: 실패 시 라우팅
    FAILURE_NEXT_ROUTINGS = {
        "A": ["D", None],  # 실패 → 재분석 또는 종료
        "B": ["D", None],
        "C": ["D", None],
        "E": ["D", None],
        "F": [None],  # F 실패 → 종료
    }

    def decide_initial_routing(
        self, classification: IssueClassification, strategy: ResolutionStrategy
    ) -> RoutingInfo:
        """
        Tier D의 초기 라우팅 결정 (Rule 1) - Strategy Pattern

        Uses registered strategies to determine routing.

        Args:
            classification: 이슈 분류 결과
            strategy: 해결 전략

        Returns:
            RoutingInfo 객체
        """
        issue_type = classification.issue_type

        # Find appropriate strategy
        selected_strategy = self._select_strategy(issue_type)

        # Delegate to strategy
        return selected_strategy.decide_routing(classification, strategy)

    def _select_strategy(self, issue_type: str) -> RoutingStrategy:
        """
        Select appropriate routing strategy for issue type.

        Args:
            issue_type: Type of issue

        Returns:
            Selected routing strategy
        """
        for strategy in self._strategies:
            if strategy.can_handle(issue_type):
                return strategy

        # Should never reach here due to FallbackRoutingStrategy
        return self._strategies[-1]  # Return fallback

    def validate_next_routing(
        self, current_tier: str, target_tier: str, tier_result: Dict[str, Any]
    ) -> bool:
        """
        다음 라우팅이 유효한지 검증 (Rule 2)

        Args:
            current_tier: 현재 Tier
            target_tier: 목표 Tier
            tier_result: 현재 Tier의 결과 {"status": "SUCCESS" or "FAILURE"}

        Returns:
            유효 여부
        """
        status = tier_result.get("status", "UNKNOWN")

        if status == "SUCCESS":
            valid_tiers = self.VALID_NEXT_ROUTINGS.get(current_tier, [])
        else:
            valid_tiers = self.FAILURE_NEXT_ROUTINGS.get(current_tier, [])

        return target_tier in valid_tiers

    def _apply_routing_rule(self, issue_type: str, category: str) -> str:
        """
        라우팅 규칙 적용 (DEPRECATED - kept for backward compatibility)

        Now delegated to strategies, but preserved for reference.
        """
        if issue_type in self.TIER_D_ROUTING_RULES:
            rules = self.TIER_D_ROUTING_RULES[issue_type]

            # 카테고리 기반 라우팅
            if isinstance(rules, dict) and category in rules:
                return rules[category]

            # 기본 라우팅
            if isinstance(rules, str):
                return rules

        # 기본값: 재분류
        return "F"

    def _calculate_routing_confidence(
        self, classification_confidence: float, strategy: ResolutionStrategy
    ) -> float:
        """
        라우팅 신뢰도 계산 (DEPRECATED - moved to RoutingStrategy base class)

        Preserved for backward compatibility.
        """
        # 분류 신뢰도 * 전략 신뢰도
        strategy_confidence = {
            "low": 0.95,
            "medium": 0.80,
            "high": 0.60,  # 작업이 클수록 신뢰도 낮음
        }.get(strategy.estimated_effort, 0.80)

        return min(1.0, classification_confidence * strategy_confidence)

    def _generate_routing_reason(
        self, issue_type: str, category: str, approach: str
    ) -> str:
        """
        라우팅 이유 생성 (DEPRECATED - moved to strategies)

        Preserved for backward compatibility.
        """
        reason_templates = {
            "bug": f"Bug detected ({category or 'implementation'}). Approach: {approach}",
            "design_flaw": f"Design issue ({category or 'general'}). Requires architectural review.",
            "implementation": "Implementation improvement needed.",
            "documentation": "Documentation update required.",
            "unknown": "Issue requires further analysis and classification.",
        }

        return reason_templates.get(
            issue_type, f"Route to appropriate tier for {approach}"
        )

    def _generate_clarification_questions(
        self, issue_type: str, confidence: float
    ) -> List[str]:
        """
        명확화 질문 생성 (DEPRECATED - moved to RoutingStrategy base class)

        Preserved for backward compatibility.
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


__all__ = ["RoutingEngine"]
