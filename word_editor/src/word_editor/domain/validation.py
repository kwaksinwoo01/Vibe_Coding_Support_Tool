from __future__ import annotations

from collections.abc import Iterable, Protocol
from dataclasses import dataclass
from typing import Any

from .models import Severity, TemplateSnapshot, ValidationIssue


class SnapshotValidator(Protocol):
    name: str

    def validate(self, snapshot: TemplateSnapshot) -> Iterable[ValidationIssue]: ...


@dataclass(slots=True)
class ReferenceValidator:
    name: str = "style-reference"

    def validate(self, snapshot: TemplateSnapshot) -> Iterable[ValidationIssue]:
        style_names = set(snapshot.styles)
        for style in snapshot.styles.values():
            for property_name in ("style.base_style", "style.next_style"):
                reference = style.properties.get(property_name)
                if not reference or reference in style_names:
                    continue
                yield ValidationIssue(
                    validator=self.name,
                    severity=Severity.WARNING,
                    style_name=style.name,
                    property_name=property_name,
                    message=f"Referenced style is not in the snapshot: {reference}",
                )


@dataclass(slots=True)
class PropertyRangeValidator:
    name: str = "property-range"

    def validate(self, snapshot: TemplateSnapshot) -> Iterable[ValidationIssue]:
        ranges: dict[str, tuple[float, float]] = {
            "font.size_pt": (1.0, 1638.0),
            "font.scaling_percent": (1.0, 600.0),
            "paragraph.left_indent_cm": (-55.87, 55.87),
            "paragraph.right_indent_cm": (-55.87, 55.87),
            "paragraph.first_line_indent_cm": (-55.87, 55.87),
            "paragraph.space_before_pt": (0.0, 1584.0),
            "paragraph.space_after_pt": (0.0, 1584.0),
            "style.priority": (1.0, 100.0),
        }
        for style in snapshot.styles.values():
            for property_name, (minimum, maximum) in ranges.items():
                value = style.properties.get(property_name)
                if value is None:
                    continue
                if isinstance(value, bool) or not isinstance(value, (int, float)):
                    yield ValidationIssue(
                        validator=self.name,
                        severity=Severity.ERROR,
                        style_name=style.name,
                        property_name=property_name,
                        message=f"Expected a number, got {type(value).__name__}",
                    )
                    continue
                if not minimum <= float(value) <= maximum:
                    yield ValidationIssue(
                        validator=self.name,
                        severity=Severity.ERROR,
                        style_name=style.name,
                        property_name=property_name,
                        message=f"Value {value} is outside {minimum}..{maximum}",
                    )


@dataclass(slots=True)
class ListBindingValidator:
    name: str = "list-binding"

    def validate(self, snapshot: TemplateSnapshot) -> Iterable[ValidationIssue]:
        template_names = set(snapshot.list_templates)
        for style in snapshot.styles.values():
            template_name = style.list_binding.get("template_name")
            level = style.list_binding.get("level")
            if template_name and template_name not in template_names:
                yield ValidationIssue(
                    validator=self.name,
                    severity=Severity.WARNING,
                    style_name=style.name,
                    property_name="list_binding.template_name",
                    message=f"List template was not captured: {template_name}",
                )
            if level is not None and (
                isinstance(level, bool)
                or not isinstance(level, int)
                or not 1 <= level <= 9
            ):
                yield ValidationIssue(
                    validator=self.name,
                    severity=Severity.ERROR,
                    style_name=style.name,
                    property_name="list_binding.level",
                    message=f"Invalid list level: {level}",
                )


@dataclass(slots=True)
class SnapshotIntegrityValidator:
    name: str = "snapshot-integrity"

    def validate(self, snapshot: TemplateSnapshot) -> Iterable[ValidationIssue]:
        if not snapshot.sha256:
            yield ValidationIssue(
                validator=self.name,
                severity=Severity.ERROR,
                message="Snapshot has no source SHA-256.",
            )
        for key, style in snapshot.styles.items():
            if key != style.name:
                yield ValidationIssue(
                    validator=self.name,
                    severity=Severity.ERROR,
                    style_name=style.name,
                    message=f"Style dictionary key mismatch: {key}",
                )


DEFAULT_VALIDATORS: tuple[SnapshotValidator, ...] = (
    SnapshotIntegrityValidator(),
    ReferenceValidator(),
    PropertyRangeValidator(),
    ListBindingValidator(),
)


def validate_snapshot(
    snapshot: TemplateSnapshot,
    validators: Iterable[SnapshotValidator] = DEFAULT_VALIDATORS,
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for validator in validators:
        issues.extend(validator.validate(snapshot))
    return issues
