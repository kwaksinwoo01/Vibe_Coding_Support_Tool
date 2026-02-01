"""
test_feedback_loading.py

Tests for feedback loading functionality from closed GitHub issues.

Tests cover:
1. Loading feedback from closed issues
2. Parsing feedback data structure
3. Generating feedback summaries
4. Integration with D_Issue_Analysis_Flow.py
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import sys
from pathlib import Path

# Add parent directory to path for imports
tool_root = Path(__file__).parent.parent
sys.path.insert(0, str(tool_root))

from common.github_reporter import GitHubReporter


class TestFeedbackLoading:
    """Test feedback loading from closed GitHub issues"""
    
    @patch('github.Github')
    def test_load_feedback_from_closed_issues_success(self, mock_github):
        """Test successful loading of feedback from closed issues"""
        # Setup mock GitHub client
        mock_client = Mock()
        mock_repo = Mock()
        mock_github.return_value = mock_client
        mock_client.get_repo.return_value = mock_repo
        
        # Create mock issues
        mock_issue1 = Mock()
        mock_issue1.number = 1
        mock_issue1.title = "[Agent-Self-Report] Low Confidence Decision in Node D"
        mock_issue1.body = "Confidence Score: 55% (threshold: 70%)\n\nSome details..."
        mock_issue1.created_at = datetime(2026, 1, 20)
        mock_issue1.closed_at = datetime(2026, 1, 21)
        mock_issue1.html_url = "https://github.com/owner/repo/issues/1"
        mock_issue1.labels = [Mock(name="agent-self-report"), Mock(name="low-confidence")]
        
        # Mock user (not a bot)
        mock_user = Mock()
        mock_user.type = "User"
        mock_user.login = "testuser"
        
        # Mock comment
        mock_comment = Mock()
        mock_comment.user = mock_user
        mock_comment.body = "The classification was correct. Good job!"
        mock_issue1.get_comments.return_value = [mock_comment]
        
        mock_issue2 = Mock()
        mock_issue2.number = 2
        mock_issue2.title = "[Agent-Self-Report] Unclear Logic in Node F"
        mock_issue2.body = "Classification attempted: True\nConfidence: 0.45"
        mock_issue2.created_at = datetime(2026, 1, 19)
        mock_issue2.closed_at = datetime(2026, 1, 20)
        mock_issue2.html_url = "https://github.com/owner/repo/issues/2"
        mock_issue2.labels = [Mock(name="agent-self-report"), Mock(name="unclear-logic"), Mock(name="wontfix")]
        mock_issue2.get_comments.return_value = []
        
        # Mock get_issues to return our mock issues
        mock_repo.get_issues.return_value = [mock_issue1, mock_issue2]
        
        # Create reporter
        import os
        with patch.dict(os.environ, {
            'GITHUB_TOKEN': 'fake-token',
            'GITHUB_REPOSITORY': 'owner/repo'
        }):
            reporter = GitHubReporter()
            
            # Load feedback
            feedback_list = reporter.load_feedback_from_closed_issues(max_issues=50)
            
            # Verify results
            assert len(feedback_list) == 2
            
            # Check first issue
            assert feedback_list[0]["issue_number"] == 1
            assert feedback_list[0]["node"] == "D"
            assert feedback_list[0]["original_confidence"] == 0.55
            assert "testuser" in feedback_list[0]["user_feedback"]
            assert "Good job" in feedback_list[0]["user_feedback"]
            assert feedback_list[0]["resolution"] == "resolved"
            
            # Check second issue
            assert feedback_list[1]["issue_number"] == 2
            assert feedback_list[1]["node"] == "F"
            assert feedback_list[1]["original_confidence"] == 0.45
            assert feedback_list[1]["resolution"] == "dismissed"  # has wontfix label
    
    @patch('github.Github')
    def test_load_feedback_filters_bot_comments(self, mock_github):
        """Test that bot comments are filtered out"""
        # Setup mock
        mock_client = Mock()
        mock_repo = Mock()
        mock_github.return_value = mock_client
        mock_client.get_repo.return_value = mock_repo
        
        mock_issue = Mock()
        mock_issue.number = 1
        mock_issue.title = "[Agent-Self-Report] Test"
        mock_issue.body = "Test body"
        mock_issue.created_at = datetime(2026, 1, 20)
        mock_issue.closed_at = datetime(2026, 1, 21)
        mock_issue.html_url = "https://github.com/owner/repo/issues/1"
        mock_issue.labels = [Mock(name="agent-self-report")]
        
        # Mock bot user
        mock_bot_user = Mock()
        mock_bot_user.type = "Bot"
        mock_bot_user.login = "github-actions[bot]"
        
        # Mock human user
        mock_human_user = Mock()
        mock_human_user.type = "User"
        mock_human_user.login = "human"
        
        # Mock comments
        bot_comment = Mock()
        bot_comment.user = mock_bot_user
        bot_comment.body = "Automated comment"
        
        human_comment = Mock()
        human_comment.user = mock_human_user
        human_comment.body = "Human feedback"
        
        mock_issue.get_comments.return_value = [bot_comment, human_comment]
        mock_repo.get_issues.return_value = [mock_issue]
        
        import os
        with patch.dict(os.environ, {
            'GITHUB_TOKEN': 'fake-token',
            'GITHUB_REPOSITORY': 'owner/repo'
        }):
            reporter = GitHubReporter()
            feedback_list = reporter.load_feedback_from_closed_issues()
            
            # Verify bot comment was filtered out
            assert len(feedback_list) == 1
            assert "Automated comment" not in feedback_list[0]["user_feedback"]
            assert "Human feedback" in feedback_list[0]["user_feedback"]
    
    @patch('github.Github')
    def test_load_feedback_disabled_reporter(self, mock_github):
        """Test that disabled reporter returns empty list"""
        reporter = GitHubReporter(enabled=False)
        
        feedback_list = reporter.load_feedback_from_closed_issues()
        
        assert feedback_list == []
    
    @patch('github.Github')
    def test_load_feedback_respects_max_issues(self, mock_github):
        """Test that max_issues limit is respected"""
        # Setup mock
        mock_client = Mock()
        mock_repo = Mock()
        mock_github.return_value = mock_client
        mock_client.get_repo.return_value = mock_repo
        
        # Create 10 mock issues
        mock_issues = []
        for i in range(10):
            mock_issue = Mock()
            mock_issue.number = i + 1
            mock_issue.title = f"[Agent-Self-Report] Issue {i+1}"
            mock_issue.body = "Test"
            mock_issue.created_at = datetime(2026, 1, 20)
            mock_issue.closed_at = datetime(2026, 1, 21)
            mock_issue.html_url = f"https://github.com/owner/repo/issues/{i+1}"
            mock_issue.labels = [Mock(name="agent-self-report")]
            mock_issue.get_comments.return_value = []
            mock_issues.append(mock_issue)
        
        mock_repo.get_issues.return_value = mock_issues
        
        import os
        with patch.dict(os.environ, {
            'GITHUB_TOKEN': 'fake-token',
            'GITHUB_REPOSITORY': 'owner/repo'
        }):
            reporter = GitHubReporter()
            
            # Load only 5 issues
            feedback_list = reporter.load_feedback_from_closed_issues(max_issues=5)
            
            assert len(feedback_list) == 5


class TestFeedbackSummary:
    """Test feedback summary generation"""
    
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
        assert "55.00%" in summary or "55%" in summary
        assert "resolved" in summary
        assert "dismissed" in summary
    
    def test_get_feedback_summary_groups_by_node(self):
        """Test that summary groups issues by node"""
        reporter = GitHubReporter(enabled=False)
        
        feedback_list = [
            {"issue_number": 1, "node": "D", "title": "Test 1", "original_confidence": 0.5, 
             "user_feedback": "Test", "resolution": "resolved", "url": "url1"},
            {"issue_number": 2, "node": "D", "title": "Test 2", "original_confidence": 0.6,
             "user_feedback": "Test", "resolution": "resolved", "url": "url2"},
            {"issue_number": 3, "node": "F", "title": "Test 3", "original_confidence": 0.4,
             "user_feedback": "Test", "resolution": "resolved", "url": "url3"},
        ]
        
        summary = reporter.get_feedback_summary(feedback_list)
        
        # Should show node groupings
        assert "Node D (2 issues)" in summary
        assert "Node F (1 issues)" in summary

