"""
Unit tests for policy_engine.py

Tests policy loading, condition evaluation, rule matching, and priority-based evaluation.
"""

import unittest
import json
import tempfile
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from lang_graph_moduel.policy_engine import (
    OperatorType,
    PolicyCondition,
    PolicyAction,
    PolicyRule,
    PolicyEngine,
    create_default_policies
)


class TestPolicyCondition(unittest.TestCase):
    """Test PolicyCondition evaluation"""
    
    def test_equal_operator(self):
        """Test == operator"""
        condition = PolicyCondition(field="status", operator="==", value="SUCCESS")
        
        self.assertTrue(condition.evaluate({"status": "SUCCESS"}))
        self.assertFalse(condition.evaluate({"status": "FAILED"}))
    
    def test_not_equal_operator(self):
        """Test != operator"""
        condition = PolicyCondition(field="status", operator="!=", value="FAILED")
        
        self.assertTrue(condition.evaluate({"status": "SUCCESS"}))
        self.assertFalse(condition.evaluate({"status": "FAILED"}))
    
    def test_less_than_operator(self):
        """Test < operator"""
        condition = PolicyCondition(field="confidence", operator="<", value=0.5)
        
        self.assertTrue(condition.evaluate({"confidence": 0.3}))
        self.assertFalse(condition.evaluate({"confidence": 0.7}))
    
    def test_less_equal_operator(self):
        """Test <= operator"""
        condition = PolicyCondition(field="confidence", operator="<=", value=0.5)
        
        self.assertTrue(condition.evaluate({"confidence": 0.5}))
        self.assertTrue(condition.evaluate({"confidence": 0.3}))
        self.assertFalse(condition.evaluate({"confidence": 0.7}))
    
    def test_greater_than_operator(self):
        """Test > operator"""
        condition = PolicyCondition(field="retry_count", operator=">", value=2)
        
        self.assertTrue(condition.evaluate({"retry_count": 3}))
        self.assertFalse(condition.evaluate({"retry_count": 1}))
    
    def test_greater_equal_operator(self):
        """Test >= operator"""
        condition = PolicyCondition(field="retry_count", operator=">=", value=2)
        
        self.assertTrue(condition.evaluate({"retry_count": 2}))
        self.assertTrue(condition.evaluate({"retry_count": 3}))
        self.assertFalse(condition.evaluate({"retry_count": 1}))
    
    def test_in_operator(self):
        """Test 'in' operator"""
        condition = PolicyCondition(field="tier", operator="in", value=["A", "B", "C"])
        
        self.assertTrue(condition.evaluate({"tier": "A"}))
        self.assertTrue(condition.evaluate({"tier": "B"}))
        self.assertFalse(condition.evaluate({"tier": "D"}))
    
    def test_not_in_operator(self):
        """Test 'not_in' operator"""
        condition = PolicyCondition(field="tier", operator="not_in", value=["D", "E"])
        
        self.assertTrue(condition.evaluate({"tier": "A"}))
        self.assertFalse(condition.evaluate({"tier": "D"}))
    
    def test_contains_operator(self):
        """Test 'contains' operator"""
        condition = PolicyCondition(field="message", operator="contains", value="error")
        
        self.assertTrue(condition.evaluate({"message": "An error occurred"}))
        self.assertFalse(condition.evaluate({"message": "Success"}))
    
    def test_nested_field_access(self):
        """Test nested field path with dot notation"""
        condition = PolicyCondition(field="payload.status", operator="==", value="COMPLETE")
        
        context = {"payload": {"status": "COMPLETE"}}
        self.assertTrue(condition.evaluate(context))
        
        context = {"payload": {"status": "PENDING"}}
        self.assertFalse(condition.evaluate(context))
    
    def test_missing_field(self):
        """Test evaluation with missing field"""
        condition = PolicyCondition(field="nonexistent", operator="==", value="test")
        
        self.assertFalse(condition.evaluate({"other_field": "value"}))


class TestPolicyAction(unittest.TestCase):
    """Test PolicyAction model"""
    
    def test_basic_action_creation(self):
        """Test creating basic action"""
        action = PolicyAction(requires_human_approval=True)
        
        self.assertTrue(action.requires_human_approval)
        self.assertFalse(action.use_alternative)
    
    def test_alternative_routing_action(self):
        """Test action with alternative routing"""
        action = PolicyAction(
            use_alternative=True,
            alternative_tier="D"
        )
        
        self.assertTrue(action.use_alternative)
        self.assertEqual(action.alternative_tier, "D")
    
    def test_from_dict(self):
        """Test creating action from dictionary"""
        data = {
            "requires_human_approval": True,
            "use_alternative": True,
            "alternative_tier": "E",
            "override_confidence": 0.9
        }
        
        action = PolicyAction.from_dict(data)
        
        self.assertTrue(action.requires_human_approval)
        self.assertTrue(action.use_alternative)
        self.assertEqual(action.alternative_tier, "E")
        self.assertEqual(action.override_confidence, 0.9)


class TestPolicyRule(unittest.TestCase):
    """Test PolicyRule evaluation"""
    
    def test_rule_evaluation_matching(self):
        """Test rule evaluation when condition matches"""
        condition = PolicyCondition(field="confidence", operator="<", value=0.4)
        action = PolicyAction(requires_human_approval=True)
        rule = PolicyRule(
            name="low_confidence",
            condition=condition,
            action=action,
            enabled=True
        )
        
        result = rule.evaluate({"confidence": 0.3})
        
        self.assertIsNotNone(result)
        self.assertTrue(result.requires_human_approval)
    
    def test_rule_evaluation_not_matching(self):
        """Test rule evaluation when condition doesn't match"""
        condition = PolicyCondition(field="confidence", operator="<", value=0.4)
        action = PolicyAction(requires_human_approval=True)
        rule = PolicyRule(
            name="low_confidence",
            condition=condition,
            action=action,
            enabled=True
        )
        
        result = rule.evaluate({"confidence": 0.7})
        
        self.assertIsNone(result)
    
    def test_disabled_rule(self):
        """Test disabled rule returns None"""
        condition = PolicyCondition(field="confidence", operator="<", value=0.4)
        action = PolicyAction(requires_human_approval=True)
        rule = PolicyRule(
            name="low_confidence",
            condition=condition,
            action=action,
            enabled=False
        )
        
        result = rule.evaluate({"confidence": 0.3})
        
        self.assertIsNone(result)
    
    def test_from_dict(self):
        """Test creating rule from dictionary"""
        data = {
            "name": "test_rule",
            "condition": {
                "field": "status",
                "operator": "==",
                "value": "FAILED"
            },
            "action": {
                "use_alternative": True,
                "alternative_tier": "D"
            },
            "priority": 100,
            "enabled": True,
            "description": "Route failures to issue analysis"
        }
        
        rule = PolicyRule.from_dict(data)
        
        self.assertEqual(rule.name, "test_rule")
        self.assertEqual(rule.priority, 100)
        self.assertTrue(rule.enabled)
        self.assertEqual(rule.description, "Route failures to issue analysis")


class TestPolicyEngine(unittest.TestCase):
    """Test PolicyEngine functionality"""
    
    def setUp(self):
        """Set up test engine"""
        self.engine = PolicyEngine()
    
    def test_add_rule(self):
        """Test adding a rule"""
        condition = PolicyCondition(field="tier", operator="==", value="A")
        action = PolicyAction(use_alternative=True, alternative_tier="B")
        rule = PolicyRule(
            name="tier_a_to_b",
            condition=condition,
            action=action,
            priority=50
        )
        
        self.engine.add_rule(rule)
        
        self.assertEqual(self.engine.get_rule_count(), 1)
        self.assertEqual(self.engine.get_enabled_count(), 1)
    
    def test_remove_rule(self):
        """Test removing a rule"""
        condition = PolicyCondition(field="tier", operator="==", value="A")
        action = PolicyAction(use_alternative=True, alternative_tier="B")
        rule = PolicyRule(name="test_rule", condition=condition, action=action)
        
        self.engine.add_rule(rule)
        removed = self.engine.remove_rule("test_rule")
        
        self.assertTrue(removed)
        self.assertEqual(self.engine.get_rule_count(), 0)
    
    def test_enable_disable_rule(self):
        """Test enabling and disabling rules"""
        condition = PolicyCondition(field="tier", operator="==", value="A")
        action = PolicyAction(use_alternative=True, alternative_tier="B")
        rule = PolicyRule(name="test_rule", condition=condition, action=action)
        
        self.engine.add_rule(rule)
        
        self.engine.disable_rule("test_rule")
        self.assertEqual(self.engine.get_enabled_count(), 0)
        
        self.engine.enable_rule("test_rule")
        self.assertEqual(self.engine.get_enabled_count(), 1)
    
    def test_evaluate_first_match(self):
        """Test evaluation returns first matching rule"""
        # Add two rules with different priorities
        rule1 = PolicyRule(
            name="high_priority",
            condition=PolicyCondition(field="confidence", operator="<", value=0.5),
            action=PolicyAction(requires_human_approval=True),
            priority=100
        )
        
        rule2 = PolicyRule(
            name="low_priority",
            condition=PolicyCondition(field="confidence", operator="<", value=0.5),
            action=PolicyAction(use_alternative=True, alternative_tier="D"),
            priority=50
        )
        
        self.engine.add_rule(rule1)
        self.engine.add_rule(rule2)
        
        action = self.engine.evaluate({"confidence": 0.3})
        
        # Should return high priority rule's action
        self.assertIsNotNone(action)
        self.assertTrue(action.requires_human_approval)
    
    def test_evaluate_all_matches(self):
        """Test evaluating all matching rules"""
        rule1 = PolicyRule(
            name="rule1",
            condition=PolicyCondition(field="tier", operator="==", value="A"),
            action=PolicyAction(use_alternative=True, alternative_tier="B"),
            priority=100
        )
        
        rule2 = PolicyRule(
            name="rule2",
            condition=PolicyCondition(field="tier", operator="==", value="A"),
            action=PolicyAction(requires_human_approval=True),
            priority=50
        )
        
        self.engine.add_rule(rule1)
        self.engine.add_rule(rule2)
        
        matches = self.engine.evaluate_all({"tier": "A"})
        
        self.assertEqual(len(matches), 2)
        self.assertEqual(matches[0][0], "rule1")
        self.assertEqual(matches[1][0], "rule2")
    
    def test_load_policies_from_json(self):
        """Test loading policies from JSON file"""
        # Create temporary JSON file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config = {
                "rules": [
                    {
                        "name": "test_rule",
                        "condition": {
                            "field": "confidence",
                            "operator": "<",
                            "value": 0.4
                        },
                        "action": {
                            "requires_human_approval": True
                        },
                        "priority": 100,
                        "enabled": True
                    }
                ]
            }
            json.dump(config, f)
            temp_path = f.name
        
        try:
            engine = PolicyEngine(temp_path)
            
            self.assertEqual(engine.get_rule_count(), 1)
            
            rule = engine.get_rule("test_rule")
            self.assertIsNotNone(rule)
            self.assertEqual(rule.priority, 100)
        finally:
            Path(temp_path).unlink()
    
    def test_validate_rules(self):
        """Test rule validation"""
        # Add valid rule
        valid_rule = PolicyRule(
            name="valid_rule",
            condition=PolicyCondition(field="tier", operator="==", value="A"),
            action=PolicyAction(use_alternative=True),
            priority=50
        )
        self.engine.add_rule(valid_rule)
        
        # Add invalid rule (no name)
        invalid_rule = PolicyRule(
            name="",
            condition=PolicyCondition(field="tier", operator="==", value="A"),
            action=PolicyAction(),
            priority=50
        )
        self.engine.add_rule(invalid_rule)
        
        issues = self.engine.validate_rules()
        
        self.assertGreater(len(issues), 0)
        self.assertTrue(any("no name" in issue.lower() for issue in issues))
    
    def test_get_matching_rules(self):
        """Test getting names of matching rules"""
        rule1 = PolicyRule(
            name="match1",
            condition=PolicyCondition(field="status", operator="==", value="FAILED"),
            action=PolicyAction()
        )
        
        rule2 = PolicyRule(
            name="match2",
            condition=PolicyCondition(field="status", operator="==", value="FAILED"),
            action=PolicyAction()
        )
        
        rule3 = PolicyRule(
            name="no_match",
            condition=PolicyCondition(field="status", operator="==", value="SUCCESS"),
            action=PolicyAction()
        )
        
        self.engine.add_rule(rule1)
        self.engine.add_rule(rule2)
        self.engine.add_rule(rule3)
        
        matching = self.engine.get_matching_rules({"status": "FAILED"})
        
        self.assertEqual(len(matching), 2)
        self.assertIn("match1", matching)
        self.assertIn("match2", matching)
        self.assertNotIn("no_match", matching)
    
    def test_to_dict(self):
        """Test exporting policies to dictionary"""
        rule = PolicyRule(
            name="test_rule",
            condition=PolicyCondition(field="tier", operator="==", value="A"),
            action=PolicyAction(use_alternative=True, alternative_tier="B"),
            priority=50
        )
        
        self.engine.add_rule(rule)
        
        result = self.engine.to_dict()
        
        self.assertIn("rules", result)
        self.assertEqual(len(result["rules"]), 1)
        self.assertEqual(result["rules"][0]["name"], "test_rule")


class TestDefaultPolicies(unittest.TestCase):
    """Test default policy creation"""
    
    def test_create_default_policies(self):
        """Test creating default policies"""
        policies = create_default_policies()
        
        self.assertGreater(len(policies), 0)
        
        # Check specific default policies exist
        names = [p.name for p in policies]
        self.assertIn("low_confidence_human_approval", names)
        self.assertIn("cost_limit_fallback", names)
        self.assertIn("max_retries_issue_analysis", names)
    
    def test_default_policies_functional(self):
        """Test default policies are functional"""
        policies = create_default_policies()
        engine = PolicyEngine()
        
        for policy in policies:
            engine.add_rule(policy)
        
        # Test low confidence policy
        action = engine.evaluate({"confidence": 0.3})
        self.assertIsNotNone(action)
        self.assertTrue(action.requires_human_approval)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error handling"""
    
    def test_load_nonexistent_file(self):
        """Test loading from nonexistent file"""
        engine = PolicyEngine("/nonexistent/path/to/file.json")
        
        # Should not crash, just have no rules
        self.assertEqual(engine.get_rule_count(), 0)
    
    def test_evaluate_empty_engine(self):
        """Test evaluation with no rules"""
        engine = PolicyEngine()
        
        action = engine.evaluate({"confidence": 0.3})
        
        self.assertIsNone(action)
    
    def test_priority_sorting(self):
        """Test rules are sorted by priority"""
        engine = PolicyEngine()
        
        rule1 = PolicyRule(
            name="low", condition=PolicyCondition("tier", "==", "A"),
            action=PolicyAction(), priority=10
        )
        rule2 = PolicyRule(
            name="high", condition=PolicyCondition("tier", "==", "A"),
            action=PolicyAction(), priority=100
        )
        rule3 = PolicyRule(
            name="medium", condition=PolicyCondition("tier", "==", "A"),
            action=PolicyAction(), priority=50
        )
        
        engine.add_rule(rule1)
        engine.add_rule(rule2)
        engine.add_rule(rule3)
        
        # Should be sorted by priority (high to low)
        self.assertEqual(engine.rules[0].name, "high")
        self.assertEqual(engine.rules[1].name, "medium")
        self.assertEqual(engine.rules[2].name, "low")


if __name__ == "__main__":
    unittest.main()
