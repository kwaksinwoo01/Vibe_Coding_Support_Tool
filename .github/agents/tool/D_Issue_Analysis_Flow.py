"""
D_Issue_Analysis_Flow.py

Tier D: Issue Analysis and Refactoring Module (개선 버전)

Handles error analysis and debugging when issues occur.

메인 엔진으로 하위 모듈들을 통합하여 완전한 분석 워크플로우 제공

실행 순서:
1. 이슈 분류 (IssueClassifier)
2. 근본원인 분석 (RootCauseAnalyzer)
3. 해결 전략 수립 (ResolutionStrategyEngine)
4. 라우팅 결정 (RoutingEngine)
5. TierDState 구성
6. AgentState 반환

Triggers:
- "Error occurred"
- "Error after change"
- "New error found"
- "Function not working"
- "Failure"
- "오류"

Output: AgentState with comprehensive analysis and routing decision
"""

import sys
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

# 하위 모듈 import
from analysis.error.issue_classifier import IssueClassifier
from analysis.error.root_cause_analyzer import RootCauseAnalyzer
from analysis.error.resolution_strategy import ResolutionStrategyEngine
# NOTE: RoutingEngine moved to main_agent.py for centralized orchestration
# from analysis.error.routing_engine import RoutingEngine  # DEPRECATED
from models.core.reporting_models import (
    IssueClassification,
    RootCauseAnalysis,
    ResolutionStrategy,
    RoutingInfo
)

from models.core import AgentState, TierDState


class IssueAnalysisEngine:
    """
    Tier D: Issue Analysis 메인 엔진 (완전 구현)
    
    Refactored: RoutingEngine moved to MainAgent for centralized orchestration.
    This module now receives routing_engine as dependency injection.
    """
    
    def __init__(self, workspace_root: str = ".", routing_engine=None):
        """
        Initialize Issue Analysis Engine.
        
        Args:
            workspace_root: Workspace root directory
            routing_engine: Routing engine instance (injected from main_agent)
                          If None, routing decisions will use default next_node logic
        """
        self.workspace_root = Path(workspace_root)
        
        # 하위 모듈 초기화
        self.classifier = IssueClassifier()
        self.root_cause_analyzer = RootCauseAnalyzer()
        self.strategy_engine = ResolutionStrategyEngine()
        
        # Routing engine (injected from main_agent for centralized control)
        self.routing_engine = routing_engine
        
        # 실행 로그
        self.execution_log: List[str] = []
    
    def log(self, message: str):
        """로그 기록"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_msg = f"[{timestamp}] [D] {message}"
        self.execution_log.append(log_msg)
        print(log_msg)
    
    def execute(
        self,
        user_input: str,
        error_context: Optional[Dict[str, Any]] = None
    ) -> AgentState:
        """
        메인 실행 워크플로우
        
        Args:
            user_input: 사용자의 이슈 설명
            error_context: 추가 오류 컨텍스트 (선택)
            
        Returns:
            AgentState (next_node: 라우팅된 Tier)
        """
        self.log("=" * 80)
        self.log("TIER D: Issue Analysis - START")
        self.log("=" * 80)
        
        try:
            error_context = error_context or {}
            
            # Step 1: 이슈 분류
            self.log(f"Step 1: Classifying issue...")
            self.log(f"  Input: {user_input[:80]}...")
            classification = self.classifier.classify(user_input)
            self.log(f"  → Type: {classification.issue_type}, Severity: {classification.severity}")
            self.log(f"  → Category: {classification.category or 'N/A'}, Confidence: {classification.confidence_score:.2%}")
            
            # Step 2: 근본원인 분석
            self.log(f"Step 2: Analyzing root cause...")
            root_cause = self.root_cause_analyzer.analyze(
                user_input,
                classification,
                error_context
            )
            self.log(f"  → Root Cause: {root_cause.root_cause}")
            self.log(f"  → Affected Components: {', '.join(root_cause.affected_components) or 'N/A'}")
            self.log(f"  → Confidence: {root_cause.confidence_level}")
            
            # Step 3: 해결 전략 수립
            self.log(f"Step 3: Creating resolution strategy...")
            strategy = self.strategy_engine.create_strategy(
                classification,
                root_cause
            )
            self.log(f"  → Approach: {strategy.approach}")
            self.log(f"  → Target Tier: {strategy.target_tier}")
            self.log(f"  → Effort: {strategy.estimated_effort}, WPD Grade: {strategy.wpd_grade}")
            self.log(f"  → Priority: {strategy.priority}/10")
            
            # Step 4: 라우팅 결정 (use injected routing_engine if available)
            self.log(f"Step 4: Deciding routing...")
            if self.routing_engine:
                # Use injected routing engine from main_agent
                routing_info = self.routing_engine.decide_initial_routing_for_d(
                    classification,
                    strategy
                )
            else:
                # Fallback: Create simple routing info from strategy
                self.log(f"  ⚠ No routing engine injected - using strategy target_tier")
                routing_info = RoutingInfo(
                    target_tier=strategy.target_tier,
                    routing_reason=f"Fallback routing to {strategy.target_tier}",
                    routing_confidence=0.7,
                    requires_clarification=False,
                    clarification_questions=[],
                    metadata={"fallback": True}
                )
            
            self.log(f"  → Target Tier: {routing_info.target_tier}")
            self.log(f"  → Confidence: {routing_info.routing_confidence:.2%}")
            self.log(f"  → Reason: {routing_info.routing_reason}")
            
            if routing_info.requires_clarification:
                self.log(f"  ⚠ Requires clarification: {', '.join(routing_info.clarification_questions)}")
            
            # Step 5: TierDState 구성
            self.log(f"Step 5: Building TierDState...")
            tier_d_state = TierDState(
                issue_description=user_input,
                error_details=error_context,
                issue_classification=classification,
                root_cause_analysis=root_cause,
                resolution_strategy=strategy,
                routing_info=routing_info,
                analysis_metadata={
                    "analysis_steps": 4,
                    "total_evidence": len(root_cause.evidence),
                },
                analysis_timestamp=datetime.now().isoformat()
            )
            
            # Step 6: AgentState 반환 (Enhanced with auto-resolve detection)
            self.log(f"Step 6: Creating AgentState with auto-resolve detection...")
            
            # Determine if issue can be auto-resolved (Proposal 1)
            can_auto_resolve = self._can_auto_resolve(strategy, root_cause)
            
            if can_auto_resolve:
                self.log(f"  ✓ Auto-resolve capable: routing to Tier C for automatic fix")
                # Override routing to Tier C for automatic resolution
                routing_info.target_tier = "C"
                strategy.auto_resolve_flag = True
                
                # Add auto_resolve_details to payload
                auto_resolve_details = {
                    "action": strategy.approach,
                    "target_file": root_cause.affected_components[0] if root_cause.affected_components else "",
                    "confidence_level": root_cause.confidence_level,
                    "estimated_effort": strategy.estimated_effort,
                    "wpd_grade": strategy.wpd_grade
                }
                
                self.log(f"  → Auto-resolve action: {auto_resolve_details['action']}")
                self.log(f"  → Target file: {auto_resolve_details['target_file'] or 'N/A'}")
            else:
                self.log(f"  ℹ Not auto-resolvable: manual intervention may be required")
                auto_resolve_details = None
            
            agent_state = AgentState(
                tier="D",
                status="SUCCESS",
                logic_summary=(
                    f"Issue classified as {classification.issue_type} (severity: {classification.severity}). "
                    f"Root cause: {root_cause.root_cause}. "
                    f"Resolution: {strategy.approach}. "
                    f"{'[AUTO-RESOLVE] ' if can_auto_resolve else ''}"
                    f"Routing to Tier {routing_info.target_tier}."
                ),
                payload=tier_d_state.to_payload(),
                next_node=routing_info.target_tier,
                execution_log=self.execution_log,
                wpd_grade=strategy.wpd_grade
            )
            
            # Add auto_resolve_details to payload if applicable
            if auto_resolve_details:
                agent_state.payload["auto_resolve_details"] = auto_resolve_details
            
            self.log("=" * 80)
            self.log(f"TIER D: Issue Analysis - SUCCESS (→ Tier {routing_info.target_tier})")
            if can_auto_resolve:
                self.log(f"  [AUTO-RESOLVE] Chain will proceed: D → C → B")
            self.log("=" * 80)
            
            return agent_state
            
        except Exception as e:
            self.log(f"CRITICAL ERROR: {e}")
            import traceback
            traceback.print_exc()
            
            self.log("=" * 80)
            self.log("TIER D: Issue Analysis - FAILURE")
            self.log("=" * 80)
            
            # Create failure state and manually set execution_log
            failure_state = AgentState.create_failure(
                tier="D",
                error_msg=f"Issue analysis failed: {str(e)}",
                logic_summary=f"Exception: {type(e).__name__}"
            )
            failure_state.execution_log = self.execution_log
            return failure_state
    
    def _can_auto_resolve(self, strategy: ResolutionStrategy, root_cause: RootCauseAnalysis) -> bool:
        """
        Determine if issue can be automatically resolved through D → C → B chain.
        
        Criteria for auto-resolution:
        1. Root cause confidence level is "high" or "medium"
        2. Strategy approach is actionable (fix_implementation, refactor)
        3. Affected components are identified (target file known)
        4. No manual investigation required
        
        Args:
            strategy: Resolution strategy from Step 3
            root_cause: Root cause analysis from Step 2
            
        Returns:
            True if can auto-resolve, False otherwise
        """
        # Criterion 1: High/medium confidence in root cause
        confidence_ok = root_cause.confidence_level in ("high", "medium")
        
        # Criterion 2: Actionable approach (not investigation/documentation)
        actionable_approaches = {
            "fix_implementation",
            "refactor", 
            "code_modification",
            "update_logic",
            "fix_bug"
        }
        approach_ok = strategy.approach in actionable_approaches
        
        # Criterion 3: Target components identified
        has_target = len(root_cause.affected_components) > 0
        
        # Criterion 4: Not requiring manual investigation
        not_investigation = strategy.approach not in ("investigate", "manual_review")
        
        can_resolve = confidence_ok and approach_ok and has_target and not_investigation
        
        return can_resolve


def main(user_input: str, workspace_root: str = ".", error_context: Optional[Dict[str, Any]] = None) -> AgentState:
    """
    Entry point for Tier D module
    
    Args:
        user_input: User's natural language request
        workspace_root: Root directory of the workspace
        error_context: Additional error context
    
    Returns:
        AgentState with execution results
    """
    engine = IssueAnalysisEngine(workspace_root)
    state = engine.execute(user_input, error_context)
    
    # Emit AgentState to stdout for orchestrator to capture
    state.emit()
    
    return state


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python D_Issue_Analysis_Flow.py '<user_input>' [workspace_root]")
        sys.exit(1)
    
    user_input = sys.argv[1]
    workspace_root = sys.argv[2] if len(sys.argv) > 2 else "."
    
    main(user_input, workspace_root)

