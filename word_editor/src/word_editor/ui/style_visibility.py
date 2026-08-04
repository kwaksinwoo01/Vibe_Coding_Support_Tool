from __future__ import annotations

from typing import Any

from word_editor.domain.models import normalize_word_boolean

ACTIVE_PRIORITY_MAX = 10


def numeric_style_priority(style: Any) -> int | None:
    value = style.properties.get("style.priority")
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def belongs_to_hidden_tab(style: Any) -> bool:
    """Return True when a style belongs in the hidden-style tab.

    A style is placed in the hidden tab when either condition is true:
    - Word marks the style hidden.
    - Its numeric priority is 11 or higher.

    Priority 1 through 10 remains in the active tab. Missing or non-numeric
    priority values do not hide a style by themselves.
    """

    hidden = normalize_word_boolean(
        style.properties.get("style.hidden")
    )
    if hidden is True:
        return True
    priority = numeric_style_priority(style)
    return priority is not None and priority > ACTIVE_PRIORITY_MAX
