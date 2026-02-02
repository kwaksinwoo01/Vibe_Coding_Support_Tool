"""
WPD Template definitions for L0-L3 grade documents.

**Single Responsibility**: Define template structure and required sections for each WPD grade.
This module is changed only when template structure or required sections change.

**Responsibility**: WPD template definitions
**Reason to Change**: When template structure or required sections change

Note: Template rendering, validation, and generation are in separate modules:
- Rendering: formatters/template_renderer.py
- Validation: validators/template_validators.py
- Generation: builders/template_builder.py
"""

from typing import List


class wpd_0_template:
    """
    L0 WPD Template (Main Work Plan Document).

    Used for top-level task documents that organize multiple L1 work plans.
    This is the entry point in the Three-Tier Documentation hierarchy.

    Main sections:
    - ## Part [Part_N]: [Part_name]
    - ### Executive Summary
    - ### Goals and Success Criteria
    - ### child_documents
    - ### Tasks
    - #### Part [Part_N].[Phase_N]: [Phase Title]
    ... (repeat for each phase)
    """

    GRADE = "L0"
    REQUIRED_SECTIONS = [
        "## Part [Part_N]: [Part_name]",
        "### Executive Summary",
        "### Goals and Success Criteria",
        "### child_documents",
        "### Tasks",
        "#### Part [Part_N].[Phase_N]: [Phase Title]"
    ]

    SECTION_DESCRIPTIONS = {
        "## Part [Part_N]: [Part_name]": "Defines a major part of the work plan",
        "### Executive Summary": "High-level overview of the task",
        "### Goals and Success Criteria": "Goals and measurable success criteria",
        "### child_documents": "Links to L1 work plans and PRD documents",
        "### References": "Parent and related documents",
        "### Tasks": "List of tasks and their statuses",
        "#### Part [Part_N].[Phase_N]: [Phase Title]": "Details for each phase within the part",
    }


class wpd_1_template:
    """
    L1 WPD Template (Executive Level).

    Main sections per specification:
    - ## Executive Summary
    - ## Goals and Success Criteria
    - ## Execution Plan
    - ### Phase [Part_N].[Phase_N]: [Phase Title]
    - ## References
    """

    GRADE = "L1"
    REQUIRED_SECTIONS = [
        "## Executive Summary",
        "## Goals and Success Criteria",
        "## Execution Plan",
        "## References",
    ]

    SECTION_DESCRIPTIONS = {
        "## Executive Summary": "Overview of the work plan",
        "## Goals and Success Criteria": "Goals and success criteria for this level",
        "## Execution Plan": "Phases and their components",
        "## References": "Parent (L0) and child (L2) documents",
    }


class wpd_2_template:
    """
    L2 WPD Template (Phase Level).

    Main sections per specification:
    - ## Overview
    - ## Goals and Success Criteria
    - ## Audit results
    - ## Implementation Plan
    - ### Subphase [Part_N].[Phase_N].[Subphase_N]: [Subphase Title]
    - ## Implementation Notes
    - ## References
    """

    GRADE = "L2"
    REQUIRED_SECTIONS = [
        "## Overview",
        "## Goals and Success Criteria",
        "## Audit results",
        "## Implementation Plan",
        "## Implementation Notes",
        "## References",
    ]

    SECTION_DESCRIPTIONS = {
        "## Overview": "Phase overview and scope",
        "## Goals and Success Criteria": "Phase-level goals",
        "## Audit results": "Results from audit/review",
        "## Implementation Plan": "Implementation details",
        "## Implementation Notes": "Additional notes and considerations",
        "## References": "Parent (L1) and child (L3) documents",
    }


class wpd_3_template:
    """
    L3 WPD Template (Subphase Level).

    Main sections per specification:
    - ## Overview
    - ## Success Criteria
    - ## Implementation Steps
    - ## Implementation Notes
    - ## References
    """

    GRADE = "L3"
    REQUIRED_SECTIONS = [
        "## Overview",
        "## Success Criteria",
        "## Implementation Steps",
        "## Implementation Notes",
        "## References",
    ]

    SECTION_DESCRIPTIONS = {
        "## Overview": "Detailed overview of this subphase",
        "## Success Criteria": "Specific success criteria",
        "## Implementation Steps": "Step-by-step implementation",
        "## Implementation Notes": "Notes and considerations",
        "## References": "Parent (L2) document and related resources",
    }


# Template registry for easy access
WPD_TEMPLATES = {
    "L0": wpd_0_template,
    "L1": wpd_1_template,
    "L2": wpd_2_template,
    "L3": wpd_3_template,
}


def get_template_for_grade(grade: str) -> type:
    """
    Get the template class for a WPD grade.
    
    Args:
        grade: WPD grade (L0, L1, L2, L3)
    
    Returns:
        Template class for the grade
    
    Raises:
        ValueError: If grade is not recognized
    """
    if grade not in WPD_TEMPLATES:
        raise ValueError(f"Unknown WPD grade: {grade}")
    return WPD_TEMPLATES[grade]


def get_required_sections(grade: str) -> List[str]:
    """
    Get the required sections for a WPD grade.
    
    Args:
        grade: WPD grade (L0, L1, L2, L3)
    
    Returns:
        List of required section headers
    """
    template = get_template_for_grade(grade)
    return template.REQUIRED_SECTIONS


__all__ = [
    "wpd_0_template",
    "wpd_1_template",
    "wpd_2_template",
    "wpd_3_template",
    "WPD_TEMPLATES",
    "get_template_for_grade",
    "get_required_sections",
]
