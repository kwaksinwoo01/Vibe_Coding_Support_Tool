"""
Formatting modules for rendering models to presentation formats.

Each formatter has a single responsibility: render models in a specific format.

- markdown_formatter.py: Format WPDDocument and tier states as Markdown
- template_renderer.py: Render WPD templates with data (moved to models.document_format)
"""

from .markdown_formatter import (
    format_wpd_document_as_markdown,
    format_tier_a_state_as_markdown,
)

# Import from new location for backward compatibility
from ..document_format.template_renderer import (
    render_wpd_template,
    generate_template_structure,
)

__all__ = [
    "format_wpd_document_as_markdown",
    "format_tier_a_state_as_markdown",
    "render_wpd_template",  # Re-exported from document_format
    "generate_template_structure",  # Re-exported from document_format
]
