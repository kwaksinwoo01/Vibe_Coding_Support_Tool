"""
policy_engine.py

**Policy Engine Module**

Responsibility: Load and evaluate configurable decision policies for routing decisions.

Architecture:
- PolicyRule: Individual policy rule definition with conditions and actions
- PolicyEngine: Rule loader and evaluator with priority-based evaluation

**Service Layer Module**: MUST follow SRP
**Responsibility**: Policy rule loading and evaluation
**Internal Layers**: 2 (Rule, Engine)
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Callable
from enum import Enum
import json
from pathlib import Path


class OperatorType(Enum):
    """Supported comparison operators for policy conditions"""
    EQUAL = "=="
    NOT_EQUAL = "!="
    LESS_THAN = "<"
    LESS_EQUAL = "<="
    GREATER_THAN = ">"
    GREATER_EQUAL = ">="
    IN = "in"
    NOT_IN = "not_in"
    CONTAINS = "contains"
    MATCHES = "matches"  # Regex match


@dataclass
class PolicyCondition:
    """
    Condition for policy rule evaluation.
    
    Attributes:
        field: Field name to evaluate (e.g., "confidence", "retry_count")
        operator: Comparison operator
        value: Value to compare against
    """
    field: str
    operator: str
    value: Any
    
    def evaluate(self, context: Dict[str, Any]) -> bool:
        """
        Evaluate condition against context.
        
        Args:
            context: Dictionary containing field values
        
        Returns:
            True if condition is met
        """
        # Get field value from context (support nested fields with dot notation)
        field_value = self._get_field_value(context, self.field)
        
        # Apply operator
        return self._apply_operator(field_value, self.operator, self.value)
    
    def _get_field_value(self, context: Dict[str, Any], field_path: str) -> Any:
        """Get field value from context, supporting nested paths"""
        parts = field_path.split(".")
        value = context
        
        for part in parts:
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return None
        
        return value
    
    def _apply_operator(self, field_value: Any, operator: str, target_value: Any) -> bool:
        """Apply comparison operator"""
        if field_value is None:
            return False
        
        try:
            if operator == "==" or operator == OperatorType.EQUAL.value:
                return field_value == target_value
            elif operator == "!=" or operator == OperatorType.NOT_EQUAL.value:
                return field_value != target_value
            elif operator == "<" or operator == OperatorType.LESS_THAN.value:
                return field_value < target_value
            elif operator == "<=" or operator == OperatorType.LESS_EQUAL.value:
                return field_value <= target_value
            elif operator == ">" or operator == OperatorType.GREATER_THAN.value:
                return field_value > target_value
            elif operator == ">=" or operator == OperatorType.GREATER_EQUAL.value:
                return field_value >= target_value
            elif operator == "in" or operator == OperatorType.IN.value:
                return field_value in target_value
            elif operator == "not_in" or operator == OperatorType.NOT_IN.value:
                return field_value not in target_value
            elif operator == "contains" or operator == OperatorType.CONTAINS.value:
                return target_value in field_value
            elif operator == "matches" or operator == OperatorType.MATCHES.value:
                import re
                return bool(re.search(target_value, str(field_value)))
            else:
                return False
        except (TypeError, ValueError):
            return False


@dataclass
class PolicyAction:
    """
    Action to take when policy condition is met.
    
    Attributes:
        requires_human_approval: Whether to require human approval
        use_alternative: Whether to use alternative routing
        alternative_tier: Alternative tier to route to
        override_confidence: Confidence value to override
        metadata: Additional action metadata
    """
    requires_human_approval: bool = False
    use_alternative: bool = False
    alternative_tier: Optional[str] = None
    override_confidence: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PolicyAction":
        """Create PolicyAction from dictionary"""
        return cls(
            requires_human_approval=data.get("requires_human_approval", False),
            use_alternative=data.get("use_alternative", False),
            alternative_tier=data.get("alternative_tier"),
            override_confidence=data.get("override_confidence"),
            metadata=data.get("metadata", {})
        )


@dataclass
class PolicyRule:
    """
    Complete policy rule with condition and action.
    
    Attributes:
        name: Rule identifier
        condition: Condition to evaluate
        action: Action to take when condition is met
        priority: Rule priority (higher = evaluated first)
        enabled: Whether rule is active
        description: Human-readable description
    """
    name: str
    condition: PolicyCondition
    action: PolicyAction
    priority: int = 50
    enabled: bool = True
    description: str = ""
    
    def evaluate(self, context: Dict[str, Any]) -> Optional[PolicyAction]:
        """
        Evaluate rule against context.
        
        Args:
            context: Evaluation context
        
        Returns:
            PolicyAction if condition is met and rule is enabled, None otherwise
        """
        if not self.enabled:
            return None
        
        if self.condition.evaluate(context):
            return self.action
        
        return None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PolicyRule":
        """Create PolicyRule from dictionary"""
        condition_data = data.get("condition", {})
        condition = PolicyCondition(
            field=condition_data.get("field", ""),
            operator=condition_data.get("operator", "=="),
            value=condition_data.get("value")
        )
        
        action_data = data.get("action", {})
        action = PolicyAction.from_dict(action_data)
        
        return cls(
            name=data.get("name", "unnamed_rule"),
            condition=condition,
            action=action,
            priority=data.get("priority", 50),
            enabled=data.get("enabled", True),
            description=data.get("description", "")
        )


class PolicyEngine:
    """
    Policy engine for loading and evaluating decision policies.
    
    Supports:
    - Loading policies from JSON configuration files
    - Priority-based rule evaluation
    - Multiple condition operators
    - Dynamic enable/disable of rules
    - Rule validation
    
    Internal Architecture (2 layers):
    1. Rule Management (load, validate, enable/disable)
    2. Evaluation Logic (evaluate rules against context)
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize policy engine.
        
        Args:
            config_path: Path to policy configuration JSON file
        """
        self.rules: List[PolicyRule] = []
        self.config_path = config_path
        
        if config_path:
            self.load_policies(config_path)
    
    # ========================================================================
    # Layer 1: Rule Management
    # ========================================================================
    
    def load_policies(self, config_path: str) -> int:
        """
        Load policies from split JSON configuration directory.
        
        Args:
            config_path: Path to directory containing individual policy JSON files
        
        Returns:
            Number of policies loaded
        """
        try:
            path = Path(config_path)
            if not path.exists():
                print(f"Warning: Policy config directory not found: {config_path}")
                return 0
            
            if not path.is_dir():
                print(f"Warning: Policy config path is not a directory: {config_path}")
                return 0
            
            # Load all JSON files except metadata.json
            policy_files = [f for f in path.glob("*.json") if f.name != "metadata.json"]
            
            for policy_file in policy_files:
                try:
                    with open(policy_file, 'r', encoding='utf-8') as f:
                        rule_data = json.load(f)
                    
                    rule = PolicyRule.from_dict(rule_data)
                    self.add_rule(rule)
                except Exception as e:
                    print(f"Error loading policy from {policy_file.name}: {e}")
                    continue
            
            # Sort by priority (highest first)
            self.rules.sort(key=lambda r: r.priority, reverse=True)
            
            print(f"Loaded {len(self.rules)} policy rules from {config_path}")
            return len(self.rules)
            
        except Exception as e:
            print(f"Error loading policies from {config_path}: {e}")
            return 0
    
    def add_rule(self, rule: PolicyRule):
        """Add a policy rule to the engine"""
        self.rules.append(rule)
        # Re-sort by priority
        self.rules.sort(key=lambda r: r.priority, reverse=True)
    
    def remove_rule(self, rule_name: str) -> bool:
        """
        Remove a policy rule by name.
        
        Args:
            rule_name: Name of rule to remove
        
        Returns:
            True if rule was removed
        """
        initial_count = len(self.rules)
        self.rules = [r for r in self.rules if r.name != rule_name]
        return len(self.rules) < initial_count
    
    def enable_rule(self, rule_name: str) -> bool:
        """Enable a rule by name"""
        for rule in self.rules:
            if rule.name == rule_name:
                rule.enabled = True
                return True
        return False
    
    def disable_rule(self, rule_name: str) -> bool:
        """Disable a rule by name"""
        for rule in self.rules:
            if rule.name == rule_name:
                rule.enabled = False
                return True
        return False
    
    def get_rule(self, rule_name: str) -> Optional[PolicyRule]:
        """Get a rule by name"""
        for rule in self.rules:
            if rule.name == rule_name:
                return rule
        return None
    
    def validate_rules(self) -> List[str]:
        """
        Validate all rules and return list of issues.
        
        Returns:
            List of validation error messages (empty if all valid)
        """
        issues = []
        
        for rule in self.rules:
            # Check required fields
            if not rule.name:
                issues.append("Rule has no name")
            if not rule.condition.field:
                issues.append(f"Rule '{rule.name}' has no condition field")
            if not rule.condition.operator:
                issues.append(f"Rule '{rule.name}' has no condition operator")
            
            # Check valid operator
            valid_operators = [op.value for op in OperatorType] + ["==", "!=", "<", "<=", ">", ">="]
            if rule.condition.operator not in valid_operators:
                issues.append(f"Rule '{rule.name}' has invalid operator: {rule.condition.operator}")
            
            # Check priority range
            if rule.priority < 0 or rule.priority > 1000:
                issues.append(f"Rule '{rule.name}' has invalid priority: {rule.priority}")
        
        return issues
    
    # ========================================================================
    # Layer 2: Evaluation Logic
    # ========================================================================
    
    def evaluate(self, context: Dict[str, Any]) -> Optional[PolicyAction]:
        """
        Evaluate all rules against context and return first matching action.
        
        Rules are evaluated in priority order (highest first).
        
        Args:
            context: Context dictionary for evaluation
        
        Returns:
            PolicyAction if any rule matches, None otherwise
        """
        for rule in self.rules:
            if not rule.enabled:
                continue
            
            action = rule.evaluate(context)
            if action is not None:
                return action
        
        return None
    
    def evaluate_all(self, context: Dict[str, Any]) -> List[tuple[str, PolicyAction]]:
        """
        Evaluate all rules and return all matching actions.
        
        Args:
            context: Context dictionary for evaluation
        
        Returns:
            List of (rule_name, action) tuples for all matching rules
        """
        matches = []
        
        for rule in self.rules:
            if not rule.enabled:
                continue
            
            action = rule.evaluate(context)
            if action is not None:
                matches.append((rule.name, action))
        
        return matches
    
    def get_matching_rules(self, context: Dict[str, Any]) -> List[str]:
        """
        Get names of all rules that match the context.
        
        Args:
            context: Context dictionary for evaluation
        
        Returns:
            List of rule names that match
        """
        return [rule.name for rule in self.rules 
                if rule.enabled and rule.evaluate(context) is not None]
    
    # ========================================================================
    # Utility Methods
    # ========================================================================
    
    def get_rule_count(self) -> int:
        """Get total number of rules"""
        return len(self.rules)
    
    def get_enabled_count(self) -> int:
        """Get number of enabled rules"""
        return sum(1 for r in self.rules if r.enabled)
    
    def clear_rules(self):
        """Clear all rules"""
        self.rules.clear()
    
    def to_dict(self) -> Dict[str, Any]:
        """Export current rules to dictionary format"""
        return {
            "rules": [
                {
                    "name": rule.name,
                    "condition": {
                        "field": rule.condition.field,
                        "operator": rule.condition.operator,
                        "value": rule.condition.value
                    },
                    "action": {
                        "requires_human_approval": rule.action.requires_human_approval,
                        "use_alternative": rule.action.use_alternative,
                        "alternative_tier": rule.action.alternative_tier,
                        "override_confidence": rule.action.override_confidence,
                        "metadata": rule.action.metadata
                    },
                    "priority": rule.priority,
                    "enabled": rule.enabled,
                    "description": rule.description
                }
                for rule in self.rules
            ]
        }
    
    def save_policies(self, output_path: str):
        """
        Save current policies to JSON file.
        
        Args:
            output_path: Path to save policies
        """
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2)


# ============================================================================
# Utility Functions
# ============================================================================

def create_default_policies() -> List[PolicyRule]:
    """
    Create default policy rules for common scenarios.
    
    Returns:
        List of default PolicyRule instances
    """
    return [
        PolicyRule(
            name="low_confidence_human_approval",
            condition=PolicyCondition(
                field="confidence",
                operator="<",
                value=0.4
            ),
            action=PolicyAction(requires_human_approval=True),
            priority=100,
            enabled=True,
            description="Require human approval for low confidence decisions"
        ),
        PolicyRule(
            name="cost_limit_fallback",
            condition=PolicyCondition(
                field="estimated_cost",
                operator=">",
                value=100.0
            ),
            action=PolicyAction(
                use_alternative=True,
                alternative_tier="E"
            ),
            priority=90,
            enabled=True,
            description="Use alternative tier when cost exceeds limit"
        ),
        PolicyRule(
            name="max_retries_issue_analysis",
            condition=PolicyCondition(
                field="retry_count",
                operator=">=",
                value=3
            ),
            action=PolicyAction(
                use_alternative=True,
                alternative_tier="D"
            ),
            priority=95,
            enabled=True,
            description="Route to issue analysis after max retries"
        ),
        PolicyRule(
            name="failure_to_issue_analysis",
            condition=PolicyCondition(
                field="status",
                operator="==",
                value="FAILED"
            ),
            action=PolicyAction(
                use_alternative=True,
                alternative_tier="D"
            ),
            priority=85,
            enabled=True,
            description="Route failures to issue analysis"
        )
    ]
