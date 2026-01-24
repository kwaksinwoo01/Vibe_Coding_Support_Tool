"""
Unit tests for analysis/error/routing_engine.py

Tests:
- Initial routing decisions (Rule 1) with Strategy Pattern
- Strategy selection and registration
- Next routing validation (Rule 2)
- Routing confidence calculation
- Clarification questions generation
- Routing rules enforcement
- D→C→B auto-resolve chain scenario
"""

import pytest
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from analysis.error.routing_engine import RoutingEngine
from analysis.error.strategies import (
    RoutingStrategy,
    BugRoutingStrategy,
    DesignFlawRoutingStrategy,
    PerformanceRoutingStrategy,
    FallbackRoutingStrategy
)
from models.core.reporting_models import IssueClassification, ResolutionStrategy, RoutingInfo


class TestRoutingEngineStrategyPattern:
    """Test RoutingEngine with Strategy Pattern"""

    @pytest.fixture
    def engine(self):
        """Create engine instance"""
        return RoutingEngine()

    @pytest.fixture
    def bug_classification(self):
        """Create bug classification"""
        return IssueClassification(
            issue_type="bug",
            severity="high",
            confidence_score=0.9,
            category="implementation_error"
        )

    @pytest.fixture
    def strategy(self):
        """Create resolution strategy"""
        return ResolutionStrategy(
            approach="fix_implementation",
            estimated_effort="medium",
            target_tier="C",
            wpd_grade="L1",
            priority=7
        )

    def test_routing_engine_has_strategies_registered(self, engine):
        """Test routing engine has strategies registered"""
        assert hasattr(engine, '_strategies')
        assert len(engine._strategies) > 0
        
        # Verify all strategy types are registered
        strategy_types = [type(s).__name__ for s in engine._strategies]
        assert 'BugRoutingStrategy' in strategy_types
        assert 'DesignFlawRoutingStrategy' in strategy_types
        assert 'PerformanceRoutingStrategy' in strategy_types
        assert 'FallbackRoutingStrategy' in strategy_types

    def test_strategy_selection_for_bug(self, engine):
        """Test strategy selection for bug issue type"""
        strategy = engine._select_strategy("bug")
        assert isinstance(strategy, BugRoutingStrategy)

    def test_strategy_selection_for_design_flaw(self, engine):
        """Test strategy selection for design flaw"""
        strategy = engine._select_strategy("design_flaw")
        assert isinstance(strategy, DesignFlawRoutingStrategy)

    def test_strategy_selection_for_performance(self, engine):
        """Test strategy selection for performance"""
        strategy = engine._select_strategy("performance")
        assert isinstance(strategy, PerformanceRoutingStrategy)

    def test_strategy_selection_fallback_for_unknown(self, engine):
        """Test fallback strategy for unknown types"""
        strategy = engine._select_strategy("unknown_type")
        assert isinstance(strategy, FallbackRoutingStrategy)

    def test_decide_initial_routing_returns_routing_info(self, engine, bug_classification, strategy):
        """Test decide_initial_routing returns RoutingInfo instance"""
        result = engine.decide_initial_routing(bug_classification, strategy)
        assert isinstance(result, RoutingInfo)

    def test_route_bug_implementation_error_to_c(self, engine, strategy):
        """Test bug with implementation_error routes to C"""
        classification = IssueClassification(
            issue_type="bug",
            category="implementation_error",
            confidence_score=0.9
        )
        result = engine.decide_initial_routing(classification, strategy)
        assert result.target_tier == "C"

    def test_route_bug_environment_error_to_b(self, engine, strategy):
        """Test bug with environment_error routes to B"""
        classification = IssueClassification(
            issue_type="bug",
            category="environment_error",
            confidence_score=0.9
        )
        result = engine.decide_initial_routing(classification, strategy)
        assert result.target_tier == "B"

    def test_route_bug_data_error_to_e(self, engine, strategy):
        """Test bug with data_error routes to E"""
        classification = IssueClassification(
            issue_type="bug",
            category="data_error",
            confidence_score=0.9
        )
        result = engine.decide_initial_routing(classification, strategy)
        assert result.target_tier == "E"

    def test_route_design_flaw_architecture_to_a(self, engine, strategy):
        """Test design_flaw with architecture routes to A"""
        classification = IssueClassification(
            issue_type="design_flaw",
            category="architecture",
            confidence_score=0.85
        )
        result = engine.decide_initial_routing(classification, strategy)
        assert result.target_tier == "A"

    def test_route_design_flaw_algorithm_to_c(self, engine, strategy):
        """Test design_flaw with algorithm routes to C"""
        classification = IssueClassification(
            issue_type="design_flaw",
            category="algorithm",
            confidence_score=0.85
        )
        result = engine.decide_initial_routing(classification, strategy)
        assert result.target_tier == "C"

    def test_route_performance_optimization_to_c(self, engine, strategy):
        """Test performance with optimization routes to C"""
        classification = IssueClassification(
            issue_type="performance",
            category="optimization",
            confidence_score=0.8
        )
        result = engine.decide_initial_routing(classification, strategy)
        assert result.target_tier == "C"

    def test_route_performance_scaling_to_a(self, engine, strategy):
        """Test performance with scaling routes to A"""
        classification = IssueClassification(
            issue_type="performance",
            category="scaling",
            confidence_score=0.8
        )
        result = engine.decide_initial_routing(classification, strategy)
        assert result.target_tier == "A"

    def test_route_implementation_to_c(self, engine, strategy):
        """Test implementation issue routes to C"""
        classification = IssueClassification(
            issue_type="implementation",
            confidence_score=0.8
        )
        result = engine.decide_initial_routing(classification, strategy)
        assert result.target_tier == "C"

    def test_route_documentation_to_e(self, engine, strategy):
        """Test documentation issue routes to E"""
        classification = IssueClassification(
            issue_type="documentation",
            confidence_score=0.9
        )
        result = engine.decide_initial_routing(classification, strategy)
        assert result.target_tier == "E"

    def test_route_unknown_to_f(self, engine, strategy):
        """Test unknown issue routes to F"""
        classification = IssueClassification(
            issue_type="unknown",
            confidence_score=0.5
        )
        result = engine.decide_initial_routing(classification, strategy)
        assert result.target_tier == "F"

    def test_routing_confidence_calculation(self, engine, bug_classification, strategy):
        """Test routing confidence is calculated"""
        result = engine.decide_initial_routing(bug_classification, strategy)
        assert 0.0 <= result.routing_confidence <= 1.0

    def test_high_confidence_no_clarification(self, engine, bug_classification, strategy):
        """Test high confidence doesn't require clarification"""
        bug_classification.confidence_score = 0.95
        result = engine.decide_initial_routing(bug_classification, strategy)
        assert result.requires_clarification is False
        assert len(result.clarification_questions) == 0

    def test_low_confidence_requires_clarification(self, engine, strategy):
        """Test low confidence requires clarification"""
        classification = IssueClassification(
            issue_type="unknown",
            confidence_score=0.6
        )
        result = engine.decide_initial_routing(classification, strategy)
        assert result.routing_confidence < 0.7
        assert result.requires_clarification is True

    def test_clarification_questions_for_unknown(self, engine, strategy):
        """Test clarification questions generated for unknown type"""
        classification = IssueClassification(
            issue_type="unknown",
            confidence_score=0.5
        )
        result = engine.decide_initial_routing(classification, strategy)
        assert len(result.clarification_questions) > 0

    def test_routing_reason_set(self, engine, bug_classification, strategy):
        """Test routing reason is set"""
        result = engine.decide_initial_routing(bug_classification, strategy)
        assert result.routing_reason != ""
        assert isinstance(result.routing_reason, str)

    def test_routing_metadata_set(self, engine, bug_classification, strategy):
        """Test routing metadata is set"""
        result = engine.decide_initial_routing(bug_classification, strategy)
        assert isinstance(result.metadata, dict)
        assert "analysis_type" in result.metadata
        assert "approach" in result.metadata
        assert "priority" in result.metadata

    def test_routing_timestamp_set(self, engine, bug_classification, strategy):
        """Test routing timestamp is set"""
        result = engine.decide_initial_routing(bug_classification, strategy)
        assert result.routing_timestamp != ""


class TestRoutingEngineValidation:
    """Test routing validation (Rule 2)"""
    
    @pytest.fixture
    def engine(self):
        """Create engine instance"""
        return RoutingEngine()

    # Rule 2: Validate next routing tests
    def test_validate_tier_a_success_to_b(self, engine):
        """Test Tier A success can route to B"""
        assert engine.validate_next_routing("A", "B", {"status": "SUCCESS"}) is True

    def test_validate_tier_a_success_to_c(self, engine):
        """Test Tier A success can route to C"""
        assert engine.validate_next_routing("A", "C", {"status": "SUCCESS"}) is True

    def test_validate_tier_a_success_to_e(self, engine):
        """Test Tier A success can route to E"""
        assert engine.validate_next_routing("A", "E", {"status": "SUCCESS"}) is True

    def test_validate_tier_a_success_to_none(self, engine):
        """Test Tier A success can terminate"""
        assert engine.validate_next_routing("A", None, {"status": "SUCCESS"}) is True

    def test_validate_tier_a_failure_to_d(self, engine):
        """Test Tier A failure can route to D"""
        assert engine.validate_next_routing("A", "D", {"status": "FAILURE"}) is True

    def test_validate_tier_a_failure_to_none(self, engine):
        """Test Tier A failure can terminate"""
        assert engine.validate_next_routing("A", None, {"status": "FAILURE"}) is True

    def test_validate_tier_a_success_cannot_route_to_d(self, engine):
        """Test Tier A success cannot route to D"""
        assert engine.validate_next_routing("A", "D", {"status": "SUCCESS"}) is False

    def test_validate_tier_b_success_to_e(self, engine):
        """Test Tier B success can route to E"""
        assert engine.validate_next_routing("B", "E", {"status": "SUCCESS"}) is True

    def test_validate_tier_b_success_to_c(self, engine):
        """Test Tier B success can route to C"""
        assert engine.validate_next_routing("B", "C", {"status": "SUCCESS"}) is True

    def test_validate_tier_b_failure_to_d(self, engine):
        """Test Tier B failure can route to D"""
        assert engine.validate_next_routing("B", "D", {"status": "FAILURE"}) is True

    def test_validate_tier_c_success_to_b(self, engine):
        """Test Tier C success can route to B"""
        assert engine.validate_next_routing("C", "B", {"status": "SUCCESS"}) is True

    def test_validate_tier_c_success_to_e(self, engine):
        """Test Tier C success can route to E"""
        assert engine.validate_next_routing("C", "E", {"status": "SUCCESS"}) is True

    def test_validate_tier_c_failure_to_d(self, engine):
        """Test Tier C failure can route to D"""
        assert engine.validate_next_routing("C", "D", {"status": "FAILURE"}) is True

    def test_validate_tier_e_success_to_none(self, engine):
        """Test Tier E success can only terminate"""
        assert engine.validate_next_routing("E", None, {"status": "SUCCESS"}) is True

    def test_validate_tier_e_success_cannot_route_to_others(self, engine):
        """Test Tier E success cannot route to other tiers"""
        assert engine.validate_next_routing("E", "A", {"status": "SUCCESS"}) is False
        assert engine.validate_next_routing("E", "B", {"status": "SUCCESS"}) is False
        assert engine.validate_next_routing("E", "C", {"status": "SUCCESS"}) is False

    def test_validate_tier_e_failure_to_d(self, engine):
        """Test Tier E failure can route to D"""
        assert engine.validate_next_routing("E", "D", {"status": "FAILURE"}) is True

    def test_validate_tier_f_success_to_any(self, engine):
        """Test Tier F success can route to any tier"""
        for tier in ["A", "B", "C", "D", "E", None]:
            assert engine.validate_next_routing("F", tier, {"status": "SUCCESS"}) is True

    def test_validate_tier_f_failure_to_none(self, engine):
        """Test Tier F failure can only terminate"""
        assert engine.validate_next_routing("F", None, {"status": "FAILURE"}) is True

    def test_validate_invalid_status_defaults_to_failure(self, engine):
        """Test invalid status defaults to failure routing"""
        result = engine.validate_next_routing("A", "D", {"status": "UNKNOWN"})
        assert result is True  # Should use failure routing rules


class TestAutoResolveChain:
    """Test D→C→B auto-resolve chain scenario"""
    
    @pytest.fixture
    def engine(self):
        """Create engine instance"""
        return RoutingEngine()
    
    def test_auto_resolve_chain_d_to_c(self, engine):
        """Test auto-resolve routing from D to C"""
        # Simulate Tier D detecting auto-resolvable bug
        classification = IssueClassification(
            issue_type="bug",
            category="implementation_error",
            confidence_score=0.95,
            severity="medium"
        )
        
        strategy = ResolutionStrategy(
            approach="fix_implementation",
            estimated_effort="low",
            target_tier="C",
            auto_resolve_flag=True,  # Mark as auto-resolvable
            confidence_thresholds={"auto_resolve": 0.85}
        )
        
        routing = engine.decide_initial_routing(classification, strategy)
        
        # Should route to C for automatic fix
        assert routing.target_tier == "C"
        assert routing.routing_confidence >= strategy.confidence_thresholds["auto_resolve"]
        assert strategy.auto_resolve_flag is True
    
    def test_auto_resolve_chain_c_to_b(self, engine):
        """Test auto-resolve routing from C to B after fix"""
        # After C applies fix, should route to B for re-execution
        c_result = {"status": "SUCCESS", "modified_files": ["main.py"]}
        
        # Tier C SUCCESS with modifications should route to B
        assert engine.validate_next_routing("C", "B", c_result) is True
    
    def test_auto_resolve_complete_chain(self, engine):
        """Test complete D→C→B auto-resolve chain"""
        # Step 1: D routes to C
        classification = IssueClassification(
            issue_type="bug",
            category="implementation_error",
            confidence_score=0.95
        )
        
        strategy = ResolutionStrategy(
            approach="fix_implementation",
            estimated_effort="low",
            auto_resolve_flag=True
        )
        
        d_routing = engine.decide_initial_routing(classification, strategy)
        assert d_routing.target_tier == "C"
        
        # Step 2: C routes to B (validation)
        c_result = {"status": "SUCCESS"}
        assert engine.validate_next_routing("C", "B", c_result) is True
        
        # Step 3: B routes to E or completes (validation)
        b_result = {"status": "SUCCESS"}
        assert engine.validate_next_routing("B", "E", b_result) is True
        assert engine.validate_next_routing("B", None, b_result) is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
