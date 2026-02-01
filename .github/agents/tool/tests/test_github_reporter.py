"""
test_github_reporter.py

Tests for GitHub auto-reporting functionality

Tests cover:
1. GitHubReporter initialization and configuration
2. Low confidence issue reporting (Trigger 1)
3. Unclear logic issue reporting (Trigger 3)
4. Competing paths issue reporting (Trigger 2)
5. Error handling and fallback behavior
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
tool_root = Path(__file__).parent.parent
sys.path.insert(0, str(tool_root))

from common.github_reporter import GitHubReporter, get_github_reporter


class TestGitHubReporterInitialization:
    """Test GitHubReporter initialization and configuration"""
    
    def test_init_without_pygithub(self):
        """Test that reporter is disabled when PyGithub is not available"""
        with patch('common.github_reporter.GITHUB_AVAILABLE', False):
            reporter = GitHubReporter()
            assert reporter.is_enabled() is False
    
    def test_init_disabled_by_config(self):
        """Test that reporter can be disabled via configuration"""
        reporter = GitHubReporter(enabled=False)
        assert reporter.is_enabled() is False
    
    def test_init_without_token(self):
        """Test that reporter is disabled without GITHUB_TOKEN"""
        with patch.dict(os.environ, {}, clear=True):
            reporter = GitHubReporter()
            assert reporter.is_enabled() is False
    
    def test_init_without_repo(self):
        """Test that reporter is disabled without GITHUB_REPOSITORY"""
        with patch.dict(os.environ, {'GITHUB_TOKEN': 'fake-token'}, clear=True):
            reporter = GitHubReporter()
            assert reporter.is_enabled() is False
    
    @patch('common.github_reporter.Github')
    def test_init_success(self, mock_github):
        """Test successful initialization with proper credentials"""
        mock_client = Mock()
        mock_repo = Mock()
        mock_github.return_value = mock_client
        mock_client.get_repo.return_value = mock_repo
        
        with patch.dict(os.environ, {
            'GITHUB_TOKEN': 'fake-token',
            'GITHUB_REPOSITORY': 'owner/repo'
        }):
            reporter = GitHubReporter()
            assert reporter.is_enabled() is True
            mock_github.assert_called_once_with('fake-token')
            mock_client.get_repo.assert_called_once_with('owner/repo')
    
    @patch('common.github_reporter.Github')
    def test_init_with_parameters(self, mock_github):
        """Test initialization with explicit parameters"""
        mock_client = Mock()
        mock_repo = Mock()
        mock_github.return_value = mock_client
        mock_client.get_repo.return_value = mock_repo
        
        reporter = GitHubReporter(
            github_token='explicit-token',
            repo_name='explicit/repo'
        )
        
        assert reporter.is_enabled() is True
        mock_github.assert_called_once_with('explicit-token')
        mock_client.get_repo.assert_called_once_with('explicit/repo')


class TestLowConfidenceReporting:
    """Test low confidence issue reporting (Trigger 1)"""
    
    @patch('common.github_reporter.Github')
    def test_report_low_confidence_success(self, mock_github):
        """Test successful low confidence issue creation"""
        mock_client = Mock()
        mock_repo = Mock()
        mock_issue = Mock()
        mock_issue.html_url = "https://github.com/owner/repo/issues/1"
        
        mock_github.return_value = mock_client
        mock_client.get_repo.return_value = mock_repo
        mock_repo.create_issue.return_value = mock_issue
        
        with patch.dict(os.environ, {
            'GITHUB_TOKEN': 'fake-token',
            'GITHUB_REPOSITORY': 'owner/repo'
        }):
            reporter = GitHubReporter()
            
            url = reporter.report_low_confidence_issue(
                active_node="D",
                state_flow="A → B → D",
                confidence_score=0.55,
                decision_basis="Insufficient data for analysis",
                hypothesis="Classification may be incorrect"
            )
            
            assert url == "https://github.com/owner/repo/issues/1"
            
            # Verify issue was created with correct parameters
            mock_repo.create_issue.assert_called_once()
            call_args = mock_repo.create_issue.call_args
            
            assert "[Agent-Self-Report]" in call_args.kwargs['title']
            assert "Node D" in call_args.kwargs['title']
            assert "A → B → D" in call_args.kwargs['body']
            # Check that confidence is shown as percentage (e.g., "55.00%" or "55%")
            assert ("55" in call_args.kwargs['body'] and "%" in call_args.kwargs['body'])
            assert "Insufficient data for analysis" in call_args.kwargs['body']
            assert "Classification may be incorrect" in call_args.kwargs['body']
            assert "agent-self-report" in call_args.kwargs['labels']
            assert "low-confidence" in call_args.kwargs['labels']
    
    def test_report_low_confidence_disabled(self):
        """Test that reporting is skipped when disabled"""
        reporter = GitHubReporter(enabled=False)
        
        url = reporter.report_low_confidence_issue(
            active_node="D",
            state_flow="→ D",
            confidence_score=0.55,
            decision_basis="Test",
            hypothesis="Test"
        )
        
        assert url is None
    
    @patch('common.github_reporter.Github')
    def test_report_low_confidence_with_context(self, mock_github):
        """Test low confidence reporting with additional context"""
        mock_client = Mock()
        mock_repo = Mock()
        mock_issue = Mock()
        mock_issue.html_url = "https://github.com/owner/repo/issues/2"
        
        mock_github.return_value = mock_client
        mock_client.get_repo.return_value = mock_repo
        mock_repo.create_issue.return_value = mock_issue
        
        with patch.dict(os.environ, {
            'GITHUB_TOKEN': 'fake-token',
            'GITHUB_REPOSITORY': 'owner/repo'
        }):
            reporter = GitHubReporter()
            
            additional_context = {
                "issue_type": "bug",
                "severity": "high",
                "affected_components": ["file1.py", "file2.py"]
            }
            
            url = reporter.report_low_confidence_issue(
                active_node="D",
                state_flow="→ D",
                confidence_score=0.65,
                decision_basis="Test basis",
                hypothesis="Test hypothesis",
                additional_context=additional_context
            )
            
            assert url == "https://github.com/owner/repo/issues/2"
            
            # Verify context was included in issue body
            call_args = mock_repo.create_issue.call_args
            assert '"issue_type": "bug"' in call_args.kwargs['body']
            assert '"severity": "high"' in call_args.kwargs['body']


class TestUnclearLogicReporting:
    """Test unclear logic issue reporting (Trigger 3)"""
    
    @patch('common.github_reporter.Github')
    def test_report_unclear_logic_success(self, mock_github):
        """Test successful unclear logic issue creation"""
        mock_client = Mock()
        mock_repo = Mock()
        mock_issue = Mock()
        mock_issue.html_url = "https://github.com/owner/repo/issues/3"
        
        mock_github.return_value = mock_client
        mock_client.get_repo.return_value = mock_repo
        mock_repo.create_issue.return_value = mock_issue
        
        with patch.dict(os.environ, {
            'GITHUB_TOKEN': 'fake-token',
            'GITHUB_REPOSITORY': 'owner/repo'
        }):
            reporter = GitHubReporter()
            
            url = reporter.report_unclear_logic_issue(
                user_input="Do something unclear",
                classification_attempted=True,
                suggested_tier="A",
                confidence_score=0.45,
                reasoning="Matched 2 keywords for Tier A"
            )
            
            assert url == "https://github.com/owner/repo/issues/3"
            
            # Verify issue was created with correct parameters
            call_args = mock_repo.create_issue.call_args
            
            assert "[Agent-Self-Report]" in call_args.kwargs['title']
            assert "Unclear Logic" in call_args.kwargs['title']
            assert "Node F" in call_args.kwargs['title']
            assert "Do something unclear" in call_args.kwargs['body']
            assert "Tier A" in call_args.kwargs['body'] or "None" in call_args.kwargs['body']
            assert "agent-self-report" in call_args.kwargs['labels']
            assert "unclear-logic" in call_args.kwargs['labels']
            assert "node-f" in call_args.kwargs['labels']
    
    def test_report_unclear_logic_disabled(self):
        """Test that reporting is skipped when disabled"""
        reporter = GitHubReporter(enabled=False)
        
        url = reporter.report_unclear_logic_issue(
            user_input="Test input",
            classification_attempted=False,
            suggested_tier=None,
            confidence_score=0.0,
            reasoning="No reasoning"
        )
        
        assert url is None


class TestCompetingPathsReporting:
    """Test competing paths issue reporting (Trigger 2)"""
    
    @patch('common.github_reporter.Github')
    def test_report_competing_paths_success(self, mock_github):
        """Test successful competing paths issue creation"""
        mock_client = Mock()
        mock_repo = Mock()
        mock_issue = Mock()
        mock_issue.html_url = "https://github.com/owner/repo/issues/4"
        
        mock_github.return_value = mock_client
        mock_client.get_repo.return_value = mock_repo
        mock_repo.create_issue.return_value = mock_issue
        
        with patch.dict(os.environ, {
            'GITHUB_TOKEN': 'fake-token',
            'GITHUB_REPOSITORY': 'owner/repo'
        }):
            reporter = GitHubReporter()
            
            url = reporter.report_competing_paths_issue(
                active_node="CLASSIFY",
                state_flow="Initial Classification",
                competing_paths=["A", "B", "C"],
                selected_path="A",
                selection_reason="tie-break (equal scores)",
                context={"tier_scores": {"A": 2.0, "B": 2.0, "C": 1.9}}
            )
            
            assert url == "https://github.com/owner/repo/issues/4"
            
            # Verify issue was created with correct parameters
            call_args = mock_repo.create_issue.call_args
            
            assert "[Agent-Self-Report]" in call_args.kwargs['title']
            assert "Competing Paths" in call_args.kwargs['title']
            assert "Initial Classification" in call_args.kwargs['body']
            assert "3" in call_args.kwargs['body']  # Number of competing paths
            assert "tie-break" in call_args.kwargs['body']
            assert "agent-self-report" in call_args.kwargs['labels']
            assert "competing-paths" in call_args.kwargs['labels']
    
    def test_report_competing_paths_disabled(self):
        """Test that reporting is skipped when disabled"""
        reporter = GitHubReporter(enabled=False)
        
        url = reporter.report_competing_paths_issue(
            active_node="CLASSIFY",
            state_flow="Test",
            competing_paths=["A", "B"],
            selected_path="A",
            selection_reason="test"
        )
        
        assert url is None


class TestErrorHandling:
    """Test error handling and edge cases"""
    
    @patch('common.github_reporter.Github')
    def test_github_exception_handling(self, mock_github):
        """Test handling of GitHub API exceptions"""
        from github import GithubException
        
        mock_client = Mock()
        mock_repo = Mock()
        mock_github.return_value = mock_client
        mock_client.get_repo.return_value = mock_repo
        
        # Simulate GitHub API error
        mock_repo.create_issue.side_effect = GithubException(
            status=500,
            data={"message": "Server error"}
        )
        
        with patch.dict(os.environ, {
            'GITHUB_TOKEN': 'fake-token',
            'GITHUB_REPOSITORY': 'owner/repo'
        }):
            reporter = GitHubReporter()
            
            url = reporter.report_low_confidence_issue(
                active_node="D",
                state_flow="→ D",
                confidence_score=0.5,
                decision_basis="Test",
                hypothesis="Test"
            )
            
            assert url is None  # Should return None on error
    
    @patch('common.github_reporter.Github')
    def test_generic_exception_handling(self, mock_github):
        """Test handling of generic exceptions"""
        mock_client = Mock()
        mock_repo = Mock()
        mock_github.return_value = mock_client
        mock_client.get_repo.return_value = mock_repo
        
        # Simulate generic error
        mock_repo.create_issue.side_effect = Exception("Unexpected error")
        
        with patch.dict(os.environ, {
            'GITHUB_TOKEN': 'fake-token',
            'GITHUB_REPOSITORY': 'owner/repo'
        }):
            reporter = GitHubReporter()
            
            url = reporter.report_unclear_logic_issue(
                user_input="Test",
                classification_attempted=True,
                suggested_tier=None,
                confidence_score=0.0,
                reasoning="Test"
            )
            
            assert url is None  # Should return None on error


class TestFactoryFunction:
    """Test get_github_reporter factory function"""
    
    @patch('common.github_reporter.Github')
    def test_factory_function(self, mock_github):
        """Test factory function creates reporter correctly"""
        mock_client = Mock()
        mock_repo = Mock()
        mock_github.return_value = mock_client
        mock_client.get_repo.return_value = mock_repo
        
        reporter = get_github_reporter(
            github_token='test-token',
            repo_name='test/repo',
            enabled=True
        )
        
        assert isinstance(reporter, GitHubReporter)
        assert reporter.is_enabled() is True
    
    def test_factory_function_disabled(self):
        """Test factory function with disabled reporter"""
        reporter = get_github_reporter(enabled=False)
        
        assert isinstance(reporter, GitHubReporter)
        assert reporter.is_enabled() is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
