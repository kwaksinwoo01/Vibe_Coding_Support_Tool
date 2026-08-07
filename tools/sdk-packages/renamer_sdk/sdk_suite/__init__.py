"""Toolchain/orchestrator for composing ReNamer development SDKs."""

from __future__ import annotations

from dataclasses import dataclass

from renamer_sdk.core_sdk import OperationStatus
from renamer_sdk.migration_sdk import plan_name_migration
from renamer_sdk.observability_sdk import EventRecorder
from renamer_sdk.test_sdk import oracle_merge, policy_b_scenarios
from renamer_sdk.validation_sdk import validate_name_migration


@dataclass(frozen=True, slots=True)
class ScenarioRun:
    name: str
    passed: bool
    messages: tuple[str, ...]


def run_policy_b_suite(
    recorder: EventRecorder | None = None,
) -> tuple[ScenarioRun, ...]:
    events = recorder or EventRecorder()
    results: list[ScenarioRun] = []

    for scenario in policy_b_scenarios():
        plan = plan_name_migration(scenario.migration_input)
        validation = validate_name_migration(scenario.migration_input, plan)
        oracle_names, oracle_tombstones = oracle_merge(scenario.migration_input)

        messages = list(validation.messages)
        if plan.merged_names != scenario.expected_names:
            messages.append("Migration result does not match scenario expectation.")
        if plan.tombstones != scenario.expected_tombstones:
            messages.append("Migration tombstones do not match scenario expectation.")
        if plan.merged_names != oracle_names or plan.tombstones != oracle_tombstones:
            messages.append("Migration result does not match the independent oracle.")

        passed = validation.status is OperationStatus.PASSED and not messages
        results.append(ScenarioRun(scenario.name, passed, tuple(messages)))
        events.emit(
            "policy_b_scenario",
            f"{scenario.name}: {'passed' if passed else 'failed'}",
        )

    return tuple(results)


def assert_policy_b_suite() -> None:
    failures = [result for result in run_policy_b_suite() if not result.passed]
    if failures:
        details = "; ".join(
            f"{item.name}: {', '.join(item.messages)}" for item in failures
        )
        raise AssertionError(details)
