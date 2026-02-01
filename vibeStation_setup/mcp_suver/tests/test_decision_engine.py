"""
Unit tests for decision_engine.py

Tests confidence calculation, failure classification, retry logic, and decision evaluation.
"""

import unittest
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from lang_graph_moduel.decision_engine import (
    ConfidenceLevel,
    FailureType,
    DecisionContext,
    RoutingDecision,
    DecisionEngine,
    create_decision_context
)


class TestConfidenceLevel(unittest.TestCase):
    """Test ConfidenceLevel enumeration and classification"""
    
    def test_from_score_very_high(self):
        """Test VERY_HIGH classification"""
        level = ConfidenceLevel.from_score(0.95)
        self.assertEqual(level, ConfidenceLevel.VERY_HIGH)
    
    def test_from_score_high(self):
        """Test HIGH classification"""
        level = ConfidenceLevel.from_score(0.85)
        self.assertEqual(level, ConfidenceLevel.HIGH)
    
    def test_from_score_medium(self):
        """Test MEDIUM classification"""
        level = ConfidenceLevel.from_score(0.65)
        self.assertEqual(level, ConfidenceLevel.MEDIUM)
    
    def test_from_score_low(self):
        """Test LOW classification"""
        level = ConfidenceLevel.from_score(0.45)
        self.assertEqual(level, ConfidenceLevel.LOW)
    
    def test_from_score_very_low(self):
        """Test VERY_LOW classification"""
        level = ConfidenceLevel.from_score(0.25)
        self.assertEqual(level, ConfidenceLevel.VERY_LOW)
    
    def test_boundary_conditions(self):
        """Test boundary values"""
        self.assertEqual(ConfidenceLevel.from_score(0.0), ConfidenceLevel.VERY_LOW)
        self.assertEqual(ConfidenceLevel.from_score(1.0), ConfidenceLevel.VERY_HIGH)
        self.assertEqual(ConfidenceLevel.from_score(0.9), ConfidenceLevel.VERY_HIGH)
        self.assertEqual(ConfidenceLevel.from_score(0.75), ConfidenceLevel.HIGH)


class TestDecisionContext(unittest.TestCase):
    """Test DecisionContext creation and usage"""
    
    def test_basic_context_creation(self):
        """Test creating basic decision context"""
        context = DecisionContext(
            tier="A",
            status="SUCCESS",
            user_input="Create a work plan"
        )
        
        self.assertEqual(context.tier, "A")
        self.assertEqual(context.status, "SUCCESS")
        self.assertEqual(context.user_input, "Create a work plan")
        self.assertEqual(context.retry_count, 0)
    
    def test_context_with_retry(self):
        """Test context with retry information"""
        context = DecisionContext(
            tier="B",
            status="FAILED",
            user_input="Execute plan",
            retry_count=2
        )
        
        self.assertEqual(context.retry_count, 2)
    
    def test_create_decision_context_helper(self):
        """Test helper function for creating context"""
        context = create_decision_context(
            tier="C",
            status="PARTIAL",
            user_input="Modify plan",
            payload={"next_node": "E"},
            retry_count=1
        )
        
        self.assertEqual(context.tier, "C")
        self.assertEqual(context.status, "PARTIAL")
        self.assertEqual(context.payload["next_node"], "E")
        self.assertEqual(context.retry_count, 1)


class TestDecisionEngine(unittest.TestCase):
    """Test DecisionEngine core functionality"""
    
    def setUp(self):
        """Set up test engine"""
        self.engine = DecisionEngine(
            confidence_threshold=0.5,
            max_retries=3,
            base_retry_delay_ms=1000
        )
    
    def test_confidence_calculation_success(self):
        """Test confidence calculation for successful execution"""
        context = DecisionContext(
            tier="A",
            status="SUCCESS",
            user_input="Test input"
        )
        
        factors = self.engine.analyze_context(context)
        confidence = self.engine.calculate_confidence(context, factors)
        
        # Success should increase confidence
        self.assertGreater(confidence, 0.5)
        self.assertTrue(factors["status_success"])
    
    def test_confidence_calculation_failure(self):
        """Test confidence calculation for failed execution"""
        context = DecisionContext(
            tier="B",
            status="FAILED",
            user_input="Test input"
        )
        
        factors = self.engine.analyze_context(context)
        confidence = self.engine.calculate_confidence(context, factors)
        
        # Failure should decrease confidence
        self.assertLess(confidence, 0.5)
        self.assertTrue(factors["status_failed"])
    
    def test_confidence_calculation_with_retries(self):
        """Test confidence penalty for retries"""
        context = DecisionContext(
            tier="C",
            status="SUCCESS",
            user_input="Test input",
            retry_count=2
        )
        
        factors = self.engine.analyze_context(context)
        confidence = self.engine.calculate_confidence(context, factors)
        
        # Retries should decrease confidence
        self.assertLess(confidence, 0.8)  # Success +0.3, retries -0.2
    
    def test_failure_classification_transient(self):
        """Test classification of transient failures"""
        error_messages = [
            "Connection timeout",
            "Network error",
            "503 Service Unavailable",
            "Rate limit exceeded",
            "429 Too Many Requests"
        ]
        
        for msg in error_messages:
            failure_type = self.engine.classify_failure(msg)
            self.assertEqual(failure_type, FailureType.TRANSIENT,
                           f"Expected TRANSIENT for: {msg}")
    
    def test_failure_classification_permanent(self):
        """Test classification of permanent failures"""
        error_messages = [
            "404 Not Found",
            "400 Bad Request",
            "Invalid input",
            "Validation error",
            "401 Unauthorized"
        ]
        
        for msg in error_messages:
            failure_type = self.engine.classify_failure(msg)
            self.assertEqual(failure_type, FailureType.PERMANENT,
                           f"Expected PERMANENT for: {msg}")
    
    def test_failure_classification_unknown(self):
        """Test classification of unknown failures"""
        error_messages = [
            "Something went wrong",
            "Unexpected error",
            "Internal error"
        ]
        
        for msg in error_messages:
            failure_type = self.engine.classify_failure(msg)
            self.assertEqual(failure_type, FailureType.UNKNOWN,
                           f"Expected UNKNOWN for: {msg}")
    
    def test_retry_eligibility_transient(self):
        """Test retry eligibility for transient failures"""
        context = DecisionContext(
            tier="D",
            status="FAILED",
            user_input="Test",
            retry_count=1
        )
        
        eligible = self.engine.determine_retry_eligibility(
            context, FailureType.TRANSIENT
        )
        
        self.assertTrue(eligible)
    
    def test_retry_eligibility_permanent(self):
        """Test no retry for permanent failures"""
        context = DecisionContext(
            tier="D",
            status="FAILED",
            user_input="Test",
            retry_count=0
        )
        
        eligible = self.engine.determine_retry_eligibility(
            context, FailureType.PERMANENT
        )
        
        self.assertFalse(eligible)
    
    def test_retry_eligibility_max_retries(self):
        """Test no retry when max retries reached"""
        context = DecisionContext(
            tier="D",
            status="FAILED",
            user_input="Test",
            retry_count=3
        )
        
        eligible = self.engine.determine_retry_eligibility(
            context, FailureType.TRANSIENT
        )
        
        self.assertFalse(eligible)
    
    def test_backoff_calculation(self):
        """Test exponential backoff calculation"""
        delay_0 = self.engine.calculate_backoff_delay(0)
        delay_1 = self.engine.calculate_backoff_delay(1)
        delay_2 = self.engine.calculate_backoff_delay(2)
        
        self.assertEqual(delay_0, 1000)   # 1s * 2^0
        self.assertEqual(delay_1, 2000)   # 1s * 2^1
        self.assertEqual(delay_2, 4000)   # 1s * 2^2
    
    def test_evaluate_routing_success(self):
        """Test routing evaluation for successful execution"""
        context = DecisionContext(
            tier="A",
            status="SUCCESS",
            user_input="Create plan",
            payload={"next_node": "B"}
        )
        
        decision = self.engine.evaluate_routing(context)
        
        self.assertEqual(decision.next_tier, "B")
        self.assertGreater(decision.confidence, 0.5)
        self.assertFalse(decision.requires_human_approval)
    
    def test_evaluate_routing_low_confidence(self):
        """Test routing evaluation with low confidence"""
        context = DecisionContext(
            tier="B",
            status="FAILED",
            user_input="Execute",
            retry_count=2,
            previous_failures=["Error 1", "Error 2"]
        )
        
        decision = self.engine.evaluate_routing(context)
        
        # Low confidence should trigger human approval
        self.assertLess(decision.confidence, self.engine.HUMAN_APPROVAL_THRESHOLD)
        self.assertTrue(decision.requires_human_approval)
    
    def test_evaluate_failure(self):
        """Test failure evaluation with retry decision"""
        context = DecisionContext(
            tier="C",
            status="FAILED",
            user_input="Modify",
            retry_count=1
        )
        
        decision = self.engine.evaluate_failure(context, "Network timeout")
        
        self.assertTrue(decision.requires_retry)
        self.assertEqual(decision.failure_type, FailureType.TRANSIENT)
        self.assertGreater(decision.retry_delay_ms, 0)
    
    def test_decision_history(self):
        """Test decision history tracking"""
        context1 = create_decision_context("A", "SUCCESS", "Test 1")
        context2 = create_decision_context("B", "SUCCESS", "Test 2")
        
        self.engine.evaluate_routing(context1)
        self.engine.evaluate_routing(context2)
        
        history = self.engine.get_decision_history()
        
        self.assertEqual(len(history), 2)
        self.assertIsInstance(history[0], dict)
        self.assertIn("confidence", history[0])


class TestRoutingDecision(unittest.TestCase):
    """Test RoutingDecision model"""
    
    def test_decision_to_dict(self):
        """Test converting decision to dictionary"""
        decision = RoutingDecision(
            next_tier="B",
            confidence=0.85,
            confidence_level=ConfidenceLevel.HIGH,
            reasoning="High confidence routing",
            requires_human_approval=False
        )
        
        result = decision.to_dict()
        
        self.assertEqual(result["next_tier"], "B")
        self.assertEqual(result["confidence"], 0.85)
        self.assertEqual(result["confidence_level"], "HIGH")
        self.assertFalse(result["requires_human_approval"])
    
    def test_decision_with_retry(self):
        """Test decision with retry information"""
        decision = RoutingDecision(
            next_tier="C",
            confidence=0.3,
            confidence_level=ConfidenceLevel.LOW,
            reasoning="Retry needed",
            requires_retry=True,
            retry_delay_ms=2000,
            failure_type=FailureType.TRANSIENT
        )
        
        result = decision.to_dict()
        
        self.assertTrue(result["requires_retry"])
        self.assertEqual(result["retry_delay_ms"], 2000)
        self.assertEqual(result["failure_type"], "transient")


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error handling"""
    
    def setUp(self):
        self.engine = DecisionEngine()
    
    def test_confidence_clamping(self):
        """Test confidence values are clamped to 0-1 range"""
        context_high = DecisionContext(
            tier="A",
            status="SUCCESS",
            user_input="Test",
            retry_count=0
        )
        
        factors = self.engine.analyze_context(context_high)
        confidence = self.engine.calculate_confidence(context_high, factors)
        
        self.assertLessEqual(confidence, 1.0)
        self.assertGreaterEqual(confidence, 0.0)
    
    def test_empty_error_message(self):
        """Test failure classification with empty error"""
        failure_type = self.engine.classify_failure("")
        self.assertEqual(failure_type, FailureType.UNKNOWN)
    
    def test_case_insensitive_classification(self):
        """Test failure classification is case-insensitive"""
        failure_type1 = self.engine.classify_failure("TIMEOUT ERROR")
        failure_type2 = self.engine.classify_failure("timeout error")
        
        self.assertEqual(failure_type1, failure_type2)
        self.assertEqual(failure_type1, FailureType.TRANSIENT)


if __name__ == "__main__":
    unittest.main()
