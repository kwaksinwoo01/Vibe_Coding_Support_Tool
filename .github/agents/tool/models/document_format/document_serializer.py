"""
Document serializers for WPDDocument.

**Single Responsibility**: Serialize/deserialize WPDDocument.
This module is changed only when document serialization format changes.

**Responsibility**: WPDDocument serialization
**Reason to Change**: When document serialization format changes
"""

from typing import Dict, Any
from ..core import WPDDocument


def serialize_wpd_document(doc: WPDDocument) -> Dict[str, Any]:
    """
    Serialize WPDDocument to dictionary.
    
    Args:
        doc: WPDDocument to serialize
    
    Returns:
        Dictionary representation of the document
    """
    return doc.to_dict()


def deserialize_wpd_document(data: Dict[str, Any]) -> WPDDocument:
    """
    Deserialize dictionary to WPDDocument.
    
    Args:
        data: Dictionary with document data
    
    Returns:
        WPDDocument instance
    """
    return WPDDocument.from_dict(data)


__all__ = [
    "serialize_wpd_document",
    "deserialize_wpd_document",
]
