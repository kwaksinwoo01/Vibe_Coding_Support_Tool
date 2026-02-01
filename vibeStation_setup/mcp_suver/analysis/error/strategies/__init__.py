"""
Routing strategies for the RoutingEngine.

This package contains strategy pattern implementations for routing decisions.
Each strategy handles a specific type of issue and determines the appropriate
target tier based on classification results.
"""

from .base import RoutingStrategy
from .bug_routing_strategy import BugRoutingStrategy
from .design_flaw_routing_strategy import DesignFlawRoutingStrategy
from .performance_routing_strategy import PerformanceRoutingStrategy
from .fallback_routing_strategy import FallbackRoutingStrategy

__all__ = [
    "RoutingStrategy",
    "BugRoutingStrategy",
    "DesignFlawRoutingStrategy",
    "PerformanceRoutingStrategy",
    "FallbackRoutingStrategy",
]
