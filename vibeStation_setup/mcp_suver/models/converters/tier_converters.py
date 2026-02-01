"""
Tier state converters for chaining between tier executions.

**Single Responsibility**: Convert data between different tier states.
This module is changed only when tier conversion logic changes.

**Responsibility**: Tier state conversion logic
**Reason to Change**: When conversion rules between tiers change
"""

from typing import Optional, Dict, Any
from ..core import TierAState, TierBState, TierCState, TierDState, TierEState, TierFState, DocumentSources


def tier_a_to_tier_b(tier_a: TierAState) -> TierBState:
    """
    Convert TierAState to TierBState for plan execution.
    
    Note: wpd_source_path is in AgentState, not TierBState.
    
    Example usage:
        tier_b = tier_a_to_tier_b(tier_a)
        state = AgentState(tier="B", status="PENDING")
        state.wpd_source_path = tier_a.created_documents[0] if tier_a.created_documents else ""
        state.payload = tier_b.to_payload()
    
    Args:
        tier_a: TierAState with created documents
    
    Returns:
        TierBState ready for execution
    """
    sources = DocumentSources(
        wpd_sources=tier_a.created_documents.copy(),
        prd_path=None,
        execution_report_path=None,
    )
    
    tier_b = TierBState(
        sources=sources,
    )
    
    return tier_b


def tier_b_to_tier_e(tier_b: TierBState, prd_path: str = "") -> TierEState:
    """
    Convert TierBState to TierEState for document management.
    
    Args:
        tier_b: TierBState with execution results
        prd_path: PRD document path
    
    Returns:
        TierEState ready for document management
    """
    sources = DocumentSources(
        wpd_sources=tier_b.sources.wpd_sources.copy(),
        prd_path=prd_path or tier_b.sources.prd_path,
        execution_report_path=tier_b.sources.execution_report_path,
    )
    
    tier_e = TierEState(sources=sources)
    
    return tier_e


def tier_c_to_tier_e(tier_c: TierCState) -> TierEState:
    """
    Convert TierCState to TierEState for document management.
    
    Args:
        tier_c: TierCState with modifications
    
    Returns:
        TierEState ready for document management
    """
    sources = DocumentSources(
        wpd_sources=tier_c.modified_documents.copy(),
        prd_path=None,
        execution_report_path=None,
    )
    
    tier_e = TierEState(sources=sources)
    
    return tier_e


def tier_d_to_tier_c(tier_d: TierDState, wpd_path: str = "") -> TierCState:
    """
    Convert TierDState to TierCState for applying fixes.
    
    Args:
        tier_d: TierDState with analysis results
        wpd_path: WPD document path to modify
    
    Returns:
        TierCState ready for modifications
    """
    tier_c = TierCState(
        wpd_path=wpd_path,
    )
    
    # Convert suggested fixes to modifications
    for fix in tier_d.suggested_fixes:
        tier_c.modifications.append({"description": fix})
    
    return tier_c


def tier_c_to_tier_a(tier_c: TierCState) -> TierAState:
    """
    Convert TierCState to TierAState for document creation.
    
    Used when Tier C needs to delegate document creation to Tier A.
    
    Note: execution_log is in AgentState, not tier states.
    The calling code should manage execution_log in AgentState.
    
    Args:
        tier_c: TierCState with creation context
    
    Returns:
        TierAState ready for document creation
    """
    from ..core import DocumentMetadata, DocumentHierarchy
    
    tier_a = TierAState()
    
    # Transfer creation context
    tier_a.metadata = DocumentMetadata(
        document_type="WPD",
        Part_N=tier_c.creation_context.creation_parameters.get("Part_N", ""),
        document_title="",
    )
    
    tier_a.hierarchy = DocumentHierarchy(
        parent_document=tier_c.creation_context.parent_document_path,
    )
    
    return tier_a


def tier_a_to_tier_c(tier_a: TierAState, tier_c: TierCState) -> TierCState:
    """
    Merge TierAState results back into TierCState.
    
    Used after Tier A completes document creation delegated by Tier C.
    
    Note: execution_log is in AgentState, not tier states.
    The calling code should manage execution_log in AgentState.
    
    Args:
        tier_a: TierAState with creation results
        tier_c: Original TierCState to merge into
    
    Returns:
        Updated TierCState with merged results
    """
    # Merge created documents
    tier_c.modified_documents.extend(tier_a.created_documents)
    
    # Clear creation queue
    tier_c.creation_context.documents_to_create = []
    
    return tier_c


class TierStateConverter:
    """
    Facade for tier state conversion operations.
    
    Provides convenient class methods for all tier conversions.
    """
    
    @staticmethod
    def a_to_b(tier_a: TierAState) -> TierBState:
        """Convert Tier A to Tier B."""
        return tier_a_to_tier_b(tier_a)
    
    @staticmethod
    def b_to_e(tier_b: TierBState, prd_path: str = "") -> TierEState:
        """Convert Tier B to Tier E."""
        return tier_b_to_tier_e(tier_b, prd_path)
    
    @staticmethod
    def c_to_e(tier_c: TierCState) -> TierEState:
        """Convert Tier C to Tier E."""
        return tier_c_to_tier_e(tier_c)
    
    @staticmethod
    def d_to_c(tier_d: TierDState, wpd_path: str = "") -> TierCState:
        """Convert Tier D to Tier C."""
        return tier_d_to_tier_c(tier_d, wpd_path)
    
    @staticmethod
    def c_to_a(tier_c: TierCState) -> TierAState:
        """Convert Tier C to Tier A for document creation."""
        return tier_c_to_tier_a(tier_c)
    
    @staticmethod
    def a_to_c(tier_a: TierAState, tier_c: TierCState) -> TierCState:
        """Merge Tier A results back into Tier C."""
        return tier_a_to_tier_c(tier_a, tier_c)


__all__ = [
    "tier_a_to_tier_b",
    "tier_b_to_tier_e",
    "tier_c_to_tier_e",
    "tier_d_to_tier_c",
    "tier_c_to_tier_a",
    "tier_a_to_tier_c",
    "TierStateConverter",
]
