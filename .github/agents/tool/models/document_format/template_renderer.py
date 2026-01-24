"""
Template rendering for WPD templates.

**Single Responsibility**: Render WPD templates with data.
This module is changed only when template rendering logic changes.

**Responsibility**: WPD template rendering
**Reason to Change**: When template rendering behavior changes
"""

from typing import Optional, Dict, Any
from ..core import TierAState
from .templates import wpd_0_template, wpd_1_template, wpd_2_template, wpd_3_template


def render_wpd_template(grade: str, tier_a_state: Optional[TierAState] = None) -> str:
    """
    Render a WPD template with data from TierAState.
    
    Args:
        grade: WPD grade (L0, L1, L2, L3)
        tier_a_state: Optional TierAState with metadata for injection
    
    Returns:
        Rendered template content
    """
    templates = {
        "L0": wpd_0_template,
        "L1": wpd_1_template,
        "L2": wpd_2_template,
        "L3": wpd_3_template,
    }
    
    template_class = templates.get(grade)
    if not template_class:
        raise ValueError(f"Unknown WPD grade: {grade}")
    
    # Generate basic template structure
    content = generate_template_structure(template_class, tier_a_state)
    
    return content


def generate_template_structure(template_class: type, state: Optional[TierAState]) -> str:
    """
    Generate template structure from template class.
    
    Args:
        template_class: Template class (wpd_*_template)
        state: Optional TierAState with metadata
    
    Returns:
        Template structure as string
    """
    grade = template_class.GRADE
    
    # Get title and metadata from state if available
    title = state.metadata.document_title if state and state.metadata else "New WPD Document"
    step = state.metadata.Part_N if state and state.metadata else ""
    
    lines = [
        f"# {title}",
        "",
        "## Document Metadata",
        f"- **Grade**: {grade}",
        f"- **Step**: {step}",
        "",
    ]
    
    # Add required sections
    for section in template_class.REQUIRED_SECTIONS:
        lines.append(section)
        description = template_class.SECTION_DESCRIPTIONS.get(section, "")
        if description:
            lines.append(f"> {description}")
        lines.append("")
    
    return "\n".join(lines)


__all__ = [
    "render_wpd_template",
    "generate_template_structure",
]
