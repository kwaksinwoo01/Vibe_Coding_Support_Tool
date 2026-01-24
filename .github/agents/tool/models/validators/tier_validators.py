"""
Tier-specific state validators.

**Single Responsibility**: Validate tier-specific state data structures.
This module is changed only when validation rules for tier states change.

**Responsibility**: Tier state validation logic
**Reason to Change**: When validation rules for tier states change
"""

from typing import List, Dict, Any


def validate_tier_a_state(state: Any) -> List[str]:
    """
    Validate TierAState for Work Plan Creation.
    
    Args:
        state: TierAState instance to validate
    
    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []
    
    # Check required fields
    if not state.wpd_grade:
        errors.append("wpd_grade is required")
    
    if state.wpd_grade not in ["L0", "L1", "L2", "L3"]:
        errors.append(f"Invalid wpd_grade: {state.wpd_grade}")
    
    if not state.metadata or not state.metadata.Part_N:
        errors.append("metadata.Part_N is required")
    
    if not state.metadata or not state.metadata.document_title:
        errors.append("metadata.document_title is required")
    
    return errors


def validate_tier_b_state(state: Any) -> List[str]:
    """
    Validate TierBState for Plan Execution.
    
    Args:
        state: TierBState instance to validate
    
    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []
    
    # Check required fields
    if not state.wpd_source_path:
        errors.append("wpd_source_path is required")
    
    if state.sources and not state.sources.wpd_sources and not state.wpd_source_path:
        errors.append("Either wpd_source_path or sources.wpd_sources must be provided")
    
    return errors


def validate_tier_c_state(state: Any) -> List[str]:
    """
    Validate TierCState for Plan Modification.
    
    Args:
        state: TierCState instance to validate
    
    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []
    
    # Check required fields
    if not state.wpd_path:
        errors.append("wpd_path is required")
    
    if not state.creation_context or not state.creation_context.documents_to_create:
        if not state.modifications:
            errors.append("Either documents_to_create or modifications must be provided")
    
    return errors


def validate_tier_d_state(state: Any) -> List[str]:
    """
    Validate TierDState for Issue Analysis.
    
    Args:
        state: TierDState instance to validate
    
    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []
    
    # Check required fields
    if not state.issue_description:
        errors.append("issue_description is required")
    
    return errors


def validate_tier_e_state(state: Any) -> List[str]:
    """
    Validate TierEState for Document Management.
    
    Args:
        state: TierEState instance to validate
    
    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []
    
    # Check required fields
    if not state.sources or not state.sources.prd_path:
        errors.append("sources.prd_path is required")
    
    return errors


def validate_tier_f_state(state: Any) -> List[str]:
    """
    Validate TierFState for Unknown Logic.
    
    Args:
        state: TierFState instance to validate
    
    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []
    
    # Check required fields
    if not state.user_request:
        errors.append("user_request is required")
    
    return errors


__all__ = [
    "validate_tier_a_state",
    "validate_tier_b_state",
    "validate_tier_c_state",
    "validate_tier_d_state",
    "validate_tier_e_state",
    "validate_tier_f_state",
]
