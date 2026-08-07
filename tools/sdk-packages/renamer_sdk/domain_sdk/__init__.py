"""Pure ReNamer name-domain rules. No filesystem or process access."""

from __future__ import annotations


def name_key(value: str) -> str:
    return value.strip().casefold()


def normalize_names(values: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    output: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = value.strip()
        key = name_key(cleaned)
        if cleaned and key not in seen:
            output.append(cleaned)
            seen.add(key)
    return tuple(output)


def contains_name(values: tuple[str, ...], candidate: str) -> bool:
    key = name_key(candidate)
    return any(name_key(value) == key for value in values)
