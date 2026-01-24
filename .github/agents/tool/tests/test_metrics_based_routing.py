"""
Unit tests for metrics-based routing strategies.

Tests the new IRoutingStrategy interface and implementations:
- KeywordRoutingStrategy
- MetricsBasedRoutingStrategy
- Dynamic confidence threshold adjustment
- Pattern-based routing decisions
"""

import unittest
import sys
from pathlib import Path
from unittest.mock import Mock, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from main_agent import MainAgent
from lang_graph_moduel.metrics_collector import MetricsCollector


class TestMetricsBasedRouting(unittest.TestCase):
    """Test metrics-based routing strategy"""
    
    def setUp(self):
        """Set up test agent with metrics enabled"""
        self.agent = MainAgent(enable_metrics=True, workspace_root=".")
        self.metrics = self.agent.metrics
        if self.metrics:
            self.metrics.reset()
    
    def test_metrics_strategy_initialization(self):
        """Test that metrics strategy is initialized when metrics enabled"""
        self.assertIsNotNone(self.agent.routing_engine.metrics_strategy)
        self.assertIsNotNone(self.agent.routing_engine.keyword_strategy)
        
        # Should default to metrics strategy when metrics enabled
        self.assertIsInstance(
            self.agent.routing_engine.active_strategy,
            MainAgent.MetricsBasedRoutingStrategy
        )
    
    def test_strategy_switching(self):
        """Test switching between strategies"""
        # Switch to keyword
        self.agent.routing_engine.set_strategy(use_metrics_based=False)
        self.assertIsInstance(
            self.agent.routing_engine.active_strategy,
            MainAgent.KeywordRoutingStrategy
        )
        
        # Switch back to metrics
        self.agent.routing_engine.set_strategy(use_metrics_based=True)
        self.assertIsInstance(
            self.agent.routing_engine.active_strategy,
            MainAgent.MetricsBasedRoutingStrategy
        )
    
    def test_dynamic_confidence_threshold(self):
        """Test dynamic confidence threshold calculation"""
        if not self.metrics:
            self.skipTest("Metrics not enabled")
        
        # Add successful executions to get high success rate
        for i in range(20):
            self.metrics.increment_counter(
                "tier_execution_total",
                labels={"tier": "A", "status": "SUCCESS"}
            )
        
        threshold = self.agent.routing_engine.get_dynamic_confidence_threshold()
        
        # With 100% success rate, threshold should be lowered to 0.6
        self.assertLessEqual(threshold, 0.7)
        self.assertGreaterEqual(threshold, 0.6)
    
    def test_dynamic_threshold_with_failures(self):
        """Test dynamic threshold increases with failures"""
        if not self.metrics:
            self.skipTest("Metrics not enabled")
        
        # Add many failures to get low success rate
        for i in range(20):
            self.metrics.increment_counter(
                "tier_execution_total",
                labels={"tier": "A", "status": "FAILED"}
            )
        
        threshold = self.agent.routing_engine.get_dynamic_confidence_threshold()
        
        # With 0% success rate, threshold should be raised to 0.8
        self.assertGreaterEqual(threshold, 0.7)
    
    def test_metrics_based_routing_high_success(self):
        """Test metrics-based routing with high success rate"""
        if not self.metrics:
            self.skipTest("Metrics not enabled")
        
        # Setup: Tier A with high success rate
        for i in range(15):
            self.metrics.increment_counter(
                "tier_execution_total",
                labels={"tier": "A", "status": "SUCCESS"}
            )
        
        result = {
            "status": "SUCCESS",
            "next_node": "B"
        }
        
        next_tier = self.agent.routing_engine.metrics_strategy.decide_routing(
            tier="A",
            result=result,
            execution_history=self.agent.execution_history,
            metrics_collector=self.metrics
        )
        
        # Should trust the next_node recommendation due to high success rate
        self.assertEqual(next_tier, "B")
    
    def test_metrics_based_routing_repeated_failures(self):
        """Test metrics-based routing detects repeated failure patterns"""
        if not self.metrics:
            self.skipTest("Metrics not enabled")
        
        # Setup: Multiple failures in Tier B
        for i in range(3):
            self.metrics.increment_counter(
                "tier_execution_total",
                labels={"tier": "B", "status": "FAILED"}
            )
        
        result = {
            "status": "FAILED",
            "next_node": None
        }
        
        next_tier = self.agent.routing_engine.metrics_strategy.decide_routing(
            tier="B",
            result=result,
            execution_history=self.agent.execution_history,
            metrics_collector=self.metrics
        )
        
        # Should route to D for analysis due to repeated failures
        self.assertEqual(next_tier, "D")
    
    def test_keyword_strategy_fallback(self):
        """Test fallback to keyword strategy when no metrics"""
        agent_no_metrics = MainAgent(enable_metrics=False, workspace_root=".")
        
        # Should use keyword strategy
        self.assertIsInstance(
            agent_no_metrics.routing_engine.active_strategy,
            MainAgent.KeywordRoutingStrategy
        )
        
        # Test basic routing
        result = {"status": "SUCCESS", "next_node": "B"}
        next_tier = agent_no_metrics.routing_engine.decide_routing("A", result)
        
        self.assertEqual(next_tier, "B")


class TestAnalyzePatterns(unittest.TestCase):
    """Test MetricsCollector.analyze_patterns() method"""
    
    def setUp(self):
        """Set up test metrics collector"""
        self.collector = MetricsCollector()
        self.collector.reset()
    
    def test_analyze_patterns_empty_history(self):
        """Test analyze_patterns with no data"""
        patterns = self.collector.analyze_patterns()
        
        self.assertEqual(patterns["tier_success_rates"], {})
        self.assertEqual(patterns["tier_failure_rates"], {})
        self.assertEqual(patterns["total_executions_analyzed"], 0)
        self.assertEqual(patterns["recommended_confidence_threshold"], 0.8)  # Default high threshold
    
    def test_analyze_patterns_with_success_data(self):
        """Test analyze_patterns with successful executions"""
        # Add 10 successful executions for Tier A
        for i in range(10):
            self.collector.increment_counter(
                "tier_execution_total",
                labels={"tier": "A", "status": "SUCCESS"}
            )
            self.collector.observe_histogram(
                "tier_execution_duration_ms",
                100.0 + i * 5,
                labels={"tier": "A"}
            )
            self.collector.set_gauge(
                "routing_confidence",
                0.8 + i * 0.01,
                labels={"tier": "A"}
            )
        
        patterns = self.collector.analyze_patterns()
        
        # Check success rate
        self.assertIn("A", patterns["tier_success_rates"])
        self.assertEqual(patterns["tier_success_rates"]["A"], 1.0)
        
        # Check execution time
        self.assertIn("A", patterns["avg_execution_time"])
        self.assertGreater(patterns["avg_execution_time"]["A"], 100.0)
        
        # Check confidence trends
        self.assertIn("A", patterns["confidence_trends"])
        self.assertEqual(len(patterns["confidence_trends"]["A"]), 10)
        
        # High success rate should lower threshold
        self.assertLessEqual(patterns["recommended_confidence_threshold"], 0.7)
    
    def test_analyze_patterns_with_mixed_results(self):
        """Test analyze_patterns with mixed success/failure"""
        # Add 5 successes and 5 failures for Tier B
        for i in range(5):
            self.collector.increment_counter(
                "tier_execution_total",
                labels={"tier": "B", "status": "SUCCESS"}
            )
        
        for i in range(5):
            self.collector.increment_counter(
                "tier_execution_total",
                labels={"tier": "B", "status": "FAILED"}
            )
        
        patterns = self.collector.analyze_patterns()
        
        # Check success/failure rates
        self.assertIn("B", patterns["tier_success_rates"])
        self.assertIn("B", patterns["tier_failure_rates"])
        self.assertEqual(patterns["tier_success_rates"]["B"], 0.5)
        self.assertEqual(patterns["tier_failure_rates"]["B"], 0.5)
        
        # Medium success rate should keep standard threshold
        self.assertGreaterEqual(patterns["recommended_confidence_threshold"], 0.6)
        self.assertLessEqual(patterns["recommended_confidence_threshold"], 0.8)
    
    def test_analyze_patterns_tier_filter(self):
        """Test analyze_patterns with tier filter"""
        # Add data for multiple tiers
        for tier in ["A", "B", "C"]:
            for i in range(5):
                self.collector.increment_counter(
                    "tier_execution_total",
                    labels={"tier": tier, "status": "SUCCESS"}
                )
        
        # Analyze only Tier A
        patterns = self.collector.analyze_patterns(tier="A")
        
        # Should only have Tier A data
        self.assertIn("A", patterns["tier_success_rates"])
        self.assertNotIn("B", patterns["tier_success_rates"])
        self.assertNotIn("C", patterns["tier_success_rates"])
    
    def test_analyze_patterns_failure_patterns(self):
        """Test common failure patterns identification"""
        # Add some failures
        for i in range(3):
            self.collector.increment_counter(
                "tier_execution_total",
                labels={"tier": "C", "status": "FAILED"}
            )
        
        patterns = self.collector.analyze_patterns()
        
        # Check common failure patterns
        self.assertIn("common_failure_patterns", patterns)
        self.assertGreater(len(patterns["common_failure_patterns"]), 0)
        
        # All failure patterns should be for Tier C
        for failure in patterns["common_failure_patterns"]:
            self.assertEqual(failure["tier"], "C")


class TestIntegration(unittest.TestCase):
    """Integration tests for metrics-based routing"""
    
    def setUp(self):
        """Set up test agent"""
        self.agent = MainAgent(enable_metrics=True, workspace_root=".")
        if self.agent.metrics:
            self.agent.metrics.reset()
    
    def test_evaluate_routing_decision_uses_dynamic_threshold(self):
        """Test that evaluate_routing_decision uses dynamic threshold"""
        if not self.agent.metrics or not self.agent.enable_decision_engine:
            self.skipTest("Metrics or decision engine not enabled")
        
        # Add successful executions to lower threshold
        for i in range(20):
            self.agent.metrics.increment_counter(
                "tier_execution_total",
                labels={"tier": "A", "status": "SUCCESS"}
            )
        
        from lang_graph_moduel.decision_engine import create_decision_context
        
        context = create_decision_context(
            tier="A",
            status="SUCCESS",
            user_input="Test",
            payload={"next_node": "B"}
        )
        
        decision = self.agent.evaluate_routing_decision(context)
        
        # Should have made a decision
        self.assertIsNotNone(decision)
        self.assertIsNotNone(decision.next_tier)


if __name__ == "__main__":
    unittest.main()
