from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

JsonValue = str | int | float | bool | None | list[Any] | dict[str, Any]


@dataclass(slots=True)
class StyleDefinition:
    name: str
    style_type: str
    built_in: bool
    in_use: bool
    properties: dict[str, JsonValue] = field(default_factory=dict)
    list_binding: dict[str, JsonValue] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "style_type": self.style_type,
            "built_in": self.built_in,
            "in_use": self.in_use,
            "properties": self.properties,
            "list_binding": self.list_binding,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "StyleDefinition":
        return cls(
            name=str(value["name"]),
            style_type=str(value.get("style_type", "Unknown")),
            built_in=bool(value.get("built_in", False)),
            in_use=bool(value.get("in_use", False)),
            properties=dict(value.get("properties", {})),
            list_binding=dict(value.get("list_binding", {})),
        )


@dataclass(slots=True)
class TemplateSnapshot:
    source_path: str
    sha256: str
    captured_at: str
    word_version: str
    styles: dict[str, StyleDefinition] = field(default_factory=dict)
    list_templates: dict[str, dict[str, JsonValue]] = field(default_factory=dict)
    metadata: dict[str, JsonValue] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "source_path": self.source_path,
            "sha256": self.sha256,
            "captured_at": self.captured_at,
            "word_version": self.word_version,
            "styles": {
                key: style.to_dict() for key, style in sorted(self.styles.items())
            },
            "list_templates": self.list_templates,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "TemplateSnapshot":
        return cls(
            source_path=str(value.get("source_path", "")),
            sha256=str(value.get("sha256", "")),
            captured_at=str(value.get("captured_at", "")),
            word_version=str(value.get("word_version", "")),
            styles={
                str(key): StyleDefinition.from_dict(style)
                for key, style in dict(value.get("styles", {})).items()
            },
            list_templates=dict(value.get("list_templates", {})),
            metadata=dict(value.get("metadata", {})),
        )


@dataclass(frozen=True, slots=True)
class PatchOperation:
    style_name: str
    property_name: str
    value: JsonValue
    expected_old_value: JsonValue


class ConflictChoice(str, Enum):
    KEEP_NORMAL = "keep_normal"
    USE_DOCUMENT = "use_document"
    USE_BASELINE = "use_baseline"
    MANUAL = "manual"


@dataclass(slots=True)
class MergeConflict:
    style_name: str
    property_name: str
    baseline_value: JsonValue
    normal_value: JsonValue
    document_value: JsonValue
    choice: ConflictChoice | None = None
    manual_value: JsonValue = None


@dataclass(slots=True)
class MergePlan:
    baseline_sha256: str
    normal_sha256: str
    document_sha256: str
    automatic_values: dict[str, dict[str, JsonValue]] = field(default_factory=dict)
    conflicts: list[MergeConflict] = field(default_factory=list)
    added_styles: list[str] = field(default_factory=list)
    removed_styles: list[str] = field(default_factory=list)

    @property
    def has_conflicts(self) -> bool:
        return bool(self.conflicts)


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    validator: str
    severity: Severity
    message: str
    style_name: str | None = None
    property_name: str | None = None


@dataclass(frozen=True, slots=True)
class BackupRecord:
    path: Path
    sha256: str
    created_at: str
