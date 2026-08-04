from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

JsonValue = str | int | float | bool | None | list[Any] | dict[str, Any]

BOOLEAN_PROPERTY_NAMES = frozenset(
    {
        "style.quick_style",
        "style.hidden",
        "style.unhide_when_used",
        "style.automatically_update",
        "style.no_space_same_style",
        "font.bold",
        "font.italic",
        "paragraph.keep_together",
        "paragraph.keep_with_next",
        "paragraph.page_break_before",
    }
)


def normalize_word_boolean(value: Any) -> bool | int | None | Any:
    """Normalize Word/COM boolean variants without hiding unknown sentinels.

    Word commonly uses VARIANT_BOOL values 0 and -1. pywin32 may expose the
    same true value as Python True, which becomes integer 1 if converted before
    checking its type. Both -1 and 1 therefore mean True at the application
    boundary. Other numeric sentinels remain unchanged for inspection.
    """

    if value is None:
        return None
    if isinstance(value, bool):
        return value
    try:
        integer = int(value)
    except (TypeError, ValueError):
        return value
    if integer == 0:
        return False
    if integer in {-1, 1}:
        return True
    return integer


def normalize_style_properties(
    properties: dict[str, JsonValue],
) -> dict[str, JsonValue]:
    normalized = dict(properties)
    for property_name in BOOLEAN_PROPERTY_NAMES:
        if property_name in normalized:
            normalized[property_name] = normalize_word_boolean(
                normalized[property_name]
            )
    return normalized


@dataclass(slots=True)
class StyleDefinition:
    # name remains the stable lookup key used by the current Word locale.
    name: str
    style_type: str
    built_in: bool
    in_use: bool
    original_name: str = ""
    built_in_id: int | None = None
    properties: dict[str, JsonValue] = field(default_factory=dict)
    list_binding: dict[str, JsonValue] = field(default_factory=dict)

    @property
    def local_name(self) -> str:
        return self.name

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "local_name": self.local_name,
            "original_name": self.original_name,
            "built_in_id": self.built_in_id,
            "style_type": self.style_type,
            "built_in": self.built_in,
            "in_use": self.in_use,
            "properties": normalize_style_properties(self.properties),
            "list_binding": self.list_binding,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "StyleDefinition":
        name = str(value.get("local_name") or value["name"])
        built_in_id_value = value.get("built_in_id")
        try:
            built_in_id = (
                int(built_in_id_value)
                if built_in_id_value is not None
                else None
            )
        except (TypeError, ValueError):
            built_in_id = None
        return cls(
            name=name,
            original_name=str(value.get("original_name") or name),
            built_in_id=built_in_id,
            style_type=str(value.get("style_type", "Unknown")),
            built_in=bool(normalize_word_boolean(value.get("built_in", False))),
            in_use=bool(normalize_word_boolean(value.get("in_use", False))),
            properties=normalize_style_properties(
                dict(value.get("properties", {}))
            ),
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
            "schema_version": 2,
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
