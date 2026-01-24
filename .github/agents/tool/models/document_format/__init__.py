"""
Document Format Module - Consolidated document formatting, templating, and validation.

This module consolidates all document format-related functionality into a single,
well-organized location for easier maintenance and customization.

**Modules**:
- templates: WPD template definitions (L0-L3)
- template_renderer: Renders templates into Markdown content
- template_validators: Validates template structure and required sections
- document_serializer: Serializes/deserializes WPDDocument
- document_converters: Converts between WPDDocument and tier states
- document_builder: Builds WPDDocument instances
- template_builder: Builds template instances

**Usage**:
    from models.document_format import templates, template_renderer
    from models.document_format.templates import get_template_for_grade
    from models.document_format.template_renderer import render_wpd_template
"""

# Re-export commonly used items for convenience
from .templates import (
    wpd_0_template,
    wpd_1_template,
    wpd_2_template,
    wpd_3_template,
    WPD_TEMPLATES,
    get_template_for_grade,
    get_required_sections,
)

from .template_renderer import (
    render_wpd_template,
    generate_template_structure,
)

from .template_validators import (
    validate_template_structure,
    validate_required_sections,
    get_required_sections_for_grade,
)

__all__ = [
    # Template classes
    "wpd_0_template",
    "wpd_1_template",
    "wpd_2_template",
    "wpd_3_template",
    "WPD_TEMPLATES",
    # Template functions
    "get_template_for_grade",
    "get_required_sections",
    # Rendering functions
    "render_wpd_template",
    "generate_template_structure",
    # Validation functions
    "validate_template_structure",
    "validate_required_sections",
    "get_required_sections_for_grade",
]
