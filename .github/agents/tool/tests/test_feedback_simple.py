"""
test_feedback_simple.py

Simplified tests for feedback loading functionality
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime
import sys
from pathlib import Path

tool_root = Path(__file__).parent.parent
sys.path.insert(0, str(tool_root))

from common.github_reporter import GitHubReporter


class TestFeedbackSummary:
    """Test feedback summary generation (no GitHub API calls needed)"""
    
    def test_get_feedback_summary_empty_list(self):
        """Test summary generation with empty feedback list"""
        reporter = GitHubReporter(enabled=False)
        summary = reporter.get_feedback_summary([])
        assert "No historical feedback available" in summary
    
    def test_get_feedback_summary_with_data(self):
        """Test summary generation with feedback data"""
        reporter = GitHubReporter(enabled=False)
        
        feedback_list = [
            {
                "issue_number": 1,
                "title": "Low Confidence in Node D",
                "node": "D",
                "original_confidence": 0.55,
                "user_feedback": "Classification was correct",
                "resolution": "resolved",
                "url": "https://github.com/test/issues/1"
            },
            {
                "issue_number": 2,
                "title": "Unclear Logic in Node F",
                "node": "F",
                "original_confidence": 0.45,
                "user_feedback": "Need more context",
                "resolution": "dismissed",
                "url": "https://github.com/test/issues/2"
            }
        ]
        
        summary = reporter.get_feedback_summary(feedback_list)
        
        # Verify summary contains key information
        assert "2 issues" in summary
        assert "Node D" in summary
        assert "Node F" in summary
        assert "Issue #1" in summary
        assert "Issue #2" in summary
        assert "resolved" in summary
        assert "dismissed" in summary


class TestFeedbackLoadingLogic:
    """Test feedback loading returns empty when disabled"""
    
    def test_load_feedback_disabled_reporter(self):
        """Test that disabled reporter returns empty list"""
        reporter = GitHubReporter(enabled=False)
        feedback_list = reporter.load_feedback_from_closed_issues()
        assert feedback_list == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
