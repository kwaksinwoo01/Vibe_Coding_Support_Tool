"""
Common Utilities Module

Hierarchical utilities with nested classes for better organization.
Provides modern, clean implementations of web tools and state management.

Modules:
- web_tools: Web page loading, search, and storage
- state_utils: State and outline management
"""

from .web_tools import (
    WebPageStorage,
    WebPageLoader,
)

from .state_utils import (
    StateManager,
    OutlineManager,
)

__all__ = [
    'WebPageStorage',
    'WebPageLoader',
    'StateManager',
    'OutlineManager',
]
