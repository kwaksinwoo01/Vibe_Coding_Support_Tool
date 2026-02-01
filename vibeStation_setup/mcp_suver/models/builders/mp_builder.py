"""
MP model builder for creating MP model instances.

**Single Responsibility**: Create MP model instances.
This module is changed only when MP model creation logic changes.

**Responsibility**: MP model creation and initialization
**Reason to Change**: When MP model creation patterns change
"""

from typing import Optional, List, Dict, Tuple, Any
from ..core import (
    MPMetadata,
    MPSection,
    MPFlow,
    MPValidation,
    MPDiff,
)


def create_mp_metadata(
    file_path: str,
    purpose: str = "",
    scope: Optional[str] = None,
) -> MPMetadata:
    """Create MPMetadata instance."""
    return MPMetadata(
        file_path=file_path,
        purpose=purpose,
        scope=scope,
    )


def create_mp_section(
    file_path: str,
    name: str,
    content: str = "",
    line_start: int = 0,
    line_end: int = 0,
) -> MPSection:
    """Create MPSection instance."""
    return MPSection(
        file_path=file_path,
        name=name,
        content=content,
        line_start=line_start,
        line_end=line_end,
    )


def create_mp_validation(
    file_path: str,
    severity: str,
    message: str,
    line_number: Optional[int] = None,
) -> MPValidation:
    """Create MPValidation instance."""
    return MPValidation(
        file_path=file_path,
        severity=severity,
        message=message,
        line_number=line_number,
    )


__all__ = [
    "create_mp_metadata",
    "create_mp_section",
    "create_mp_validation",
]
