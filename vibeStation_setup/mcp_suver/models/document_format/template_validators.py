"""
Template validators for WPD templates.

**Single Responsibility**: Validate template structure and required sections.
This module is changed only when template validation rules change.

**Responsibility**: Template validation logic
**Reason to Change**: When template structure or required sections change
"""

from typing import List


def validate_template_structure(content: str, grade: str) -> List[str]:
    """
    Validate WPD template structure and required sections.
    
    Args:
        content: Template content to validate
        grade: WPD grade (L0, L1, L2, L3)
    
    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []
    
    # Get required sections for grade
    required_sections = get_required_sections_for_grade(grade)
    
    # Check for required sections
    for section in required_sections:
        if section not in content:
            errors.append(f"Missing required section: {section}")
    
    return errors


def validate_required_sections(content: str, grade: str) -> List[str]:
    """
    Validate that all required sections are present.
    
    Args:
        content: Template content to validate
        grade: WPD grade (L0, L1, L2, L3)
    
    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []
    
    required_sections = get_required_sections_for_grade(grade)
    
    for section in required_sections:
        if section not in content:
            errors.append(f"Missing required section: {section}")
    
    return errors


def get_required_sections_for_grade(grade: str) -> List[str]:
    """
    Get required sections for a WPD grade.
    
    Args:
        grade: WPD grade (L0, L1, L2, L3)
    
    Returns:
        List of required section headers
    """
    sections_map = {
        "L0": [
            "## Executive Summary",
            "## Goals and Success Criteria",
            "## Three-Tier Documentation",
            "## References",
        ],
        "L1": [
            "## Executive Summary",
            "## Goals and Success Criteria",
            "## Execution Plan",
            "## References",
        ],
        "L2": [
            "## Overview",
            "## Goals and Success Criteria",
            "## Audit results",
            "## Implementation Plan",
            "## Implementation Notes",
            "## References",
        ],
        "L3": [
            "## Overview",
            "## Success Criteria",
            "## Implementation Steps",
            "## Implementation Notes",
            "## References",
        ],
    }
    
    return sections_map.get(grade, [])


__all__ = [
    "validate_template_structure",
    "validate_required_sections",
    "get_required_sections_for_grade",
]
