"""
Tier state builders for creating tier-specific state instances.

**Single Responsibility**: Create tier state instances.
This module is changed only when tier state creation logic changes.

**Responsibility**: Tier state creation and initialization
**Reason to Change**: When tier state creation patterns or defaults change
"""

from typing import Optional, Dict, Any, List
from ..core import (
    TierAState,
    TierBState,
    TierCState,
    TierDState,
    TierEState,
    TierFState,
    DocumentMetadata,
    DocumentHierarchy,
    DocumentSources,
    DocumentCreationContext,
)


def create_tier_a_state(
    Part_N: str = "",
    document_title: str = "",
    parent_document: Optional[str] = None,
    version: str = "1.0.0",
) -> TierAState:
    """
    Create a TierAState for work plan creation.
    
    Note: wpd_grade is now in AgentState, not TierAState.
    
    Example usage:
        tier_a = create_tier_a_state(Part_N="5", document_title="Feature")
        state = AgentState(tier="A", status="PENDING")
        state.wpd_grade = "L1"  # Set wpd_grade on AgentState
        state.payload = tier_a.to_payload()
    
    Args:
        Part_N: Step number
        document_title: Document title
        parent_document: Parent document path
        version: Document version
    
    Returns:
        TierAState instance
    """
    metadata = DocumentMetadata(
        document_type="WPD",
        Part_N=Part_N,
        document_title=document_title,
        version=version,
    )
    
    hierarchy = DocumentHierarchy(
        parent_document=parent_document,
    )
    
    return TierAState(
        metadata=metadata,
        hierarchy=hierarchy,
    )


def create_tier_b_state(
    wpd_sources: Optional[List[str]] = None,
    prd_path: Optional[str] = None,
) -> TierBState:
    """
    Create a TierBState for plan execution.
    
    Note: wpd_source_path is now in AgentState, not TierBState.
    Set wpd_source_path on the AgentState when creating the full state.
    
    Args:
        wpd_sources: List of WPD sources
        prd_path: PRD output path
    
    Returns:
        TierBState instance
    """
    sources = DocumentSources(
        wpd_sources=wpd_sources or [],
        prd_path=prd_path,
    )
    
    return TierBState(
        sources=sources,
    )


def create_tier_c_state(
    wpd_path: str = "",
    documents_to_create: Optional[List[str]] = None,
    parent_document_path: Optional[str] = None,
) -> TierCState:
    """
    Create a TierCState for plan modification.
    
    Args:
        wpd_path: Path to WPD to modify
        documents_to_create: Documents to create
        parent_document_path: Parent document path
    
    Returns:
        TierCState instance
    """
    context = DocumentCreationContext(
        documents_to_create=documents_to_create or [],
        parent_document_path=parent_document_path,
    )
    
    return TierCState(
        wpd_path=wpd_path,
        creation_context=context,
    )


def create_tier_d_state(
    issue_description: str = "",
    error_details: Optional[Dict[str, Any]] = None,
) -> TierDState:
    """
    Create a TierDState for issue analysis.
    
    Args:
        issue_description: Description of the issue
        error_details: Error details dictionary
    
    Returns:
        TierDState instance
    """
    return TierDState(
        issue_description=issue_description,
        error_details=error_details or {},
    )


def create_tier_e_state(
    wpd_sources: Optional[List[str]] = None,
    prd_path: Optional[str] = None,
) -> TierEState:
    """
    Create a TierEState for document management.
    
    Args:
        wpd_sources: WPD source paths
        prd_path: PRD path
    
    Returns:
        TierEState instance
    """
    sources = DocumentSources(
        wpd_sources=wpd_sources or [],
        prd_path=prd_path,
    )
    
    return TierEState(sources=sources)


def create_tier_f_state(
    user_request: str = "",
) -> TierFState:
    """
    Create a TierFState for unknown logic (fallback).
    
    Args:
        user_request: Original user request
    
    Returns:
        TierFState instance
    """
    return TierFState(user_request=user_request)


__all__ = [
    "create_tier_a_state",
    "create_tier_b_state",
    "create_tier_c_state",
    "create_tier_d_state",
    "create_tier_e_state",
    "create_tier_f_state",
]
