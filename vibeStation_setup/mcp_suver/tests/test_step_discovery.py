"""
Tests for automated step discovery and confidence-based routing functionality.

Tests the enhanced 6-Tier Task Orchestration Framework features:
- Automated step discovery from workspace structure
- Confidence-based routing with manual override support
- Integration with existing classification system
"""

import unittest
import sys
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from main_agent import MainAgent
from models.core import AgentState


class TestStepDiscovery(unittest.TestCase):
    """Test automated step discovery functionality"""
    
    def setUp(self):
        """Set up test workspace with step directories"""
        # Create temporary workspace
        self.test_workspace = tempfile.mkdtemp()
        self.docs_path = Path(self.test_workspace) / "docs_2"
        self.docs_path.mkdir(parents=True)
        
        # Create sample step directories
        self.create_step_directory(8, "Automated Router Framework Project")
        self.create_step_directory(5, "Complete Remaining User Requirements")
        
        # Create NextTask-2.md
        self.create_nexttask_file()
        
        # Create agent with test workspace
        self.agent = MainAgent(workspace_root=self.test_workspace, enable_metrics=False)
    
    def tearDown(self):
        """Clean up test workspace"""
        shutil.rmtree(self.test_workspace, ignore_errors=True)
    
    def create_step_directory(self, step_num: int, goal: str):
        """Helper to create a step directory with test files"""
        step_dir = self.docs_path / f"P{step_num}"
        step_dir.mkdir(parents=True)
        
        # Create a sample markdown file
        index_file = step_dir / f"P{step_num}-Index.md"
        index_file.write_text(f"""# Step {step_num}

## Goal: {goal}

This is a test step for automated discovery.
""", encoding='utf-8')
    
    def create_nexttask_file(self):
        """Create sample NextTask-2.md file"""
        nexttask = self.docs_path / "NextTask-2.md"
        nexttask.write_text("""# Next Tasks

## step 8: Automated Router Framework Project

### Goal: Enhance automated routing framework

This is step 8 content.

## step 5: Complete Remaining User Requirements

### Goal: Implement remaining features

This is step 5 content.
""", encoding='utf-8')
    
    def test_discover_step_with_directory(self):
        """Test step discovery when step directory exists"""
        result = self.agent.routing_engine.discover_steps("Execute step 8")
        
        self.assertIsNotNone(result)
        self.assertEqual(result["step_number"], 8)
        self.assertEqual(result["step_dir"], "P8")
        self.assertGreater(len(result["documents"]), 0)
        self.assertGreater(result["confidence"], 0.3)
    
    def test_discover_step_with_nexttask_reference(self):
        """Test step discovery using NextTask-2.md reference"""
        result = self.agent.routing_engine.discover_steps("Work on step 5")
        
        self.assertIsNotNone(result)
        self.assertEqual(result["step_number"], 5)
        self.assertGreater(result["confidence"], 0.3)
    
    def test_discover_step_no_match(self):
        """Test step discovery when no step is found"""
        result = self.agent.routing_engine.discover_steps("Create a new plan")
        
        self.assertIsNone(result)
    
    def test_discover_step_nonexistent_step(self):
        """Test step discovery for non-existent step"""
        result = self.agent.routing_engine.discover_steps("Execute step 99")
        
        # Should return None or very low confidence
        if result is not None:
            self.assertLess(result["confidence"], 0.3)
    
    def test_discover_step_pattern_matching(self):
        """Test various input patterns for step discovery"""
        test_cases = [
            ("step 8", 8),
            ("Step 8", 8),
            ("스텝 8", 8),
            ("P8", 8),
            ("part 8", 8),
        ]
        
        for input_text, expected_step in test_cases:
            result = self.agent.routing_engine.discover_steps(input_text)
            if result:  # May be None for some patterns
                self.assertEqual(result["step_number"], expected_step,
                               f"Failed for input: {input_text}")
    
    def test_discover_step_context_extraction(self):
        """Test extraction of step context/goal"""
        result = self.agent.routing_engine.discover_steps("Execute step 8")
        
        self.assertIsNotNone(result)
        # Should extract goal from markdown file
        if result["context"]:
            self.assertIn("Router", result["context"])


class TestConfidenceBasedRouting(unittest.TestCase):
    """Test confidence-based routing with manual override"""
    
    def setUp(self):
        """Set up test agent"""
        self.agent = MainAgent(workspace_root=".", enable_metrics=False)
    
    def test_classify_input_returns_tuple(self):
        """Test that classify_input returns (tier, confidence) tuple"""
        result = self.agent.classify_input("Create a new plan")
        
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)
        
        tier, confidence = result
        self.assertIn(tier, ["A", "B", "C", "D", "E", "F"])
        self.assertGreaterEqual(confidence, 0.0)
        self.assertLessEqual(confidence, 1.0)
    
    def test_high_confidence_classification(self):
        """Test classification with high confidence keywords"""
        tier, confidence = self.agent.classify_input(
            "Create a new work plan for the project"
        )
        
        self.assertEqual(tier, "A")
        self.assertGreater(confidence, 0.5)
    
    def test_low_confidence_classification(self):
        """Test classification with ambiguous input"""
        tier, confidence = self.agent.classify_input(
            "Do something with the system"
        )
        
        # Should have lower confidence due to ambiguity
        self.assertLess(confidence, 0.9)
    
    def test_multiple_keyword_confidence(self):
        """Test that multiple matching keywords increase confidence"""
        # Single keyword
        tier1, conf1 = self.agent.classify_input("execute")
        
        # Multiple keywords
        tier2, conf2 = self.agent.classify_input("execute perform run implement")
        
        # Multiple keywords should have higher confidence
        self.assertEqual(tier1, tier2)
        self.assertGreaterEqual(conf2, conf1)
    
    def test_conflicting_keywords_lower_confidence(self):
        """Test that conflicting keywords lower confidence"""
        tier, confidence = self.agent.classify_input(
            "create and execute and modify"
        )
        
        # Should still classify but with lower confidence
        self.assertIsNotNone(tier)
        # Confidence should be lower due to conflicts
        self.assertLess(confidence, 0.9)


class TestConfidenceBasedRoutingIntegration(unittest.TestCase):
    """Integration tests for confidence-based routing in route_and_execute"""
    
    def setUp(self):
        """Set up test agent"""
        self.agent = MainAgent(workspace_root=".", enable_metrics=False)
    
    @patch.object(MainAgent, 'execute_tier_with_retry')
    def test_automatic_routing_high_confidence(self, mock_execute):
        """Test automatic routing when confidence is high"""
        # Mock successful execution
        mock_execute.return_value = AgentState.create_success(
            tier="A",
            logic_summary="Test execution",
            payload={"next_node": None}
        )
        
        # High confidence input
        result = self.agent.route_and_execute(
            "Create a new work plan",
            max_iterations=1
        )
        
        self.assertEqual(result.status, "SUCCESS")
        mock_execute.assert_called_once()
    
    @patch.object(MainAgent, 'execute_tier_with_retry')
    def test_manual_override_low_confidence(self, mock_execute):
        """Test manual override suggestion when confidence is low"""
        # Mock successful execution
        mock_execute.return_value = AgentState.create_success(
            tier="A",
            logic_summary="Test execution",
            payload={"next_node": None}
        )
        
        # Low confidence input with low threshold
        result = self.agent.route_and_execute(
            "Do something",
            max_iterations=1,
            manual_confidence_threshold=0.9  # High threshold to trigger manual
        )
        
        # Should still execute but log manual override suggestion
        self.assertEqual(result.status, "SUCCESS")
    
    @patch.object(MainAgent, 'execute_tier_with_retry')
    def test_force_manual_routing_flag(self, mock_execute):
        """Test force_manual_routing parameter"""
        # Mock successful execution
        mock_execute.return_value = AgentState.create_success(
            tier="A",
            logic_summary="Test execution",
            payload={"next_node": None}
        )
        
        # Force manual routing even with high confidence
        result = self.agent.route_and_execute(
            "Create a new work plan",
            max_iterations=1,
            force_manual_routing=True
        )
        
        # Should still execute but log forced manual routing
        self.assertEqual(result.status, "SUCCESS")


class TestStepDiscoveryIntegration(unittest.TestCase):
    """Integration tests for step discovery with classification"""
    
    def setUp(self):
        """Set up test workspace"""
        self.test_workspace = tempfile.mkdtemp()
        self.docs_path = Path(self.test_workspace) / "docs_2"
        self.docs_path.mkdir(parents=True)
        
        # Create step 8 directory
        step_dir = self.docs_path / "P8"
        step_dir.mkdir()
        (step_dir / "P8-Index.md").write_text(
            "## Goal: Test step 8\n\nTest content",
            encoding='utf-8'
        )
        
        self.agent = MainAgent(workspace_root=self.test_workspace, enable_metrics=False)
    
    def tearDown(self):
        """Clean up"""
        shutil.rmtree(self.test_workspace, ignore_errors=True)
    
    def test_step_discovery_with_execute_keyword(self):
        """Test step discovery routes to Tier B for execution"""
        tier, confidence = self.agent.classify_input("Execute step 8")
        
        self.assertEqual(tier, "B")  # Execute → Tier B
        self.assertGreater(confidence, 0.3)
    
    def test_step_discovery_with_create_keyword(self):
        """Test step discovery routes to Tier A for planning"""
        tier, confidence = self.agent.classify_input("Create plan for step 8")
        
        self.assertEqual(tier, "A")  # Create → Tier A
        self.assertGreater(confidence, 0.3)
    
    def test_step_discovery_with_modify_keyword(self):
        """Test step discovery routes to Tier C for modification"""
        tier, confidence = self.agent.classify_input("Modify step 8 plan")
        
        self.assertEqual(tier, "C")  # Modify → Tier C
        self.assertGreater(confidence, 0.3)
    
    def test_step_discovery_default_to_execution(self):
        """Test step discovery defaults to execution when no action keyword"""
        tier, confidence = self.agent.classify_input("step 8")
        
        self.assertEqual(tier, "B")  # Default to execution
        self.assertGreater(confidence, 0.3)


if __name__ == "__main__":
    unittest.main()
