"""
Document builder for creating WPDDocument instances.

**Single Responsibility**: Create WPDDocument instances.
This module is changed only when document creation logic changes.

**Responsibility**: WPDDocument creation and initialization
**Reason to Change**: When document creation patterns or defaults change
"""

from typing import Optional, List
from ..core import WPDDocument


def create_wpd_document(
    Part_N: str,
    wpd_grade: str,
    title: str,
    description: str = "",
    parent_document: Optional[str] = None,
    child_documents: Optional[List[str]] = None,
) -> WPDDocument:
    """
    Create a WPDDocument instance.
    
    Args:
        Part_N: Step number
        wpd_grade: WPD grade (L0-L3)
        title: Document title
        description: Document description
        parent_document: Parent document path
        child_documents: Child document paths
    
    Returns:
        WPDDocument instance
    """
    return WPDDocument(
        Part_N=Part_N,
        wpd_grade=wpd_grade,
        title=title,
        description=description,
        parent_document=parent_document,
        child_documents=child_documents or [],
    )


__all__ = [
    "create_wpd_document",
]
