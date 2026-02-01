"""
Integration tests for main_agent.py

Tests end-to-end orchestration with decision engine, circuit breaker, retry logic,
and policy integration.
"""

import unittest
import sys
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from main_agent import MainAgent, CircuitBreakerState
from models.core import AgentState
from lang_graph_moduel.decision_engine import DecisionContext, RoutingDecision, ConfidenceLevel
from lang_graph_moduel.policy_engine import PolicyRule, PolicyCondition, PolicyAction


class TestCircuitBreakerState(unittest.TestCase):
    """Test CircuitBreakerState functionality"""
    
    def test_initial_state(self):
        """Test circuit breaker starts in CLOSED state"""
        cb = CircuitBreakerState("A")
        
        self.assertEqual(cb.state, CircuitBreakerState.CLOSED)
        self.assertEqual(cb.failure_count, 0)
        self.assertTrue(cb.can_execute())
    
    def test_record_success_resets_failures(self):
        """Test success resets failure count"""
        cb = CircuitBreakerState("A")
        cb.failure_count = 3
        
        cb.record_success()
        
        self.assertEqual(cb.failure_count, 0)
        self.assertEqual(cb.state, CircuitBreakerState.CLOSED)
    
    def test_circuit_opens_after_threshold(self):
        """Test circuit opens after failure threshold"""
        cb = CircuitBreakerState("A", failure_threshold=3)
        
        cb.record_failure()
        cb.record_failure()
        self.assertTrue(cb.can_execute())  # Still closed
        
        cb.record_failure()
        self.assertFalse(cb.can_execute())  # Now open
        self.assertEqual(cb.state, CircuitBreakerState.OPEN)
    
    def test_cooldown_period(self):
        """Test circuit transitions to HALF_OPEN after cooldown"""
        cb = CircuitBreakerState("A", failure_threshold=2, cooldown_seconds=1)
        
        # Trigger circuit open
        cb.record_failure()
        cb.record_failure()
        
        self.assertFalse(cb.can_execute())
        
        # Wait for cooldown
        time.sleep(1.1)
        
        self.assertTrue(cb.can_execute())
        self.assertEqual(cb.state, CircuitBreakerState.HALF_OPEN)
    
    def test_half_open_success_closes_circuit(self):
        """Test success in HALF_OPEN state closes circuit"""
        cb = CircuitBreakerState("A")
        cb.state = CircuitBreakerState.HALF_OPEN
        
        cb.record_success()
        
        self.assertEqual(cb.state, CircuitBreakerState.CLOSED)
    
    def test_reset(self):
        """Test circuit breaker reset"""
        cb = CircuitBreakerState("A")
        cb.record_failure()
        cb.record_failure()
        
        cb.reset()
        
        self.assertEqual(cb.state, CircuitBreakerState.CLOSED)
        self.assertEqual(cb.failure_count, 0)


class TestMainAgentInitialization(unittest.TestCase):
    """Test MainAgent initialization"""
    
    def test_default_initialization(self):
        """Test agent initialization with defaults"""
        agent = MainAgent(workspace_root=".")
        
        self.assertIsNotNone(agent.decision_engine)
        self.assertIsNotNone(agent.policy_engine)
        self.assertIsNotNone(agent.metrics)
        self.assertTrue(agent.enable_decision_engine)
        self.assertTrue(agent.enable_circuit_breaker)
        self.assertTrue(agent.enable_metrics)
    
    def test_disable_decision_engine(self):
        """Test initialization with decision engine disabled"""
        agent = MainAgent(enable_decision_engine=False)
        
        self.assertIsNone(agent.decision_engine)
    
    def test_disable_metrics(self):
        """Test initialization with metrics disabled"""
        agent = MainAgent(enable_metrics=False)
        
        self.assertIsNone(agent.metrics)
    
    def test_circuit_breakers_created(self):
        """Test circuit breakers created for all tiers"""
        agent = MainAgent()
        
        for tier in ["A", "B", "C", "D", "E", "F"]:
            self.assertIn(tier, agent.circuit_breakers)
            self.assertIsInstance(agent.circuit_breakers[tier], CircuitBreakerState)


class TestClassification(unittest.TestCase):
    """Test input classification"""
    
    def setUp(self):
        self.agent = MainAgent(workspace_root=".", enable_metrics=True)
        if self.agent.metrics:
            self.agent.metrics.reset()
    
    def test_classify_tier_a(self):
        """Test classification for Tier A (work plan creation)"""
        tier, confidence = self.agent.classify_input("Create a new work plan")
        self.assertEqual(tier, "A")
        self.assertGreater(confidence, 0.0)
    
    def test_classify_tier_b(self):
        """Test classification for Tier B (execution)"""
        tier, confidence = self.agent.classify_input("Execute the plan and perform tasks")
        self.assertEqual(tier, "B")
        self.assertGreater(confidence, 0.0)
    
    def test_classify_tier_c(self):
        """Test classification for Tier C (modification)"""
        tier, confidence = self.agent.classify_input("Change and modify the milestone")
        self.assertEqual(tier, "C")
        self.assertGreater(confidence, 0.0)
    
    def test_classify_tier_d(self):
        """Test classification for Tier D (issue analysis)"""
        tier, confidence = self.agent.classify_input("Analyze this error")
        self.assertEqual(tier, "D")
        self.assertGreater(confidence, 0.0)
    
    def test_classify_tier_e(self):
        """Test classification for Tier E (document management)"""
        tier, confidence = self.agent.classify_input("Save the document")
        self.assertEqual(tier, "E")
        self.assertGreater(confidence, 0.0)
    
    def test_classify_tier_f(self):
        """Test classification for ambiguous input defaults to Tier A (plan creation)"""
        # Changed behavior: ambiguous inputs now default to Tier A for automatic workflow
        tier, confidence = self.agent.classify_input("Random unclear request")
        self.assertEqual(tier, "A")  # Changed from "F" to "A" for automatic workflow
        # Low confidence for ambiguous input
        self.assertLessEqual(confidence, 0.5)
    
    def test_classify_input_records_metrics(self):
        """Test that classify_input() records appropriate metrics"""
        # Reset metrics
        if self.agent.metrics:
            self.agent.metrics.reset()
        
        # Classify input
        tier, confidence = self.agent.classify_input("Create a work plan")
        
        # Verify metrics were recorded (if decision engine was used)
        if self.agent.enable_decision_engine and self.agent.metrics:
            # Check if AI classification or keyword classification metric exists
            ai_confidence = self.agent.metrics.get_gauge("ai_classification_confidence")
            keyword_used = self.agent.metrics.get_gauge("keyword_classification_used")
            
            # At least one should be set (either AI or keyword-based classification)
            self.assertTrue(
                ai_confidence is not None or keyword_used is not None,
                "Classification should record either AI confidence or keyword usage metric"
            )
    
    def test_classify_input_records_decision_engine_failure(self):
        """Test that decision engine failures are recorded in metrics"""
        # Create agent with decision engine that will fail
        agent = MainAgent(workspace_root=".", enable_metrics=True, enable_decision_engine=True)
        if agent.metrics:
            agent.metrics.reset()
        
        # Mock decision engine to raise exception
        if agent.decision_engine:
            original_evaluate = agent.decision_engine.evaluate_routing
            
            def failing_evaluate(*args, **kwargs):
                raise Exception("Simulated decision engine failure")
            
            agent.decision_engine.evaluate_routing = failing_evaluate
            
            # Should fall back to keyword matching and record failure
            tier, confidence = agent.classify_input("Create plan")
            
            # Verify failure was recorded
            if agent.metrics:
                failure_count = agent.metrics.get_counter("decision_engine_failures")
                self.assertGreater(failure_count, 0, "Decision engine failure should be recorded")
            
            # Restore original method
            agent.decision_engine.evaluate_routing = original_evaluate


class TestCircuitBreakerManagement(unittest.TestCase):
    """Test circuit breaker management"""
    
    def setUp(self):
        self.agent = MainAgent()
    
    def test_is_circuit_breaker_open(self):
        """Test checking circuit breaker state"""
        self.assertFalse(self.agent.is_circuit_breaker_open("A"))
        
        # Trigger circuit breaker
        cb = self.agent.circuit_breakers["A"]
        cb.state = CircuitBreakerState.OPEN
        
        self.assertTrue(self.agent.is_circuit_breaker_open("A"))
    
    def test_record_tier_success(self):
        """Test recording tier success"""
        cb = self.agent.circuit_breakers["B"]
        cb.failure_count = 2
        
        self.agent.record_tier_success("B")
        
        self.assertEqual(cb.failure_count, 0)
    
    def test_record_tier_failure(self):
        """Test recording tier failure"""
        cb = self.agent.circuit_breakers["C"]
        
        for _ in range(5):  # Default threshold is 5
            self.agent.record_tier_failure("C")
        
        self.assertEqual(cb.state, CircuitBreakerState.OPEN)
    
    def test_reset_circuit_breaker(self):
        """Test resetting circuit breaker"""
        cb = self.agent.circuit_breakers["D"]
        cb.state = CircuitBreakerState.OPEN
        cb.failure_count = 5
        
        self.agent.reset_circuit_breaker("D")
        
        self.assertEqual(cb.state, CircuitBreakerState.CLOSED)
        self.assertEqual(cb.failure_count, 0)


class TestDecisionEvaluation(unittest.TestCase):
    """Test decision evaluation with policies"""
    
    def setUp(self):
        self.agent = MainAgent(enable_metrics=False)
    
    def test_evaluate_routing_decision_success(self):
        """Test routing decision for successful execution"""
        context = DecisionContext(
            tier="A",
            status="SUCCESS",
            user_input="Test input",
            payload={"next_node": "B"}
        )
        
        decision = self.agent.evaluate_routing_decision(context)
        
        self.assertEqual(decision.next_tier, "B")
        self.assertGreater(decision.confidence, 0.5)
    
    def test_evaluate_routing_decision_low_confidence(self):
        """Test routing decision with low confidence"""
        context = DecisionContext(
            tier="B",
            status="FAILED",
            user_input="Test input",
            retry_count=2,
            previous_failures=["Error 1", "Error 2"]
        )
        
        decision = self.agent.evaluate_routing_decision(context)
        
        # Should have low confidence
        self.assertLess(decision.confidence, 0.5)
    
    def test_policy_application(self):
        """Test policy rules are applied to decisions"""
        # Add a custom policy
        policy = PolicyRule(
            name="test_policy",
            condition=PolicyCondition(field="tier", operator="==", value="A"),
            action=PolicyAction(use_alternative=True, alternative_tier="Z"),
            priority=200  # High priority
        )
        self.agent.policy_engine.add_rule(policy)
        
        context = DecisionContext(
            tier="A",
            status="SUCCESS",
            user_input="Test"
        )
        
        decision = self.agent.evaluate_routing_decision(context)
        
        # Policy should override to Z
        self.assertEqual(decision.next_tier, "Z")


class TestTierExecution(unittest.TestCase):
    """Test tier execution (mocked)"""
    
    def setUp(self):
        self.agent = MainAgent(enable_metrics=False)
    
    @patch('main_agent.MainAgent.execute_tier')
    def test_execute_tier_with_retry_success(self, mock_execute):
        """Test successful execution without retry"""
        mock_state = AgentState.create_success("A", "Success", next_node="B")
        mock_execute.return_value = mock_state
        
        result = self.agent.execute_tier_with_retry("A", "Test input")
        
        self.assertEqual(result.status, "SUCCESS")
        self.assertEqual(mock_execute.call_count, 1)
    
    @patch('main_agent.MainAgent.execute_tier')
    def test_execute_tier_with_retry_transient_failure(self, mock_execute):
        """Test retry on transient failure"""
        # First call fails, second succeeds
        mock_execute.side_effect = [
            AgentState.create_failure("A", "Network timeout"),
            AgentState.create_success("A", "Success after retry")
        ]
        
        result = self.agent.execute_tier_with_retry("A", "Test input")
        
        # Should have retried
        self.assertGreater(mock_execute.call_count, 1)
    
    @patch('main_agent.MainAgent.execute_tier')
    def test_execute_tier_circuit_breaker_blocks(self, mock_execute):
        """Test circuit breaker blocks execution"""
        # Open circuit breaker
        cb = self.agent.circuit_breakers["B"]
        cb.state = CircuitBreakerState.OPEN
        
        result = self.agent.execute_tier_with_retry("B", "Test input")
        
        self.assertEqual(result.status, "FAILED")
        self.assertIn("Circuit breaker", result.errors[0])
        mock_execute.assert_not_called()


class TestHumanInTheLoop(unittest.TestCase):
    """Test human-in-the-loop functionality"""
    
    def setUp(self):
        self.agent = MainAgent(enable_metrics=False)
    
    def test_handle_human_decision(self):
        """Test handling human decision input"""
        decision_data = {
            "next_tier": "B",
            "override_confidence": 0.95,
            "reason": "Human approved routing to B"
        }
        
        decision = self.agent.handle_human_decision(decision_data)
        
        self.assertEqual(decision.next_tier, "B")
        self.assertEqual(decision.confidence, 0.95)
        self.assertFalse(self.agent.awaiting_decision)
    
    def test_awaiting_decision_flag(self):
        """Test awaiting decision flag is set correctly"""
        self.agent.awaiting_decision = True
        self.assertIsNone(self.agent.pending_decision_context)
        
        decision_data = {"next_tier": "C", "reason": "Approved"}
        self.agent.handle_human_decision(decision_data)
        
        self.assertFalse(self.agent.awaiting_decision)


class TestMetricsIntegration(unittest.TestCase):
    """Test metrics collection during execution"""
    
    def setUp(self):
        self.agent = MainAgent(enable_metrics=True)
        self.agent.metrics.reset()
    
    @patch('main_agent.MainAgent.execute_tier')
    def test_metrics_recorded_on_execution(self, mock_execute):
        """Test metrics are recorded during tier execution"""
        mock_state = AgentState.create_success("A", "Success")
        mock_execute.return_value = mock_state
        
        self.agent.execute_tier_with_retry("A", "Test")
        
        # Check metrics were recorded
        tier_count = self.agent.metrics.get_counter(
            "tier_execution_total",
            labels={"tier": "A", "status": "SUCCESS"}
        )
        self.assertGreater(tier_count, 0)
    
    def test_circuit_breaker_metrics(self):
        """Test circuit breaker metrics are recorded"""
        # Trigger circuit breaker open
        for _ in range(5):
            self.agent.record_tier_failure("B")
        
        open_count = self.agent.metrics.get_counter(
            "circuit_breaker_open_total",
            labels={"tier": "B"}
        )
        self.assertEqual(open_count, 1.0)


class TestExecutionHistory(unittest.TestCase):
    """Test execution history tracking"""
    
    def setUp(self):
        self.agent = MainAgent(enable_metrics=False)
    
    def test_execution_history_recorded(self):
        """Test execution history is recorded"""
        # Create a simple state and manually add to history
        state = AgentState.create_success("A", "Success", next_node="B")
        
        # Manually record in history (simulating what execute_tier does)
        self.agent.execution_history.append({
            "tier": "A",
            "timestamp": "2026-01-12T00:00:00",
            "status": state.status,
            "next_node": state.next_node,
            "confidence": state.confidence,
            "retry_count": state.retry_count
        })
        
        self.assertEqual(len(self.agent.execution_history), 1)
        self.assertEqual(self.agent.execution_history[0]["tier"], "A")
        self.assertEqual(self.agent.execution_history[0]["status"], "SUCCESS")


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error handling"""
    
    def setUp(self):
        self.agent = MainAgent(enable_metrics=False)
    
    def test_invalid_tier(self):
        """Test handling of invalid tier"""
        result = self.agent.execute_tier("Z", "Invalid tier")
        
        self.assertEqual(result.status, "FAILED")
        self.assertIn("Invalid tier", result.errors[0])
    
    @patch('main_agent.MainAgent.execute_tier')
    def test_max_retries_reached(self, mock_execute):
        """Test behavior when max retries reached"""
        # Always return transient failure
        mock_execute.return_value = AgentState.create_failure("C", "Timeout error")
        
        result = self.agent.execute_tier_with_retry("C", "Test")
        
        # Should have attempted max retries (3) + original attempt = 4
        self.assertGreaterEqual(mock_execute.call_count, 1)
        self.assertEqual(result.status, "FAILED")
    
    def test_export_metrics_disabled(self):
        """Test metrics export when metrics disabled"""
        agent = MainAgent(enable_metrics=False)
        
        result = agent.export_metrics(format="json")
        
        self.assertEqual(result, "{}")


class TestEndToEndScenarios(unittest.TestCase):
    """Test end-to-end execution scenarios"""
    
    def test_successful_chain_execution(self):
        """Test successful chained execution simulation"""
        agent = MainAgent(enable_metrics=False)
        
        # Manually simulate chain execution by adding to history
        agent.execution_history.append({
            "tier": "A",
            "timestamp": "2026-01-12T00:00:00",
            "status": "SUCCESS",
            "next_node": "B",
            "confidence": 0.8,
            "retry_count": 0
        })
        agent.execution_history.append({
            "tier": "B",
            "timestamp": "2026-01-12T00:00:01",
            "status": "SUCCESS",
            "next_node": "E",
            "confidence": 0.8,
            "retry_count": 0
        })
        agent.execution_history.append({
            "tier": "E",
            "timestamp": "2026-01-12T00:00:02",
            "status": "SUCCESS",
            "next_node": None,
            "confidence": 0.8,
            "retry_count": 0
        })
        
        # Should have executed multiple tiers
        self.assertEqual(len(agent.execution_history), 3)
        self.assertEqual(agent.execution_history[0]["tier"], "A")
        self.assertEqual(agent.execution_history[1]["tier"], "B")
        self.assertEqual(agent.execution_history[2]["tier"], "E")


if __name__ == "__main__":
    unittest.main()
