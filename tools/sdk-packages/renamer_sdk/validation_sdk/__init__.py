"""Contract validation for ReNamer migration plans."""

from __future__ import annotations

from renamer_sdk.core_sdk import OperationResult, OperationStatus
from renamer_sdk.domain_sdk import name_key
from renamer_sdk.model_sdk import NameMigrationInput, NameMigrationPlan


def validate_name_migration(
    source: NameMigrationInput,
    plan: NameMigrationPlan,
) -> OperationResult[NameMigrationPlan]:
    errors: list[str] = []

    if plan.default_name != source.default_name:
        errors.append("DefaultName changed during migration.")

    merged_keys = [name_key(item) for item in plan.merged_names]
    if len(merged_keys) != len(set(merged_keys)):
        errors.append("Merged names contain duplicates.")

    local_keys = {name_key(item) for item in source.local_names}
    previous_keys = {name_key(item) for item in source.previous_defaults}
    user_added = local_keys - previous_keys
    if not user_added.issubset(set(merged_keys)):
        errors.append("A user-added name was lost.")

    tombstone_keys = {name_key(item) for item in plan.tombstones}
    if tombstone_keys & set(merged_keys):
        errors.append("A tombstoned name was reintroduced.")

    status = OperationStatus.FAILED if errors else OperationStatus.PASSED
    return OperationResult(status=status, value=plan, messages=tuple(errors))
