"""
Model conversion modules for data transformation between different types.

Each converter module has a single responsibility: convert between specific model types.

- tier_converters.py: Convert between different tier states
- document_converters.py: Convert between WPDDocument and tier states
- mp_converters.py: Convert between MP models
"""

from .tier_converters import (
    tier_a_to_tier_b,
    tier_b_to_tier_e,
    tier_c_to_tier_e,
    tier_d_to_tier_c,
    tier_c_to_tier_a,
    tier_a_to_tier_c,
    TierStateConverter,
)

try:
    from .document_converters import (
        wpd_document_to_tier_a,
        tier_a_to_wpd_document,
    )
except ImportError:
    # Module not yet implemented
    wpd_document_to_tier_a = None
    tier_a_to_wpd_document = None

__all__ = [
    "tier_a_to_tier_b",
    "tier_b_to_tier_e",
    "tier_c_to_tier_e",
    "tier_d_to_tier_c",
    "tier_c_to_tier_a",
    "tier_a_to_tier_c",
    "TierStateConverter",
    "wpd_document_to_tier_a",
    "tier_a_to_wpd_document",
]
