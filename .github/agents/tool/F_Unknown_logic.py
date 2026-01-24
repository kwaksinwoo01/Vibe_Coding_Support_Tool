"""
F_Unknown_logic.py

Tier F: Unknown/Exception Logic Handler

Handles requests that don't fit into Tiers A-E. Acts as a fallback classifier
and can route to appropriate tiers after analysis.

Triggers:
- Any input that doesn't match patterns for Tiers A-E
- Ambiguous requests
- Requests requiring clarification

Workflow:
1. Analyze the user input
2. Attempt to classify into one of Tiers A-E
3. If classification successful, route to appropriate tier
4. Otherwise, ask for clarification or provide guidance

Output: AgentState with classification results or clarification request
"""

import sys
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from models.core import AgentState, TierFState
from models.builders import create_tier_f_state, create_pending_state
from models.serializers import emit_agent_state


class UnknownLogicHandler:
    """Handler for unclassified or ambiguous requests"""
    
    # Enhanced keyword mapping for tier classification
    TIER_KEYWORDS = {
        "A": [
            "create", "plan", "새로운", "작성", "wpd 생성", "work plan",
            "make plan", "generate plan", "start plan"
        ],
        "B": [
            "perform", "execute", "run", "실행", "진행", "작업 계획 실행",
            "do task", "complete task", "implement"
        ],
        "C": [
            "change", "modify", "edit", "수정", "변경", "마일스톤",
            "update", "revise", "alter"
        ],
        "D": [
            "error", "issue", "fails", "failure", "오류", "문제", "작동 안",
            "bug", "broken", "not working", "debug"
        ],
        "E": [
            "save", "mapping", "저장", "동기화", "데이터 클래스", "필드",
            "document", "reflect", "update mapping"
        ]
    }
    
    def __init__(self, workspace_root: str = "."):
        self.workspace_root = Path(workspace_root)
        self.state = AgentState(tier="F", status="PENDING")  # Parent state
        self.tier_state = TierFState()  # Tier-specific state
        self.execution_log: List[str] = []
    
    def log(self, message: str):
        """Add message to execution log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_msg = f"[{timestamp}] {message}"
        self.execution_log.append(log_msg)
        print(log_msg)
    
    def classify_input(self, user_input: str) -> Optional[str]:
        """
        Attempt to classify user input into one of Tiers A-E
        
        Returns:
            Tier letter (A-E) or None if unable to classify
        """
        user_input_lower = user_input.lower()
        tier_scores = {}
        
        for tier, keywords in self.TIER_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in user_input_lower)
            if score > 0:
                tier_scores[tier] = score
        
        if tier_scores:
            # Return tier with highest score (max key by value)
            best_tier = max(tier_scores.items(), key=lambda x: x[1])[0]
            confidence = tier_scores[best_tier] / max(len(self.TIER_KEYWORDS[best_tier]), 1)
            
            self.tier_state.confidence_score = min(confidence, 1.0)
            self.tier_state.suggested_tier = best_tier
            self.tier_state.classification_reasoning = f"Matched {tier_scores[best_tier]} keywords for Tier {best_tier}"
            
            self.log(f"Classified input as Tier {best_tier} (confidence: {confidence:.2f})")
            return best_tier
        
        self.log("Unable to classify input into known tiers")
        self.tier_state.confidence_score = 0.0
        return None
    
    def execute(self, user_input: str) -> AgentState:
        """
        Main execution entry point for Tier F
        
        Args:
            user_input: User's natural language request
        
        Returns:
            AgentState with classification results or clarification request
        """
        self.log("=" * 80)
        self.log("TIER F: Unknown Logic Handler - Starting")
        self.log("=" * 80)
        
        try:
            self.log(f"Analyzing user input: {user_input[:100]}...")
            
            # Attempt classification
            classified_tier = self.classify_input(user_input)
            
            # Store classification results in tier state
            self.tier_state.user_request = user_input
            
            # Build final AgentState
            self.state.tier = "F"
            self.state.payload = self.tier_state.to_payload()
            self.state.execution_log = self.execution_log
            
            if classified_tier and self.tier_state.confidence_score > 0.3:
                # Successfully classified - route to appropriate tier
                self.tier_state.routed_to_tier = classified_tier
                self.tier_state.routing_successful = True
                
                self.state.status = "SUCCESS"
                self.state.logic_summary = f"Input classified as Tier {classified_tier}. Routing request."
                self.state.next_node = classified_tier
                
                self.log(f"Routing to Tier {classified_tier}")
            else:
                # Unable to classify - request clarification
                self.tier_state.requires_clarification = True
                self.tier_state.clarification_questions = [
                    "What would you like to do?",
                    "- Create a new work plan?",
                    "- Execute an existing plan?",
                    "- Modify a plan?",
                    "- Analyze an error?",
                    "- Manage documents?"
                ]
                
                clarification_message = (
                    "Unable to automatically classify your request. "
                    "Please specify one of the following:\n"
                    "- 'Create plan' (Tier A) - Create a new work plan\n"
                    "- 'Execute plan' (Tier B) - Execute existing plan\n"
                    "- 'Modify plan' (Tier C) - Change/edit a plan\n"
                    "- 'Analyze issue' (Tier D) - Debug/fix an error\n"
                    "- 'Save changes' (Tier E) - Document management"
                )
                
                self.state.status = "PENDING"
                self.state.logic_summary = clarification_message
                self.state.next_node = None
                self.state.add_warning("Input classification uncertain - clarification needed")
                
                self.log("Requesting user clarification")
            
            self.log("=" * 80)
            self.log("TIER F: Unknown Logic Handler - Completed")
            self.log("=" * 80)
            
            return self.state
            
        except Exception as e:
            self.log(f"CRITICAL ERROR: {e}")
            import traceback
            traceback.print_exc()
            
            return AgentState.create_failure(
                tier="F",
                error_msg=f"Unknown logic handling failed: {str(e)}",
                logic_summary=f"Exception during execution: {type(e).__name__}"
            )


def main(user_input: str, workspace_root: str = ".") -> AgentState:
    """
    Entry point for Tier F module
    
    Args:
        user_input: User's natural language request
        workspace_root: Root directory of the workspace
    
    Returns:
        AgentState with execution results
    """
    handler = UnknownLogicHandler(workspace_root)
    state = handler.execute(user_input)
    
    # Emit AgentState to stdout for orchestrator to capture
    state.emit()
    
    return state


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python F_Unknown_logic.py '<user_input>' [workspace_root]")
        sys.exit(1)
    
    user_input = sys.argv[1]
    workspace_root = sys.argv[2] if len(sys.argv) > 2 else "."
    
    main(user_input, workspace_root)
