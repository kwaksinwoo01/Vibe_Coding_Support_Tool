"""
Document converters for WPDDocument transformations.

**Single Responsibility**: Convert between WPDDocument and tier states.
This module is changed only when document conversion logic changes.

**Responsibility**: WPDDocument conversion logic
**Reason to Change**: When conversion rules between documents and tier states change
"""

from typing import Optional
from ..core import WPDDocument, TierAState, TierEState, DocumentMetadata, DocumentHierarchy


def wpd_document_to_tier_a(doc: WPDDocument) -> TierAState:
    """
    Convert WPDDocument to TierAState.
    
    Note: wpd_grade is in AgentState, not TierAState.
    The calling code should set wpd_grade on AgentState from doc.wpd_grade.
    
    Args:
        doc: WPDDocument to convert
    
    Returns:
        TierAState with document data
    """
    metadata = DocumentMetadata.from_wpd_document(doc)
    hierarchy = DocumentHierarchy.from_wpd_document(doc)
    
    tier_a = TierAState(
        metadata=metadata,
        hierarchy=hierarchy,
    )
    
    return tier_a


def tier_a_to_wpd_document(tier_a: TierAState, wpd_grade: str) -> WPDDocument:
    """
    Convert TierAState to WPDDocument.
    
    Note: wpd_grade is in AgentState, not TierAState.
    Pass wpd_grade from AgentState.wpd_grade to this function.
    
    Example usage:
        state = AgentState(tier="A", status="SUCCESS", wpd_grade="L1")
        tier_a = TierAState()
        wpd_doc = tier_a_to_wpd_document(tier_a, wpd_grade=state.wpd_grade)
    
    Args:
        tier_a: TierAState to convert
        wpd_grade: WPD grade from AgentState (required)
    
    Returns:
        WPDDocument with state data
    """
    doc = WPDDocument(
        Part_N=tier_a.metadata.Part_N,
        wpd_grade=wpd_grade,
        title=tier_a.metadata.document_title,
        version=tier_a.metadata.version,
        status=tier_a.metadata.status,
        document_type=tier_a.metadata.document_type,
        parent_document=tier_a.hierarchy.parent_document,
        child_documents=tier_a.hierarchy.child_documents.copy(),
        reference_documents=tier_a.hierarchy.reference_documents.copy(),
    )
    
    return doc


__all__ = [
    "wpd_document_to_tier_a",
    "tier_a_to_wpd_document",
]
