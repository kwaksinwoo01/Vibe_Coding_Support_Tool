"""
Indexer Package - Repository-level indexing automation

Provides modular indexing automation framework that replaces legacy agent_indexer.py:
- Core indexing logic (commit threshold, file collection, SQLite building)
- Release management (upload, pruning)
- Workflow generation
- Integration with Tier E (Document Management)

Architecture: Facade pattern with nested components
- IndexFacade: Main entry point for consumers
- CoreIndexer: Index decision and database building
- Releaser: GitHub release upload and pruning
- WorkflowGenerator: YAML workflow template generation
"""

from .facade import IndexFacade
from .core import CoreIndexer
from .releaser import Releaser
from .workflow import WorkflowGenerator

__all__ = [
    "IndexFacade",
    "CoreIndexer",
    "Releaser",
    "WorkflowGenerator",
]
