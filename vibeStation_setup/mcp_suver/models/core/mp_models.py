"""
Separated MP (Memory/Metadata Protocol) data models.

**Single Responsibility**: Each model type has a single responsibility.
Instead of a single MPModel with all purposes, we have:
- MPMetadata: Metadata information
- MPSection: Section content
- MPFlow: Process flow
- MPValidation: Validation results
- MPDiff: Diff tracking

**Responsibility**: Type-specific MP model definitions
**Reason to Change**: When a specific model type's structure changes

Note: Model creation, validation, and conversion are in separate modules:
- Factory methods: builders/mp_builder.py
- Validation: validators/mp_validators.py
- Conversion: converters/mp_converters.py
"""

from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Tuple, Any


# ============================================================================
# MP Metadata Model
# ============================================================================

@dataclass
class MPMetadata:
    """
    Metadata information for Memory/Metadata Protocol.
    
    **Responsibility**: Encapsulate metadata fields
    **Reason to Change**: When metadata structure changes
    """
    
    file_path: str = ""
    purpose: str = ""
    current_line: int = 0
    scope: Optional[str] = None
    related_project: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ============================================================================
# MP Section Model
# ============================================================================

@dataclass
class MPSection:
    """
    Section content in Memory/Metadata Protocol.
    
    **Responsibility**: Encapsulate section-specific fields
    **Reason to Change**: When section structure changes
    """
    
    file_path: str = ""
    name: str = ""  # Section title
    content: Optional[str] = None
    level: int = 0
    line_start: int = 0
    line_end: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    def get_line_count(self) -> int:
        """Get the number of lines in this section."""
        return max(0, self.line_end - self.line_start + 1)


# ============================================================================
# MP Flow Model
# ============================================================================

@dataclass
class MPFlow:
    """
    Process flow in Memory/Metadata Protocol.
    
    **Responsibility**: Encapsulate flow-specific fields
    **Reason to Change**: When flow structure changes
    """
    
    file_path: str = ""
    name: str = ""  # Flow name
    content: Optional[str] = None  # Flow text
    connections: List[str] = field(default_factory=list)
    line_start: int = 0
    line_end: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ============================================================================
# MP Validation Model
# ============================================================================

@dataclass
class MPValidation:
    """
    Validation result in Memory/Metadata Protocol.
    
    **Responsibility**: Encapsulate validation-specific fields
    **Reason to Change**: When validation structure changes
    """
    
    file_path: str = ""
    line_number: Optional[int] = None
    severity: Optional[str] = None  # 'error', 'warning', 'info'
    message: Optional[str] = None
    suggestion: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    def is_error(self) -> bool:
        """Check if this is an error-level validation."""
        return self.severity == "error"
    
    def is_warning(self) -> bool:
        """Check if this is a warning-level validation."""
        return self.severity == "warning"
    
    def is_blocking(self) -> bool:
        """Check if this validation is blocking."""
        return self.severity == "error"


# ============================================================================
# MP Diff Model
# ============================================================================

@dataclass
class MPDiff:
    """
    Diff tracking in Memory/Metadata Protocol.
    
    **Responsibility**: Encapsulate diff-specific fields
    **Reason to Change**: When diff structure changes
    """
    
    file_path: str = ""
    
    # Metadata changes
    metadata_changes: Dict[str, Tuple[str, str]] = field(default_factory=dict)  # {key: (old, new)}
    
    # Section changes
    sections_added: List[str] = field(default_factory=list)
    sections_removed: List[str] = field(default_factory=list)
    sections_modified: List[str] = field(default_factory=list)
    line_count_change: Tuple[int, int] = (0, 0)  # (old_count, new_count)
    
    # Flow changes
    flow_changes: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    def has_changes(self) -> bool:
        """Check if there are any changes."""
        return (
            bool(self.metadata_changes)
            or bool(self.sections_added)
            or bool(self.sections_removed)
            or bool(self.sections_modified)
            or bool(self.flow_changes)
        )


__all__ = [
    "MPMetadata",
    "MPSection",
    "MPFlow",
    "MPValidation",
    "MPDiff",
]
