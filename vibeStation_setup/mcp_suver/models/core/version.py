"""
Version information model.

**Single Responsibility**: Define version data structure (N1.N2.N3 format).
This module is changed only when version structure needs modification.

**Responsibility**: Version data model
**Reason to Change**: When version numbering scheme changes

Migrated from:
- doc_management/template_generator.py

Architecture:
- Semantic versioning support (N1.N2.N3)
- Increment helpers for major/minor/patch
- String representation
"""

from dataclasses import dataclass, asdict
from typing import Dict, Any


@dataclass
class VersionInfo:
    """
    Version information in N1.N2.N3 format (semantic versioning).
    
    Attributes:
        major: Major version number (N1) - Breaking changes
        minor: Minor version number (N2) - Feature additions
        patch: Patch version number (N3) - Bug fixes
    """
    major: int  # N1 - Major changes
    minor: int  # N2 - Medium changes  
    patch: int  # N3 - Small changes
    
    def __str__(self) -> str:
        """String representation in N1.N2.N3 format."""
        return f"{self.major}.{self.minor}.{self.patch}"
    
    def increment_major(self) -> "VersionInfo":
        """
        Increment major version (N1 +1, N2=0, N3=0).
        
        Use for breaking changes.
        
        Returns:
            New VersionInfo with incremented major version
        """
        return VersionInfo(self.major + 1, 0, 0)
    
    def increment_minor(self) -> "VersionInfo":
        """
        Increment minor version (N2 +1, N3=0).
        
        Use for feature additions.
        
        Returns:
            New VersionInfo with incremented minor version
        """
        return VersionInfo(self.major, self.minor + 1, 0)
    
    def increment_patch(self) -> "VersionInfo":
        """
        Increment patch version (N3 +1).
        
        Use for bug fixes.
        
        Returns:
            New VersionInfo with incremented patch version
        """
        return VersionInfo(self.major, self.minor, self.patch + 1)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VersionInfo":
        """Create from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
    
    @classmethod
    def parse(cls, version_str: str) -> "VersionInfo":
        """
        Parse version string to VersionInfo.
        
        Args:
            version_str: Version string in "N1.N2.N3" format
            
        Returns:
            VersionInfo instance
            
        Examples:
            >>> VersionInfo.parse("1.2.3")
            VersionInfo(major=1, minor=2, patch=3)
            >>> VersionInfo.parse("invalid")
            VersionInfo(major=1, minor=0, patch=0)  # Default fallback
            >>> VersionInfo.parse("1.2")
            VersionInfo(major=1, minor=0, patch=0)  # Default fallback - requires all 3 parts
        """
        try:
            parts = version_str.split('.')
            if len(parts) != 3:
                # Requires exactly 3 parts for valid version
                return cls(1, 0, 0)
            return cls(int(parts[0]), int(parts[1]), int(parts[2]))
        except (ValueError, IndexError):
            return cls(1, 0, 0)  # Default fallback


__all__ = ["VersionInfo"]
