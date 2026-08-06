from __future__ import annotations

from typing import Any

from word_editor.domain.template_lifecycle import TemplateAssetInventory


def _entry_map(entries: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        str(entry.get("key", "")): dict(entry)
        for entry in entries
        if entry.get("key")
    }


def compare_header_footer_inventories(
    baseline: TemplateAssetInventory,
    current: TemplateAssetInventory,
) -> tuple[list[str], list[str], list[str]]:
    before = _entry_map(baseline.header_footer_entries)
    after = _entry_map(current.header_footer_entries)
    before_keys = set(before)
    after_keys = set(after)
    added = sorted(after_keys - before_keys, key=str.casefold)
    removed = sorted(before_keys - after_keys, key=str.casefold)
    changed = sorted(
        key
        for key in before_keys & after_keys
        if before[key] != after[key]
    )
    return added, removed, changed
