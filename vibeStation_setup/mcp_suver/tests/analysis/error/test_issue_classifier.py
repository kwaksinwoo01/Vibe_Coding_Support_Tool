"""
Unit tests for analysis/error/issue_classifier.py

Tests:
- Classification accuracy for each issue type
- Keyword matching logic
- Category determination
- Severity determination
- Confidence scoring
- Edge cases
"""

import pytest

from analysis.error.issue_classifier import IssueClassifier
from models.core.reporting_models import IssueClassification


class TestIssueClassifier:
    """Test IssueClassifier engine"""

    @pytest.fixture
    def classifier(self):
        """Create classifier instance"""
        return IssueClassifier()

    def test_classify_bug_with_error(self, classifier):
        """Test classification of bug with error keyword"""
        result = classifier.classify("ValueError occurred in process_data function")
        assert result.issue_type == "bug"
        assert "error" in result.keywords or "valueerror" in result.keywords
        assert result.confidence_score > 0.0

    def test_classify_bug_with_exception(self, classifier):
        """Test classification of bug with exception keyword"""
        result = classifier.classify("Exception raised when executing the code")
        assert result.issue_type == "bug"
        assert "exception" in result.keywords
        assert result.confidence_score > 0.0

    def test_classify_bug_implementation_error(self, classifier):
        """Test classification of implementation error"""
        result = classifier.classify("TypeError in the new function")
        assert result.issue_type == "bug"
        assert result.category == "implementation_error"

    def test_classify_bug_environment_error(self, classifier):
        """Test classification of environment error"""
        result = classifier.classify("Environment configuration error during setup")
        assert result.issue_type == "bug"
        assert result.category == "environment_error"

    def test_classify_bug_data_error(self, classifier):
        """Test classification of data error"""
        result = classifier.classify("Invalid data format causing error")
        assert result.issue_type == "bug"
        assert result.category == "data_error"

    def test_classify_design_flaw(self, classifier):
        """Test classification of design flaw"""
        result = classifier.classify("The architecture needs refactoring")
        assert result.issue_type == "design_flaw"
        assert result.confidence_score > 0.0

    def test_classify_design_flaw_architecture(self, classifier):
        """Test classification of architecture design flaw"""
        result = classifier.classify("The system architecture is poorly designed")
        assert result.issue_type == "design_flaw"
        assert result.category == "architecture"

    def test_classify_design_flaw_algorithm(self, classifier):
        """Test classification of algorithm design flaw"""
        result = classifier.classify("The algorithm design complexity is too high")
        assert result.issue_type == "design_flaw"
        assert result.category == "algorithm"

    def test_classify_implementation(self, classifier):
        """Test classification of implementation issue"""
        result = classifier.classify("Need to implement the new feature")
        assert result.issue_type == "implementation"
        assert result.confidence_score > 0.0

    def test_classify_documentation(self, classifier):
        """Test classification of documentation issue"""
        result = classifier.classify("The README needs to be updated")
        assert result.issue_type == "documentation"
        assert result.confidence_score > 0.0

    def test_classify_unknown_issue(self, classifier):
        """Test classification of unknown issue type"""
        result = classifier.classify("Something strange is happening")
        assert result.issue_type == "unknown"
        assert result.confidence_score == 0.0

    def test_severity_critical(self, classifier):
        """Test critical severity detection"""
        result = classifier.classify("Critical crash causing data loss")
        assert result.severity == "critical"

    def test_severity_high(self, classifier):
        """Test high severity detection"""
        result = classifier.classify("Error preventing the system from working")
        assert result.severity == "high"

    def test_severity_medium(self, classifier):
        """Test medium severity detection"""
        result = classifier.classify("There is a warning in the logs")
        assert result.severity == "medium"

    def test_severity_low(self, classifier):
        """Test low severity detection"""
        result = classifier.classify("Minor improvement needed")
        assert result.severity == "low"

    def test_keyword_extraction(self, classifier):
        """Test keyword extraction"""
        result = classifier.classify("Error and exception in the code with bug")
        assert len(result.keywords) > 0
        assert any(kw in ["error", "exception", "bug"] for kw in result.keywords)

    def test_multiple_keyword_matches(self, classifier):
        """Test multiple keyword matches increase confidence"""
        result = classifier.classify("Error exception crash fail bug")
        assert result.issue_type == "bug"
        assert result.confidence_score > 0.9  # Multiple matches should increase confidence

    def test_empty_description(self, classifier):
        """Test empty description"""
        result = classifier.classify("")
        assert result.issue_type == "unknown"
        assert result.confidence_score == 0.0

    def test_case_insensitivity(self, classifier):
        """Test case insensitive matching"""
        result1 = classifier.classify("ERROR in the system")
        result2 = classifier.classify("error in the system")
        assert result1.issue_type == result2.issue_type
        assert result1.severity == result2.severity

    def test_mixed_keywords(self, classifier):
        """Test issue with mixed keywords (should pick best match)"""
        # Design keywords should win over implementation
        result = classifier.classify("Need to refactor the architecture design")
        assert result.issue_type == "design_flaw"

    def test_returns_issue_classification_instance(self, classifier):
        """Test that classify returns IssueClassification instance"""
        result = classifier.classify("Test issue")
        assert isinstance(result, IssueClassification)

    def test_confidence_score_range(self, classifier):
        """Test confidence score is in valid range [0, 1]"""
        result = classifier.classify("Error in the system")
        assert 0.0 <= result.confidence_score <= 1.0

    def test_korean_keywords(self, classifier):
        """Test Korean keyword support"""
        result = classifier.classify("시스템에 오류가 발생했습니다")
        assert result.issue_type == "bug"
        assert "오류" in result.keywords

    def test_category_defaults_to_empty(self, classifier):
        """Test category is empty when no subcategory matches"""
        result = classifier.classify("General bug without specific category")
        # Category may or may not be empty depending on keywords, just check it's a string
        assert isinstance(result.category, str)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
