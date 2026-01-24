"""
MP Constants Module - Refactored with Clean Data Classes

Provides constants and configuration for MP (Mapping Table) tools.

Architecture:
- Nested classes for logical grouping
- Clean data classes without legacy field support
- Type-safe enumerations
- Compiled patterns for performance
"""

from pathlib import Path
from enum import Enum
from typing import Dict
import re
from dataclasses import dataclass


# ============================================================================
# File Size Limits
# ============================================================================

class FileLimits:
    """File size constraints for MP files"""
    MAX_LINES = 500
    TARGET_LINES = 400  # Aim for this when splitting
    MIN_LINES = 50      # Don't create files smaller than this
    MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


# ============================================================================
# Scopes and Metadata
# ============================================================================

class MPScope:
    """Valid MP scopes"""
    CLIENT = 'client'
    EVENT_PROCESSING = 'event_processing'
    SHARED = 'shared'
    
    ALL = [CLIENT, EVENT_PROCESSING, SHARED]
    
    @classmethod
    def is_valid(cls, scope: str) -> bool:
        """Check if scope is valid"""
        return scope in cls.ALL


@dataclass
class MetadataField:
    """Metadata field definition"""
    name: str
    required: bool
    pattern: str = ""


class MPMetadataFields:
    """Required and optional metadata fields"""
    TYPE = MetadataField('Type', required=True)
    PURPOSE = MetadataField('Purpose', required=True)
    SCOPE = MetadataField('Scope', required=True)
    CURRENT_LINE = MetadataField('Current line', required=True)
    RELATED_PROJECT = MetadataField('Related Project', required=False)
    
    REQUIRED = [TYPE, PURPOSE, SCOPE, CURRENT_LINE]
    ALL = REQUIRED + [RELATED_PROJECT]


# ============================================================================
# Patterns and Regex
# ============================================================================

class MPPatterns:
    """Compiled regex patterns for MP file processing"""
    
    # File naming patterns
    FILE = re.compile(r'MP-\d+-flow\.md$')
    EXTENSION = re.compile(r'MP-\d+-flow-ext\d+\.md$')
    
    # Structural patterns
    SECTION_MARKER = re.compile(r'^#{1,4}\s+(.+)$')
    CODE_BLOCK = re.compile(r'```.*?\n(.*?)\n```', re.DOTALL)
    
    # Metadata patterns
    LINE_COUNT = re.compile(r'\*\*Current line\*\*:\s*(\d+)')
    PURPOSE = re.compile(r'\*\*Purpose\*\*:\s*(.+?)(?:\n|$)')
    TYPE = re.compile(r'\*\*Type\*\*:\s*(.+?)(?:\n|$)')
    SCOPE = re.compile(r'(?:client|event_processing|shared)')
    RELATED_PROJECT = re.compile(r'\*\*Related Project\*\*:\s*(.+?)(?:\n|$)')
    
    # Prose detection patterns
    PROSE = [
        re.compile(r'\bThe\s+\w+\s+(?:is|are|was|were)\b'),
        re.compile(r'\bThis\s+\w+\s+(?:provides|allows|enables|creates)\b'),
        re.compile(r'\bIn\s+order\s+to\b'),
        re.compile(r'\bFor\s+example\b'),
        re.compile(r'\bAs\s+mentioned\b'),
        re.compile(r'\bIt\s+(?:is|was|can|will)\s+\w+'),
        re.compile(r'\bOne\s+(?:can|must|should|will)\b'),
        re.compile(r'\bDue\s+to\b'),
        re.compile(r'\b(?:Moreover|Furthermore|However|Therefore|Nonetheless)\b'),
        re.compile(r'\bIn\s+conclusion\b'),
    ]
    
    # Flow diagram indicators
    FLOW_INDICATORS = ['→', '↓', '├', '└', '->', '|', 'flow', 'Process']


# ============================================================================
# Path Utilities
# ============================================================================

class MPPaths:
    """Path resolution for MP directories"""
    
    @staticmethod
    def get_repo_root() -> Path:
        """Get repository root directory"""
        current = Path(__file__).resolve()
        while current.parent != current:
            if (current / '.git').exists() or current.name == 'turbo-system':
                return current
            current = current.parent
        # Fallback
        return Path(__file__).resolve().parents[6]
    
    @staticmethod
    def get_mp_root() -> Path:
        """Get MP directory root (docs_2/mp)"""
        return MPPaths.get_repo_root() / 'docs_2' / 'mp'
    
    @staticmethod
    def get_scope_dir(scope: str) -> Path:
        """Get directory for specific scope"""
        if not MPScope.is_valid(scope):
            raise ValueError(f"Invalid scope: {scope}. Must be one of: {MPScope.ALL}")
        return MPPaths.get_mp_root() / scope


# ============================================================================
# Enumerations
# ============================================================================

class ValidationSeverity(Enum):
    """Validation severity levels"""
    ERROR = 'error'
    WARNING = 'warning'
    INFO = 'info'


class MPFileType(Enum):
    """MP file types"""
    MAIN = 'main'           # Main MP file (MP-N-flow.md)
    EXTENSION = 'extension' # Extension file (MP-N-flow-extN.md)


# ============================================================================
# Display and Output
# ============================================================================

class DisplayLimits:
    """Limits for CLI output"""
    MAX_MATCHES = 5
    MAX_REFERENCES = 3


# ============================================================================
# Default Values
# ============================================================================

@dataclass
class MPMetadataDefaults:
    """Default values for MP file creation"""
    type: str = 'Flow Diagram'
    purpose: str = 'To be defined'
    scope: str = 'shared'
    current_line: str = '0'
    related_project: str = ''


# ============================================================================
# Configuration
# ============================================================================

class MPConfig:
    """General MP configuration"""
    FILE_ENCODING = 'utf-8'
    SCOPE_DIRS: Dict[str, str] = {
        'client': 'client',
        'event_processing': 'event_processing',
        'shared': 'shared',
    }


# ============================================================================
# Error Messages
# ============================================================================

class MPErrors:
    """Error message templates"""
    
    INVALID_SCOPE = 'Invalid scope: {scope}. Must be one of: {valid}'
    FILE_EXCEEDS_LIMIT = 'File {file} exceeds {limit} line limit: {actual} lines'
    MISSING_METADATA = 'Missing required metadata: {field} in {file}'
    INVALID_FORMAT = 'Invalid format in {file}: {detail}'
    FILE_NOT_FOUND = 'File not found: {file}'
    IMPORT_ERROR = 'Failed to import MP data models: {error}'
    INVALID_MODEL_TYPE = 'Invalid model type: {model_type}'
    INVALID_LINE_RANGE = 'Invalid line range: {start}-{end}'
    
    @staticmethod
    def format(template: str, **kwargs) -> str:
        """Format error message with parameters"""
        return template.format(**kwargs)
