"""
Validation modules for the 6-tier task orchestration system.

Each validator module has a single responsibility: validate data for a specific domain.

- tier_validators.py: Validates tier-specific state data
- document_validators.py: Validates WPD/PRD documents
- template_validators.py: Validates template structure and required sections
- mp_validators.py: Validates MP models
"""

from .tier_validators import (
    validate_tier_a_state,
    validate_tier_b_state,
    validate_tier_c_state,
    validate_tier_d_state,
    validate_tier_e_state,
    validate_tier_f_state,
)
from .document_validators import (
    validate_wpd_document,
    validate_wpd_grade,
    validate_Part_N,
    validate_document_hierarchy,
)
try:
    from ..document_format.template_validators import (
        validate_template_structure,
        validate_required_sections,
    )
except ImportError:
    # Avoid circular import - these will be available at runtime
    validate_template_structure = None
    validate_required_sections = None
from .mp_validators import (
    validate_mp_metadata,
    validate_mp_section,
    validate_mp_validation,
)

__all__ = [
    # Tier validators
    "validate_tier_a_state",
    "validate_tier_b_state",
    "validate_tier_c_state",
    "validate_tier_d_state",
    "validate_tier_e_state",
    "validate_tier_f_state",
    # Document validators
    "validate_wpd_document",
    "validate_wpd_grade",
    "validate_Part_N",
    "validate_document_hierarchy",
    # Template validators
    "validate_template_structure",
    "validate_required_sections",
    # MP validators
    "validate_mp_metadata",
    "validate_mp_section",
    "validate_mp_validation",
]
