"""
Resolution Strategy Engine - 해결 전략 수립

책임:
- 분석 결과로부터 해결 전략 수립
- 목표 Tier 결정
- 작업 우선순위 설정
"""

from ...models.core.reporting_models import (
    IssueClassification,
    RootCauseAnalysis,
    ResolutionStrategy
)


class ResolutionStrategyEngine:
    """해결 전략 수립 엔진"""
    
    def create_strategy(
        self,
        classification: IssueClassification,
        root_cause: RootCauseAnalysis
    ) -> ResolutionStrategy:
        """
        분석 결과로부터 해결 전략 수립
        
        Args:
            classification: 이슈 분류 결과
            root_cause: 근본원인 분석 결과
            
        Returns:
            ResolutionStrategy 객체
        """
        # Step 1: 해결 방법 결정
        approach = self._determine_approach(classification, root_cause)
        
        # Step 2: 목표 Tier 결정
        target_tier = self._determine_target_tier(approach, classification)
        
        # Step 3: 작업 규모 추정
        effort = self._estimate_effort(approach, root_cause)
        
        # Step 4: WPD 등급 결정
        wpd_grade = self._determine_wpd_grade(approach, effort)
        
        # Step 5: 우선순위 결정
        priority = self._determine_priority(classification.severity, wpd_grade)
        
        # Step 6: 의존성 식별
        dependencies = self._identify_dependencies(approach, target_tier)
        
        # Step 7: 롤백 계획 수립
        rollback_plan = self._create_rollback_plan(approach)
        
        return ResolutionStrategy(
            approach=approach,
            estimated_effort=effort,
            target_tier=target_tier,
            wpd_grade=wpd_grade,
            priority=priority,
            dependencies=dependencies,
            rollback_plan=rollback_plan,
            estimated_duration_hours=self._estimate_duration(effort)
        )
    
    def _determine_approach(
        self,
        classification: IssueClassification,
        root_cause: RootCauseAnalysis
    ) -> str:
        """해결 방법 결정"""
        issue_type = classification.issue_type
        
        if issue_type == "bug":
            return "fix_implementation"
        elif issue_type == "design_flaw":
            return "refactor_design"
        elif issue_type == "implementation":
            return "improve_implementation"
        elif issue_type == "documentation":
            return "update_documentation"
        else:
            return "investigate"
    
    def _determine_target_tier(self, approach: str, classification: IssueClassification) -> str:
        """목표 Tier 결정"""
        tier_map = {
            "fix_implementation": "C",           # Tier C: 계획 수정
            "refactor_design": "A",             # Tier A: 새 계획
            "improve_implementation": "C",      # Tier C: 계획 수정
            "update_documentation": "E",        # Tier E: 문서 관리
            "investigate": "F",                 # Tier F: 재분류
        }
        
        return tier_map.get(approach, "F")
    
    def _estimate_effort(self, approach: str, root_cause: RootCauseAnalysis) -> str:
        """작업 규모 추정"""
        components_count = len(root_cause.affected_components)
        
        effort_map = {
            "fix_implementation": "medium" if components_count <= 2 else "high",
            "refactor_design": "high",
            "improve_implementation": "medium",
            "update_documentation": "low",
            "investigate": "medium",
        }
        
        return effort_map.get(approach, "medium")
    
    def _determine_wpd_grade(self, approach: str, effort: str) -> str:
        """WPD 등급 결정"""
        if effort == "high":
            return "L3"
        elif effort == "medium":
            return "L2" if approach in ["refactor_design"] else "L1"
        else:
            return "L0"
    
    def _determine_priority(self, severity: str, wpd_grade: str) -> int:
        """우선순위 결정 (1~10, 높을수록 우선)"""
        severity_points = {
            "critical": 8,
            "high": 6,
            "medium": 4,
            "low": 2,
        }
        
        grade_points = {
            "L3": 3,
            "L2": 2,
            "L1": 1,
            "L0": 0,
        }
        
        return min(10, severity_points.get(severity, 4) + grade_points.get(wpd_grade, 0))
    
    def _identify_dependencies(self, approach: str, target_tier: str) -> list:
        """의존성 식별"""
        dependencies = []
        
        if target_tier == "A":
            dependencies.append("prd_review")
        elif target_tier == "C":
            dependencies.append("code_review")
        elif target_tier == "E":
            dependencies.append("doc_review")
        
        return dependencies
    
    def _create_rollback_plan(self, approach: str) -> str:
        """롤백 계획 수립"""
        rollback_map = {
            "fix_implementation": "Revert the fix commit and test",
            "refactor_design": "Restore previous design documents and plan",
            "improve_implementation": "Revert to previous version",
            "update_documentation": "Revert document changes",
            "investigate": "No rollback needed (investigation only)",
        }
        
        return rollback_map.get(approach, "Rollback plan TBD")
    
    def _estimate_duration(self, effort: str) -> float:
        """작업 예상 소요 시간"""
        duration_map = {
            "low": 1.0,
            "medium": 4.0,
            "high": 8.0,
        }
        
        return duration_map.get(effort, 4.0)


__all__ = ["ResolutionStrategyEngine"]
