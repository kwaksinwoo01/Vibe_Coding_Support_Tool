"""
Template builder for creating WPD template instances.

**Single Responsibility**: Create and initialize WPD templates.
This module is changed only when template creation logic changes.

**Responsibility**: WPD template creation and initialization
**Reason to Change**: When template creation patterns change
"""

from .templates import get_template_for_grade, WPD_TEMPLATES


__all__ = []
