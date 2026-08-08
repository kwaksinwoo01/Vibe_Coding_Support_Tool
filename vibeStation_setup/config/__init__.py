"""
config package - Configuration module for vibeStation_setup

Provides centralized configuration management including:
- Tier keywords (tier_keywords.py)
- Tier keywords management (tier_keywords_manager.py)
- Configuration variables
"""

from .tier_keywords import (
    get_tier_keywords,
    get_context_bonuses,
    get_tier_max_score,
    get_tier_keywords_list,
    TIER_A_KEYWORDS,
    TIER_B_KEYWORDS,
    TIER_C_KEYWORDS,
    TIER_D_KEYWORDS,
    TIER_E_KEYWORDS,
    TIER_F_KEYWORDS,
    CONTEXT_BONUSES,
)

from .tier_keywords_manager import (
    TierKeywordsManager,
    add_keyword,
    remove_keyword,
    add_context_bonus,
    save_keywords,
    load_keywords,
    get_keywords_summary,
    restore_backup,
)

__all__ = [
    # tier_keywords.py exports
    "get_tier_keywords",
    "get_context_bonuses",
    "get_tier_max_score",
    "get_tier_keywords_list",
    "TIER_A_KEYWORDS",
    "TIER_B_KEYWORDS",
    "TIER_C_KEYWORDS",
    "TIER_D_KEYWORDS",
    "TIER_E_KEYWORDS",
    "TIER_F_KEYWORDS",
    "CONTEXT_BONUSES",
    # tier_keywords_manager.py exports
    "TierKeywordsManager",
    "add_keyword",
    "remove_keyword",
    "add_context_bonus",
    "save_keywords",
    "load_keywords",
    "get_keywords_summary",
    "restore_backup",
]
