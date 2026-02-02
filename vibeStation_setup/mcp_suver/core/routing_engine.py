"""
Standalone Routing Engine Module

Extracted from main_agent.py to follow SRP and separate routing logic.

This module contains:
- IRoutingStrategy: Interface for routing strategies
- KeywordRoutingStrategy: Keyword-based routing
- MetricsBasedRoutingStrategy: Metrics-driven routing
- RoutingEngine: Core routing decision engine
- RoutingValidator: Routing validation facade

Call structure:
    main_agent.py ← routing_engine.py ← reporting_models.py

No adapter functions - direct integration only.
"""

from typing import Optional, Dict, Any, List, Tuple
from abc import ABC, abstractmethod
from pathlib import Path

# Import data models
from ..models.core.reporting_models import (
    IssueClassification,
    ResolutionStrategy,
    RoutingInfo,
)
from ...config import get_tier_keywords


class IRoutingStrategy(ABC):
    """
    Interface for routing strategies.
    
    Defines the contract for different routing decision approaches:
    - KeywordRoutingStrategy: Traditional keyword/rule-based routing
    - MetricsBasedRoutingStrategy: Metrics-driven dynamic routing
    """
    
    @abstractmethod
    def decide_routing(
        self,
        tier: str,
        result: Dict[str, Any],
        execution_history: List[Dict[str, Any]],
        metrics_collector: Optional[Any]
    ) -> Optional[str]:
        """
        Decide next tier based on current tier result.
        
        Args:
            tier: Current tier (A-F)
            result: Tier execution result
            execution_history: Historical execution data
            metrics_collector: Metrics collector for pattern analysis
            
        Returns:
            Next tier to route to (or None to end)
        """
        pass
    
    @abstractmethod
    def calculate_confidence_threshold(
        self,
        metrics_collector: Optional[Any]
    ) -> float:
        """
        Calculate dynamic confidence threshold based on strategy.
        
        Args:
            metrics_collector: Metrics collector for analysis
            
        Returns:
            Recommended confidence threshold (0.0-1.0)
        """
        pass


class KeywordRoutingStrategy(IRoutingStrategy):
    """
    Traditional keyword and rule-based routing strategy.
    
    Uses predefined rules from TIER_D_ROUTING_RULES and VALID_NEXT_ROUTINGS.
    This is the existing routing logic, now encapsulated as a strategy.
    """
    
    def __init__(self, routing_engine: 'RoutingEngine'):
        """Initialize with reference to RoutingEngine for accessing rules."""
        self.routing_engine = routing_engine
    
    def decide_routing(
        self,
        tier: str,
        result: Dict[str, Any],
        execution_history: List[Dict[str, Any]],
        metrics_collector: Optional[Any]
    ) -> Optional[str]:
        """Apply traditional keyword-based routing rules."""
        status = result.get("status", "UNKNOWN")
        
        if tier == "D":
            # Use existing routing engine for Tier D
            return result.get("next_node", "F")
        
        elif tier == "C":
            # Tier C routing rules
            return self.routing_engine._apply_routing_rules_for_c(result)
        
        elif tier == "E":
            # Tier E routing rules
            return self.routing_engine._apply_routing_rules_for_e(result)
        
        else:
            # Default: use next_node from result
            return result.get("next_node")
    
    def calculate_confidence_threshold(
        self,
        metrics_collector: Optional[Any]
    ) -> float:
        """Return static threshold for keyword-based routing."""
        return 0.7  # Traditional static threshold


class MetricsBasedRoutingStrategy(IRoutingStrategy):
    """
    Metrics-driven routing strategy.
    
    Analyzes historical execution patterns and success rates to make
    intelligent routing decisions. Adjusts confidence thresholds dynamically
    based on recent performance.
    """
    
    def __init__(self, routing_engine: 'RoutingEngine'):
        """Initialize with reference to RoutingEngine."""
        self.routing_engine = routing_engine
        self.fallback_strategy = None  # Will be set to KeywordRoutingStrategy
    
    def decide_routing(
        self,
        tier: str,
        result: Dict[str, Any],
        execution_history: List[Dict[str, Any]],
        metrics_collector: Optional[Any]
    ) -> Optional[str]:
        """
        Apply metrics-based routing with intelligent fallback patterns.
        
        Analyzes execution history to identify:
        1. Frequent failure patterns (e.g., A→D repeatedly)
        2. Successful routing paths (e.g., D→C→B success rate)
        3. Tier-specific performance trends
        """
        if not metrics_collector:
            # No metrics available, fallback to keyword strategy
            if self.fallback_strategy:
                return self.fallback_strategy.decide_routing(
                    tier, result, execution_history, metrics_collector
                )
            return result.get("next_node")
        
        # Analyze recent patterns
        patterns = metrics_collector.analyze_patterns(tier=tier, limit=50)
        
        status = result.get("status", "UNKNOWN")
        
        # Rule 1: If tier has high failure rate (>50%), route to D for analysis
        if tier in patterns["tier_failure_rates"]:
            failure_rate = patterns["tier_failure_rates"][tier]
            if failure_rate > 0.5 and status == "SUCCESS":
                print(f"[METRICS_ROUTING] Tier {tier} has high failure rate ({failure_rate:.2f}), "
                      f"recommending preemptive analysis via D")
                # Don't override SUCCESS status, but log the pattern
        
        # Rule 2: Learn from common failure patterns
        if status != "SUCCESS":
            # Check if this failure pattern has occurred before
            common_failures = patterns["common_failure_patterns"]
            if len(common_failures) > 0:
                # If we've seen this failure pattern recently, route to D
                similar_failures = [f for f in common_failures if f["tier"] == tier]
                if len(similar_failures) >= 2:
                    print(f"[METRICS_ROUTING] Detected repeated failure pattern for Tier {tier}, "
                          f"routing to D for analysis")
                    return "D"
        
        # Rule 3: Optimize successful paths
        # If tier has high success rate (>80%), trust its next_node recommendation
        if tier in patterns["tier_success_rates"]:
            success_rate = patterns["tier_success_rates"][tier]
            if success_rate > 0.8 and status == "SUCCESS":
                next_node = result.get("next_node")
                print(f"[METRICS_ROUTING] Tier {tier} has high success rate ({success_rate:.2f}), "
                      f"trusting its recommendation: {next_node}")
                return next_node
        
        # Rule 4: Predictive routing based on execution history
        # Look at last 5 executions to predict next tier
        if len(execution_history) >= 5:
            recent_executions = execution_history[-5:]
            # Count most common next_tier transitions from current tier
            next_tier_counts = {}
            for exec_entry in recent_executions:
                if exec_entry.get("tier") == tier and exec_entry.get("status") == "SUCCESS":
                    next_tier = exec_entry.get("next_node")
                    if next_tier:
                        next_tier_counts[next_tier] = next_tier_counts.get(next_tier, 0) + 1
            
            if next_tier_counts:
                # Use most common successful transition
                predicted_next = max(next_tier_counts, key=next_tier_counts.get)
                current_next = result.get("next_node")
                if predicted_next != current_next and status == "SUCCESS":
                    print(f"[METRICS_ROUTING] Historical pattern suggests {tier}→{predicted_next} "
                          f"instead of {tier}→{current_next} (based on {next_tier_counts[predicted_next]} occurrences)")
                    # Don't override, but log for learning
        
        # Fallback to keyword strategy if no metrics-based decision made
        if self.fallback_strategy:
            return self.fallback_strategy.decide_routing(
                tier, result, execution_history, metrics_collector
            )
        
        return result.get("next_node")
    
    def calculate_confidence_threshold(
        self,
        metrics_collector: Optional[Any]
    ) -> float:
        """
        Calculate dynamic confidence threshold based on recent success rates.
        
        Uses metrics.analyze_patterns() to adjust threshold:
        - High success rate (>80%) → lower threshold (0.6) for faster decisions
        - Medium success rate (50-80%) → standard threshold (0.7)
        - Low success rate (<50%) → higher threshold (0.8) for more caution
        """
        if not metrics_collector:
            return 0.7  # Default threshold
        
        patterns = metrics_collector.analyze_patterns(limit=100)
        recommended = patterns.get("recommended_confidence_threshold", 0.7)
        
        print(f"[METRICS_ROUTING] Dynamic confidence threshold: {recommended:.2f} "
              f"(based on {patterns.get('total_executions_analyzed', 0)} executions, "
              f"success rate: {patterns.get('overall_success_rate', 0):.2%})")
        
        return recommended


class RoutingValidator:
    """
    Facade for routing validation (payload and policy checks).
    Default implementation is permissive; extend with strict checks.
    """

    def __init__(self, metrics: Optional[Any] = None, reporter: Optional[Any] = None):
        self.metrics = metrics
        self.reporter = reporter

    def validate_transition(self, current_tier: str, target_tier: Optional[str], tier_result: Dict[str, Any]) -> bool:
        """
        Validate routing transition.
        
        Args:
            current_tier: Current tier
            target_tier: Target tier
            tier_result: Tier execution result
            
        Returns:
            True if transition is valid
        """
        # Default: use simple table check if engine exposes validate rules;
        # by default allow transitions (implement strict rules in real refactor)
        return True

    def _report(self, frm: str, to: Optional[str], reason: str, context: Dict[str, Any]):
        """Report validation failure."""
        try:
            print(f"[ROUTING_VALIDATOR] Reject {frm} -> {to}: {reason}")
            if self.metrics:
                self.metrics.increment_counter(
                    "routing_validation_failures",
                    labels={"from": frm, "to": str(to), "reason": reason}
                )
            if self.reporter and getattr(self.reporter, "is_enabled", lambda: False)():
                self.reporter.report_competing_paths_issue(
                    active_node="ROUTING_VALIDATOR",
                    state_flow=f"{frm} -> {to}",
                    competing_paths=[frm, to],
                    selected_path=to,
                    selection_reason=reason,
                    context={"context": context},
                )
        except Exception:
            pass


class RoutingEngine:
    """
    Standalone RoutingEngine extracted from MainAgent.

    Responsibilities:
    - Classify user input to determine initial tier
    - Decide routing between tiers based on execution results
    - Validate routing transitions
    - Manage routing strategies (keyword-based vs metrics-based)
    - Apply Tier D routing rules for issue analysis
    """

    # Rule 1: Tier D initial routing rules
    TIER_D_ROUTING_RULES = {
        "bug": {
            "implementation_error": "C",  # Tier C: code modification
            "environment_error": "B",  # Tier B: re-execute in environment
            "data_error": "E",  # Tier E: data management
        },
        "design_flaw": {
            "architecture": "A",  # Tier A: new plan
            "algorithm": "C",  # Tier C: modify existing plan
            "interface": "C",  # Tier C: modify existing plan
        },
        "implementation": "C",  # Tier C: plan modification
        "documentation": "E",  # Tier E: document management
        "unknown": "F",  # Tier F: re-classification
    }

    # Rule 2: Valid next tier routing for each tier (SUCCESS case)
    VALID_NEXT_ROUTINGS = {
        "A": ["B", "C", "E", None],  # Plan created → execute/modify/document/end
        "B": ["E", "C", None],  # Executed → document/modify/end
        "C": ["B", "E", None],  # Modified → execute/document/end
        "E": [None],  # Documented → end only
        "F": ["A", "B", "C", "D", "E", None],  # Re-classified → anywhere
    }

    # Rule 2: Failure routing for each tier
    FAILURE_NEXT_ROUTINGS = {
        "A": ["D", None],  # Failed → analyze or end
        "B": ["D", None],
        "C": ["D", None],
        "E": ["D", None],
        "F": [None],  # F failed → end
    }

    def __init__(
        self,
        workspace_root: str = ".",
        metrics_collector: Optional[Any] = None,
        github_reporter: Optional[Any] = None,
        enable_metrics: bool = True,
        execution_history: Optional[List[Dict[str, Any]]] = None,
    ):
        """
        Initialize routing engine.
        
        Args:
            workspace_root: Root directory of workspace
            metrics_collector: Metrics collector instance
            github_reporter: GitHub reporter for auto-reporting
            enable_metrics: Enable metrics-based routing
            execution_history: Historical execution data
        """
        self.workspace_root = workspace_root
        self.metrics = metrics_collector
        self.github_reporter = github_reporter
        self.execution_history = execution_history if execution_history is not None else []
        
        # Initialize routing strategies
        self.keyword_strategy = KeywordRoutingStrategy(self)
        self.metrics_strategy = MetricsBasedRoutingStrategy(self)
        
        # Set up bidirectional fallback
        self.metrics_strategy.fallback_strategy = self.keyword_strategy
        
        # Default to metrics-based strategy if metrics enabled
        self.active_strategy: IRoutingStrategy = (
            self.metrics_strategy if enable_metrics
            else self.keyword_strategy
        )
        
        # Validator facade (permissive by default)
        self.validator = RoutingValidator(metrics=metrics_collector, reporter=github_reporter)
        
        print(f"[ROUTING_ENGINE] Initialized with strategy: "
              f"{type(self.active_strategy).__name__}")
    
    def set_strategy(self, use_metrics_based: bool):
        """
        Switch between keyword-based and metrics-based routing strategies.
        
        Args:
            use_metrics_based: If True, use MetricsBasedRoutingStrategy.
                              If False, use KeywordRoutingStrategy.
        """
        if use_metrics_based and self.metrics:
            self.active_strategy = self.metrics_strategy
            print("[ROUTING_ENGINE] Switched to MetricsBasedRoutingStrategy")
        else:
            self.active_strategy = self.keyword_strategy
            print("[ROUTING_ENGINE] Switched to KeywordRoutingStrategy")
    
    def get_dynamic_confidence_threshold(self) -> float:
        """
        Get dynamic confidence threshold from active strategy.
        
        Returns:
            Confidence threshold (0.0-1.0) calculated by active strategy
        """
        return self.active_strategy.calculate_confidence_threshold(self.metrics)

    def decide_initial_routing_for_d(
        self, classification: IssueClassification, strategy: ResolutionStrategy
    ) -> RoutingInfo:
        """
        Tier D initial routing decision (Rule 1).

        Renamed from decide_initial_routing to avoid ambiguity.

        Args:
            classification: Issue classification result
            strategy: Resolution strategy

        Returns:
            RoutingInfo object
        """
        issue_type = classification.issue_type
        category = classification.category

        # Step 1: Apply routing rule
        target_tier = self._apply_routing_rule(issue_type, category)

        # Step 2: Calculate routing confidence
        confidence = self._calculate_routing_confidence(
            classification.confidence_score, strategy
        )

        # Step 3: Generate routing reason
        routing_reason = self._generate_routing_reason(
            issue_type, category, strategy.approach
        )

        # Step 4: Build metadata
        metadata = {
            "analysis_type": issue_type,
            "approach": strategy.approach,
            "priority": strategy.priority,
            "estimated_effort": strategy.estimated_effort,
            "wpd_grade": strategy.wpd_grade,
        }

        return RoutingInfo(
            target_tier=target_tier,
            routing_reason=routing_reason,
            routing_confidence=confidence,
            requires_clarification=confidence < 0.7,
            clarification_questions=self._generate_clarification_questions(
                issue_type, confidence
            ),
            metadata=metadata,
        )

    def validate_next_routing(
        self, current_tier: str, target_tier: str, tier_result: Dict[str, Any]
    ) -> bool:
        """
        Validate next tier routing (Rule 2).

        Args:
            current_tier: Current tier
            target_tier: Target tier
            tier_result: Current tier result {"status": "SUCCESS" or "FAILURE"}

        Returns:
            True if routing is valid
        """
        status = tier_result.get("status", "UNKNOWN")

        if status == "SUCCESS":
            valid_tiers = self.VALID_NEXT_ROUTINGS.get(current_tier, [])
        else:
            valid_tiers = self.FAILURE_NEXT_ROUTINGS.get(current_tier, [])

        return target_tier in valid_tiers

    def _apply_routing_rule(self, issue_type: str, category: str) -> str:
        """Apply routing rule based on issue type and category"""
        if issue_type in self.TIER_D_ROUTING_RULES:
            rules = self.TIER_D_ROUTING_RULES[issue_type]

            # Category-based routing
            if isinstance(rules, dict) and category in rules:
                return rules[category]

            # Default routing for this issue type
            if isinstance(rules, str):
                return rules

        # Default: re-classification
        return "F"

    def _calculate_routing_confidence(
        self, classification_confidence: float, strategy: ResolutionStrategy
    ) -> float:
        """Calculate routing confidence"""
        # Classification confidence * strategy confidence
        strategy_confidence = {
            "low": 0.95,
            "medium": 0.80,
            "high": 0.60,  # Higher effort → lower confidence
        }.get(strategy.estimated_effort, 0.80)

        return min(1.0, classification_confidence * strategy_confidence)

    def _generate_routing_reason(
        self, issue_type: str, category: str, approach: str
    ) -> str:
        """Generate routing reason"""
        reason_templates = {
            "bug": f"Bug detected ({category or 'implementation'}). Approach: {approach}",
            "design_flaw": f"Design issue ({category or 'general'}). Requires architectural review.",
            "implementation": "Implementation improvement needed.",
            "documentation": "Documentation update required.",
            "unknown": "Issue requires further analysis and classification.",
        }

        return reason_templates.get(
            issue_type, f"Route to appropriate tier for {approach}"
        )

    def _generate_clarification_questions(
        self, issue_type: str, confidence: float
    ) -> List[str]:
        """Generate clarification questions"""
        if confidence > 0.7:
            return []

        questions = []

        if issue_type == "unknown":
            questions.append("Can you provide more specific error information?")
            questions.append("What is the context in which this issue occurred?")

        if confidence < 0.5:
            questions.append("Could you describe the expected vs actual behavior?")
            questions.append("When did this issue start occurring?")

        return questions

    def decide_routing(self, tier: str, result: Dict[str, Any]) -> Optional[str]:
        """
        Centralized routing decision using active strategy (Strategy Pattern).

        This is the single entry point for all routing decisions.
        Delegates to the active strategy (keyword-based or metrics-based).

        Args:
            tier: Current tier (A-F)
            result: Tier execution result

        Returns:
            Next tier to route to
        """
        # Use active strategy for routing decision
        next_tier = self.active_strategy.decide_routing(
            tier=tier,
            result=result,
            execution_history=self.execution_history,
            metrics_collector=self.metrics
        )
        
        return next_tier

    def _apply_routing_rules_for_c(self, result: Dict[str, Any]) -> Optional[str]:
        """
        Apply routing rules for Tier C (Plan Modification).
        
        Success path:
        - Modified successfully → B (execute) or E (document) or None (end)
        
        Failure path:
        - Modification failed → D (analyze issue)
        """
        status = result.get("status", "UNKNOWN")
        next_node = result.get("next_node")
        
        if status == "SUCCESS":
            # Valid success routing: B, E, or None
            if next_node in ["B", "E", None]:
                return next_node
            else:
                # Invalid routing, default to E (document changes)
                print(f"[ROUTING_C] Invalid next_node '{next_node}', defaulting to E")
                return "E"
        else:
            # Failure: route to D for analysis
            return "D"

    def _apply_routing_rules_for_e(self, result: Dict[str, Any]) -> Optional[str]:
        """
        Apply routing rules for Tier E (Document Management).
        
        Success path:
        - Documented successfully → None (end workflow)
        
        Failure path:
        - Documentation failed → D (analyze issue)
        """
        status = result.get("status", "UNKNOWN")
        
        if status == "SUCCESS":
            # E is terminal tier in success path
            return None
        else:
            # Failure: route to D for analysis
            return "D"

    def discover_steps(self, user_input: str) -> Optional[Dict[str, Any]]:
        """
        Discover step references in user input using workspace structure.
        
        Checks for:
        1. Explicit step references (e.g., "step 5", "P5", "Part 5")
        2. Step document existence in workspace
        3. Step metadata from existing WPD documents
        
        Args:
            user_input: User's natural language input
            
        Returns:
            Dict with step info if discovered, None otherwise:
            {
                "step_number": "5",
                "step_path": "docs_2/P5/P5-Task.md",
                "confidence": 0.9,
                "metadata": {...}
            }
        """
        import re
        
        # Pattern 1: "step N" or "Part N" or "PN"
        step_patterns = [
            r'step\s+(\d+)',
            r'part\s+(\d+)',
            r'p(\d+)',
            r'단계\s+(\d+)',
        ]
        
        user_lower = user_input.lower()
        step_number = None
        
        for pattern in step_patterns:
            match = re.search(pattern, user_lower)
            if match:
                step_number = match.group(1)
                break
        
        if not step_number:
            return None
        
        # Check if step document exists
        workspace_path = Path(self.workspace_root)
        potential_paths = [
            workspace_path / f"docs_2/P{step_number}/P{step_number}-Task.md",
            workspace_path / f"docs_2/P{step_number}/P{step_number}.md",
            workspace_path / f"docs_2/P{step_number}",
        ]
        
        for path in potential_paths:
            if path.exists():
                print(f"[STEP_DISCOVERY] Found step {step_number} at {path}")
                return {
                    "step_number": step_number,
                    "step_path": str(path),
                    "confidence": 0.9,
                    "metadata": {
                        "discovery_method": "pattern_match",
                        "pattern": pattern,
                    }
                }
        
        # Step mentioned but not found
        print(f"[STEP_DISCOVERY] Step {step_number} mentioned but not found in workspace")
        return {
            "step_number": step_number,
            "step_path": None,
            "confidence": 0.5,
            "metadata": {
                "discovery_method": "pattern_match",
                "pattern": pattern,
                "note": "Step not found in workspace"
            }
        }

    def classify_input(self, user_input: str) -> Tuple[str, float]:
        """
        Classify user input to determine initial tier with confidence score.

        Enhanced with:
        - Automated step discovery from workspace structure
        - Keyword matching as baseline
        - Confidence-based routing support

        Args:
            user_input: User's natural language input

        Returns:
            Tuple of (tier, confidence):
            - tier: Initial tier (A-F)
            - confidence: Classification confidence (0.0-1.0)
        """
        # Step 1: Check if user input references a specific step
        step_info = self.discover_steps(user_input)
        
        if step_info and step_info["step_path"]:
            user_lower = user_input.lower()
            
            # If step exists, classify based on action keywords
            # "modify", "edit", "change" → Tier C
            if any(kw in user_lower for kw in ["modify", "edit", "change", "update", "수정"]):
                print(f"[CLASSIFY] Step {step_info['step_number']} discovered → routing to Tier C (modification)")
                return ("C", step_info["confidence"])
            
            # If input contains execution keywords → Tier B
            elif any(kw in user_lower for kw in ["perform", "execute", "run", "실행", "진행"]):
                print(f"[CLASSIFY] Step {step_info['step_number']} discovered → routing to Tier B (execution)")
                return ("B", step_info["confidence"])
            
            # If input contains "create" keywords → Tier A
            # Note: "plan" alone is ambiguous, so we check it last
            elif any(kw in user_lower for kw in ["create", "새로운", "작성"]) or \
                 (("plan" in user_lower or "wpd" in user_lower) and "modify" not in user_lower):
                print(f"[CLASSIFY] Step {step_info['step_number']} discovered → routing to Tier A (planning)")
                return ("A", step_info["confidence"])
            
            # Default: assume execution if step is explicitly mentioned
            else:
                print(f"[CLASSIFY] Step {step_info['step_number']} discovered → defaulting to Tier B (execution)")
                return ("B", step_info["confidence"])
        
        # Step 2: Traditional keyword matching
        tier_keywords = get_tier_keywords()

        user_input_lower = user_input.lower()
        tier_scores = {}

        # Baseline: keyword matching with priority weights
        # Higher-priority keywords get additional weight to break ties
        priority_keywords = {
            "modify": 0.5,
            "change": 0.5,
            "edit": 0.5,
            "update": 0.3,
            "error": 0.5,
            "bug": 0.5,
            "failure": 0.5,
        }
        
        for tier, keywords in tier_keywords.items():
            score = 0.0
            matched_keywords = []
            
            for keyword in keywords:
                if keyword in user_input_lower:
                    # Base score for match
                    base_score = 1.0
                    # Add priority bonus if applicable
                    priority_bonus = priority_keywords.get(keyword, 0.0)
                    score += base_score + priority_bonus
                    matched_keywords.append(keyword)
            
            if score > 0:
                tier_scores[tier] = {
                    "score": score,
                    "matched_keywords": matched_keywords
                }

        # Select tier with highest score
        if not tier_scores:
            # No keywords matched → default to Tier F (unknown)
            print("[CLASSIFY] No keywords matched, routing to Tier F")
            return ("F", 0.3)

        # Get tier with max score
        selected_tier = max(tier_scores, key=lambda t: tier_scores[t]["score"])
        max_score = tier_scores[selected_tier]["score"]
        
        # Check for competing paths (multiple tiers with similar scores)
        threshold = max_score * 0.8  # Within 80% of max score
        competing_tiers = [
            tier for tier, data in tier_scores.items()
            if data["score"] >= threshold
        ]
        
        # Calculate confidence based on:
        # 1. Score magnitude (higher is better)
        # 2. Number of competing tiers (fewer is better)
        base_confidence = min(1.0, max_score / 5.0)  # Normalize by expected max score
        competition_penalty = 0.1 * (len(competing_tiers) - 1)  # Penalty for ambiguity
        confidence = max(0.3, base_confidence - competition_penalty)
        
        print(f"[CLASSIFY] Selected tier: {selected_tier} "
              f"(score: {max_score:.2f}, confidence: {confidence:.2f})")
        print(f"[CLASSIFY] Matched keywords: {tier_scores[selected_tier]['matched_keywords']}")
        
        if len(competing_tiers) > 1:
            print(f"[CLASSIFY] Competing tiers detected: {competing_tiers}")
            self._check_competing_paths(tier_scores, selected_tier, user_input)
        
        return (selected_tier, confidence)

    def _check_competing_paths(
        self,
        tier_scores: Dict[str, Dict[str, Any]],
        selected_tier: str,
        user_input: str,
    ):
        """
        Check for competing classification paths and report if needed.
        
        Args:
            tier_scores: Scores for each tier
            selected_tier: The tier that was selected
            user_input: Original user input
        """
        if not self.github_reporter or not getattr(self.github_reporter, "is_enabled", lambda: False)():
            return
        
        max_score = tier_scores[selected_tier]["score"]
        threshold = max_score * 0.8
        
        competing_tiers = [
            tier for tier, data in tier_scores.items()
            if data["score"] >= threshold and tier != selected_tier
        ]
        
        if len(competing_tiers) > 0:
            # Build context for reporting
            competing_info = []
            for tier in competing_tiers:
                competing_info.append({
                    "tier": tier,
                    "score": tier_scores[tier]["score"],
                    "matched_keywords": tier_scores[tier]["matched_keywords"]
                })
            
            context = {
                "user_input": user_input,
                "selected_tier": selected_tier,
                "selected_score": max_score,
                "selected_keywords": tier_scores[selected_tier]["matched_keywords"],
                "competing_tiers": competing_info,
                "threshold": threshold,
            }
            
            selection_reason = (
                f"Tier {selected_tier} scored {max_score:.2f}, "
                f"but {len(competing_tiers)} other tier(s) scored within 80% threshold. "
                f"Keywords matched: {tier_scores[selected_tier]['matched_keywords']}"
            )
            
            try:
                # Report the issue
                self.github_reporter.report_competing_paths_issue(
                    active_node="CLASSIFY",
                    state_flow="Initial Classification",
                    competing_paths=[selected_tier] + competing_tiers,
                    selected_path=selected_tier,
                    selection_reason=selection_reason,
                    context=context
                )
            except Exception as e:
                print(f"[ROUTING_ENGINE] Failed to report competing paths: {e}")


__all__ = [
    "RoutingEngine",
    "RoutingValidator",
    "IRoutingStrategy",
    "KeywordRoutingStrategy",
    "MetricsBasedRoutingStrategy",
]
