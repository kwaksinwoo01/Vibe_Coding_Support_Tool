"""
WPD template definitions for L0-L3 grades.

Provides template structure and required sections for each WPD grade.
"""

from typing import Dict, List


# WPD Grade L0 Template
wpd_0_template = {
    "name": "L0 Template",
    "grade": "L0",
    "required_sections": [
        "Goal",
        "Success Criteria",
        "Scope",
        "Work Progress"
    ],
    "content": """# {title}

**WPD_grade**: L0
**Version**: 1.0.0
**Status**: 📋 PENDING

## Goal

{goal}

## Success Criteria

{success_criteria}

## Scope

{scope}

## Work Progress

- [ ] Task 1
- [ ] Task 2
- [ ] Task 3
"""
}

# WPD Grade L1 Template
wpd_1_template = {
    "name": "L1 Template",
    "grade": "L1",
    "required_sections": [
        "Goal",
        "Success Criteria",
        "Scope",
        "Implementation Summary",
        "Work Progress"
    ],
    "content": """# {title}

**WPD_grade**: L1
**Version**: 1.0.0
**Status**: 📋 PENDING

## Goal

{goal}

## Success Criteria

{success_criteria}

## Scope

{scope}

## Implementation Summary

{implementation_summary}

## Work Progress

- [ ] Task 1
- [ ] Task 2
- [ ] Task 3
"""
}

# WPD Grade L2 Template
wpd_2_template = {
    "name": "L2 Template",
    "grade": "L2",
    "required_sections": [
        "Goal",
        "Success Criteria",
        "Scope",
        "Implementation Summary",
        "Test Results",
        "Work Progress"
    ],
    "content": """# {title}

**WPD_grade**: L2
**Version**: 1.0.0
**Status**: 📋 PENDING

## Goal

{goal}

## Success Criteria

{success_criteria}

## Scope

{scope}

## Implementation Summary

{implementation_summary}

## Test Results

{test_results}

## Work Progress

- [ ] Task 1
- [ ] Task 2
- [ ] Task 3
"""
}

# WPD Grade L3 Template
wpd_3_template = {
    "name": "L3 Template",
    "grade": "L3",
    "required_sections": [
        "Goal",
        "Success Criteria",
        "Scope",
        "Implementation Summary",
        "Test Results",
        "Blockers and Workarounds",
        "Work Progress"
    ],
    "content": """# {title}

**WPD_grade**: L3
**Version**: 1.0.0
**Status**: 📋 PENDING

## Goal

{goal}

## Success Criteria

{success_criteria}

## Scope

{scope}

## Implementation Summary

{implementation_summary}

## Test Results

{test_results}

## Blockers and Workarounds

{blockers}

## Work Progress

- [ ] Task 1
- [ ] Task 2
- [ ] Task 3
"""
}

# Template registry
WPD_TEMPLATES = {
    "L0": wpd_0_template,
    "L1": wpd_1_template,
    "L2": wpd_2_template,
    "L3": wpd_3_template,
}


def get_template_for_grade(grade: str) -> Dict:
    """
    Get template for a given WPD grade.
    
    Args:
        grade: WPD grade (L0, L1, L2, L3)
        
    Returns:
        Template dictionary
    """
    return WPD_TEMPLATES.get(grade, wpd_0_template)


def get_required_sections(grade: str) -> List[str]:
    """
    Get required sections for a given WPD grade.
    
    Args:
        grade: WPD grade (L0, L1, L2, L3)
        
    Returns:
        List of required section names
    """
    template = get_template_for_grade(grade)
    return template.get("required_sections", [])


__all__ = [
    "wpd_0_template",
    "wpd_1_template",
    "wpd_2_template",
    "wpd_3_template",
    "WPD_TEMPLATES",
    "get_template_for_grade",
    "get_required_sections",
]
