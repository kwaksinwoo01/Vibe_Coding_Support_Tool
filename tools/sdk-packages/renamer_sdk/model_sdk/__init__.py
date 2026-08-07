"""Structured models shared by ReNamer development SDKs."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class NameMigrationInput:
    default_name: str
    previous_defaults: tuple[str, ...]
    local_names: tuple[str, ...]
    incoming_defaults: tuple[str, ...]
    removed_defaults: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class NameMigrationPlan:
    default_name: str
    merged_names: tuple[str, ...]
    added_by_release: tuple[str, ...]
    preserved_user_names: tuple[str, ...]
    removed_by_user: tuple[str, ...]
    tombstones: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class MigrationScenario:
    name: str
    migration_input: NameMigrationInput
    expected_names: tuple[str, ...]
    expected_tombstones: tuple[str, ...] = ()
