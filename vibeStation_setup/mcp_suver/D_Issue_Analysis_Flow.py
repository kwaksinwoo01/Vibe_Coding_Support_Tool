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

# Setup UTF-8 encoding globally to prevent cp949 errors
if sys.stdout:
    try:
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
if sys.stderr:
    try:
        if hasattr(sys.stderr, 'reconfigure'):
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

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
from common.github_reporter import get_github_reporter


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
        
        # GitHub reporter for auto-reporting low confidence issues
        self.github_reporter = get_github_reporter()
        
        # Learning context from historical feedback (loaded on demand)
        self.feedback_context: Optional[str] = None
        
        # 실행 로그
        self.execution_log: List[str] = []
    
    def load_feedback_context(self, max_issues: int = 20) -> str:
        """
        Load historical feedback from closed GitHub issues into learning context.
        
        This method fetches closed agent-self-report issues, extracts user feedback,
        and creates a summary that can inform future decision-making.
        
        Args:
            max_issues: Maximum number of closed issues to retrieve (default: 20)
            
        Returns:
            Formatted feedback summary string (also cached in self.feedback_context)
        """
        if not self.github_reporter.is_enabled():
            self.log("Feedback loading disabled (GitHub reporter not enabled)")
            return "No feedback context available (GitHub reporter disabled)."
        
        self.log(f"Loading feedback context from closed issues (max: {max_issues})...")
        
        try:
            feedback_list = self.github_reporter.load_feedback_from_closed_issues(
                label_filter="agent-self-report",
                max_issues=max_issues
            )
            
            if not feedback_list:
                self.feedback_context = "No historical feedback available yet."
                self.log("  → No closed issues found")
                return self.feedback_context
            
            # Generate summary
            self.feedback_context = self.github_reporter.get_feedback_summary(feedback_list)
            
            self.log(f"  → Loaded feedback from {len(feedback_list)} closed issues")
            
            # Log some stats
            node_counts = {}
            for fb in feedback_list:
                node = fb.get("node", "UNKNOWN")
                node_counts[node] = node_counts.get(node, 0) + 1
            
            for node, count in sorted(node_counts.items()):
                self.log(f"    - Node {node}: {count} issues")
            
            return self.feedback_context
            
        except Exception as e:
            self.log(f"  [ERROR] Failed to load feedback context: {e}")
            self.feedback_context = "Failed to load feedback context."
            return self.feedback_context
    
    def log(self, message: str):
        """로그 기록"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_msg = f"[{timestamp}] [D] {message}"
        self.execution_log.append(log_msg)
        print(log_msg)
    
    def execute(
        self,
        user_input: str,
        error_context: Optional[Dict[str, Any]] = None,
        use_feedback_context: bool = False
    ) -> AgentState:
        """
        메인 실행 워크플로우
        
        Args:
            user_input: 사용자의 이슈 설명
            error_context: 추가 오류 컨텍스트 (선택)
            use_feedback_context: If True, loads historical feedback to enhance analysis (default: False)
            
        Returns:
            AgentState (next_node: 라우팅된 Tier)
        """
        self.log("=" * 80)
        self.log("TIER D: Issue Analysis - START")
        self.log("=" * 80)
        
        try:
            error_context = error_context or {}
            
            # Optional: Load feedback context for enhanced analysis
            if use_feedback_context and self.feedback_context is None:
                self.load_feedback_context()
            
            # Step 1: 이슈 분류
            self.log(f"Step 1: Classifying issue...")
            
            # Enhance user input with feedback context if available
            enhanced_input = user_input
            if use_feedback_context and self.feedback_context:
                self.log(f"  → Using historical feedback context")
                # Note: The feedback context can be used by sub-analyzers
                # For now, we log it for visibility
                error_context["feedback_context"] = self.feedback_context
            
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
                self.log(f"   No routing engine injected - using strategy target_tier")
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
            
            # Auto-report to GitHub if confidence is low (Trigger 1)
            if routing_info.routing_confidence < 0.7:
                self._auto_report_to_github(
                    tier_d_state={
                        "routing_info": routing_info,
                        "classification": classification,
                        "root_cause": root_cause,
                        "strategy": strategy,
                    },
                    user_input=user_input
                )
            
            if routing_info.requires_clarification:
                self.log(f"   Requires clarification: {', '.join(routing_info.clarification_questions)}")
            
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
                self.log(f"  [OK] Auto-resolve capable: routing to Tier C for automatic fix")
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
                self.log(f"Not auto-resolvable: manual intervention may be required")
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
    
    def _auto_report_to_github(
        self,
        tier_d_state: Dict[str, Any],
        user_input: str
    ) -> None:
        """
        Automatically report low confidence decisions to GitHub
        
        Creates a GitHub issue when routing confidence is below threshold (0.7).
        This enables asynchronous feedback collection without interrupting workflow.
        
        Implements Part 8.3 requirements for automatic issue creation.
        
        Args:
            tier_d_state: Dictionary containing routing_info, classification, root_cause, strategy
            user_input: Original user input that triggered the analysis
        """
        if not self.github_reporter.is_enabled():
            self.log("GitHub auto-reporting disabled (no GITHUB_TOKEN or PyGithub)")
            return
        
        routing_info = tier_d_state.get("routing_info")
        classification = tier_d_state.get("classification")
        root_cause = tier_d_state.get("root_cause")
        strategy = tier_d_state.get("strategy")
        
        if not routing_info:
            return
        
        self.log("   Low confidence detected. Auto-reporting issue to GitHub...")
        
        # Build decision basis from analysis results
        decision_basis = f"""
**Issue Classification**: {classification.issue_type if classification else 'Unknown'} (severity: {classification.severity if classification else 'N/A'})

**Root Cause Analysis**:
- Root Cause: {root_cause.root_cause if root_cause else 'Unknown'}
- Confidence Level: {root_cause.confidence_level if root_cause else 'N/A'}
- Affected Components: {', '.join(root_cause.affected_components) if root_cause and root_cause.affected_components else 'None identified'}

**Resolution Strategy**:
- Approach: {strategy.approach if strategy else 'Unknown'}
- Target Tier: {strategy.target_tier if strategy else 'Unknown'}
- Estimated Effort: {strategy.estimated_effort if strategy else 'Unknown'}

**User Input**: {user_input[:200]}{'...' if len(user_input) > 200 else ''}
"""
        
        # Build hypothesis about why confidence is low
        hypothesis = f"""
If the routing decision to **Tier {routing_info.target_tier}** is incorrect, it may be because:

1. **Ambiguous Error Context**: The error description provided insufficient details for accurate classification
2. **Multiple Valid Interpretations**: The issue could be classified in multiple ways with similar confidence
3. **Missing Pattern Match**: The issue pattern doesn't closely match known patterns in the routing rules
4. **Insufficient Evidence**: Root cause analysis found limited evidence (only {len(root_cause.evidence) if root_cause else 0} evidence items)

**Routing Reasoning**: {routing_info.routing_reason}
"""
        
        # Additional context
        additional_context = {
            "issue_type": classification.issue_type if classification else None,
            "severity": classification.severity if classification else None,
            "category": classification.category if classification else None,
            "target_tier": routing_info.target_tier,
            "routing_confidence": routing_info.routing_confidence,
            "requires_clarification": routing_info.requires_clarification,
            "clarification_questions": routing_info.clarification_questions if routing_info.requires_clarification else [],
            "root_cause_confidence": root_cause.confidence_level if root_cause else None,
            "affected_components": root_cause.affected_components if root_cause else [],
        }
        
        # Create the issue
        issue_url = self.github_reporter.report_low_confidence_issue(
            active_node="D",
            state_flow="→ D (Issue Analysis)",
            confidence_score=routing_info.routing_confidence,
            decision_basis=decision_basis,
            hypothesis=hypothesis,
            additional_context=additional_context
        )
        
        if issue_url:
            self.log(f"  [OK] Created GitHub issue: {issue_url}")
        else:
            self.log(f"  [ERROR] Failed to create GitHub issue")
    
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
    
    def analyze_document_issue(
        self,
        document_path: str,
        issue_description: str
    ) -> AgentState:
        """
        문서 중복/오류 분석 (신규 기능)
        
        Detects:
        - Duplicate document creation
        - Document placed in wrong directory
        - Document should be merged with existing documents
        
        Args:
            document_path: 문제 문서 경로 (예: "docs_2/MIGRATION_GUIDE_v3.1.0.md")
            issue_description: 이슈 설명
            
        Returns:
            AgentState with merge strategy and routing to Tier E
        """
        from pathlib import Path
        self.log("=" * 80)
        self.log("TIER D: Document Analysis Mode - START")
        self.log("=" * 80)
        
        try:
            doc_path = Path(self.workspace_root) / document_path
            
            # Step 1: 문서 검증
            self.log(f"\n[STEP 1] Validating document: {document_path}")
            if not doc_path.exists():
                self.log(f" Document not found: {doc_path}")
                return self._create_document_error_state(f"Document not found: {document_path}")
            
            self.log(f"[OK] Document found: {doc_path.name} ({doc_path.stat().st_size} bytes)")
            
            # Step 2: 문서 내용 로드
            self.log(f"\n[STEP 2] Loading document content...")
            content = doc_path.read_text(encoding='utf-8')
            self.log(f"[OK] Loaded {len(content)} characters, {len(content.split())} words")
            
            # Step 3: 키워드 추출 및 관련 문서 탐색
            self.log(f"\n[STEP 3] Extracting keywords and finding related documents...")
            
            # DocumentMerger의 SemanticAnalyzer 사용
            from doc_management.document_merger import DocumentMerger, SemanticAnalyzer
            analyzer = SemanticAnalyzer()
            keywords = analyzer.extract_keywords(content)
            self.log(f"[OK] Extracted {len(keywords)} keywords")
            
            # Part 번호 추출
            import re
            part_match = re.search(r'/P(\d+)/', str(doc_path))
            part_num = int(part_match.group(1)) if part_match else None
            if part_num:
                self.log(f"[OK] Part number: P{part_num}")
            
            # 관련 문서 검색
            docs_root = Path(self.workspace_root) / "docs_2"
            if part_num:
                search_dir = docs_root / f"P{part_num}"
            else:
                search_dir = docs_root
            
            related_docs = []
            if search_dir.exists():
                for md_file in search_dir.rglob("*.md"):
                    if md_file == doc_path:
                        continue
                    try:
                        file_content = md_file.read_text(encoding='utf-8')
                        file_keywords = analyzer.extract_keywords(file_content)
                        match_count = len(keywords.intersection(file_keywords))
                        if match_count > 0:
                            match_ratio = match_count / len(keywords)
                            related_docs.append((md_file, match_ratio))
                    except Exception:
                        pass
            
            related_docs.sort(key=lambda x: x[1], reverse=True)
            related_paths = [d[0] for d in related_docs[:5]]
            
            self.log(f"[OK] Found {len(related_docs)} related documents (showing top {len(related_paths)}):")
            for doc, score in related_docs[:5]:
                self.log(f"  - {doc.name}: {score:.2%} keyword match")
            
            # Step 4: 신뢰도 기반 병합 전략 분석
            self.log(f"\n[STEP 4] Analyzing merge strategy...")
            merger = DocumentMerger(Path(self.workspace_root))
            analysis = merger.analyze_merge_strategy(
                source_path=doc_path,
                related_docs=related_paths,
                keywords=keywords
            )
            
            if not analysis["success"]:
                self.log(f"[ERROR] Analysis failed: {analysis.get('error', 'Unknown error')}")
                return self._create_document_error_state(analysis.get('error', 'Analysis failed'))
            
            # Step 5: 분석 결과 로깅
            self.log(f"\n[STEP 5] Analysis result:")
            self.log(f"  Strategy: {analysis['strategy']}")
            self.log(f"  Confidence: {analysis['confidence']:.2%}")
            self.log(f"  Target document: {analysis.get('target_document', 'None')}")
            self.log(f"  Source words: {analysis['source_word_count']}")
            self.log(f"  Total existing words: {analysis['total_existing_words']}")
            self.log(f"\n  Reasoning: {analysis['reasoning']}")
            self.log(f"\n  Recommendations:")
            for rec in analysis['recommendations']:
                self.log(f"    - {rec}")
            
            # Step 6: 라우팅 결정
            self.log(f"\n[STEP 6] Deciding routing...")
            
            # 전략에 따라 다음 노드 결정
            # 규칙: D는 분석만 수행, 실제 작업은 A/C에 위임
            if analysis['strategy'] in ('DISTRIBUTED_EDIT', 'SINGLE_DOC_MODIFY'):
                # 문서 수정 필요 → Tier C (Plan Modification)
                # Tier C가 문서 병합/수정 후 → Tier E (Document Management)로 자동 라우팅
                next_node = "C"
                routing_reason = f"Route to Tier C for document modification ({analysis['strategy']}). C will handle merge and route to E for finalization."
            elif analysis['strategy'] == 'UNIFIED_CREATION':
                # 통합 문서 생성 필요 → Tier A (Plan Creation)
                next_node = "A"
                routing_reason = "Route to Tier A to create unified consolidated document"
            else:
                next_node = "F"
                routing_reason = "Unknown strategy - manual review required"
            
            self.log(f"  → Next node: {next_node}")
            self.log(f"  → Reason: {routing_reason}")
            
            # Step 7: AgentState 생성
            self.log(f"\n[STEP 7] Creating AgentState...")
            
            payload = {
                "document_path": str(doc_path),
                "issue_description": issue_description,
                "merge_analysis": analysis,
                "routing_reason": routing_reason
            }
            
            agent_state = AgentState(
                tier="D",
                status="SUCCESS",
                logic_summary=(
                    f"Document analysis completed. Strategy: {analysis['strategy']} "
                    f"(confidence: {analysis['confidence']:.2%}). "
                    f"Routing to Tier {next_node} for {routing_reason}."
                ),
                payload=payload,
                next_node=next_node,
                execution_log=self.execution_log
            )
            
            self.log("=" * 80)
            self.log(f"TIER D: Document Analysis - SUCCESS (→ Tier {next_node})")
            self.log("=" * 80)
            
            return agent_state
            
        except Exception as e:
            self.log(f"CRITICAL ERROR in document analysis: {e}", level="ERROR")
            import traceback
            traceback.print_exc()
            return self._create_document_error_state(str(e))
    
    def _create_document_error_state(self, error_msg: str) -> AgentState:
        """문서 분석 에러 상태 생성"""
        failure_state = AgentState.create_failure(
            tier="D",
            error_msg=f"Document analysis failed: {error_msg}",
            logic_summary=f"Document analysis error: {error_msg}"
        )
        failure_state.execution_log = self.execution_log
        return failure_state


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
    
    # 문서 분석 트리거 감지
    doc_keywords = [
        "document", "문서", "incorrectly created", "잘못된 문서",
        "merge", "병합", "duplicate", "중복", "wrong directory", "잘못된 경로"
    ]
    
    is_document_issue = any(kw in user_input.lower() for kw in doc_keywords)
    
    # 문서 경로 감지 (.md 파일)
    import re
    has_doc_path = bool(re.search(r'\.md\b', user_input, re.IGNORECASE))
    
    if is_document_issue or has_doc_path:
        # 문서 분석 모드
        engine.log(f"Detected document-related issue - using document analysis mode")
        
        # 문서 경로 파싱
        doc_path_match = re.search(r'(docs_2[^\s]+\.md|[A-Z][A-Za-z0-9_-]+\.md)', user_input)
        if doc_path_match:
            doc_path = doc_path_match.group(1)
            # docs_2로 시작하지 않으면 검색
            if not doc_path.startswith('docs_2'):
                docs_root = Path(workspace_root) / "docs_2"
                for found_path in docs_root.rglob(doc_path):
                    doc_path = str(found_path.relative_to(workspace_root))
                    break
        else:
            # 기본값
            doc_path = "docs_2/MIGRATION_GUIDE_v3.1.0.md"
            engine.log(f"No document path found in input - using default: {doc_path}")
        
        state = engine.analyze_document_issue(
            document_path=doc_path,
            issue_description=user_input
        )
    else:
        # 일반 이슈 분석 모드
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

