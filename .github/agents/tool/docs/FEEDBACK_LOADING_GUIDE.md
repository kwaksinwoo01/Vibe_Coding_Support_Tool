# Feedback Loading from Closed Issues - Usage Guide

## Overview

The feedback loading feature enables the Issue Analysis Engine to learn from historical closed issues. When users provide feedback on auto-reported issues, this feedback can be loaded and used to improve future decision-making.

## How It Works

1. **Agent Creates Issue**: When confidence is low (< 0.7), agent creates GitHub issue
2. **User Provides Feedback**: User reviews the issue, adds comments or edits the issue body
3. **Issue is Closed**: User closes the issue with appropriate labels
4. **Feedback is Loaded**: Engine loads closed issues and extracts user feedback
5. **Context is Used**: Feedback context is included in future analyses

## API Reference

### GitHubReporter Methods

#### `load_feedback_from_closed_issues(label_filter="agent-self-report", max_issues=50)`

Loads user feedback from closed GitHub issues.

**Parameters:**
- `label_filter` (str): Label to filter issues (default: "agent-self-report")
- `max_issues` (int): Maximum number of issues to retrieve (default: 50)

**Returns:**
```python
List[Dict[str, Any]] with structure:
{
    "issue_number": int,
    "title": str,
    "created_at": str (ISO format),
    "closed_at": str (ISO format),
    "node": str,  # e.g., "D", "F", "CLASSIFY"
    "original_confidence": float,  # e.g., 0.55
    "user_feedback": str,  # Combined comments from non-bot users
    "resolution": str,  # "resolved", "dismissed", or "duplicate"
    "labels": List[str],
    "url": str
}
```

**Example:**
```python
from common.github_reporter import get_github_reporter

reporter = get_github_reporter()
feedback_list = reporter.load_feedback_from_closed_issues(max_issues=20)

for feedback in feedback_list:
    print(f"Issue #{feedback['issue_number']}: {feedback['title']}")
    print(f"  Confidence: {feedback['original_confidence']:.2%}")
    print(f"  Feedback: {feedback['user_feedback'][:100]}...")
```

#### `get_feedback_summary(feedback_list)`

Generates a human-readable summary of feedback for learning context.

**Parameters:**
- `feedback_list` (List[Dict]): List from `load_feedback_from_closed_issues()`

**Returns:**
- Formatted string suitable for prompts or analysis

**Example:**
```python
summary = reporter.get_feedback_summary(feedback_list)
print(summary)
```

**Output:**
```
Historical Feedback Summary (5 issues):
============================================================

### Node D (3 issues)

**Issue #1**: [Agent-Self-Report] Low Confidence Decision in Node D
  Resolution: resolved
  Original Confidence: 55.00%
  Feedback: [user1]: The classification was correct...
  URL: https://github.com/owner/repo/issues/1

**Issue #2**: [Agent-Self-Report] Low Confidence Decision in Node D
  Resolution: resolved
  Original Confidence: 62.00%
  Feedback: [user2]: Should have routed to Tier C instead...
  URL: https://github.com/owner/repo/issues/2

### Node F (2 issues)

**Issue #3**: [Agent-Self-Report] Unclear Logic in Node F
  Resolution: dismissed
  Original Confidence: 45.00%
  Feedback: [user1]: Request was too vague...
  URL: https://github.com/owner/repo/issues/3
```

### IssueAnalysisEngine Methods

#### `load_feedback_context(max_issues=20)`

Loads historical feedback from closed issues into learning context.

**Parameters:**
- `max_issues` (int): Maximum number of issues to load (default: 20)

**Returns:**
- Formatted feedback summary string (also cached in `self.feedback_context`)

**Example:**
```python
from D_Issue_Analysis_Flow import IssueAnalysisEngine

engine = IssueAnalysisEngine()

# Load feedback context
context = engine.load_feedback_context(max_issues=20)
print(context)

# Feedback is now cached in engine.feedback_context
```

#### `execute(user_input, error_context=None, use_feedback_context=False)`

Enhanced execute method with optional feedback context.

**Parameters:**
- `user_input` (str): User's issue description
- `error_context` (Dict, optional): Additional error context
- `use_feedback_context` (bool): If True, loads and uses historical feedback

**Example:**
```python
# Without feedback context (default)
state = engine.execute("Error in file processing")

# With feedback context
state = engine.execute(
    "Error in file processing",
    use_feedback_context=True
)
```

## Complete Workflow Example

```python
#!/usr/bin/env python3
"""
Complete example of using feedback loading in Issue Analysis
"""

from D_Issue_Analysis_Flow import IssueAnalysisEngine
import os

# Set environment variables
os.environ["GITHUB_TOKEN"] = "your-github-token"
os.environ["GITHUB_REPOSITORY"] = "owner/repo"

# Initialize engine
engine = IssueAnalysisEngine()

# Scenario 1: Analyze issue without feedback context
print("=" * 60)
print("Scenario 1: Analysis without feedback context")
print("=" * 60)

state1 = engine.execute(
    user_input="File upload fails with unclear error message",
    use_feedback_context=False
)

print(f"Status: {state1.status}")
print(f"Routing: Tier {state1.next_node}")
print(f"Confidence: {state1.payload.get('routing_info', {}).get('routing_confidence', 0):.2%}")

# Scenario 2: Load feedback and analyze with context
print("\n" + "=" * 60)
print("Scenario 2: Analysis WITH feedback context")
print("=" * 60)

# Load feedback (done once, cached in engine)
feedback_context = engine.load_feedback_context(max_issues=20)
print(f"\nLoaded feedback context ({len(feedback_context)} chars)")

# Analyze with feedback context
state2 = engine.execute(
    user_input="File upload fails with unclear error message",
    use_feedback_context=True
)

print(f"\nStatus: {state2.status}")
print(f"Routing: Tier {state2.next_node}")
print(f"Confidence: {state2.payload.get('routing_info', {}).get('routing_confidence', 0):.2%}")

# Scenario 3: Direct access to feedback data
print("\n" + "=" * 60)
print("Scenario 3: Direct feedback data access")
print("=" * 60)

from common.github_reporter import get_github_reporter

reporter = get_github_reporter()
feedback_list = reporter.load_feedback_from_closed_issues(max_issues=10)

print(f"\nLoaded {len(feedback_list)} closed issues")

# Analyze feedback patterns
node_stats = {}
for fb in feedback_list:
    node = fb.get("node", "UNKNOWN")
    if node not in node_stats:
        node_stats[node] = {"count": 0, "avg_confidence": []}
    
    node_stats[node]["count"] += 1
    if fb.get("original_confidence"):
        node_stats[node]["avg_confidence"].append(fb["original_confidence"])

print("\nFeedback Statistics by Node:")
for node, stats in sorted(node_stats.items()):
    avg_conf = sum(stats["avg_confidence"]) / len(stats["avg_confidence"]) if stats["avg_confidence"] else 0
    print(f"  Node {node}: {stats['count']} issues, avg confidence: {avg_conf:.2%}")
```

## Best Practices

### 1. Cache Feedback Context

Load feedback once and reuse:

```python
engine = IssueAnalysisEngine()

# Load once at startup
engine.load_feedback_context(max_issues=20)

# Reuse for multiple analyses
for user_input in inputs:
    state = engine.execute(user_input, use_feedback_context=True)
```

### 2. Limit Feedback Size

Don't load too many issues to avoid overwhelming the context:

```python
# Good: 10-20 most recent issues
engine.load_feedback_context(max_issues=20)

# Avoid: Loading hundreds of issues
# engine.load_feedback_context(max_issues=500)  # Too much!
```

### 3. Filter by Node Type

If analyzing a specific tier, filter feedback:

```python
# Get all feedback
all_feedback = reporter.load_feedback_from_closed_issues(max_issues=50)

# Filter for Node D only
node_d_feedback = [fb for fb in all_feedback if fb.get("node") == "D"]

# Generate summary for D-specific feedback
d_summary = reporter.get_feedback_summary(node_d_feedback)
```

### 4. Provide Quality Feedback

When closing auto-reported issues, provide detailed feedback:

**Good feedback:**
```
The classification was incorrect. The issue should have been routed to Tier C 
(Plan Modification) instead of Tier B (Execution) because the user was asking 
to modify an existing plan, not execute it. The keyword "change" should have 
higher priority than "run" in the classification logic.
```

**Poor feedback:**
```
Wrong
```

## Environment Setup

Required environment variables:

```bash
export GITHUB_TOKEN=<your-github-personal-access-token>
export GITHUB_REPOSITORY=owner/repo
```

## Limitations

1. **GitHub API Rate Limits**: Loading feedback makes API calls. Be mindful of rate limits.
2. **Bot Comments Filtered**: Only human user comments are included in feedback.
3. **No Retroactive Learning**: Feedback must be manually loaded; it doesn't automatically improve the model.
4. **Context Size**: Large feedback contexts may consume significant prompt space.

## Future Enhancements

- [ ] Automatic periodic feedback loading
- [ ] Feedback-based confidence adjustment
- [ ] ML model training from feedback data
- [ ] Feedback deduplication and clustering
- [ ] Automated feedback quality scoring

## Troubleshooting

### "GitHubReporter disabled" message

**Cause**: Missing environment variables or PyGithub not installed

**Solution**:
```bash
pip install PyGithub>=2.1.0
export GITHUB_TOKEN=<token>
export GITHUB_REPOSITORY=owner/repo
```

### Empty feedback list

**Cause**: No closed issues with "agent-self-report" label

**Solution**: Create and close some test issues, or wait for natural feedback accumulation

### Import errors

**Cause**: Module path issues

**Solution**: Ensure you're running from the correct directory:
```bash
cd /path/to/turbo-system/.github/agents/tool
python your_script.py
```

## Version History

- **v1.0** (2026-01-26): Initial feedback loading implementation
  - `load_feedback_from_closed_issues()` method
  - `get_feedback_summary()` method
  - Integration with `IssueAnalysisEngine`
  - Comprehensive documentation and examples
