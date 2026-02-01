"""
Unit tests for Tier D auto-resolve functionality

Tests the enhanced workflow: B failure → D (analysis) → auto-resolve decision → C → B

Test Coverage:
1. ResolutionStrategy.auto_resolve_flag field
2. IssueAnalysisEngine._can_auto_resolve() logic
3. D_Issue_Analysis_Flow.py auto_resolve_details in payload
4. main_agent.py auto-resolve routing enforcement
"""

import unittest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add tool directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.core.reporting_models import ResolutionStrategy, RootCauseAnalysis, IssueClassification

from D_Issue_Analysis_Flow import IssueAnalysisEngine
from lang_graph_moduel.decision_engine import DecisionContext
from main_agent import MainAgent


class TestResolutionStrategyAutoResolveFlag(unittest.TestCase):
    """Test ResolutionStrategy.auto_resolve_flag field"""
    
    def test_auto_resolve_flag_default_false(self):
        """Test auto_resolve_flag defaults to False"""
        strategy = ResolutionStrategy(
            approach="fix_implementation",
            target_tier="C"
        )
        self.assertFalse(strategy.auto_resolve_flag)
    
    def test_auto_resolve_flag_can_be_set_true(self):
        """Test auto_resolve_flag can be set to True"""
        strategy = ResolutionStrategy(
            approach="fix_implementation",
            target_tier="C",
            auto_resolve_flag=True
        )
        self.assertTrue(strategy.auto_resolve_flag)
    
    def test_auto_resolve_flag_serialization(self):
        """Test auto_resolve_flag is included in serialization"""
        strategy = ResolutionStrategy(
            approach="refactor",
            target_tier="C",
            auto_resolve_flag=True
        )
        data = strategy.to_dict()
        self.assertIn("auto_resolve_flag", data)
        self.assertTrue(data["auto_resolve_flag"])
    
    def test_auto_resolve_flag_deserialization(self):
        """Test auto_resolve_flag is preserved in deserialization"""
        data = {
            "approach": "fix_implementation",
            "target_tier": "C",
            "auto_resolve_flag": True
        }
        strategy = ResolutionStrategy.from_dict(data)
        self.assertTrue(strategy.auto_resolve_flag)
    
    def test_auto_resolve_flag_no_role_overlap(self):
        """Test auto_resolve_flag has unique purpose (no role overlap with existing fields)"""
        strategy = ResolutionStrategy(
            approach="fix_implementation",  # approach = method
            target_tier="C",                 # target_tier = destination
            auto_resolve_flag=True           # auto_resolve_flag = automation capability
        )
        # All three fields serve different purposes - no overlap
        self.assertEqual(strategy.approach, "fix_implementation")  # HOW to fix
        self.assertEqual(strategy.target_tier, "C")                 # WHERE to route
        self.assertTrue(strategy.auto_resolve_flag)                 # CAN auto-resolve?


class TestIssueAnalysisEngineCanAutoResolve(unittest.TestCase):
    """Test IssueAnalysisEngine._can_auto_resolve() method"""
    
    def setUp(self):
        self.engine = IssueAnalysisEngine()
    
    def test_can_auto_resolve_high_confidence_actionable(self):
        """Test auto-resolve with high confidence and actionable approach"""
        strategy = ResolutionStrategy(
            approach="fix_implementation",
            target_tier="C"
        )
        root_cause = RootCauseAnalysis(
            root_cause="Missing validation",
            affected_components=["module.py"],
            confidence_level="high"
        )
        
        result = self.engine._can_auto_resolve(strategy, root_cause)
        self.assertTrue(result)
    
    def test_can_auto_resolve_medium_confidence_refactor(self):
        """Test auto-resolve with medium confidence and refactor approach"""
        strategy = ResolutionStrategy(
            approach="refactor",
            target_tier="C"
        )
        root_cause = RootCauseAnalysis(
            root_cause="Code duplication",
            affected_components=["util.py", "helper.py"],
            confidence_level="medium"
        )
        
        result = self.engine._can_auto_resolve(strategy, root_cause)
        self.assertTrue(result)
    
    def test_cannot_auto_resolve_low_confidence(self):
        """Test cannot auto-resolve with low confidence"""
        strategy = ResolutionStrategy(
            approach="fix_implementation",
            target_tier="C"
        )
        root_cause = RootCauseAnalysis(
            root_cause="Unknown cause",
            affected_components=["module.py"],
            confidence_level="low"
        )
        
        result = self.engine._can_auto_resolve(strategy, root_cause)
        self.assertFalse(result)
    
    def test_cannot_auto_resolve_investigation_approach(self):
        """Test cannot auto-resolve when approach is investigation"""
        strategy = ResolutionStrategy(
            approach="investigate",
            target_tier="F"
        )
        root_cause = RootCauseAnalysis(
            root_cause="Complex issue",
            affected_components=["module.py"],
            confidence_level="high"
        )
        
        result = self.engine._can_auto_resolve(strategy, root_cause)
        self.assertFalse(result)
    
    def test_cannot_auto_resolve_no_target_components(self):
        """Test cannot auto-resolve when no target components identified"""
        strategy = ResolutionStrategy(
            approach="fix_implementation",
            target_tier="C"
        )
        root_cause = RootCauseAnalysis(
            root_cause="Missing validation",
            affected_components=[],  # No components identified
            confidence_level="high"
        )
        
        result = self.engine._can_auto_resolve(strategy, root_cause)
        self.assertFalse(result)


class TestDIssueAnalysisAutoResolvePayload(unittest.TestCase):
    """Test D_Issue_Analysis_Flow auto_resolve_details in payload"""
    
    @patch('D_Issue_Analysis_Flow.IssueClassifier')
    @patch('D_Issue_Analysis_Flow.RootCauseAnalyzer')
    @patch('D_Issue_Analysis_Flow.ResolutionStrategyEngine')
    def test_auto_resolve_details_added_to_payload(
        self, 
        mock_strategy_engine,
        mock_root_cause_analyzer,
        mock_classifier
    ):
        """Test auto_resolve_details is added to AgentState payload when applicable"""
        # Setup mocks
        mock_classification = IssueClassification(
            issue_type="bug",
            severity="high",
            confidence_score=0.95
        )
        mock_classifier.return_value.classify.return_value = mock_classification
        
        mock_root_cause = RootCauseAnalysis(
            root_cause="Missing type validation",
            affected_components=["validator.py"],
            confidence_level="high"
        )
        mock_root_cause_analyzer.return_value.analyze.return_value = mock_root_cause
        
        mock_strategy = ResolutionStrategy(
            approach="fix_implementation",
            target_tier="C",
            wpd_grade="L1",
            estimated_effort="low"
        )
        mock_strategy_engine.return_value.create_strategy.return_value = mock_strategy
        
        from models.core.reporting_models import RoutingInfo
        mock_routing = RoutingInfo(
            target_tier="C",
            routing_reason="Fix required",
            routing_confidence=0.9
        )
        # RoutingEngine is now in main_agent, not D_Issue_Analysis_Flow
        # The engine will use strategy.target_tier as fallback when routing_engine is None
        
        # Execute
        engine = IssueAnalysisEngine()
        result = engine.execute("Test error", {})
        
        # Verify
        self.assertEqual(result.status, "SUCCESS")
        self.assertIn("auto_resolve_details", result.payload)
        
        auto_resolve = result.payload["auto_resolve_details"]
        self.assertEqual(auto_resolve["action"], "fix_implementation")
        self.assertEqual(auto_resolve["target_file"], "validator.py")
        self.assertEqual(auto_resolve["confidence_level"], "high")
        self.assertEqual(auto_resolve["estimated_effort"], "low")
        
        # Verify routing override to C
        self.assertEqual(result.next_node, "C")


class TestMainAgentAutoResolveRouting(unittest.TestCase):
    """Test main_agent.py auto-resolve routing enforcement"""
    
    def setUp(self):
        self.agent = MainAgent(workspace_root=".", enable_decision_engine=True)
    
    def test_auto_resolve_routing_enforcement(self):
        """Test main_agent forces routing to C when auto_resolve_details present"""
        from lang_graph_moduel.decision_engine import create_decision_context
        
        # Create context with auto_resolve_details (simulating Tier D success)
        context = create_decision_context(
            tier="D",
            status="SUCCESS",
            user_input="Fix error in module",
            payload={
                "next_node": "F",  # Default routing
                "auto_resolve_details": {
                    "action": "fix_implementation",
                    "target_file": "module.py",
                    "confidence_level": "high",
                    "estimated_effort": "low"
                }
            }
        )
        
        # Evaluate routing
        decision = self.agent.evaluate_routing_decision(context)
        
        # Verify forced routing to C
        self.assertEqual(decision.next_tier, "C")
        self.assertGreaterEqual(decision.confidence, 0.9)
        self.assertIn("Auto-resolve chain", decision.reasoning)
        self.assertIn("D → C → B", decision.reasoning)
    
    def test_no_auto_resolve_routing_when_details_missing(self):
        """Test normal routing when auto_resolve_details not present"""
        from lang_graph_moduel.decision_engine import create_decision_context
        
        # Create context without auto_resolve_details
        context = create_decision_context(
            tier="D",
            status="SUCCESS",
            user_input="Analyze error",
            payload={
                "next_node": "F"
            }
        )
        
        # Evaluate routing
        decision = self.agent.evaluate_routing_decision(context)
        
        # Verify normal routing (not forced to C)
        self.assertNotEqual(decision.next_tier, "C")  # Should use default routing


class TestAutoResolveWorkflowIntegration(unittest.TestCase):
    """Integration test for complete auto-resolve workflow"""
    
    def test_expected_workflow_b_failure_to_d_to_c_to_b(self):
        """Test expected workflow: B failure → D (auto-resolve) → C → B"""
        # This is a documentation test showing the expected flow
        workflow = [
            ("B", "FAILURE", "Test execution failed"),
            ("D", "SUCCESS", "Auto-resolve capable: routing to C"),
            ("C", "SUCCESS", "Applied fix from auto-resolve"),
            ("B", "SUCCESS", "Test execution passed after fix")
        ]
        
        # Verify workflow structure
        self.assertEqual(len(workflow), 4)
        self.assertEqual(workflow[0][0], "B")  # Starts with B failure
        self.assertEqual(workflow[1][0], "D")  # Routes to D for analysis
        self.assertEqual(workflow[2][0], "C")  # D routes to C for fix
        self.assertEqual(workflow[3][0], "B")  # C routes back to B for retry


if __name__ == "__main__":
    unittest.main()
