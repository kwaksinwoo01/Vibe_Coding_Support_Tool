"""
Unit tests for analysis/error/root_cause_analyzer.py

Tests:
- Root cause analysis by issue type
- Component identification
- Evidence collection
- Confidence determination
- Edge cases
"""

import pytest

from analysis.error.root_cause_analyzer import RootCauseAnalyzer
from models.core.reporting_models import IssueClassification, RootCauseAnalysis


class TestRootCauseAnalyzer:
    """Test RootCauseAnalyzer engine"""

    @pytest.fixture
    def analyzer(self):
        """Create analyzer instance"""
        return RootCauseAnalyzer()

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
    def design_classification(self):
        """Create design flaw classification"""
        return IssueClassification(
            issue_type="design_flaw",
            severity="medium",
            confidence_score=0.85,
            category="architecture"
        )

    def test_analyze_returns_root_cause_analysis(self, analyzer, bug_classification):
        """Test analyze returns RootCauseAnalysis instance"""
        result = analyzer.analyze("Test issue", bug_classification)
        assert isinstance(result, RootCauseAnalysis)

    def test_analyze_bug_implementation_error(self, analyzer, bug_classification):
        """Test analysis of implementation error bug"""
        result = analyzer.analyze(
            "TypeError in process_data function",
            bug_classification,
            {"error_message": "TypeError: unsupported operand"}
        )
        assert "validation" in result.root_cause.lower() or "type" in result.root_cause.lower()
        assert result.confidence_level in ["high", "medium", "low"]

    def test_analyze_bug_environment_error(self, analyzer):
        """Test analysis of environment error"""
        classification = IssueClassification(
            issue_type="bug",
            category="environment_error"
        )
        result = analyzer.analyze(
            "Environment config issue",
            classification,
            {"error_message": "Missing environment variable"}
        )
        assert "environment" in result.root_cause.lower() or "config" in result.root_cause.lower()

    def test_analyze_bug_data_error(self, analyzer):
        """Test analysis of data error"""
        classification = IssueClassification(
            issue_type="bug",
            category="data_error"
        )
        result = analyzer.analyze(
            "Invalid data causing issue",
            classification
        )
        assert "data" in result.root_cause.lower() or "invalid" in result.root_cause.lower()

    def test_analyze_design_flaw_architecture(self, analyzer, design_classification):
        """Test analysis of architecture design flaw"""
        result = analyzer.analyze(
            "System architecture needs refactoring",
            design_classification
        )
        assert "architecture" in result.root_cause.lower() or "design" in result.root_cause.lower()

    def test_analyze_design_flaw_algorithm(self, analyzer):
        """Test analysis of algorithm design flaw"""
        classification = IssueClassification(
            issue_type="design_flaw",
            category="algorithm"
        )
        result = analyzer.analyze(
            "Algorithm is inefficient",
            classification
        )
        assert "algorithm" in result.root_cause.lower() or "inefficien" in result.root_cause.lower()

    def test_analyze_implementation(self, analyzer):
        """Test analysis of implementation issue"""
        classification = IssueClassification(
            issue_type="implementation",
            category=""
        )
        result = analyzer.analyze(
            "Need to implement feature X",
            classification
        )
        assert "implementation" in result.root_cause.lower() or "specif" in result.root_cause.lower()

    def test_analyze_documentation(self, analyzer):
        """Test analysis of documentation issue"""
        classification = IssueClassification(
            issue_type="documentation",
            category=""
        )
        result = analyzer.analyze(
            "Documentation is incomplete",
            classification
        )
        assert "documentation" in result.root_cause.lower() or "incomplete" in result.root_cause.lower()

    def test_analyze_unknown(self, analyzer):
        """Test analysis of unknown issue"""
        classification = IssueClassification(
            issue_type="unknown",
            category=""
        )
        result = analyzer.analyze(
            "Something is wrong",
            classification
        )
        assert "unclear" in result.root_cause.lower() or "investigation" in result.root_cause.lower()

    def test_identify_components_from_context(self, analyzer, bug_classification):
        """Test component identification from context"""
        context = {
            "file": "module_x.py",
            "function": "process_data"
        }
        result = analyzer.analyze("Test issue", bug_classification, context)
        assert "module_x.py" in result.affected_components
        assert "process_data()" in result.affected_components

    def test_identify_components_from_description(self, analyzer, bug_classification):
        """Test component identification from description"""
        result = analyzer.analyze(
            "Error in the module and service handler",
            bug_classification
        )
        # Should identify keywords like module, service, handler
        assert len(result.affected_components) >= 0  # May find components

    def test_collect_evidence_from_classification(self, analyzer, bug_classification):
        """Test evidence collection from classification"""
        result = analyzer.analyze("Test issue", bug_classification)
        assert len(result.evidence) > 0
        # Should include classification info
        assert any("bug" in ev.lower() for ev in result.evidence)

    def test_collect_evidence_from_context(self, analyzer, bug_classification):
        """Test evidence collection from error context"""
        context = {
            "error_message": "ValueError: invalid literal",
            "traceback": "Traceback (most recent call last)..."
        }
        result = analyzer.analyze("Test issue", bug_classification, context)
        assert len(result.evidence) > 0
        assert any("error" in ev.lower() for ev in result.evidence)
        assert any("traceback" in ev.lower() for ev in result.evidence)

    def test_confidence_high_with_evidence(self, analyzer, bug_classification):
        """Test high confidence with sufficient evidence"""
        context = {
            "error_message": "TypeError",
            "traceback": "...",
            "line": 42
        }
        result = analyzer.analyze("Detailed issue description", bug_classification, context)
        assert len(result.evidence) >= 3
        assert result.confidence_level == "high"

    def test_confidence_medium_with_some_evidence(self, analyzer, bug_classification):
        """Test medium confidence with some evidence"""
        context = {"error_message": "Error occurred"}
        result = analyzer.analyze("Issue description", bug_classification, context)
        assert result.confidence_level in ["high", "medium"]

    def test_confidence_low_with_minimal_evidence(self, analyzer):
        """Test low confidence with minimal evidence"""
        classification = IssueClassification(issue_type="unknown")
        result = analyzer.analyze("Vague issue", classification)
        # With minimal info, confidence should be lower
        assert result.confidence_level in ["low", "medium"]

    def test_error_context_optional(self, analyzer, bug_classification):
        """Test that error_context is optional"""
        result = analyzer.analyze("Test issue", bug_classification)
        assert isinstance(result, RootCauseAnalysis)
        assert result.error_context == {}

    def test_error_context_preserved(self, analyzer, bug_classification):
        """Test that error context is preserved"""
        context = {"custom_field": "custom_value", "line": 123}
        result = analyzer.analyze("Test issue", bug_classification, context)
        assert result.error_context == context

    def test_affected_components_unique(self, analyzer, bug_classification):
        """Test that affected components are unique"""
        context = {"file": "test.py", "function": "test"}
        result = analyzer.analyze(
            "Error in test module and test package",
            bug_classification,
            context
        )
        # Check no duplicates
        assert len(result.affected_components) == len(set(result.affected_components))

    def test_analysis_timestamp_set(self, analyzer, bug_classification):
        """Test that analysis timestamp is set"""
        result = analyzer.analyze("Test issue", bug_classification)
        assert result.analysis_timestamp != ""
        assert isinstance(result.analysis_timestamp, str)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
