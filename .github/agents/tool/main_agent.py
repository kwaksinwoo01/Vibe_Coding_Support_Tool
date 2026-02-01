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
1. User Input -> Classification (via Tier F or keyword matching)
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
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
from queue import Queue
from threading import Lock

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

from models.core.reporting_models import (
    IssueClassification,
    ResolutionStrategy,
    RoutingInfo,
)
from common.github_reporter import get_github_reporter

# Import routing engine (extracted from inner classes)
from core.routing_engine import (
    RoutingEngine,
    IRoutingStrategy,
    KeywordRoutingStrategy,
    MetricsBasedRoutingStrategy,
    RoutingValidator,
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
        self.on_resolve = None

    def enqueue(self, decision_id: str, context: DecisionContext):
        """Add a decision to the queue"""
        with self._lock:
            self.pending_decisions[decision_id] = context
            self.queue.put(decision_id)
            print(f"[HUMAN_QUEUE] Enqueued decision {decision_id}")

    def dequeue(self) -> Optional[str]:
        """Get next decision from queue (non-blocking), skipping resolved entries"""
        while True:
            try:
                decision_id = self.queue.get_nowait()
            except:
                return None

            with self._lock:
                # If still pending, return it; otherwise skip stale id
                if decision_id in self.pending_decisions:
                    return decision_id
                else:
                    # stale/already resolved - continue to next
                    continue

    def resolve(self, decision_id: str, decision_data: Dict[str, Any]) -> bool:
        """
        Mark a decision as resolved.

        Behavior:
        - Attach decision_data into the DecisionContext.metadata['human_decision']
        - Add resolved timestamp and optional audit info
        - Remove from pending_decisions
        - Call on_resolve(decision_id, context) if callback provided
        - Return True if resolved, False if not found
        """
        with self._lock:
            ctx = self.pending_decisions.get(decision_id)
            if not ctx:
                print(f"[HUMAN_QUEUE] Resolve requested for unknown decision {decision_id}")
                return False

            # Ensure metadata exists
            meta = getattr(ctx, "metadata", None)
            if meta is None:
                ctx.metadata = {}

            ctx.metadata["human_decision"] = decision_data
            ctx.metadata["resolved_at"] = datetime.now().isoformat()
            # Optionally store who resolved it, reason, etc.
            ctx.metadata["resolved_by"] = decision_data.get("user", decision_data.get("resolved_by", "human_api"))

            # Remove from pending list
            del self.pending_decisions[decision_id]
            print(f"[HUMAN_QUEUE] Resolved decision {decision_id}")

        # Call callback outside lock to avoid deadlocks
        if callable(self.on_resolve):
            try:
                self.on_resolve(decision_id, ctx)
            except Exception as e:
                print(f"[HUMAN_QUEUE] on_resolve callback failed for {decision_id}: {e}")

        return True

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
        
        # Multi-tier routing: Store alternative tiers with valid confidence
        self._alternative_tiers: List[Tuple[str, float]] = []

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
        # Register callback to be invoked when a human decision is resolved
        self.human_decision_queue.on_resolve = self._on_human_decision_resolved
        self.human_retry_max_cycles: int = 2  # Max retry cycles before async wait

        # Routing engine (integrated from routing_engine.py for centralized orchestration)
        self.routing_engine = RoutingEngine(
            workspace_root=workspace_root,
            metrics_collector=self.metrics,
            github_reporter=get_github_reporter(),
            enable_metrics=enable_metrics,
            execution_history=self.execution_history,
        )

    def shutdown(self):
        """Shutdown the agent and cleanup resources"""
        print("[MAIN_AGENT] Shutting down...")
        if self.redis_client:
            try:
                self.redis_client.close()
                print("[MAIN_AGENT] Redis connection closed")
            except Exception as e:
                print(f"[MAIN_AGENT] Error closing Redis: {e}")
        print("[MAIN_AGENT] Shutdown complete")

    # ========================================================================
    # Routing Strategy Interface and Implementations
    # ========================================================================
    
    def decide_routing(self, tier: str, result: Dict[str, Any]) -> Optional[str]:
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

    def classify_input(self, user_input: str) -> Tuple[str, float]:
        """
        Classify user input with INDEPENDENT confidence scoring for each tier.
        
        **New Multi-Evaluation Approach**:
        - Each tier evaluates independently with 0.0~1.0 confidence (NOT competitive distribution)
        - Returns primary tier with highest confidence
        - Stores ALL tiers with valid confidence (>= 0.4) for sequential routing
        
        Returns: (primary_tier, primary_confidence)
        Side Effect: Sets self._alternative_tiers for sequential routing
        """
        user_input_lower = user_input.lower()
        
        # Enhanced keyword mapping with INDEPENDENT scoring (not competitive)
        tier_keywords = {
            "A": {
                "keywords": [
                    "create", "make", "new", "plan", "wpd", "work plan",
                    "작업 계획", "생성", "작성", "문서 생성"
                ],
                "negative": ["edit", "modify", "change", "execute", "perform", "run", "save", "error", "debug"],
                "max_score": 10.0,  # Independent max score
            },
            "B": {
                "keywords": [
                    "execute", "perform", "run", "implement", "do", "fulfill",
                    "실행", "수행", "실행하기", "진행", "완료",
                    "execute the plan", "perform plan", "run task"
                ],
                "negative": ["create", "plan", "edit", "error", "debug"],
                "max_score": 10.0,
            },
            "C": {
                "keywords": [
                    "edit", "modify", "change", "update", "alter", "adjust",
                    "수정", "변경", "편집", "업데이트", "조정",
                    "edit plan", "modify task", "change task",
                    # Document correction keywords (HIGH PRIORITY)
                    "incorrectly created", "wrong document", "should merge",
                    "잘못 생성", "문서 병합", "경로 수정", "incorrectly generated"
                ],
                "negative": ["create new", "execute", "run"],
                "max_score": 12.0,  # Higher max for document correction
            },
            "D": {
                "keywords": [
                    "error", "bug", "issue", "problem", "debug", "fix",
                    "not working", "broken", "failed", "failure",
                    "오류", "버그", "문제", "해결", "디버그",
                    "error handling", "debug issue",
                    # Document ANALYSIS keywords (not correction)
                    "analyze document", "check document", "validate",
                    "문서 분석", "검증"
                ],
                "negative": ["create new", "execute"],
                "max_score": 10.0,
            },
            "E": {
                "keywords": [
                    "save", "mapping", "relationship", "organize",
                    "저장", "매핑", "관계", "정리",
                    "save changes", "update mapping", "document management"
                ],
                "negative": ["create", "execute", "error"],
                "max_score": 8.0,
            },
            "F": {
                "keywords": [],  # Fallback - no specific keywords
                "negative": [],
                "max_score": 3.0,
            },
        }
        
        # INDEPENDENT EVALUATION: Each tier gets 0.0~1.0 independently
        independent_scores: Dict[str, float] = {}
        
        for tier, tier_config in tier_keywords.items():
            raw_score = 0.0
            keywords = tier_config["keywords"]
            negative = tier_config["negative"]
            max_score = tier_config["max_score"]
            
            # Positive keyword matching (1.0 per keyword)
            for keyword in keywords:
                if keyword in user_input_lower:
                    raw_score += 1.0
            
            # Negative keyword matching (penalize -0.5 per negative)
            for neg_keyword in negative:
                if neg_keyword in user_input_lower:
                    raw_score -= 0.5
            
            # Context-specific bonuses (phrase matching)
            if tier == "B" and "execute" in user_input_lower and "plan" in user_input_lower:
                raw_score += 2.0
            elif tier == "C":
                # HIGH PRIORITY: Document incorrectly created/wrong path/merge needed
                if ("incorrectly" in user_input_lower or "잘못" in user_input_lower) and \
                   ("document" in user_input_lower or "문서" in user_input_lower or "generated" in user_input_lower or "created" in user_input_lower):
                    raw_score += 4.0  # STRONG signal for Tier C
                if ("merge" in user_input_lower or "병합" in user_input_lower) and \
                   ("document" in user_input_lower or "문서" in user_input_lower):
                    raw_score += 3.0
                if "wrong directory" in user_input_lower or "wrong path" in user_input_lower or "잘못된 경로" in user_input_lower:
                    raw_score += 3.0
                if "should be in" in user_input_lower or "should merge" in user_input_lower:
                    raw_score += 2.5
            elif tier == "D":
                # Document analysis (NOT correction) - should score LOWER than C for correction tasks
                if ("error" in user_input_lower or "debug" in user_input_lower):
                    raw_score += 1.5
                # If it's document ANALYSIS (not correction), give moderate score
                if ("document" in user_input_lower or "문서" in user_input_lower) and \
                   not ("incorrectly" in user_input_lower or "merge" in user_input_lower or "wrong" in user_input_lower):
                    raw_score += 1.0
            
            # Normalize to 0.0~1.0 using tier-specific max_score
            normalized_score = min(1.0, max(0.0, raw_score / max_score))
            independent_scores[tier] = normalized_score
        
        # Find primary tier (highest confidence)
        primary_tier = max(independent_scores.keys(), key=lambda k: independent_scores[k])
        primary_confidence = independent_scores[primary_tier]
        
        # Find ALL alternative tiers with valid confidence (>= 0.4)
        VALID_THRESHOLD = 0.4
        valid_tiers = [
            (tier, conf) for tier, conf in independent_scores.items()
            if conf >= VALID_THRESHOLD and tier != primary_tier
        ]
        
        # Sort alternatives by confidence (descending)
        valid_tiers.sort(key=lambda x: x[1], reverse=True)
        
        # Store alternatives for sequential routing
        self._alternative_tiers = valid_tiers
        
        # Fallback to Tier F if primary confidence too low
        if primary_confidence < 0.3:
            primary_tier = "F"
            primary_confidence = independent_scores.get("F", 0.3)
            self._alternative_tiers = []  # Clear alternatives
        
        print(f"[CLASSIFY] Input: '{user_input}' -> Tier {primary_tier} (confidence: {primary_confidence:.2f})")
        print(f"[CLASSIFY] Independent Scores: {independent_scores}")
        if self._alternative_tiers:
            alt_str = ", ".join([f"{t}({c:.2f})" for t, c in self._alternative_tiers])
            print(f"[CLASSIFY] Alternative Tiers (>={VALID_THRESHOLD}): {alt_str}")
        
        return primary_tier, primary_confidence

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

                    print(f"[MAIN_AGENT] Circuit breaker OPEN for Tier {tier}")

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
                        f"[MAIN_AGENT]   -> Action: {auto_resolve_details.get('action', 'N/A')}"
                    )
                    print(
                        f"[MAIN_AGENT]   -> Target: {auto_resolve_details.get('target_file', 'N/A')}"
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
                    f"[MAIN_AGENT]   -> Action: {auto_resolve_details.get('action', 'N/A')}"
                )
                print(
                    f"[MAIN_AGENT]   -> Target file: {auto_resolve_details.get('target_file', 'N/A')}"
                )
                print(
                    f"[MAIN_AGENT]   -> Confidence: {auto_resolve_details.get('confidence_level', 'N/A')}"
                )
                print(
                    f"[MAIN_AGENT]   -> Estimated effort: {auto_resolve_details.get('estimated_effort', 'N/A')}"
                )

                # Force routing to Tier C for automatic resolution (destructive change allowed)
                decision.next_tier = "C"
                decision.confidence = 0.95  # High confidence for auto-resolve
                decision.reasoning = (
                    f"Auto-resolve chain: D detected fix-capable issue. "
                    f"Routing to C for '{auto_resolve_details.get('action')}' "
                    f"on {auto_resolve_details.get('target_file', 'unknown file')}. "
                    f"Chain: D -> C -> B (automatic re-execution)"
                )

                # Record auto-resolve in metrics (using existing methods)
                if self.metrics:
                    self.metrics.increment_counter(
                        "auto_resolve_triggered_total", labels={"tier": "D"}
                    )
                    self.metrics.set_gauge(
                        "auto_resolve_confidence", 0.95, labels={"tier": "D"}
                    )

                print(f"[MAIN_AGENT] [OK] Forced routing: D → C (auto-resolve chain)")

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
        
        Enhanced: Prioritize classification-based alternatives from self._alternative_tiers
        
        Args:
            current_tier: Current tier requiring human approval
            context: Decision context

        Returns:
            List of alternative tier names to try (prioritized by classification confidence)
        """
        # PRIORITY 1: Use classification-based alternatives (from multi-evaluation)
        classification_alternatives = []
        if hasattr(self, '_alternative_tiers') and self._alternative_tiers:
            # Extract tier names from (tier, confidence) tuples
            classification_alternatives = [tier for tier, conf in self._alternative_tiers]
            print(f"[ALTERNATIVE_ROUTING] Using classification-based alternatives: {classification_alternatives}")
        
        # PRIORITY 2: Fallback to dependency-based alternatives
        tier_alternatives = {
            "A": ["E", "F"],  # If A needs approval, try E or F first
            "B": ["E", "D"],  # If B needs approval, try E or D
            "C": ["E", "F"],  # If C needs approval, try E or F
            "D": ["F", "E"],  # If D needs approval, try F or E
            "E": ["F"],  # If E needs approval, try F
            "F": [],  # F has no alternatives
        }

        dependency_alternatives = tier_alternatives.get(current_tier, [])
        
        # Combine: classification first, then dependency-based (avoid duplicates)
        combined = classification_alternatives + [t for t in dependency_alternatives if t not in classification_alternatives]

        # Filter out tiers with open circuit breakers
        available = [
            tier for tier in combined if not self.is_circuit_breaker_open(tier)
        ]
        
        print(f"[ALTERNATIVE_ROUTING] Available alternatives (after circuit breaker filter): {available}")

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

    def _on_human_decision_resolved(self, decision_id: str, context: DecisionContext):
        """Callback invoked when a human decision is resolved."""
        decision_data = context.metadata.get("human_decision", {})
        if not decision_data:
            print(f"[MAIN_AGENT] Resolved {decision_id} but no decision payload found")
            return

        # Convert human decision to RoutingDecision via existing handler
        routing_decision = self.handle_human_decision(decision_data)

        # Store result in context for audit/trace
        try:
            context.metadata["_resolved_decision"] = routing_decision.to_dict()
        except Exception:
            context.metadata["_resolved_decision"] = {
                "next_tier": routing_decision.next_tier,
                "confidence": getattr(routing_decision, "confidence", None),
            }

        # If this was the current awaiting decision, clear awaiting state
        if self.awaiting_decision and self.pending_decision_context == context:
            self.awaiting_decision = False
            self.pending_decision_context = None
            print(f"[MAIN_AGENT] Human decision applied for {decision_id} (auto-resume possible)")

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
                print(f"[MAIN_AGENT]  Manual routing forced")
            else:
                print(f"[MAIN_AGENT]  Low confidence ({classification_confidence:.2f} < {manual_confidence_threshold})")
            
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
            print(f"[MAIN_AGENT] [OK] High confidence - proceeding with automatic routing\n")
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
                    f"[MAIN_AGENT]  Human approval requested (confidence: {decision.confidence:.2f})"
                )

                # Policy-based auto-decision: proceed automatically if confidence > 0.7
                if decision.confidence >= 0.7:
                    print(
                        f"[MAIN_AGENT] [OK] Auto-approving (confidence {decision.confidence:.2f} >= 0.7 threshold)"
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
                        f"[MAIN_AGENT]  Confidence too low ({decision.confidence:.2f} < 0.7), attempting system retry..."
                    )

                    # Attempt system retry cycles before entering async wait
                    alt_state = self.attempt_system_tasks_before_human_wait(
                        context, current_tier, iteration, max_iterations
                    )

                    if alt_state:
                        # Alternative path succeeded, continue with that state
                        print(f"[MAIN_AGENT] [OK] Alternative system path succeeded")
                        final_state = alt_state
                        previous_state = alt_state

                        # Determine next tier from alternative state
                        next_tier = alt_state.next_node
                        if next_tier and next_tier != "STOP":
                            current_tier = next_tier
                            current_input = f"Continue from Tier {alt_state.tier}: {alt_state.logic_summary}"
                            print(f"[MAIN_AGENT] -> Next: Tier {current_tier}")
                            continue
                        else:
                            print(f"[MAIN_AGENT] [OK] Execution chain complete")
                            break

                    # No alternative succeeded - enter async wait (minimized to last resort)
                    decision_id = f"{self.current_session_id}_{iteration}"
                    # attach decision id to context for traceability
                    context.decision_id = decision_id
                    self.human_decision_queue.enqueue(decision_id, context)
                    self.awaiting_decision = True
                    self.pending_decision_context = context

                    print(
                        f"[MAIN_AGENT] -> Queued for async human decision (ID: {decision_id})"
                    )
                    print(f"[MAIN_AGENT] -> Continuing with non-blocking tasks...")

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

                print(f"[MAIN_AGENT] -> Next: Tier {current_tier}")
            else:
                print(f"[MAIN_AGENT] [OK] Execution chain complete")
                break

        if iteration >= max_iterations:
            print(f"[MAIN_AGENT] Max iterations ({max_iterations}) reached")

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
                f"{i}. Tier {entry['tier']} -> {entry['status']} "
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


if __name__ == "__main__":
    main()
