#!/usr/bin/env python3
"""
feedback_loading_demo.py

Demonstration of feedback loading functionality for learning from closed issues.

This script shows how to:
1. Load feedback from closed GitHub issues
2. Generate feedback summaries
3. Use feedback context in Issue Analysis

Usage:
    python feedback_loading_demo.py
    
Environment variables required:
    GITHUB_TOKEN - GitHub personal access token
    GITHUB_REPOSITORY - Repository name (e.g., "owner/repo")
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.github_reporter import get_github_reporter


def demo_feedback_loading():
    """Demonstrate basic feedback loading"""
    print("=" * 70)
    print("Feedback Loading Demo")
    print("=" * 70)
    
    # Initialize reporter
    reporter = get_github_reporter()
    
    if not reporter.is_enabled():
        print("\n❌ GitHub reporter is not enabled")
        print("   Please set GITHUB_TOKEN and GITHUB_REPOSITORY environment variables")
        print("\n   Example:")
        print("   export GITHUB_TOKEN=your_token_here")
        print("   export GITHUB_REPOSITORY=owner/repo")
        return
    
    print("\n[OK] GitHub reporter is enabled")
    print(f"  Repository: {reporter.repo_name}")
    
    # Load feedback from closed issues
    print("\n" + "-" * 70)
    print("Loading feedback from closed issues...")
    print("-" * 70)
    
    feedback_list = reporter.load_feedback_from_closed_issues(
        label_filter="agent-self-report",
        max_issues=10
    )
    
    if not feedback_list:
        print("\n📋 No closed issues found yet")
        print("   Issues will appear here after:")
        print("   1. Agent creates auto-report issues")
        print("   2. User provides feedback")
        print("   3. Issues are closed")
        return
    
    print(f"\n[OK] Loaded {len(feedback_list)} closed issues")
    
    # Display feedback data
    print("\n" + "-" * 70)
    print("Feedback Details")
    print("-" * 70)
    
    for i, feedback in enumerate(feedback_list[:5], 1):  # Show first 5
        print(f"\n{i}. Issue #{feedback['issue_number']}: {feedback['title']}")
        print(f"   Node: {feedback.get('node', 'N/A')}")
        
        if feedback.get('original_confidence'):
            print(f"   Original Confidence: {feedback['original_confidence']:.2%}")
        
        print(f"   Resolution: {feedback['resolution']}")
        print(f"   URL: {feedback['url']}")
        
        # Show feedback snippet
        feedback_text = feedback['user_feedback']
        if len(feedback_text) > 100:
            feedback_text = feedback_text[:100] + "..."
        print(f"   Feedback: {feedback_text}")
    
    if len(feedback_list) > 5:
        print(f"\n   ... and {len(feedback_list) - 5} more issues")
    
    # Generate and display summary
    print("\n" + "-" * 70)
    print("Feedback Summary")
    print("-" * 70)
    
    summary = reporter.get_feedback_summary(feedback_list)
    print(f"\n{summary}")
    
    # Statistics
    print("\n" + "-" * 70)
    print("Statistics")
    print("-" * 70)
    
    # Count by node
    node_counts = {}
    for fb in feedback_list:
        node = fb.get("node", "UNKNOWN")
        node_counts[node] = node_counts.get(node, 0) + 1
    
    print("\nIssues by Node:")
    for node, count in sorted(node_counts.items()):
        print(f"  {node}: {count} issue(s)")
    
    # Count by resolution
    resolution_counts = {}
    for fb in feedback_list:
        res = fb.get("resolution", "unknown")
        resolution_counts[res] = resolution_counts.get(res, 0) + 1
    
    print("\nIssues by Resolution:")
    for res, count in sorted(resolution_counts.items()):
        print(f"  {res}: {count} issue(s)")
    
    # Average confidence
    confidences = [fb['original_confidence'] for fb in feedback_list if fb.get('original_confidence')]
    if confidences:
        avg_conf = sum(confidences) / len(confidences)
        print(f"\nAverage Original Confidence: {avg_conf:.2%}")
        print(f"Min: {min(confidences):.2%}, Max: {max(confidences):.2%}")
    
    print("\n" + "=" * 70)
    print("Demo Complete!")
    print("=" * 70)


def demo_usage_in_analysis():
    """Demonstrate using feedback in Issue Analysis"""
    print("\n" + "=" * 70)
    print("Using Feedback in Issue Analysis")
    print("=" * 70)
    
    print("\nNote: This demo shows the API usage.")
    print("      Actual analysis requires full D_Issue_Analysis_Flow module.")
    
    print("\nExample code:")
    print("""
    from D_Issue_Analysis_Flow import IssueAnalysisEngine
    
    # Initialize engine
    engine = IssueAnalysisEngine()
    
    # Load feedback context
    engine.load_feedback_context(max_issues=20)
    
    # Analyze with feedback context
    state = engine.execute(
        user_input="Error in file processing",
        use_feedback_context=True
    )
    
    print(f"Routing: Tier {state.next_node}")
    print(f"Confidence: {state.payload['routing_info']['routing_confidence']:.2%}")
    """)


if __name__ == "__main__":
    try:
        demo_feedback_loading()
        demo_usage_in_analysis()
    except KeyboardInterrupt:
        print("\n\n Demo interrupted by user")
    except Exception as e:
        print(f"\n\n Error: {e}")
        import traceback
        traceback.print_exc()
