"""
Document Management Package

Provides facade pattern for document management operations:
- Link Management
- Version Management
- Checklist Management
- Progress Management
- Mapping Management
- Error Session Management
- Markdown Autofix (MD024, MD029, MD031, MD032, MD034)
- Document Modification (ADMP Rules)
- Document Updates (WPD/PRD)
- Template Generation

DESTRUCTIVE REFACTOR: VersionInfo moved to models.core.version
- Import VersionInfo from models.core.version instead of template_generator
"""

import sys
from pathlib import Path

from .link_manager import LinkManager
from .version_manager import VersionManager
from .checklist_manager import ChecklistManager
from .progress_manager import ProgressManager
from .mapping_manager import MappingManager
from .error_session_manager import ErrorSessionManager
from .markdown_autofix import MarkdownAutofixManager
from .document_modifier import DocumentModifier, ModificationPermissionError
from .document_updater import DocumentUpdater
from .template_generator import TemplateGenerator
from .document_merger import DocumentMerger, SemanticAnalyzer

# Import VersionInfo from canonical models
sys.path.insert(0, str(Path(__file__).parent.parent))
from models.core.version import VersionInfo

__all__ = [
    "LinkManager",
    "VersionManager",
    "ChecklistManager",
    "ProgressManager",
    "MappingManager",
    "ErrorSessionManager",
    "MarkdownAutofixManager",
    "DocumentModifier",
    "ModificationPermissionError",
    "DocumentUpdater",
    "TemplateGenerator",
    "VersionInfo",
    "DocumentMerger",
    "SemanticAnalyzer",
]
