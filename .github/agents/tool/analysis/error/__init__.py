"""
Error Analysis Module - Issue Classification, Root Cause Analysis, and Resolution Strategy

Provides:
- IssueClassifier: Classify issues by type and severity
- RootCauseAnalyzer: Identify root causes
- ResolutionStrategyEngine: Generate resolution strategies
- RoutingEngine: Determine routing decisions

Note: Data models migrated to models.core.reporting_models
"""

from models.core.reporting_models import (
    IssueClassification,
    RootCauseAnalysis,
    ResolutionStrategy,
    RoutingInfo,
)

__all__ = [
    "IssueClassification",
    "RootCauseAnalysis",
    "ResolutionStrategy",
    "RoutingInfo",
]
