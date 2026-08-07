"""Version-to-version migration planning for managed ReNamer names."""

from __future__ import annotations

from renamer_sdk.domain_sdk import name_key, normalize_names
from renamer_sdk.model_sdk import NameMigrationInput, NameMigrationPlan


def plan_name_migration(value: NameMigrationInput) -> NameMigrationPlan:
    """Plan policy-B migration without mutating files.

    Local user additions are preserved, explicit deletions of previously managed
    defaults become tombstones, and new packaged defaults are added unless a
    tombstone suppresses them. The user's DefaultName is never migrated.
    """

    previous = normalize_names(value.previous_defaults)
    local = normalize_names(value.local_names)
    incoming = normalize_names(value.incoming_defaults)
    existing_tombstones = normalize_names(value.removed_defaults)

    previous_by_key = {name_key(item): item for item in previous}
    local_keys = {name_key(item) for item in local}
    tombstone_by_key = {name_key(item): item for item in existing_tombstones}

    removed_by_user = tuple(
        item for item in previous if name_key(item) not in local_keys
    )
    for item in removed_by_user:
        tombstone_by_key.setdefault(name_key(item), item)

    # A manual local restore wins over a previously recorded tombstone.
    for item in local:
        tombstone_by_key.pop(name_key(item), None)

    merged = list(local)
    merged_keys = {name_key(item) for item in merged}
    added_by_release: list[str] = []

    for item in incoming:
        key = name_key(item)
        if key in merged_keys or key in tombstone_by_key:
            continue
        merged.append(item)
        merged_keys.add(key)
        if key not in previous_by_key:
            added_by_release.append(item)

    previous_keys = set(previous_by_key)
    preserved_user_names = tuple(
        item for item in local if name_key(item) not in previous_keys
    )

    return NameMigrationPlan(
        default_name=value.default_name,
        merged_names=tuple(merged),
        added_by_release=tuple(added_by_release),
        preserved_user_names=preserved_user_names,
        removed_by_user=removed_by_user,
        tombstones=tuple(tombstone_by_key.values()),
    )
