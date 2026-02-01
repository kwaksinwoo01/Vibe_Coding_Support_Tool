"""
MP (Mapping Table) Module - Refactored

Clean architecture for managing mapping table files.

Main Components:
- constants: Constants and enumerations
- config: Path and environment configuration
- utils: File, metadata, and section operations
- reporting: Report generation and formatting
"""

from .constants import (
    FileLimits,
    MPScope,
    MPMetadataFields,
    MPPatterns,
    MPPaths,
    ValidationSeverity,
    MPFileType,
    DisplayLimits,
    MPMetadataDefaults,
    MPConfig,
    MPErrors,
)

from .config import (
    MPConfigurator,
    PathResolver,
    PathConfig,
    ModuleValidator,
    EnvironmentDetector,
)

from .utils import (
    FileOperations,
    MetadataOperations,
    SectionOperations,
    FlowOperations,
    PathOperations,
    # Legacy compatibility
    MPFileUtils,
    MetadataUtils,
    SectionUtils,
)

from .reporting import (
    Reporter,
    ReportFormat,
    Formatters,
    ValidationIssue,
    SyncResult,
    FileMetadata,
    # Legacy compatibility
    MPReporter,
    MarkdownFormatter,
    ConsoleFormatter,
    JSONFormatter,
)

__all__ = [
    # Constants
    'FileLimits',
    'MPScope',
    'MPMetadataFields',
    'MPPatterns',
    'MPPaths',
    'ValidationSeverity',
    'MPFileType',
    'DisplayLimits',
    'MPMetadataDefaults',
    'MPConfig',
    'MPErrors',
    
    # Config
    'MPConfigurator',
    'PathResolver',
    'PathConfig',
    'ModuleValidator',
    'EnvironmentDetector',
    
    # Utils
    'FileOperations',
    'MetadataOperations',
    'SectionOperations',
    'FlowOperations',
    'PathOperations',
    
    # Reporting
    'Reporter',
    'ReportFormat',
    'Formatters',
    'ValidationIssue',
    'SyncResult',
    'FileMetadata',
    
    # Legacy
    'MPFileUtils',
    'MetadataUtils',
    'SectionUtils',
    'MPReporter',
    'MarkdownFormatter',
    'ConsoleFormatter',
    'JSONFormatter',
]
