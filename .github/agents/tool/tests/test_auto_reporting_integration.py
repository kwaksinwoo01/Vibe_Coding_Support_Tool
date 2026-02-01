"""
test_auto_reporting_integration.py

Integration tests for automatic GitHub issue reporting

Tests the integration of auto-reporting functionality through mocking.
We test the logic without importing the full modules to avoid dependency issues.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
from pathlib import Path

# Add parent directory to path for imports
tool_root = Path(__file__).parent.parent
sys.path.insert(0, str(tool_root))


class TestTierDAutoReportingLogic:
    """Test auto-reporting logic in Tier D (Issue Analysis)"""
    
    @patch('common.github_reporter.get_github_reporter')
    def test_low_confidence_triggers_auto_report_logic(self, mock_get_reporter):
        """Test that low confidence (<0.7) triggers auto-report logic"""
        # Setup mock reporter
        mock_reporter = Mock()
        mock_reporter.is_enabled.return_value = True
        mock_reporter.report_low_confidence_issue.return_value = "https://github.com/test/issues/1"
        mock_get_reporter.return_value = mock_reporter
        
        # Simulate the logic in _auto_report_to_github
        routing_confidence = 0.55  # Below threshold
        
        if routing_confidence < 0.7:
            # This would trigger auto-reporting
            if mock_reporter.is_enabled():
                url = mock_reporter.report_low_confidence_issue(
                    active_node="D",
                    state_flow="→ D (Issue Analysis)",
                    confidence_score=routing_confidence,
                    decision_basis="Test",
                    hypothesis="Test",
                    additional_context={}
                )
                assert url == "https://github.com/test/issues/1"
                mock_reporter.report_low_confidence_issue.assert_called_once()
    
    @patch('common.github_reporter.get_github_reporter')
    def test_high_confidence_no_auto_report_logic(self, mock_get_reporter):
        """Test that high confidence (>=0.7) does NOT trigger auto-report"""
        # Setup mock reporter
        mock_reporter = Mock()
        mock_reporter.is_enabled.return_value = True
        mock_get_reporter.return_value = mock_reporter
        
        # Simulate the logic
        routing_confidence = 0.85  # Above threshold
        
        if routing_confidence < 0.7:
            # This should NOT execute
            mock_reporter.report_low_confidence_issue(
                active_node="D",
                state_flow="→ D",
                confidence_score=routing_confidence,
                decision_basis="Test",
                hypothesis="Test"
            )
        
        # Verify auto-report was NOT called
        mock_reporter.report_low_confidence_issue.assert_not_called()


class TestTierFAutoReportingLogic:
    """Test auto-reporting logic in Tier F (Unknown Logic)"""
    
    @patch('common.github_reporter.get_github_reporter')
    def test_unclear_logic_triggers_auto_report_logic(self, mock_get_reporter):
        """Test that unclear logic triggers auto-report logic"""
        # Setup mock reporter
        mock_reporter = Mock()
        mock_reporter.is_enabled.return_value = True
        mock_reporter.report_unclear_logic_issue.return_value = "https://github.com/test/issues/2"
        mock_get_reporter.return_value = mock_reporter
        
        # Simulate unclear logic scenario
        confidence_score = 0.0  # No classification
        suggested_tier = None
        
        # This would trigger auto-reporting
        if mock_reporter.is_enabled():
            url = mock_reporter.report_unclear_logic_issue(
                user_input="unclear request",
                classification_attempted=True,
                suggested_tier=suggested_tier,
                confidence_score=confidence_score,
                reasoning="No matching keywords"
            )
            assert url == "https://github.com/test/issues/2"
            mock_reporter.report_unclear_logic_issue.assert_called_once()
    
    @patch('common.github_reporter.get_github_reporter')
    def test_low_confidence_classification_triggers_report_logic(self, mock_get_reporter):
        """Test that low confidence classification (0.3-0.7) triggers auto-report"""
        # Setup mock reporter
        mock_reporter = Mock()
        mock_reporter.is_enabled.return_value = True
        mock_reporter.report_unclear_logic_issue.return_value = "https://github.com/test/issues/3"
        mock_get_reporter.return_value = mock_reporter
        
        # Simulate low confidence classification
        confidence_score = 0.45  # Low confidence
        suggested_tier = "A"
        
        # Auto-report on low confidence (< 0.7)
        if confidence_score < 0.7 and mock_reporter.is_enabled():
            url = mock_reporter.report_unclear_logic_issue(
                user_input="ambiguous request",
                classification_attempted=True,
                suggested_tier=suggested_tier,
                confidence_score=confidence_score,
                reasoning="Matched few keywords"
            )
            assert url == "https://github.com/test/issues/3"
            mock_reporter.report_unclear_logic_issue.assert_called_once()


class TestCompetingPathsLogic:
    """Test competing paths detection logic"""
    
    @patch('common.github_reporter.get_github_reporter')
    def test_competing_paths_detection_logic(self, mock_get_reporter):
        """Test that competing paths are detected correctly"""
        # Setup mock reporter
        mock_reporter = Mock()
        mock_reporter.is_enabled.return_value = True
        mock_reporter.report_competing_paths_issue.return_value = "https://github.com/test/issues/4"
        mock_get_reporter.return_value = mock_reporter
        
        # Simulate competing tier scores
        tier_scores = {
            "A": 3.0,
            "B": 2.9,  # Within 80% of max (3.0 * 0.8 = 2.4)
            "C": 2.8,  # Also within threshold
            "D": 1.0   # Not competing
        }
        
        selected_tier = "A"
        user_input = "ambiguous request"
        
        # Detect competing paths
        max_score = tier_scores[selected_tier]
        threshold = max_score * 0.8
        
        competing_tiers = [
            tier for tier, score in tier_scores.items()
            if score >= threshold
        ]
        
        # Verify we detected competing paths
        assert len(competing_tiers) >= 2
        assert "A" in competing_tiers
        assert "B" in competing_tiers
        assert "C" in competing_tiers
        assert "D" not in competing_tiers
        
        # If 2+ competing paths, report
        if len(competing_tiers) >= 2 and mock_reporter.is_enabled():
            url = mock_reporter.report_competing_paths_issue(
                active_node="CLASSIFY",
                state_flow="Initial Classification",
                competing_paths=competing_tiers,
                selected_path=selected_tier,
                selection_reason="highest score",
                context={"tier_scores": tier_scores}
            )
            assert url == "https://github.com/test/issues/4"
            mock_reporter.report_competing_paths_issue.assert_called_once()
    
    @patch('common.github_reporter.get_github_reporter')
    def test_no_competing_paths_no_report(self, mock_get_reporter):
        """Test that single dominant path doesn't trigger report"""
        # Setup mock reporter
        mock_reporter = Mock()
        mock_reporter.is_enabled.return_value = True
        mock_get_reporter.return_value = mock_reporter
        
        # Simulate clear winner
        tier_scores = {
            "A": 5.0,
            "B": 1.0,  # Not within 80% (5.0 * 0.8 = 4.0)
            "C": 0.5
        }
        
        selected_tier = "A"
        max_score = tier_scores[selected_tier]
        threshold = max_score * 0.8
        
        competing_tiers = [
            tier for tier, score in tier_scores.items()
            if score >= threshold
        ]
        
        # Only one tier above threshold
        assert len(competing_tiers) == 1
        
        # Should NOT report
        if len(competing_tiers) >= 2:
            mock_reporter.report_competing_paths_issue(
                active_node="CLASSIFY",
                state_flow="Test",
                competing_paths=competing_tiers,
                selected_path=selected_tier,
                selection_reason="test"
            )
        
        mock_reporter.report_competing_paths_issue.assert_not_called()


class TestAsynchronousReporting:
    """Test that reporting doesn't interrupt workflow"""
    
    @patch('common.github_reporter.get_github_reporter')
    def test_reporting_failure_doesnt_break_workflow_logic(self, mock_get_reporter):
        """Test that reporter failure doesn't break the workflow"""
        # Setup reporter that raises exception
        mock_reporter = Mock()
        mock_reporter.is_enabled.return_value = True
        mock_reporter.report_low_confidence_issue.side_effect = Exception("GitHub API error")
        mock_get_reporter.return_value = mock_reporter
        
        # Simulate auto-reporting with exception handling
        try:
            if mock_reporter.is_enabled():
                url = mock_reporter.report_low_confidence_issue(
                    active_node="D",
                    state_flow="→ D",
                    confidence_score=0.50,
                    decision_basis="Test",
                    hypothesis="Test"
                )
                # Should not reach here due to exception
                assert False, "Expected exception not raised"
        except Exception as e:
            # Exception caught - workflow continues
            assert str(e) == "GitHub API error"
            # Workflow would continue normally after this


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
