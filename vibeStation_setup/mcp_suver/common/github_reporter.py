"""
github_reporter.py

GitHub Issue Auto-Reporting Module

Provides functionality for agents to automatically create GitHub issues when
encountering uncertain situations, low confidence decisions, or unclear logic paths.

This module implements the requirements from Part 8.3 of the project documentation
for asynchronous issue reporting without interrupting task execution.

Trigger Conditions:
1. Confidence score < 0.7 during IssueAnalysisEngine execution
2. Two or more competing paths in decision nodes requiring random selection
3. Entering F_Unknown_logic.py node with unclear logic

Usage:
    from common.github_reporter import GitHubReporter
    
    reporter = GitHubReporter()
    reporter.report_low_confidence_issue(
        active_node="D",
        state_flow="A → B → D",
        confidence_score=0.55,
        decision_basis="Insufficient data for root cause analysis",
        hypothesis="Path selection may be incorrect due to ambiguous error messages"
    )
"""

import os
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from pathlib import Path

try:
    from github import Github, GithubException
    GITHUB_AVAILABLE = True
except ImportError:
    GITHUB_AVAILABLE = False
    logging.warning(
        "PyGithub not available. GitHub issue auto-reporting will be disabled. "
        "Install with: pip install PyGithub>=2.1.0"
    )


class GitHubReporter:
    """
    GitHub Issue Auto-Reporter for Agent Self-Reporting
    
    Creates issues automatically when agents encounter uncertain situations,
    enabling asynchronous feedback collection without interrupting workflows.
    """
    
    def __init__(
        self,
        github_token: Optional[str] = None,
        repo_name: Optional[str] = None,
        enabled: bool = True
    ):
        """
        Initialize GitHub Reporter
        
        Args:
            github_token: GitHub personal access token (defaults to GITHUB_TOKEN env var)
            repo_name: Repository name in format "owner/repo" (defaults to GITHUB_REPOSITORY env var)
            enabled: Whether auto-reporting is enabled (can be disabled for testing)
        """
        self.enabled = enabled and GITHUB_AVAILABLE
        
        if not self.enabled:
            if not GITHUB_AVAILABLE:
                logging.warning("GitHubReporter disabled: PyGithub not available")
            else:
                logging.info("GitHubReporter disabled by configuration")
            return
        
        # Get GitHub credentials from environment or parameters
        self.github_token = github_token or os.getenv("GITHUB_TOKEN")
        self.repo_name = repo_name or os.getenv("GITHUB_REPOSITORY")
        
        if not self.github_token:
            logging.warning(
                "GitHubReporter disabled: GITHUB_TOKEN not found in environment. "
                "Set GITHUB_TOKEN environment variable to enable auto-reporting."
            )
            self.enabled = False
            return
        
        if not self.repo_name:
            logging.warning(
                "GitHubReporter disabled: GITHUB_REPOSITORY not found in environment. "
                "Set GITHUB_REPOSITORY environment variable (e.g., 'owner/repo')."
            )
            self.enabled = False
            return
        
        try:
            # Initialize GitHub client
            self.github = Github(self.github_token)
            self.repo = self.github.get_repo(self.repo_name)
            logging.info(f"GitHubReporter initialized for repository: {self.repo_name}")
        except Exception as e:
            logging.error(f"Failed to initialize GitHub client: {e}")
            self.enabled = False
    
    def is_enabled(self) -> bool:
        """Check if auto-reporting is enabled"""
        return self.enabled
    
    def report_low_confidence_issue(
        self,
        active_node: str,
        state_flow: str,
        confidence_score: float,
        decision_basis: str,
        hypothesis: str,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Report a low confidence decision as a GitHub issue
        
        Args:
            active_node: Currently executing tier/node (e.g., "D", "F")
            state_flow: Flow between nodes (e.g., "A → B → D")
            confidence_score: Confidence level that triggered the report (< 0.7)
            decision_basis: Internal reasoning about why confidence was low
            hypothesis: Agent's hypothesis about potential issues
            additional_context: Optional additional context data
            
        Returns:
            URL of created issue, or None if creation failed or disabled
        """
        if not self.enabled:
            logging.debug("GitHubReporter is disabled, skipping issue creation")
            return None
        
        try:
            # Build issue title
            title = f"[Agent-Self-Report] Low Confidence Decision in Node {active_node}"
            
            # Build issue body with all context
            body = self._build_issue_body(
                active_node=active_node,
                state_flow=state_flow,
                confidence_score=confidence_score,
                decision_basis=decision_basis,
                hypothesis=hypothesis,
                additional_context=additional_context
            )
            
            # Create the issue
            issue = self.repo.create_issue(
                title=title,
                body=body,
                labels=["agent-self-report", "low-confidence", f"node-{active_node.lower()}"]
            )
            
            logging.info(f"[OK] Created GitHub issue: {issue.html_url}")
            return issue.html_url
            
        except GithubException as e:
            logging.error(f"Failed to create GitHub issue: {e}")
            return None
        except Exception as e:
            logging.error(f"Unexpected error creating GitHub issue: {e}")
            return None
    
    def report_unclear_logic_issue(
        self,
        user_input: str,
        classification_attempted: bool,
        suggested_tier: Optional[str],
        confidence_score: float,
        reasoning: str
    ) -> Optional[str]:
        """
        Report unclear logic processing (F_Unknown_logic.py node)
        
        Args:
            user_input: Original user request
            classification_attempted: Whether classification was attempted
            suggested_tier: Suggested tier if any
            confidence_score: Classification confidence
            reasoning: Classification reasoning
            
        Returns:
            URL of created issue, or None if creation failed or disabled
        """
        if not self.enabled:
            logging.debug("GitHubReporter is disabled, skipping issue creation")
            return None
        
        try:
            title = "[Agent-Self-Report] Unclear Logic in Node F"
            
            body = f"""## [AGENT-REPORT] Agent Self-Report: Unclear Logic

**Node**: F (Unknown Logic Handler)
**Timestamp**: {datetime.now().isoformat()}"

### State Information

- **State Flow**: → F (Unknown Logic Entry)
- **Classification Attempted**: {classification_attempted}
- **Suggested Tier**: {suggested_tier or "None"}
- **Confidence Score**: {confidence_score:.2%}

### User Input

```
{user_input}
```

### Classification Reasoning

{reasoning}

### Hypothesis

If the classification is incorrect, it may be because:
- The user's request doesn't match known patterns for Tiers A-E
- New keywords or phrases are being used that aren't in the classification dictionary
- The request is genuinely ambiguous and requires human clarification

### User Request

After reviewing the task outcome, please:
1. Edit this issue to provide the correct tier classification
2. Add any missing keywords to the TIER_KEYWORDS dictionary
3. Close this issue with your feedback

---
*This issue was automatically created by the agent's self-reporting system.*
"""
            
            issue = self.repo.create_issue(
                title=title,
                body=body,
                labels=["agent-self-report", "unclear-logic", "node-f"]
            )
            
            logging.info(f"[OK] Created GitHub issue for unclear logic: {issue.html_url}")
            return issue.html_url
            
        except Exception as e:
            logging.error(f"Failed to create unclear logic issue: {e}")
            return None
    
    def report_competing_paths_issue(
        self,
        active_node: str,
        state_flow: str,
        competing_paths: List[str],
        selected_path: str,
        selection_reason: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Report when two or more competing paths must be randomly selected
        
        Args:
            active_node: Currently executing tier/node
            state_flow: Flow between nodes
            competing_paths: List of competing path options
            selected_path: Path that was selected
            selection_reason: Reason for selection (e.g., "random", "tie-break")
            context: Additional context
            
        Returns:
            URL of created issue, or None if creation failed or disabled
        """
        if not self.enabled:
            logging.debug("GitHubReporter is disabled, skipping issue creation")
            return None
        
        try:
            title = f"[Agent-Self-Report] Competing Paths in Node {active_node}"
            
            body = f"""## [AGENT-REPORT] Agent Self-Report: Competing Paths Decision

**Node**: {active_node}
**Timestamp**: {datetime.now().isoformat()}

### State Information

- **State Flow**: {state_flow}
- **Number of Competing Paths**: {len(competing_paths)}
- **Selected Path**: {selected_path}
- **Selection Reason**: {selection_reason}

### Competing Path Options

{chr(10).join(f"{i+1}. {path}" for i, path in enumerate(competing_paths))}

### Decision Context

The agent encountered multiple equally valid paths and had to make a selection.
This may indicate:
- Ambiguous routing rules that need clarification
- Insufficient context to differentiate between paths
- Equal confidence scores requiring tie-breaking logic

### Additional Context

```json
{self._format_context(context)}
```

### User Request

After completing the task, please review:
1. Was the selected path correct?
2. Should the routing rules be updated to better differentiate these paths?
3. Is additional context needed to make better decisions in similar cases?

---
*This issue was automatically created by the agent's self-reporting system.*
"""
            
            issue = self.repo.create_issue(
                title=title,
                body=body,
                labels=["agent-self-report", "competing-paths", f"node-{active_node.lower()}"]
            )
            
            logging.info(f"[OK] Created GitHub issue for competing paths: {issue.html_url}")
            return issue.html_url
            
        except Exception as e:
            logging.error(f"Failed to create competing paths issue: {e}")
            return None
    
    def _build_issue_body(
        self,
        active_node: str,
        state_flow: str,
        confidence_score: float,
        decision_basis: str,
        hypothesis: str,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build issue body with all required information"""
        
        body = f"""## [AGENT-REPORT] Agent Self-Report: Low Confidence Decision

**Node**: {active_node}
**Timestamp**: {datetime.now().isoformat()}

### State Information

- **State Flow**: {state_flow}
- **Confidence Score**: {confidence_score:.2%} (threshold: 70%)

### Decision Basis

{decision_basis}

### Hypothesis

{hypothesis}

### Additional Context

```json
{self._format_context(additional_context)}
```

### User Request

After completing the task, please:
1. Review the agent's decision and provide feedback
2. Edit this issue body to provide the correct guidance
3. Close this issue with appropriate labels

---
*This issue was automatically created by the agent's self-reporting system.*
*Issue creation is asynchronous and does not interrupt task execution.*
"""
        return body
    
    def _format_context(self, context: Optional[Dict[str, Any]]) -> str:
        """Format additional context as JSON string"""
        if not context:
            return "{}"
        
        import json
        try:
            return json.dumps(context, indent=2, default=str)
        except Exception:
            return str(context)
    
    def load_feedback_from_closed_issues(
        self,
        label_filter: str = "agent-self-report",
        max_issues: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Load user feedback from closed GitHub issues for learning context.
        
        This method retrieves closed issues that were auto-reported by the agent,
        extracts user feedback from issue comments and body edits, and returns
        structured feedback data that can be used to improve future decisions.
        
        Args:
            label_filter: Label to filter issues (default: "agent-self-report")
            max_issues: Maximum number of closed issues to retrieve (default: 50)
            
        Returns:
            List of feedback dictionaries with structure:
            {
                "issue_number": int,
                "title": str,
                "created_at": str,
                "closed_at": str,
                "node": str,  # Extracted from title (e.g., "D", "F", "CLASSIFY")
                "original_confidence": float,  # Extracted from body if available
                "user_feedback": str,  # User's comments or body edits
                "resolution": str,  # How the issue was resolved
                "labels": List[str],
                "url": str
            }
        """
        if not self.enabled:
            logging.debug("GitHubReporter is disabled, cannot load feedback")
            return []
        
        try:
            # Query closed issues with the specified label
            issues = self.repo.get_issues(
                state="closed",
                labels=[label_filter],
                sort="updated",
                direction="desc"
            )
            
            feedback_list = []
            count = 0
            
            for issue in issues:
                if count >= max_issues:
                    break
                
                try:
                    # Extract node from title (e.g., "Node D" -> "D")
                    node = None
                    if "Node" in issue.title:
                        import re
                        node_match = re.search(r'Node\s+([A-F]|CLASSIFY)', issue.title)
                        if node_match:
                            node = node_match.group(1)
                    
                    # Extract confidence score from body if available
                    original_confidence = None
                    if issue.body:
                        confidence_match = re.search(r'Confidence Score[:\s]+(\d+(?:\.\d+)?%?)', issue.body)
                        if confidence_match:
                            conf_str = confidence_match.group(1).replace('%', '')
                            try:
                                original_confidence = float(conf_str)
                                # Convert percentage to decimal if needed
                                if original_confidence > 1.0:
                                    original_confidence = original_confidence / 100.0
                            except ValueError:
                                pass
                    
                    # Collect user feedback from comments
                    user_feedback_parts = []
                    comments = issue.get_comments()
                    
                    for comment in comments:
                        # Skip comments from bots or the agent itself
                        if comment.user.type != "Bot":
                            user_feedback_parts.append(f"[{comment.user.login}]: {comment.body}")
                    
                    # Also check if issue body was edited (contains user guidance)
                    if issue.body and "correct guidance" in issue.body.lower():
                        # User may have edited the issue body
                        user_feedback_parts.append(f"[Issue Body Edit]: {issue.body}")
                    
                    user_feedback = "\n\n".join(user_feedback_parts) if user_feedback_parts else "No user feedback provided"
                    
                    # Determine resolution type from labels
                    resolution = "resolved"
                    issue_labels = [label.name for label in issue.labels]
                    
                    if "wontfix" in issue_labels or "invalid" in issue_labels:
                        resolution = "dismissed"
                    elif "duplicate" in issue_labels:
                        resolution = "duplicate"
                    
                    feedback_data = {
                        "issue_number": issue.number,
                        "title": issue.title,
                        "created_at": issue.created_at.isoformat() if issue.created_at else None,
                        "closed_at": issue.closed_at.isoformat() if issue.closed_at else None,
                        "node": node,
                        "original_confidence": original_confidence,
                        "user_feedback": user_feedback,
                        "resolution": resolution,
                        "labels": issue_labels,
                        "url": issue.html_url
                    }
                    
                    feedback_list.append(feedback_data)
                    count += 1
                    
                except Exception as e:
                    logging.warning(f"Error processing issue #{issue.number}: {e}")
                    continue
            
            logging.info(f"Loaded feedback from {len(feedback_list)} closed issues")
            return feedback_list
            
        except Exception as e:
            logging.error(f"Failed to load feedback from closed issues: {e}")
            return []
    
    def get_feedback_summary(self, feedback_list: List[Dict[str, Any]]) -> str:
        """
        Generate a human-readable summary of feedback for learning context.
        
        Args:
            feedback_list: List of feedback dictionaries from load_feedback_from_closed_issues()
            
        Returns:
            Formatted summary string suitable for inclusion in prompts or analysis
        """
        if not feedback_list:
            return "No historical feedback available."
        
        summary_parts = [
            f"Historical Feedback Summary ({len(feedback_list)} issues):",
            "=" * 60
        ]
        
        # Group by node
        by_node = {}
        for fb in feedback_list:
            node = fb.get("node", "UNKNOWN")
            if node not in by_node:
                by_node[node] = []
            by_node[node].append(fb)
        
        for node, issues in sorted(by_node.items()):
            summary_parts.append(f"\n### Node {node} ({len(issues)} issues)")
            
            for fb in issues[:5]:  # Show up to 5 per node
                summary_parts.append(f"\n**Issue #{fb['issue_number']}**: {fb['title']}")
                summary_parts.append(f"  Resolution: {fb['resolution']}")
                
                if fb['original_confidence'] is not None:
                    summary_parts.append(f"  Original Confidence: {fb['original_confidence']:.2%}")
                
                # Show snippet of feedback
                feedback_snippet = fb['user_feedback'][:200]
                if len(fb['user_feedback']) > 200:
                    feedback_snippet += "..."
                summary_parts.append(f"  Feedback: {feedback_snippet}")
                summary_parts.append(f"  URL: {fb['url']}")
        
        return "\n".join(summary_parts)


def get_github_reporter(
    github_token: Optional[str] = None,
    repo_name: Optional[str] = None,
    enabled: bool = True
) -> GitHubReporter:
    """
    Factory function to get a GitHubReporter instance
    
    This function can be used to get a shared reporter instance
    or create new instances as needed.
    
    Args:
        github_token: GitHub personal access token (optional)
        repo_name: Repository name in format "owner/repo" (optional)
        enabled: Whether to enable auto-reporting (default: True)
        
    Returns:
        GitHubReporter instance
    """
    return GitHubReporter(
        github_token=github_token,
        repo_name=repo_name,
        enabled=enabled
    )
