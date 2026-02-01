"""
Document validators for WPD and PRD documents.

**Single Responsibility**: Validate WPD document data structures.
This module is changed only when document validation rules change.

**Responsibility**: WPD document validation logic
**Reason to Change**: When document validation rules change
"""

from typing import List, Any
import re


def validate_wpd_document(doc: Any) -> List[str]:
    """
    Validate WPDDocument structure.
    
    Args:
        doc: WPDDocument instance to validate
    
    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []
    
    # Check required fields
    if not doc.Part_N:
        errors.append("Part_N is required")
    
    if not doc.wpd_grade:
        errors.append("wpd_grade is required")
    else:
        wpd_errors = validate_wpd_grade(doc.wpd_grade)
        errors.extend(wpd_errors)
    
    if not doc.title:
        errors.append("title is required")
    
    # Validate Part_N format
    step_errors = validate_Part_N(doc.Part_N, doc.wpd_grade)
    errors.extend(step_errors)
    
    # Validate hierarchy
    if doc.wpd_grade != "L0":
        if not doc.parent_document:
            errors.append(f"parent_document is required for {doc.wpd_grade}")
    
    return errors


def validate_wpd_grade(grade: str) -> List[str]:
    """
    Validate WPD grade format.
    
    Args:
        grade: WPD grade to validate (L0, L1, L2, L3)
    
    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []
    
    valid_grades = ["L0", "L1", "L2", "L3"]
    if grade not in valid_grades:
        errors.append(f"Invalid wpd_grade: {grade}. Must be one of {valid_grades}")
    
    return errors


def validate_Part_N(Part_N: str, wpd_grade: str) -> List[str]:
    """
    Validate step number format for WPD grade level.
    
    Args:
        Part_N: Step number (e.g., "5", "5.2", "5.2.1")
        wpd_grade: WPD grade (L0, L1, L2, L3)
    
    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []
    
    # Basic format validation
    if not re.match(r'^\d+(\.\d+)*$', Part_N):
        errors.append(f"Invalid Part_N format: {Part_N}. Expected format: '5' or '5.2' or '5.2.1'")
        return errors
    
    # Grade-specific depth validation
    depth = Part_N.count(".") + 1
    
    grade_depth_map = {
        "L0": 1,
        "L1": 1,
        "L2": 2,
        "L3": 3,
    }
    
    expected_depth = grade_depth_map.get(wpd_grade, 1)
    
    # Allow flexibility: L2 can be "5" or "5.2", L3 can be "5" or "5.2" or "5.2.1"
    if wpd_grade == "L2" and depth > 2:
        errors.append(f"Part_N depth {depth} is too deep for {wpd_grade}")
    elif wpd_grade == "L3" and depth > 3:
        errors.append(f"Part_N depth {depth} is too deep for {wpd_grade}")
    
    return errors


def validate_document_hierarchy(doc: Any) -> List[str]:
    """
    Validate WPDDocument hierarchy relationships.
    
    Args:
        doc: WPDDocument instance to validate
    
    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []
    
    # L0 should not have parent
    if doc.wpd_grade == "L0" and doc.parent_document:
        errors.append("L0 documents should not have a parent_document")
    
    # L1+ should have parent (except L0)
    if doc.wpd_grade != "L0" and not doc.parent_document:
        errors.append(f"{doc.wpd_grade} documents must have a parent_document")
    
    # Check for circular references
    if doc.parent_document and doc.parent_document in doc.child_documents:
        errors.append("Circular reference: parent document cannot be in child_documents")
    
    return errors


__all__ = [
    "validate_wpd_document",
    "validate_wpd_grade",
    "validate_Part_N",
    "validate_document_hierarchy",
]
