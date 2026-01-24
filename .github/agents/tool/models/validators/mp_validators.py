"""
MP model validators.

**Single Responsibility**: Validate MP model data structures.
This module is changed only when MP model validation rules change.

**Responsibility**: MP model validation logic
**Reason to Change**: When MP model validation rules change
"""

from typing import List, Any


def validate_mp_metadata(metadata: Any) -> List[str]:
    """
    Validate MPMetadata structure.
    
    Args:
        metadata: MPMetadata instance to validate
    
    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []
    
    if not metadata.file_path:
        errors.append("file_path is required")
    
    return errors


def validate_mp_section(section: Any) -> List[str]:
    """
    Validate MPSection structure.
    
    Args:
        section: MPSection instance to validate
    
    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []
    
    if not section.file_path:
        errors.append("file_path is required")
    
    if not section.name:
        errors.append("name is required")
    
    if section.line_end < section.line_start:
        errors.append("line_end must be >= line_start")
    
    return errors


def validate_mp_validation(validation: Any) -> List[str]:
    """
    Validate MPValidation structure.
    
    Args:
        validation: MPValidation instance to validate
    
    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []
    
    if not validation.file_path:
        errors.append("file_path is required")
    
    valid_severities = ["error", "warning", "info"]
    if validation.severity and validation.severity not in valid_severities:
        errors.append(f"Invalid severity: {validation.severity}. Must be one of {valid_severities}")
    
    return errors


__all__ = [
    "validate_mp_metadata",
    "validate_mp_section",
    "validate_mp_validation",
]
