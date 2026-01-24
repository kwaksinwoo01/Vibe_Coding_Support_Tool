"""
Template validators for document templates.

Validates template structure and required sections.
"""

from typing import Dict, List, Optional


def validate_template_structure(template: Dict) -> bool:
    """
    Validate that a template has the required structure.
    
    Args:
        template: Template dictionary to validate
        
    Returns:
        True if valid, False otherwise
    """
    required_keys = ["name", "content"]
    return all(key in template for key in required_keys)


def validate_required_sections(content: str, required_sections: List[str]) -> bool:
    """
    Validate that content contains all required sections.
    
    Args:
        content: Document content to validate
        required_sections: List of section names that must be present
        
    Returns:
        True if all sections present, False otherwise
    """
    for section in required_sections:
        if f"## {section}" not in content and f"# {section}" not in content:
            return False
    return True


__all__ = [
    "validate_template_structure",
    "validate_required_sections",
]
