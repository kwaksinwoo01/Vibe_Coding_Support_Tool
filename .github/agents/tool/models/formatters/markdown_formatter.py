"""
Markdown formatting for documents and states.

**Single Responsibility**: Format WPDDocument and tier states as Markdown.
This module is changed only when Markdown format changes.

**Responsibility**: Markdown formatting logic
**Reason to Change**: When Markdown format or presentation changes
"""

from typing import List
from datetime import datetime
from ..core import WPDDocument, TierAState


def format_wpd_document_as_markdown(doc: WPDDocument) -> str:
    """
    Format WPDDocument as Markdown.
    
    Args:
        doc: WPDDocument to format
    
    Returns:
        Markdown string
    """
    timestamp = doc.timestamp if doc.timestamp else datetime.now().isoformat()
    
    md_lines = [
        f"# P{doc.Part_N}-{doc.title}",
        "",
        "## Document Metadata",
        f"- **WPD Grade**: {doc.wpd_grade}",
        f"- **Version**: {doc.version}",
        f"- **Status**: {doc.status}",
        f"- **Type**: {doc.document_type}",
        f"- **Created**: {timestamp}",
        "",
    ]
    
    if doc.description:
        md_lines.extend([
            "## Description",
            doc.description,
            "",
        ])
    
    if doc.action:
        md_lines.extend([
            "## Actions",
        ])
        for action in doc.action:
            md_lines.append(f"- {action}")
        md_lines.append("")
    
    if doc.checklist:
        md_lines.extend([
            "## Checklist",
        ])
        for item in doc.checklist:
            md_lines.append(f"- [ ] {item}")
        md_lines.append("")
    
    if doc.files_to_update:
        md_lines.extend([
            "## Files to Update",
        ])
        for file_path in doc.files_to_update:
            md_lines.append(f"- {file_path}")
        md_lines.append("")
    
    # References section
    md_lines.extend([
        "## References",
    ])
    
    if doc.parent_document:
        md_lines.append(f"- **Parent**: [{doc.parent_document}]({doc.parent_document})")
    
    if doc.child_documents:
        md_lines.append("- **Children**:")
        for child in doc.child_documents:
            md_lines.append(f"  - [{child}]({child})")
    
    if doc.reference_documents:
        md_lines.append("- **References**:")
        for ref in doc.reference_documents:
            md_lines.append(f"  - [{ref}]({ref})")
    
    return "\n".join(md_lines)


def format_tier_a_state_as_markdown(state: TierAState) -> str:
    """
    Format TierAState as Markdown.
    
    Args:
        state: TierAState to format
    
    Returns:
        Markdown string
    """
    md_lines = [
        "# Tier A: Work Plan Creation State",
        "",
        "## Metadata",
        f"- **WPD Grade**: {state.wpd_grade}",
        f"- **Step**: {state.metadata.Part_N}",
        f"- **Title**: {state.metadata.document_title}",
        f"- **Version**: {state.metadata.version}",
        f"- **Status**: {state.metadata.status}",
        "",
    ]
    
    if state.created_documents:
        md_lines.extend([
            "## Created Documents",
        ])
        for doc_path in state.created_documents:
            md_lines.append(f"- {doc_path}")
        md_lines.append("")
    
    if state.execution_log:
        md_lines.extend([
            "## Execution Log",
        ])
        for log_entry in state.execution_log:
            md_lines.append(f"- {log_entry}")
        md_lines.append("")
    
    if state.hierarchy.parent_document:
        md_lines.extend([
            "## Hierarchy",
            f"- **Parent**: {state.hierarchy.parent_document}",
        ])
        if state.hierarchy.child_documents:
            md_lines.append("- **Children**:")
            for child in state.hierarchy.child_documents:
                md_lines.append(f"  - {child}")
    
    return "\n".join(md_lines)


__all__ = [
    "format_wpd_document_as_markdown",
    "format_tier_a_state_as_markdown",
]
