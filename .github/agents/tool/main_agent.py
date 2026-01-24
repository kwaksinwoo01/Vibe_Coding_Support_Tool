"""
main_agent.py

**6-Tier Task Orchestration with Automated Decision Rules**

Enhanced master controller with intelligent routing, retry logic, circuit breaker,
and human-in-the-loop support.

New Features (v2.1):
- Confidence-based routing with DecisionEngine
- Automatic retry with exponential backoff
- Circuit breaker pattern with Redis persistence
- Policy-based decision rules
- Comprehensive metrics collection
- Enhanced human-in-the-loop with retry mechanism
- Decision trace recording

Workflow:
1. User Input → Classification (via Tier F or keyword matching)
2. Decision evaluation (confidence, policies, cost)
3. Tier execution with retry logic
4. Circuit breaker check and failure handling
5. Next tier routing based on decision rules
6. Metrics collection and decision trace
7. Human-in-the-loop retry before async wait

Usage:
    from main_agent import MainAgent

    agent = MainAgent(workspace_root=".")
    final_state = agent.route_and_execute(user_input)
"""

import json
import time
import warnings
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
from collections import defaultdict
from queue import Queue
from threading import Lock
from abc import ABC, abstractmethod
import requests

from models.core import AgentState, TaskContext
from lang_graph_moduel.decision_engine import (
    DecisionEngine,
    DecisionContext,
    RoutingDecision,
    FailureType,
    create_decision_context,
    ConfidenceLevel,
)
from lang_graph_moduel.policy_engine import PolicyEngine
from lang_graph_moduel.metrics_collector import get_metrics_collector, MetricsCollector
from models.core.types import EventType

# Import Tier D analysis data models for routing engine integration
from models.core.reporting_models import (
    IssueClassification,
    ResolutionStrategy,
    RoutingInfo,
)

# Redis import with fallback
try:
    import redis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    warnings.warn(
        "Redis not available. Circuit breaker state will not persist across restarts."
    )


class CircuitBreakerState:
    """Circuit breaker state for a tier with Redis persistence"""

    CLOSED = "CLOSED"  # Normal operation
    OPEN = "OPEN"  # Fast-fail mode
    HALF_OPEN = "HALF_OPEN"  # Testing recovery

    def __init__(
        self,
        tier: str,
        failure_threshold: int = 5,
        cooldown_seconds: int = 60,
        redis_client: Optional[Any] = None,
    ):
        self.tier = tier
        self.state = self.CLOSED
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self.last_failure_time: Optional[float] = None
        self.last_success_time: Optional[float] = None
        self.redis_client = redis_client
        self._lock = Lock()

        # Load from Redis if available
        if self.redis_client:
            self._load_from_redis()

    def _redis_key(self) -> str:
        """Generate Redis key for this circuit breaker"""
        return f"circuit_breaker:{self.tier}"

    def _load_from_redis(self):
        """Load state from Redis"""
        try:
            key = self._redis_key()
            data = self.redis_client.get(key)
            if data:
                state_dict = json.loads(data)
                self.state = state_dict.get("state", self.CLOSED)
                self.failure_count = state_dict.get("failure_count", 0)
                self.last_failure_time = state_dict.get("last_failure_time")
                self.last_success_time = state_dict.get("last_success_time")
        except Exception as e:
            print(f"[CIRCUIT_BREAKER] Failed to load state from Redis: {e}")

    def _save_to_redis(self):
        """Save state to Redis"""
        if not self.redis_client:
            return

        try:
            key = self._redis_key()
            state_dict = {
                "tier": self.tier,
                "state": self.state,
                "failure_count": self.failure_count,
                "last_failure_time": self.last_failure_time,
                "last_success_time": self.last_success_time,
                "timestamp": datetime.now().isoformat(),
            }
            self.redis_client.set(key, json.dumps(state_dict))
            # Set expiration to 24 hours to avoid stale data
            self.redis_client.expire(key, 86400)
        except Exception as e:
            print(f"[CIRCUIT_BREAKER] Failed to save state to Redis: {e}")

    def record_success(self):
        """Record successful execution"""
        with self._lock:
            self.failure_count = 0
            self.last_success_time = time.time()

            if self.state == self.HALF_OPEN:
                # Success in half-open closes circuit
                self.state = self.CLOSED

            self._save_to_redis()

    def record_failure(self):
        """Record failed execution"""
        with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.time()

            if self.failure_count >= self.failure_threshold:
                self.state = self.OPEN

            self._save_to_redis()

    def can_execute(self) -> bool:
        """Check if tier can execute (circuit not open)"""
        with self._lock:
            if self.state == self.CLOSED:
                return True

            if self.state == self.HALF_OPEN:
                return True

            # OPEN state - check if cooldown period has passed
            if self.last_failure_time:
                elapsed = time.time() - self.last_failure_time
                if elapsed >= self.cooldown_seconds:
                    # Enter half-open state to test
                    self.state = self.HALF_OPEN
                    self._save_to_redis()
                    return True

            return False

    def reset(self):
        """Reset circuit breaker"""
        with self._lock:
            self.state = self.CLOSED
            self.failure_count = 0
            self.last_failure_time = None
            self._save_to_redis()


class HumanDecisionQueue:
    """Queue for managing human-in-the-loop decision requests"""

    def __init__(self):
        self.queue: Queue = Queue()
        self.pending_decisions: Dict[str, DecisionContext] = {}
        self._lock = Lock()

    def enqueue(self, decision_id: str, context: DecisionContext):
        """Add a decision to the queue"""
        with self._lock:
            self.pending_decisions[decision_id] = context
            self.queue.put(decision_id)
            print(f"[HUMAN_QUEUE] Enqueued decision {decision_id}")

    def dequeue(self) -> Optional[str]:
        """Get next decision from queue (non-blocking)"""
        try:
            decision_id = self.queue.get_nowait()
            return decision_id
        except:
            return None

    def resolve(self, decision_id: str, decision_data: Dict[str, Any]):
        """Mark a decision as resolved"""
        with self._lock:
            if decision_id in self.pending_decisions:
                del self.pending_decisions[decision_id]
                print(f"[HUMAN_QUEUE] Resolved decision {decision_id}")

    def is_pending(self, decision_id: str) -> bool:
        """Check if a decision is still pending"""
        with self._lock:
            return decision_id in self.pending_decisions

    def get_context(self, decision_id: str) -> Optional[DecisionContext]:
        """Get the context for a pending decision"""
        with self._lock:
            return self.pending_decisions.get(decision_id)


class MainAgent:
    """
    Enhanced 6-tier orchestration agent with automated decision rules.

    Features:
    - Intelligent routing with confidence scoring
    - Retry logic with exponential backoff
    - Circuit breaker for fault tolerance
    - Policy-based decision rules
    - Human-in-the-loop support
    - Comprehensive metrics and decision traces
    """

    TIER_MODULES = {
        "A": "A_Working_Document_Progress",
        "B": "B_Performing_Tasks",
        "C": "C_Edit_working_document",
        "D": "D_Issue_Analysis_Flow",
        "E": "E_Document_Management",
        "F": "F_Unknown_logic",
    }

    TIER_NAMES = {
        "A": "Create Work Plan",
        "B": "Perform Instructions",
        "C": "Change Plan",
        "D": "Issue Analysis",
        "E": "Document Management",
        "F": "Exception Handler",
    }

    def __init__(
        self,
        workspace_root: str = ".",
        enable_decision_engine: bool = True,
        enable_circuit_breaker: bool = True,
        enable_metrics: bool = True,
        policy_config_path: Optional[str] = None,
        redis_host: str = "localhost",
        redis_port: int = 6379,
        redis_db: int = 0,
    ):
        """
        Initialize main agent.

        Args:
            workspace_root: Root directory of workspace
            enable_decision_engine: Enable intelligent routing decisions
            enable_circuit_breaker: Enable circuit breaker pattern
            enable_metrics: Enable metrics collection
            policy_config_path: Path to policy configuration JSON
            redis_host: Redis server host
            redis_port: Redis server port
            redis_db: Redis database number
        """
        self.workspace_root = workspace_root
        self.execution_history: List[Dict[str, Any]] = []
        self.current_session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Redis client for circuit breaker persistence
        self.redis_client = None
        if REDIS_AVAILABLE and enable_circuit_breaker:
            try:
                self.redis_client = redis.Redis(
                    host=redis_host,
                    port=redis_port,
                    db=redis_db,
                    decode_responses=True,
                    socket_timeout=2,
                    socket_connect_timeout=2,
                )
                # Test connection
                self.redis_client.ping()
                print(f"[MAIN_AGENT] Redis connected: {redis_host}:{redis_port}")
            except Exception as e:
                print(f"[MAIN_AGENT] Redis connection failed: {e}")
                print(f"[MAIN_AGENT] Falling back to in-memory circuit breaker")
                self.redis_client = None

        # Decision engine
        self.enable_decision_engine = enable_decision_engine
        if enable_decision_engine:
            self.decision_engine = DecisionEngine(
                confidence_threshold=0.5, max_retries=3, base_retry_delay_ms=1000
            )
        else:
            self.decision_engine = None

        # Policy engine
        if policy_config_path is None:
            # Use default config path
            policy_config_path = str(
                Path(__file__).parent / "config" / "decision_policies.json"
            )

        self.policy_engine = PolicyEngine(policy_config_path)

        # Circuit breakers (one per tier) with Redis persistence
        self.enable_circuit_breaker = enable_circuit_breaker
        self.circuit_breakers: Dict[str, CircuitBreakerState] = {}
        for tier in self.TIER_MODULES.keys():
            self.circuit_breakers[tier] = CircuitBreakerState(
                tier, redis_client=self.redis_client if enable_circuit_breaker else None
            )

        # Metrics
        self.enable_metrics = enable_metrics
        self.metrics: Optional[MetricsCollector] = None
        if enable_metrics:
            self.metrics = get_metrics_collector()

        # Human-in-the-loop state with enhanced retry mechanism
        self.awaiting_decision: bool = False
        self.pending_decision_context: Optional[DecisionContext] = None
        self.human_decision_queue = HumanDecisionQueue()
        self.human_retry_max_cycles: int = 2  # Max retry cycles before async wait

        # Routing engine (integrated from routing_engine.py for centralized orchestration)
        self.routing_engine = self.RoutingEngine(self)
    
    # ========================================================================
    # Routing Strategy Interface and Implementations
    # ========================================================================
    
    class IRoutingStrategy(ABC):
        """
        Interface for routing strategies.
        
        Defines the contract for different routing decision approaches:
        - KeywordRoutingStrategy: Traditional keyword/rule-based routing
        - MetricsBasedRoutingStrategy: Metrics-driven dynamic routing
        """
        
        from abc import ABC, abstractmethod
        
        @abstractmethod
        def decide_routing(
            self,
            tier: str,
            result: Dict[str, Any],
            execution_history: List[Dict[str, Any]],
            metrics_collector: Optional['MetricsCollector']
        ) -> str:
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
            metrics_collector: Optional['MetricsCollector']
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
        
        def __init__(self, routing_engine: 'MainAgent.RoutingEngine'):
            """Initialize with reference to RoutingEngine for accessing rules."""
            self.routing_engine = routing_engine
        
        def decide_routing(
            self,
            tier: str,
            result: Dict[str, Any],
            execution_history: List[Dict[str, Any]],
            metrics_collector: Optional['MetricsCollector']
        ) -> str:
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
            metrics_collector: Optional['MetricsCollector']
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
        
        def __init__(self, routing_engine: 'MainAgent.RoutingEngine'):
            """Initialize with reference to RoutingEngine."""
            self.routing_engine = routing_engine
            self.fallback_strategy = None  # Will be set to KeywordRoutingStrategy
        
        def decide_routing(
            self,
            tier: str,
            result: Dict[str, Any],
            execution_history: List[Dict[str, Any]],
            metrics_collector: Optional['MetricsCollector']
        ) -> str:
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
            metrics_collector: Optional['MetricsCollector']
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

    # ========================================================================
    # Integrated Routing Engine (Moved from analysis/error/routing_engine.py)
    # ========================================================================

    class RoutingEngine:
        """
        Centralized routing engine with Strategy Pattern support.

        Enhanced from .github/agents/tool/analysis/error/routing_engine.py
        to support both keyword-based and metrics-based routing strategies.

        Responsibilities:
        - Tier D initial routing decision (Rule 1)
        - Tier C/E routing validation (Rule 2)
        - Auto-resolve chain routing (D → C → B)
        - Strategy-based routing with metrics integration

        Note: As inner class of MainAgent, accesses outer instance via self.main_agent
        """

        def __init__(self, main_agent: "MainAgent"):
            """
            Initialize RoutingEngine with routing strategies.

            Args:
                main_agent: Reference to outer MainAgent instance for accessing
                           decision_engine, metrics, etc.
            """
            self.main_agent = main_agent
            
            # Initialize routing strategies
            self.keyword_strategy = main_agent.KeywordRoutingStrategy(self)
            self.metrics_strategy = main_agent.MetricsBasedRoutingStrategy(self)
            
            # Set up bidirectional fallback
            self.metrics_strategy.fallback_strategy = self.keyword_strategy
            
            # Default to metrics-based strategy if metrics enabled
            self.active_strategy: MainAgent.IRoutingStrategy = (
                self.metrics_strategy if main_agent.enable_metrics
                else self.keyword_strategy
            )
            
            print(f"[ROUTING_ENGINE] Initialized with strategy: "
                  f"{type(self.active_strategy).__name__}")
        
        def set_strategy(self, use_metrics_based: bool):
            """
            Switch between keyword-based and metrics-based routing strategies.
            
            Args:
                use_metrics_based: If True, use MetricsBasedRoutingStrategy.
                                  If False, use KeywordRoutingStrategy.
            """
            if use_metrics_based and self.main_agent.enable_metrics:
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
            return self.active_strategy.calculate_confidence_threshold(
                self.main_agent.metrics
            )

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

        def decide_routing(self, tier: str, result: Dict[str, Any]) -> str:
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
                execution_history=self.main_agent.execution_history,
                metrics_collector=self.main_agent.metrics
            )
            
            return next_tier

        def _apply_routing_rules_for_c(self, result: Dict[str, Any]) -> str:
            """
            Apply routing rules for Tier C (Plan Modification).

            Tier C SUCCESS routing:
            - If modification applied → B (re-execute)
            - If documentation update only → E (document management)
            - Default → None (end)

            Args:
                result: Tier C execution result

            Returns:
                Next tier
            """
            status = result.get("status", "UNKNOWN")

            if status == "SUCCESS":
                # Check if code/plan was modified → re-execute in B
                modified_files = result.get("payload", {}).get("modified_files", [])
                if modified_files:
                    return "B"  # Re-execute with modified plan

                # Check if documentation update → route to E
                doc_updates = result.get("payload", {}).get("doc_updates", [])
                if doc_updates:
                    return "E"

                # Default: end workflow
                return None
            else:
                # FAILURE → route to D for analysis
                return "D"

        def _apply_routing_rules_for_e(self, result: Dict[str, Any]) -> str:
            """
            Apply routing rules for Tier E (Document Management).

            Tier E SUCCESS routing:
            - Always end (None) - documentation is final step

            Tier E FAILURE routing:
            - Route to D for analysis

            Args:
                result: Tier E execution result

            Returns:
                Next tier (None or D)
            """
            status = result.get("status", "UNKNOWN")

            if status == "SUCCESS":
                # Documentation complete → end workflow
                return None
            else:
                # FAILURE → route to D for analysis
                return "D"

        def discover_steps(self, user_input: str) -> Optional[Dict[str, Any]]:
            """
            Automatically discover project steps from workspace structure.
            
            Scans docs_2/ directory for step-related files and references
            to enable automated step execution without requiring explicit
            documentation in NextTask-2.md.
            
            Args:
                user_input: User's natural language input
                
            Returns:
                Dictionary with step information if found, None otherwise:
                {
                    "step_number": int,
                    "step_dir": str,  # e.g., "P8"
                    "documents": List[str],  # Found related documents
                    "context": str,  # Step context/goal extracted from docs
                    "confidence": float  # Discovery confidence (0.0-1.0)
                }
            """
            import re
            from pathlib import Path
            
            # Extract step number from input (e.g., "step 8", "스텝 8", "P8")
            step_patterns = [
                r'step\s+(\d+)',
                r'스텝\s+(\d+)',
                r'part\s+(\d+)',
                r'P(\d+)(?:\s|$|/)',
            ]
            
            step_number = None
            for pattern in step_patterns:
                match = re.search(pattern, user_input, re.IGNORECASE)
                if match:
                    step_number = int(match.group(1))
                    break
            
            if step_number is None:
                return None
            
            # Scan workspace for step-related directories and files
            workspace_path = Path(self.main_agent.workspace_root) / "docs_2"
            if not workspace_path.exists():
                return None
            
            # Look for P{number} directory
            step_dir = f"P{step_number}"
            step_path = workspace_path / step_dir
            
            discovered_info = {
                "step_number": step_number,
                "step_dir": step_dir,
                "documents": [],
                "context": "",
                "confidence": 0.0
            }
            
            # Check if step directory exists
            if step_path.exists() and step_path.is_dir():
                discovered_info["confidence"] += 0.3
                
                # Find all markdown files in step directory
                md_files = list(step_path.rglob("*.md"))
                discovered_info["documents"] = [str(f.relative_to(workspace_path)) for f in md_files]
                
                if md_files:
                    discovered_info["confidence"] += 0.2
                    
                    # Try to extract step context from first markdown file
                    try:
                        with open(md_files[0], 'r', encoding='utf-8') as f:
                            content = f.read(500)  # Read first 500 chars
                            # Look for Goal: or 목표: lines
                            goal_match = re.search(r'(?:Goal|목표):\s*(.+)', content, re.IGNORECASE)
                            if goal_match:
                                discovered_info["context"] = goal_match.group(1).strip()
                                discovered_info["confidence"] += 0.2
                    except Exception:
                        pass
            
            # Check NextTask-2.md for explicit step reference
            nexttask_path = workspace_path / "NextTask-2.md"
            if nexttask_path.exists():
                try:
                    with open(nexttask_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        # Look for step section
                        step_pattern = rf'##\s+.*step\s+{step_number}[:\s](.+?)(?=\n##|\Z)'
                        step_match = re.search(step_pattern, content, re.IGNORECASE | re.DOTALL)
                        if step_match:
                            discovered_info["confidence"] += 0.3
                            if not discovered_info["context"]:
                                # Extract goal from step section
                                goal_match = re.search(r'(?:Goal|목표):\s*(.+)', step_match.group(1))
                                if goal_match:
                                    discovered_info["context"] = goal_match.group(1).strip()
                except Exception:
                    pass
            
            # Return None if confidence is too low (no evidence found)
            if discovered_info["confidence"] < 0.3:
                return None
            
            print(f"[STEP_DISCOVERY] Found step {step_number} (confidence: {discovered_info['confidence']:.2f})")
            print(f"[STEP_DISCOVERY] Directory: {step_dir}, Documents: {len(discovered_info['documents'])}")
            if discovered_info["context"]:
                print(f"[STEP_DISCOVERY] Context: {discovered_info['context'][:100]}...")
            
            return discovered_info

        def classify_input(self, user_input: str) -> tuple[str, float]:
            """
            Classify user input to determine initial tier with confidence score.

            Enhanced with:
            - Automated step discovery from workspace structure
            - Decision Engine for automatic classification
            - Keyword matching as baseline
            - Confidence-based routing support

            Args:
                user_input: User's natural language input

            Returns:
                Tuple of (tier, confidence):
                - tier: Initial tier (A-F)
                - confidence: Classification confidence (0.0-1.0)
            """
            # Step 1: Attempt automated step discovery
            step_info = self.discover_steps(user_input)
            if step_info:
                # Step discovered - determine appropriate tier based on input keywords
                # Priority: modify > execute > create (to avoid "plan" in "modify plan")
                user_lower = user_input.lower()
                
                # HIGHEST PRIORITY: If input contains "modify" or "change" keywords → Tier C
                if any(kw in user_lower for kw in ["modify", "change", "edit", "update", "수정", "변경"]):
                    print(f"[CLASSIFY] Step {step_info['step_number']} discovered → routing to Tier C (modification)")
                    return ("C", step_info["confidence"])
                
                # If input contains "execute" or "perform" keywords → Tier B
                elif any(kw in user_lower for kw in ["execute", "perform", "run", "implement", "실행", "진행"]):
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
            tier_keywords = {
                "A": [
                    "create",
                    "plan",
                    "새로운",
                    "작성",
                    "wpd 생성",
                    "work plan",
                    "make plan",
                    "generate plan",
                    "start plan",
                    "작업 계획 생성",
                ],
                "B": [
                    "perform",
                    "execute",
                    "run",
                    "실행",
                    "진행",
                    "작업 계획 실행",
                    "do task",
                    "complete task",
                    "implement",
                    "작업 수행",
                ],
                "C": [
                    "change",
                    "modify",
                    "edit",
                    "수정",
                    "변경",
                    "마일스톤",
                    "update",
                    "revise",
                    "alter",
                    "계획 변경",
                ],
                "D": [
                    "error",
                    "issue",
                    "fails",
                    "failure",
                    "오류",
                    "문제",
                    "작동 안",
                    "bug",
                    "broken",
                    "not working",
                    "debug",
                    "문제 분석",
                ],
                "E": [
                    "save",
                    "mapping",
                    "저장",
                    "동기화",
                    "데이터 클래스",
                    "필드",
                    "document",
                    "reflect",
                    "update mapping",
                    "문서 관리",
                    "read file",
                    "read",
                    "파일 읽기",
                ],
            }

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
                for kw in keywords:
                    if kw in user_input_lower:
                        # Base score
                        score += 1.0
                        # Priority bonus for certain keywords
                        if kw in priority_keywords:
                            score += priority_keywords[kw]
                
                if score > 0:
                    tier_scores[tier] = score

            # Calculate keyword-based confidence
            total_matches = sum(tier_scores.values())
            keyword_confidence = 0.0
            best_tier = None
            
            if tier_scores:
                best_tier = max(tier_scores, key=tier_scores.get)
                max_score = tier_scores[best_tier]
                # Confidence based on ratio of max score to total matches
                # Higher confidence if one tier dominates
                keyword_confidence = min(0.9, 0.5 + (max_score / total_matches) * 0.4)

            # Step 3: Use Decision Engine for automatic classification
            if (
                self.main_agent.enable_decision_engine
                and self.main_agent.decision_engine
            ):
                try:
                    context = create_decision_context(
                        tier="INITIAL",
                        status="PENDING",
                        user_input=user_input,
                        payload={"tier_scores": tier_scores},
                    )
                    decision = self.main_agent.decision_engine.evaluate_routing(context)

                    # High confidence AI decision → use directly
                    if decision.confidence > 0.8 and decision.next_tier:
                        # Track AI classification metric
                        if self.main_agent.enable_metrics and self.main_agent.metrics:
                            self.main_agent.metrics.set_gauge(
                                "ai_classification_confidence", decision.confidence
                            )
                        print(f"[CLASSIFY] Decision engine selected Tier {decision.next_tier} (confidence: {decision.confidence:.2f})")
                        return (decision.next_tier, decision.confidence)

                    # Track that we used keyword fallback
                    if self.main_agent.enable_metrics and self.main_agent.metrics:
                        self.main_agent.metrics.set_gauge(
                            "keyword_classification_used", 1.0
                        )

                except Exception as e:
                    # Decision Engine failed → fallback to keyword matching
                    if self.main_agent.enable_metrics and self.main_agent.metrics:
                        self.main_agent.metrics.increment_counter(
                            "decision_engine_failures"
                        )

            # Step 4: Return keyword matching result or fallback
            if best_tier:
                print(f"[CLASSIFY] Keyword matching selected Tier {best_tier} (confidence: {keyword_confidence:.2f})")
                return (best_tier, keyword_confidence)
            else:
                # No keyword match → default to Tier A (plan creation)
                # Low confidence since it's a fallback
                print(f"[CLASSIFY] No matches - defaulting to Tier A (confidence: 0.3)")
                return ("A", 0.3)

    # ========================================================================
    # Routing Decision (Delegated to RoutingEngine)
    # ========================================================================

    def decide_routing(self, tier: str, result: Dict[str, Any]) -> str:
        """
        Centralized routing decision for all tiers (Wrapper for RoutingEngine).

        Delegates to RoutingEngine for all routing decisions.

        Args:
            tier: Current tier (A-F)
            result: Tier execution result

        Returns:
            Next tier to route to
        """
        return self.routing_engine.decide_routing(tier, result)

    # ========================================================================
    # Classification (Delegated to RoutingEngine)
    # ========================================================================

    def classify_input(self, user_input: str) -> tuple[str, float]:
        """
        Classify user input to determine initial tier with confidence score.

        Enhanced with:
        - Automated step discovery from workspace structure
        - Decision Engine for automatic classification
        - Keyword matching as baseline
        - Confidence-based routing support

        Args:
            user_input: User's natural language input

        Returns:
            Tuple of (tier, confidence):
            - tier: Initial tier (A-F)
            - confidence: Classification confidence (0.0-1.0)
        """
        return self.routing_engine.classify_input(user_input)

    # ========================================================================
    # Circuit Breaker Management
    # ========================================================================

    def is_circuit_breaker_open(self, tier: str) -> bool:
        """Check if circuit breaker is open for tier"""
        if not self.enable_circuit_breaker:
            return False

        cb = self.circuit_breakers.get(tier)
        if cb is None:
            return False

        return not cb.can_execute()

    def record_tier_success(self, tier: str):
        """Record successful tier execution"""
        if self.enable_circuit_breaker:
            cb = self.circuit_breakers.get(tier)
            if cb:
                cb.record_success()

                if cb.state == CircuitBreakerState.CLOSED:
                    # Emit circuit breaker closed event
                    if self.metrics:
                        self.metrics.record_circuit_breaker_closed(tier)

    def record_tier_failure(self, tier: str):
        """Record failed tier execution"""
        if self.enable_circuit_breaker:
            cb = self.circuit_breakers.get(tier)
            if cb:
                cb.record_failure()

                if cb.state == CircuitBreakerState.OPEN:
                    # Emit circuit breaker open event
                    if self.metrics:
                        self.metrics.record_circuit_breaker_open(tier)

                    print(f"[MAIN_AGENT] ⚠️ Circuit breaker OPEN for Tier {tier}")

    def reset_circuit_breaker(self, tier: str):
        """Reset circuit breaker for tier"""
        if self.enable_circuit_breaker:
            cb = self.circuit_breakers.get(tier)
            if cb:
                cb.reset()
                print(f"[MAIN_AGENT] Circuit breaker reset for Tier {tier}")

    # ========================================================================
    # Decision Engine Integration
    # ========================================================================

    def evaluate_routing_decision(self, context: DecisionContext) -> RoutingDecision:
        """
        Evaluate routing decision using decision engine, policies, and dynamic thresholds.

        Enhanced with:
        - Dynamic confidence threshold from metrics-based routing strategy
        - Tier D auto-resolve detection (Proposal 2)

        Args:
            context: Decision context

        Returns:
            RoutingDecision with next tier and metadata
        """
        # Get dynamic confidence threshold from routing engine
        dynamic_threshold = self.routing_engine.get_dynamic_confidence_threshold()
        
        if not self.enable_decision_engine or self.decision_engine is None:
            # Import ConfidenceLevel for fallback
            from lang_graph_moduel.decision_engine import ConfidenceLevel

            # Fallback to simple routing
            next_tier = context.payload.get("next_node")

            # Check for Tier D auto-resolve even in fallback mode
            if context.tier == "D" and context.status == "SUCCESS":
                auto_resolve_details = context.payload.get("auto_resolve_details")
                if auto_resolve_details:
                    print(
                        f"[MAIN_AGENT] 🤖 Auto-resolve detected: Forcing route to Tier C"
                    )
                    print(
                        f"[MAIN_AGENT]   → Action: {auto_resolve_details.get('action', 'N/A')}"
                    )
                    print(
                        f"[MAIN_AGENT]   → Target: {auto_resolve_details.get('target_file', 'N/A')}"
                    )
                    next_tier = "C"  # Force routing to Tier C

            return RoutingDecision(
                next_tier=next_tier,
                confidence=0.5,
                confidence_level=ConfidenceLevel.MEDIUM,
                reasoning=f"Decision engine disabled - using default routing (threshold: {dynamic_threshold})",
            )

        # Update decision engine confidence threshold dynamically
        original_threshold = self.decision_engine.confidence_threshold
        self.decision_engine.confidence_threshold = dynamic_threshold
        
        # Get base decision from engine
        decision = self.decision_engine.evaluate_routing(context)
        
        # Restore original threshold
        self.decision_engine.confidence_threshold = original_threshold

        # Enhanced: Check for Tier D auto-resolve (Proposal 2 - breaking change allowed)
        if context.tier == "D" and context.status == "SUCCESS":
            auto_resolve_details = context.payload.get("auto_resolve_details")
            if auto_resolve_details:
                print(f"[MAIN_AGENT] 🤖 Auto-resolve detected from Tier D analysis")
                print(
                    f"[MAIN_AGENT]   → Action: {auto_resolve_details.get('action', 'N/A')}"
                )
                print(
                    f"[MAIN_AGENT]   → Target file: {auto_resolve_details.get('target_file', 'N/A')}"
                )
                print(
                    f"[MAIN_AGENT]   → Confidence: {auto_resolve_details.get('confidence_level', 'N/A')}"
                )
                print(
                    f"[MAIN_AGENT]   → Estimated effort: {auto_resolve_details.get('estimated_effort', 'N/A')}"
                )

                # Force routing to Tier C for automatic resolution (destructive change allowed)
                decision.next_tier = "C"
                decision.confidence = 0.95  # High confidence for auto-resolve
                decision.reasoning = (
                    f"Auto-resolve chain: D detected fix-capable issue. "
                    f"Routing to C for '{auto_resolve_details.get('action')}' "
                    f"on {auto_resolve_details.get('target_file', 'unknown file')}. "
                    f"Chain: D → C → B (automatic re-execution)"
                )

                # Record auto-resolve in metrics (using existing methods)
                if self.metrics:
                    self.metrics.increment_counter(
                        "auto_resolve_triggered_total", labels={"tier": "D"}
                    )
                    self.metrics.set_gauge(
                        "auto_resolve_confidence", 0.95, labels={"tier": "D"}
                    )

                print(f"[MAIN_AGENT] ✓ Forced routing: D → C (auto-resolve chain)")

        # Apply policy rules
        policy_action = self.policy_engine.evaluate(
            {
                "tier": context.tier,
                "status": context.status,
                "confidence": decision.confidence,
                "retry_count": context.retry_count,
                "estimated_cost": context.estimated_cost,
                "execution_time_ms": context.execution_time_ms,
            }
        )

        if policy_action:
            # Policy matched - apply action
            if policy_action.requires_human_approval:
                decision.requires_human_approval = True

            if policy_action.use_alternative and policy_action.alternative_tier:
                decision.next_tier = policy_action.alternative_tier
                decision.reasoning += (
                    f" (Policy override to {policy_action.alternative_tier})"
                )

            if policy_action.override_confidence is not None:
                decision.confidence = policy_action.override_confidence

            # Record policy evaluation
            if self.metrics:
                self.metrics.record_policy_evaluated("routing_policy", matched=True)

        # Record metrics
        if self.metrics:
            if decision.confidence < dynamic_threshold:
                self.metrics.record_decision_required(context.tier, decision.confidence)

        return decision

    # ========================================================================
    # Tier Execution with Retry Logic
    # ========================================================================

    def execute_tier_with_retry(
        self, tier: str, user_input: str, previous_state: Optional[AgentState] = None
    ) -> AgentState:
        """
        Execute tier with automatic retry on transient failures.

        Args:
            tier: Tier to execute
            user_input: User input
            previous_state: Previous state for chaining

        Returns:
            AgentState from execution
        """
        max_retries = 3 if self.enable_decision_engine else 0
        retry_count = 0

        while retry_count <= max_retries:
            # Check circuit breaker
            if self.is_circuit_breaker_open(tier):
                error_msg = f"Circuit breaker is OPEN for Tier {tier}"
                print(f"[MAIN_AGENT] {error_msg}")

                return AgentState.create_failure(
                    tier=tier,
                    error_msg=error_msg,
                    logic_summary="Fast-fail due to circuit breaker",
                )

            # Execute tier
            start_time = time.time()
            state = self.execute_tier(tier, user_input, previous_state)
            execution_time_ms = (time.time() - start_time) * 1000

            state.set_execution_time(execution_time_ms)
            state.retry_count = retry_count

            # Record metrics
            if self.metrics:
                self.metrics.record_tier_execution(
                    tier=tier,
                    duration_ms=execution_time_ms,
                    status=state.status,
                    confidence=state.confidence,
                )

            # Check if successful
            if state.status == "SUCCESS" or state.status == "PARTIAL":
                self.record_tier_success(tier)
                return state

            # Execution failed
            self.record_tier_failure(tier)

            # Check if retry eligible
            if retry_count >= max_retries:
                print(
                    f"[MAIN_AGENT] Max retries ({max_retries}) reached for Tier {tier}"
                )
                if self.metrics:
                    self.metrics.increment_counter(
                        "retry_exhausted_total", labels={"tier": tier}
                    )
                break

            # Classify failure
            error_msg = state.errors[0] if state.errors else "Unknown error"

            if self.decision_engine:
                failure_type = self.decision_engine.classify_failure(error_msg)

                # Check if retryable
                if failure_type == FailureType.PERMANENT:
                    print(f"[MAIN_AGENT] Permanent failure detected - no retry")
                    break

                # Calculate backoff
                retry_delay_ms = self.decision_engine.calculate_backoff_delay(
                    retry_count
                )
                print(
                    f"[MAIN_AGENT] Transient failure - retrying after {retry_delay_ms}ms (attempt {retry_count + 1}/{max_retries})"
                )

                # Wait before retry
                time.sleep(retry_delay_ms / 1000.0)

                # Record retry
                if self.metrics:
                    self.metrics.record_retry_attempted(tier, retry_count + 1)

            retry_count += 1
            state.increment_retry()

        return state

    def execute_tier(
        self, tier: str, user_input: str, previous_state: Optional[AgentState] = None
    ) -> AgentState:
        """
        Execute a specific tier (single attempt - no retry).

        Args:
            tier: Tier to execute (A-F)
            user_input: User input text
            previous_state: Previous tier's execution result

        Returns:
            AgentState from execution
        """
        if tier not in self.TIER_MODULES:
            return AgentState.create_failure(
                tier="MAIN_AGENT",
                error_msg=f"Invalid tier: {tier}",
                logic_summary="Invalid tier specification",
            )

        module_name = self.TIER_MODULES[tier]

        try:
            # Dynamic module import
            import importlib.util

            module_path = Path(__file__).parent / f"{module_name}.py"

            if not module_path.exists():
                return AgentState.create_failure(
                    tier="MAIN_AGENT",
                    error_msg=f"Module file not found: {module_path}",
                    logic_summary=f"Tier {tier} module does not exist",
                )

            spec = importlib.util.spec_from_file_location(module_name, module_path)
            module = importlib.util.module_from_spec(spec)

            # Add models to sys.path
            import sys

            models_path = str(Path(__file__).parent / "models")
            if models_path not in sys.path:
                sys.path.insert(0, models_path)

            spec.loader.exec_module(module)

            # Special handling for Tier D: Inject routing engine
            if tier == "D":
                # Get IssueAnalysisEngine class and instantiate with routing_engine
                engine_class = getattr(module, "IssueAnalysisEngine")
                engine = engine_class(
                    workspace_root=self.workspace_root,
                    routing_engine=self.routing_engine,
                )

                # Execute analyze method instead of main function
                state = engine.execute(
                    user_input,
                    error_context=previous_state.payload if previous_state else {},
                )

            else:
                # Get main function for other tiers
                main_func = getattr(module, "main")
                import inspect

                sig = inspect.signature(main_func)

                # Execute tier module
                if "previous_payload" in sig.parameters and previous_state:
                    prev_payload = {
                        "tier": previous_state.tier,
                        "status": previous_state.status,
                        "logic_summary": previous_state.logic_summary,
                        "payload": previous_state.payload,
                        "confidence": previous_state.confidence,
                        "retry_count": previous_state.retry_count,
                    }
                    state = main_func(
                        user_input,
                        workspace_root=self.workspace_root,
                        previous_payload=prev_payload,
                    )
                else:
                    state = main_func(user_input, workspace_root=self.workspace_root)

            # Store previous state info
            if previous_state and "previous_state_info" not in state.payload:
                state.payload["previous_state_info"] = {
                    "tier": previous_state.tier,
                    "status": previous_state.status,
                    "logic_summary": previous_state.logic_summary,
                }

            # Record execution
            self.execution_history.append(
                {
                    "tier": tier,
                    "timestamp": datetime.now().isoformat(),
                    "status": state.status,
                    "next_node": state.next_node,
                    "confidence": state.confidence,
                    "retry_count": state.retry_count,
                }
            )

            return state

        except Exception as e:
            import traceback

            traceback.print_exc()
            return AgentState.create_failure(
                tier="MAIN_AGENT",
                error_msg=f"Failed to execute Tier {tier}: {str(e)}",
                logic_summary=f"Module execution error: {type(e).__name__}",
            )

    # ========================================================================
    # Human-in-the-Loop Support with Enhanced Retry Mechanism
    # ========================================================================

    def attempt_system_tasks_before_human_wait(
        self,
        context: DecisionContext,
        current_tier: str,
        current_iteration: int,
        max_iterations: int,
    ) -> Optional[AgentState]:
        """
        Attempt to execute all possible system-manageable tasks before requesting human input.

        This implements a retry mechanism where the system attempts to perform all
        tasks that don't require human approval, then re-evaluates the human-required task.

        Args:
            context: Current decision context requiring human approval
            current_tier: Current tier being executed
            current_iteration: Current iteration count
            max_iterations: Maximum allowed iterations

        Returns:
            AgentState if alternative path succeeds, None if human input still required
        """
        retry_cycle = 0

        while retry_cycle < self.human_retry_max_cycles:
            retry_cycle += 1
            print(
                f"\n[HUMAN_RETRY] Cycle {retry_cycle}/{self.human_retry_max_cycles}: "
                f"Attempting system-manageable tasks before requesting human input"
            )

            # Try to find alternative tiers that don't require human approval
            alternative_tiers = self._find_system_manageable_tiers(
                current_tier, context
            )

            if not alternative_tiers:
                print(
                    f"[HUMAN_RETRY] Cycle {retry_cycle}: No alternative system tasks found"
                )
                break

            # Execute alternative tiers
            tasks_executed = False
            for alt_tier in alternative_tiers:
                if current_iteration >= max_iterations:
                    break

                print(f"[HUMAN_RETRY] Cycle {retry_cycle}: Attempting Tier {alt_tier}")

                try:
                    # Execute alternative tier
                    alt_input = (
                        f"System retry: Execute Tier {alt_tier} as alternative path"
                    )
                    alt_state = self.execute_tier_with_retry(alt_tier, alt_input, None)

                    if alt_state.status == "SUCCESS":
                        tasks_executed = True
                        print(
                            f"[HUMAN_RETRY] Cycle {retry_cycle}: Tier {alt_tier} succeeded"
                        )

                        # Re-evaluate original decision after executing alternative
                        new_context = create_decision_context(
                            tier=current_tier,
                            status=alt_state.status,
                            user_input=context.user_input,
                            payload={"next_node": alt_state.next_node},
                            retry_count=0,
                            execution_time_ms=alt_state.execution_time_ms,
                        )

                        new_decision = self.evaluate_routing_decision(new_context)

                        # Check if human approval still required
                        if not new_decision.requires_human_approval:
                            print(
                                f"[HUMAN_RETRY] Cycle {retry_cycle}: Human approval no longer required!"
                            )
                            return alt_state
                        else:
                            print(
                                f"[HUMAN_RETRY] Cycle {retry_cycle}: Human approval still required"
                            )

                except Exception as e:
                    print(
                        f"[HUMAN_RETRY] Cycle {retry_cycle}: Tier {alt_tier} failed: {e}"
                    )

            if not tasks_executed:
                print(
                    f"[HUMAN_RETRY] Cycle {retry_cycle}: No system tasks were successful"
                )
                break

        # After exhausting retry cycles, human input is definitively required
        print(
            f"[HUMAN_RETRY] Exhausted {retry_cycle} cycles. Entering async wait for human input."
        )
        return None

    def _find_system_manageable_tiers(
        self, current_tier: str, context: DecisionContext
    ) -> List[str]:
        """
        Find alternative tiers that might be executable without human approval.

        Args:
            current_tier: Current tier requiring human approval
            context: Decision context

        Returns:
            List of alternative tier names to try
        """
        # Define tier dependencies and alternatives
        tier_alternatives = {
            "A": ["E", "F"],  # If A needs approval, try E or F first
            "B": ["E", "D"],  # If B needs approval, try E or D
            "C": ["E", "F"],  # If C needs approval, try E or F
            "D": ["F", "E"],  # If D needs approval, try F or E
            "E": ["F"],  # If E needs approval, try F
            "F": [],  # F has no alternatives
        }

        alternatives = tier_alternatives.get(current_tier, [])

        # Filter out tiers with open circuit breakers
        available = [
            tier for tier in alternatives if not self.is_circuit_breaker_open(tier)
        ]

        return available

    def handle_human_decision(self, decision_data: Dict[str, Any]) -> RoutingDecision:
        """
        Handle external human decision input.

        Args:
            decision_data: Decision from human reviewer
                - next_tier: Override next tier
                - override_confidence: Confidence override
                - reason: Human decision reasoning

        Returns:
            RoutingDecision with human override
        """
        next_tier = decision_data.get("next_tier")
        override_confidence = decision_data.get("override_confidence", 0.9)
        reason = decision_data.get("reason", "Human approval provided")

        # Clear awaiting state
        self.awaiting_decision = False
        self.pending_decision_context = None

        # Record metrics
        if self.metrics:
            self.metrics.record_human_decision(
                tier=next_tier or "unknown", approved=True
            )

        # Create decision
        from lang_graph_moduel.decision_engine import ConfidenceLevel

        decision = RoutingDecision(
            next_tier=next_tier,
            confidence=override_confidence,
            confidence_level=ConfidenceLevel.from_score(override_confidence),
            reasoning=reason,
        )

        print(f"[MAIN_AGENT] Human decision received: {next_tier} ({reason})")

        return decision

    # ========================================================================
    # Main Orchestration Logic
    # ========================================================================

    def route_and_execute(
        self, 
        user_input: str, 
        max_iterations: int = 10,
        force_manual_routing: bool = False,
        manual_confidence_threshold: float = 0.8
    ) -> AgentState:
        """
        Route user input to appropriate tier and execute with chaining.

        Enhanced with:
        - Confidence-based routing with manual override support
        - Automated step discovery
        - Automatic retry logic
        - Circuit breaker pattern
        - Policy-based decisions
        - Human-in-the-loop support

        Args:
            user_input: User's natural language input
            max_iterations: Maximum execution iterations (prevent infinite loop)
            force_manual_routing: If True, always prompt for manual tier selection
            manual_confidence_threshold: Confidence threshold for automatic routing (default: 0.8)

        Returns:
            Final AgentState
        """
        print(f"\n{'='*80}")
        print(f"[MAIN_AGENT] New Session: {self.current_session_id}")
        print(f"[MAIN_AGENT] Input: {user_input[:100]}...")
        print(f"{'='*80}\n")

        # Classify initial tier with confidence
        initial_tier, classification_confidence = self.classify_input(user_input)
        
        print(f"[MAIN_AGENT] Classification: Tier {initial_tier} ({self.TIER_NAMES[initial_tier]})")
        print(f"[MAIN_AGENT] Confidence: {classification_confidence:.2f}")
        
        # Check if manual override is needed
        if force_manual_routing or classification_confidence < manual_confidence_threshold:
            if force_manual_routing:
                print(f"[MAIN_AGENT] ⚠️ Manual routing forced")
            else:
                print(f"[MAIN_AGENT] ⚠️ Low confidence ({classification_confidence:.2f} < {manual_confidence_threshold})")
            
            print(f"[MAIN_AGENT] Suggested tier: {initial_tier}")
            print(f"[MAIN_AGENT] Available tiers:")
            for tier, name in self.TIER_NAMES.items():
                print(f"  {tier}: {name}")
            print(f"\n[MAIN_AGENT] Note: In production, this would prompt for user confirmation.")
            print(f"[MAIN_AGENT] Proceeding with suggested tier for automated execution.\n")
            
            # In production, this would wait for user input
            # For now, proceed with suggestion but log the low confidence
            if self.metrics:
                self.metrics.increment_counter(
                    "manual_override_suggested", 
                    labels={"tier": initial_tier, "reason": "low_confidence"}
                )
        else:
            print(f"[MAIN_AGENT] ✓ High confidence - proceeding with automatic routing\n")
            if self.metrics:
                self.metrics.increment_counter(
                    "automatic_routing_executed",
                    labels={"tier": initial_tier}
                )

        current_tier = initial_tier
        current_input = user_input
        iteration = 0
        final_state = None
        previous_state = None

        while iteration < max_iterations:
            iteration += 1
            print(f"\n{'-'*80}")
            print(f"[MAIN_AGENT] Iteration {iteration}: Tier {current_tier}")
            print(f"{'-'*80}")

            # Execute tier with retry
            state = self.execute_tier_with_retry(
                current_tier, current_input, previous_state
            )
            final_state = state

            # Add decision trace
            state.add_decision(
                "tier_execution",
                {
                    "tier": current_tier,
                    "status": state.status,
                    "iteration": iteration,
                    "retry_count": state.retry_count,
                },
            )

            print(f"[MAIN_AGENT] Result: {state.status}")
            print(f"[MAIN_AGENT] Summary: {state.logic_summary[:100]}...")
            print(f"[MAIN_AGENT] Confidence: {state.confidence:.2f}")

            # Create decision context
            context = create_decision_context(
                tier=current_tier,
                status=state.status,
                user_input=current_input,
                payload={"next_node": state.next_node},
                retry_count=state.retry_count,
                execution_time_ms=state.execution_time_ms,
            )

            # Evaluate routing decision
            decision = self.evaluate_routing_decision(context)

            # Add routing decision to trace
            state.add_decision("routing", decision.to_dict())

            # Check if human approval required - apply policy-based auto-decision
            if decision.requires_human_approval:
                print(
                    f"[MAIN_AGENT] ⚠️ Human approval requested (confidence: {decision.confidence:.2f})"
                )

                # Policy-based auto-decision: proceed automatically if confidence > 0.7
                if decision.confidence >= 0.7:
                    print(
                        f"[MAIN_AGENT] ✓ Auto-approving (confidence {decision.confidence:.2f} >= 0.7 threshold)"
                    )
                    print(f"[MAIN_AGENT] Reasoning: {decision.reasoning}")

                    # Record auto-approval in metrics
                    if self.metrics:
                        self.metrics.increment_counter(
                            "decision_automated_total", labels={"tier": current_tier}
                        )
                        self.metrics.set_gauge(
                            "routing_confidence",
                            decision.confidence,
                            labels={"tier": current_tier},
                        )

                    # Continue with automatic execution (skip human approval)
                    decision.requires_human_approval = False
                else:
                    print(
                        f"[MAIN_AGENT] ⚠️ Confidence too low ({decision.confidence:.2f} < 0.7), attempting system retry..."
                    )

                    # Attempt system retry cycles before entering async wait
                    alt_state = self.attempt_system_tasks_before_human_wait(
                        context, current_tier, iteration, max_iterations
                    )

                    if alt_state:
                        # Alternative path succeeded, continue with that state
                        print(f"[MAIN_AGENT] ✓ Alternative system path succeeded")
                        final_state = alt_state
                        previous_state = alt_state

                        # Determine next tier from alternative state
                        next_tier = alt_state.next_node
                        if next_tier and next_tier != "STOP":
                            current_tier = next_tier
                            current_input = f"Continue from Tier {alt_state.tier}: {alt_state.logic_summary}"
                            print(f"[MAIN_AGENT] → Next: Tier {current_tier}")
                            continue
                        else:
                            print(f"[MAIN_AGENT] ✓ Execution chain complete")
                            break

                    # No alternative succeeded - enter async wait (minimized to last resort)
                    decision_id = f"{self.current_session_id}_{iteration}"
                    self.human_decision_queue.enqueue(decision_id, context)
                    self.awaiting_decision = True
                    self.pending_decision_context = context

                    print(
                        f"[MAIN_AGENT] → Queued for async human decision (ID: {decision_id})"
                    )
                    print(f"[MAIN_AGENT] → Continuing with non-blocking tasks...")

                    # In production, this would continue processing other tasks
                    # For now, we break and return current state
                    break

            # Determine next tier
            next_tier = decision.next_tier or state.next_node

            if next_tier and next_tier != "STOP":
                current_tier = next_tier
                current_input = (
                    f"Continue from Tier {state.tier}: {state.logic_summary}"
                )
                previous_state = state

                print(f"[MAIN_AGENT] → Next: Tier {current_tier}")
            else:
                print(f"[MAIN_AGENT] ✓ Execution chain complete")
                break

        if iteration >= max_iterations:
            print(f"[MAIN_AGENT] ⚠️ Max iterations ({max_iterations}) reached")

        print(f"\n{'='*80}")
        print(f"[MAIN_AGENT] Session Complete: {self.current_session_id}")
        print(f"[MAIN_AGENT] Total Iterations: {iteration}")
        print(
            f"[MAIN_AGENT] Final Status: {final_state.status if final_state else 'UNKNOWN'}"
        )
        print(f"{'='*80}\n")

        return final_state or AgentState.create_failure(
            tier="MAIN_AGENT",
            error_msg="No valid state returned",
            logic_summary="Execution chain produced no result",
        )

    def print_execution_summary(self):
        """Print execution history summary"""
        print("\n" + "=" * 80)
        print("EXECUTION SUMMARY")
        print("=" * 80)

        for i, entry in enumerate(self.execution_history, 1):
            print(
                f"{i}. Tier {entry['tier']} → {entry['status']} "
                f"(Confidence: {entry.get('confidence', 0):.2f}, "
                f"Retries: {entry.get('retry_count', 0)}, "
                f"Next: {entry.get('next_node') or 'STOP'})"
            )

        print("=" * 80 + "\n")

    def export_metrics(self, format: str = "json") -> str:
        """
        Export collected metrics.

        Args:
            format: Export format ("json" or "prometheus")

        Returns:
            Formatted metrics string
        """
        if not self.metrics:
            return "{}"

        if format == "json":
            return json.dumps(self.metrics.export_json(), indent=2)
        elif format == "prometheus":
            return self.metrics.export_prometheus()
        else:
            return "{}"


def main():
    """CLI entry point"""
    import sys
    import os

    if len(sys.argv) < 2:
        print(
            "Usage: python main_agent.py '<user_input>' [workspace_root] [redis_host] [redis_port]"
        )
        print("Example: python main_agent.py 'Create a work plan' . localhost 6379")
        sys.exit(1)

    user_input = sys.argv[1]
    workspace_root = sys.argv[2] if len(sys.argv) > 2 else "."
    redis_host = (
        sys.argv[3] if len(sys.argv) > 3 else os.getenv("REDIS_HOST", "localhost")
    )
    redis_port = (
        int(sys.argv[4]) if len(sys.argv) > 4 else int(os.getenv("REDIS_PORT", "6379"))
    )

    # Create agent with Redis configuration
    agent = MainAgent(
        workspace_root=workspace_root,
        enable_decision_engine=True,
        enable_circuit_breaker=True,
        enable_metrics=True,
        redis_host=redis_host,
        redis_port=redis_port,
    )

    # Execute
    final_state = agent.route_and_execute(user_input)

    # Print summary
    agent.print_execution_summary()

    # Print metrics
    print("\n" + "=" * 80)
    print("METRICS SUMMARY")
    print("=" * 80)
    print(agent.export_metrics(format="json"))
    print("=" * 80 + "\n")

    # Emit final state
    print("\n" + "=" * 80)
    print("FINAL AGENT STATE")
    print("=" * 80)
    final_state.emit()

def send_vibe_log(tier, message, confidence=1.0):
    try:
        url = "http://127.0.0.1:18989/log"
        payload = {"tier": tier, "message": message, "confidence": confidence}
        requests.post(url, json=payload, timeout=0.1) # 실행 속도에 지지 않도록 타임아웃 최소화
    except:
        pass # 모니터링 프로그램이 꺼져 있어도 에이전트는 계속 작동해야 함

if __name__ == "__main__":
    main()
