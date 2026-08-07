"""Independent migration oracle and reusable scenario matrix."""

from __future__ import annotations

from renamer_sdk.domain_sdk import name_key, normalize_names
from renamer_sdk.model_sdk import MigrationScenario, NameMigrationInput


LEGACY_741_DEFAULTS = (
    "곽신우",
    "김민규",
    "이슬기",
    "정우형",
    "박승주",
)
RELEASE_742_DEFAULTS = (*LEGACY_741_DEFAULTS, "김예빈")


def oracle_merge(value: NameMigrationInput) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Independent compact reference implementation used only by tests."""

    previous = normalize_names(value.previous_defaults)
    local = normalize_names(value.local_names)
    incoming = normalize_names(value.incoming_defaults)

    local_keys = {name_key(item) for item in local}
    tombstones = {name_key(item): item for item in value.removed_defaults}
    for item in previous:
        if name_key(item) not in local_keys:
            tombstones.setdefault(name_key(item), item)
    for item in local:
        tombstones.pop(name_key(item), None)

    merged = list(local)
    merged_keys = {name_key(item) for item in merged}
    for item in incoming:
        key = name_key(item)
        if key not in merged_keys and key not in tombstones:
            merged.append(item)
            merged_keys.add(key)

    return tuple(merged), tuple(tombstones.values())


def policy_b_scenarios() -> tuple[MigrationScenario, ...]:
    return (
        MigrationScenario(
            name="7.4.1-to-7.4.2-adds-new-default",
            migration_input=NameMigrationInput(
                default_name="홍길동",
                previous_defaults=LEGACY_741_DEFAULTS,
                local_names=LEGACY_741_DEFAULTS,
                incoming_defaults=RELEASE_742_DEFAULTS,
            ),
            expected_names=RELEASE_742_DEFAULTS,
        ),
        MigrationScenario(
            name="preserves-user-addition-and-deletions",
            migration_input=NameMigrationInput(
                default_name="홍길동",
                previous_defaults=LEGACY_741_DEFAULTS,
                local_names=("곽신우", "김민규", "박승주", "사용자추가이름"),
                incoming_defaults=RELEASE_742_DEFAULTS,
            ),
            expected_names=("곽신우", "김민규", "박승주", "사용자추가이름", "김예빈"),
            expected_tombstones=("이슬기", "정우형"),
        ),
        MigrationScenario(
            name="reinstall-is-idempotent",
            migration_input=NameMigrationInput(
                default_name="홍길동",
                previous_defaults=RELEASE_742_DEFAULTS,
                local_names=RELEASE_742_DEFAULTS,
                incoming_defaults=RELEASE_742_DEFAULTS,
            ),
            expected_names=RELEASE_742_DEFAULTS,
        ),
        MigrationScenario(
            name="tombstone-blocks-later-reintroduction",
            migration_input=NameMigrationInput(
                default_name="홍길동",
                previous_defaults=("곽신우",),
                local_names=("곽신우",),
                incoming_defaults=("곽신우", "이슬기"),
                removed_defaults=("이슬기",),
            ),
            expected_names=("곽신우",),
            expected_tombstones=("이슬기",),
        ),
        MigrationScenario(
            name="manual-restore-clears-tombstone",
            migration_input=NameMigrationInput(
                default_name="홍길동",
                previous_defaults=("곽신우",),
                local_names=("곽신우", "이슬기"),
                incoming_defaults=("곽신우", "이슬기"),
                removed_defaults=("이슬기",),
            ),
            expected_names=("곽신우", "이슬기"),
        ),
    )
