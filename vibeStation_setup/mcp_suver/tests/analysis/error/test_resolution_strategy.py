"""
Unit tests for analysis/error/resolution_strategy.py

Tests:
- Strategy creation from analysis results
- Approach determination
- Target tier selection
- WPD grade calculation
- Priority calculation
- Effort estimation
- Dependencies and rollback plans
"""

import pytest

from analysis.error.resolution_strategy import ResolutionStrategyEngine
from models.core.reporting_models import IssueClassification, RootCauseAnalysis, ResolutionStrategy


class TestResolutionStrategyEngine:
    """Test ResolutionStrategyEngine"""

    @pytest.fixture
    def engine(self):
        """Create engine instance"""
        return ResolutionStrategyEngine()

    @pytest.fixture
    def bug_classification(self):
        """Create bug classification"""
        return IssueClassification(
            issue_type="bug",
            severity="high",
            confidence_score=0.9
        )

    @pytest.fixture
    def design_classification(self):
        """Create design flaw classification"""
        return IssueClassification(
            issue_type="design_flaw",
            severity="medium",
            confidence_score=0.85
        )

    @pytest.fixture
    def root_cause(self):
        """Create root cause analysis"""
        return RootCauseAnalysis(
            root_cause="Missing validation",
            affected_components=["module.py"],
            confidence_level="high"
        )

    def test_create_strategy_returns_resolution_strategy(self, engine, bug_classification, root_cause):
        """Test create_strategy returns ResolutionStrategy instance"""
        result = engine.create_strategy(bug_classification, root_cause)
        assert isinstance(result, ResolutionStrategy)

    def test_approach_bug_fix_implementation(self, engine, bug_classification, root_cause):
        """Test approach for bug is fix_implementation"""
        result = engine.create_strategy(bug_classification, root_cause)
        assert result.approach == "fix_implementation"

    def test_approach_design_flaw_refactor(self, engine, design_classification, root_cause):
        """Test approach for design_flaw is refactor_design"""
        result = engine.create_strategy(design_classification, root_cause)
        assert result.approach == "refactor_design"

    def test_approach_implementation(self, engine, root_cause):
        """Test approach for implementation issue"""
        classification = IssueClassification(issue_type="implementation")
        result = engine.create_strategy(classification, root_cause)
        assert result.approach == "improve_implementation"

    def test_approach_documentation(self, engine, root_cause):
        """Test approach for documentation issue"""
        classification = IssueClassification(issue_type="documentation")
        result = engine.create_strategy(classification, root_cause)
        assert result.approach == "update_documentation"

    def test_approach_unknown(self, engine, root_cause):
        """Test approach for unknown issue"""
        classification = IssueClassification(issue_type="unknown")
        result = engine.create_strategy(classification, root_cause)
        assert result.approach == "investigate"

    def test_target_tier_bug_to_c(self, engine, bug_classification, root_cause):
        """Test bug routes to Tier C"""
        result = engine.create_strategy(bug_classification, root_cause)
        assert result.target_tier == "C"

    def test_target_tier_design_to_a(self, engine, design_classification, root_cause):
        """Test design_flaw routes to Tier A"""
        result = engine.create_strategy(design_classification, root_cause)
        assert result.target_tier == "A"

    def test_target_tier_implementation_to_c(self, engine, root_cause):
        """Test implementation routes to Tier C"""
        classification = IssueClassification(issue_type="implementation")
        result = engine.create_strategy(classification, root_cause)
        assert result.target_tier == "C"

    def test_target_tier_documentation_to_e(self, engine, root_cause):
        """Test documentation routes to Tier E"""
        classification = IssueClassification(issue_type="documentation")
        result = engine.create_strategy(classification, root_cause)
        assert result.target_tier == "E"

    def test_target_tier_unknown_to_f(self, engine, root_cause):
        """Test unknown routes to Tier F"""
        classification = IssueClassification(issue_type="unknown")
        result = engine.create_strategy(classification, root_cause)
        assert result.target_tier == "F"

    def test_effort_low_for_few_components(self, engine, root_cause):
        """Test low effort for documentation"""
        classification = IssueClassification(issue_type="documentation")
        result = engine.create_strategy(classification, root_cause)
        assert result.estimated_effort == "low"

    def test_effort_medium_for_moderate_components(self, engine, bug_classification):
        """Test medium effort for bug with 1-2 components"""
        root_cause = RootCauseAnalysis(
            root_cause="Test",
            affected_components=["file1.py", "file2.py"]
        )
        result = engine.create_strategy(bug_classification, root_cause)
        assert result.estimated_effort == "medium"

    def test_effort_high_for_many_components(self, engine, bug_classification):
        """Test high effort for bug with many components"""
        root_cause = RootCauseAnalysis(
            root_cause="Test",
            affected_components=["file1.py", "file2.py", "file3.py"]
        )
        result = engine.create_strategy(bug_classification, root_cause)
        assert result.estimated_effort == "high"

    def test_effort_high_for_refactor(self, engine, design_classification, root_cause):
        """Test high effort for refactor_design"""
        result = engine.create_strategy(design_classification, root_cause)
        assert result.estimated_effort == "high"

    def test_wpd_grade_l0_for_low_effort(self, engine, root_cause):
        """Test WPD grade L0 for low effort"""
        classification = IssueClassification(issue_type="documentation")
        result = engine.create_strategy(classification, root_cause)
        assert result.wpd_grade == "L0"

    def test_wpd_grade_l1_for_medium_effort(self, engine, bug_classification):
        """Test WPD grade L1 for medium effort"""
        root_cause = RootCauseAnalysis(
            root_cause="Test",
            affected_components=["file1.py"]
        )
        result = engine.create_strategy(bug_classification, root_cause)
        assert result.wpd_grade in ["L1", "L2"]

    def test_wpd_grade_l3_for_high_effort(self, engine, design_classification, root_cause):
        """Test WPD grade L3 for high effort refactor"""
        result = engine.create_strategy(design_classification, root_cause)
        assert result.wpd_grade == "L3"

    def test_priority_high_for_critical(self, engine, root_cause):
        """Test high priority for critical severity"""
        classification = IssueClassification(issue_type="bug", severity="critical")
        result = engine.create_strategy(classification, root_cause)
        assert result.priority >= 8

    def test_priority_low_for_low_severity(self, engine, root_cause):
        """Test low priority for low severity"""
        classification = IssueClassification(issue_type="documentation", severity="low")
        result = engine.create_strategy(classification, root_cause)
        assert result.priority <= 4

    def test_priority_in_range(self, engine, bug_classification, root_cause):
        """Test priority is in valid range 1-10"""
        result = engine.create_strategy(bug_classification, root_cause)
        assert 1 <= result.priority <= 10

    def test_dependencies_for_tier_a(self, engine, design_classification, root_cause):
        """Test dependencies for Tier A includes prd_review"""
        result = engine.create_strategy(design_classification, root_cause)
        assert "prd_review" in result.dependencies

    def test_dependencies_for_tier_c(self, engine, bug_classification, root_cause):
        """Test dependencies for Tier C includes code_review"""
        result = engine.create_strategy(bug_classification, root_cause)
        assert "code_review" in result.dependencies

    def test_dependencies_for_tier_e(self, engine, root_cause):
        """Test dependencies for Tier E includes doc_review"""
        classification = IssueClassification(issue_type="documentation")
        result = engine.create_strategy(classification, root_cause)
        assert "doc_review" in result.dependencies

    def test_rollback_plan_set(self, engine, bug_classification, root_cause):
        """Test rollback plan is set"""
        result = engine.create_strategy(bug_classification, root_cause)
        assert result.rollback_plan != ""
        assert "revert" in result.rollback_plan.lower()

    def test_duration_low_for_low_effort(self, engine, root_cause):
        """Test duration for low effort"""
        classification = IssueClassification(issue_type="documentation")
        result = engine.create_strategy(classification, root_cause)
        assert result.estimated_duration_hours == 1.0

    def test_duration_medium_for_medium_effort(self, engine, bug_classification):
        """Test duration for medium effort"""
        root_cause = RootCauseAnalysis(
            root_cause="Test",
            affected_components=["file1.py"]
        )
        result = engine.create_strategy(bug_classification, root_cause)
        assert result.estimated_duration_hours == 4.0

    def test_duration_high_for_high_effort(self, engine, design_classification, root_cause):
        """Test duration for high effort"""
        result = engine.create_strategy(design_classification, root_cause)
        assert result.estimated_duration_hours == 8.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
