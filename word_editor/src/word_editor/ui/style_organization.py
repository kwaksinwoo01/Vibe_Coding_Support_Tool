from __future__ import annotations

from collections.abc import Iterable

from word_editor.domain.models import StyleDefinition


def is_hidden_style(style: StyleDefinition) -> bool:
    return style.properties.get("style.hidden") is True


def style_sort_key(
    style: StyleDefinition,
    mode: str,
) -> tuple[object, ...]:
    name_key = style.local_name.casefold()
    if mode == "name":
        return (name_key,)
    priority = style.properties.get("style.priority")
    try:
        numeric_priority = int(priority)
    except (TypeError, ValueError):
        numeric_priority = 1_000_000
    return (numeric_priority, name_key)


def organize_styles(
    styles: Iterable[StyleDefinition],
    mode: str,
) -> tuple[list[StyleDefinition], list[StyleDefinition]]:
    active: list[StyleDefinition] = []
    hidden: list[StyleDefinition] = []
    for style in styles:
        (hidden if is_hidden_style(style) else active).append(style)
    active.sort(key=lambda item: style_sort_key(item, mode))
    hidden.sort(key=lambda item: style_sort_key(item, mode))
    return active, hidden
