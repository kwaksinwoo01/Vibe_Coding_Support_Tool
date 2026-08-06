from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class TemplateProfile:
    profile_id: str
    display_name: str
    classification_code: str
    canonical_path: str
    created_at: str
    updated_at: str
    description: str = ""
    asset_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "display_name": self.display_name,
            "classification_code": self.classification_code,
            "canonical_path": self.canonical_path,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "description": self.description,
            "asset_ids": list(self.asset_ids),
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "TemplateProfile":
        return cls(
            profile_id=str(value["profile_id"]),
            display_name=str(value["display_name"]),
            classification_code=str(value.get("classification_code", "")),
            canonical_path=str(value["canonical_path"]),
            created_at=str(value.get("created_at") or utc_now_iso()),
            updated_at=str(value.get("updated_at") or utc_now_iso()),
            description=str(value.get("description", "")),
            asset_ids=[str(item) for item in value.get("asset_ids", [])],
        )


@dataclass(slots=True)
class RegisteredTemplateAsset:
    asset_id: str
    display_name: str
    role: str
    managed_path: str
    source_path: str
    created_at: str
    updated_at: str
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "asset_id": self.asset_id,
            "display_name": self.display_name,
            "role": self.role,
            "managed_path": self.managed_path,
            "source_path": self.source_path,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "RegisteredTemplateAsset":
        return cls(
            asset_id=str(value["asset_id"]),
            display_name=str(value["display_name"]),
            role=str(value.get("role", "company-template")),
            managed_path=str(value["managed_path"]),
            source_path=str(value.get("source_path", "")),
            created_at=str(value.get("created_at") or utc_now_iso()),
            updated_at=str(value.get("updated_at") or utc_now_iso()),
            description=str(value.get("description", "")),
        )


@dataclass(slots=True)
class TemplateAssetInventory:
    source_path: str
    captured_at: str
    file_sha256: str
    file_size: int
    styles_sha256: str
    building_blocks: list[dict[str, Any]] = field(default_factory=list)
    autotext_entries: list[str] = field(default_factory=list)
    template_object_found: bool = False
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_path": self.source_path,
            "captured_at": self.captured_at,
            "file_sha256": self.file_sha256,
            "file_size": self.file_size,
            "styles_sha256": self.styles_sha256,
            "building_blocks": self.building_blocks,
            "autotext_entries": self.autotext_entries,
            "template_object_found": self.template_object_found,
            "warnings": self.warnings,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "TemplateAssetInventory":
        return cls(
            source_path=str(value.get("source_path", "")),
            captured_at=str(value.get("captured_at") or utc_now_iso()),
            file_sha256=str(value.get("file_sha256", "")),
            file_size=int(value.get("file_size", 0)),
            styles_sha256=str(value.get("styles_sha256", "")),
            building_blocks=list(value.get("building_blocks", [])),
            autotext_entries=[
                str(item) for item in value.get("autotext_entries", [])
            ],
            template_object_found=bool(value.get("template_object_found", False)),
            warnings=[str(item) for item in value.get("warnings", [])],
        )


@dataclass(slots=True)
class TemplateChangeReport:
    profile_id: str
    baseline_path: str
    current_path: str
    created_at: str
    baseline_sha256: str
    current_sha256: str
    style_changes: dict[str, dict[str, tuple[Any, Any]]] = field(
        default_factory=dict
    )
    added_building_blocks: list[str] = field(default_factory=list)
    removed_building_blocks: list[str] = field(default_factory=list)
    changed_building_blocks: list[str] = field(default_factory=list)
    added_autotext: list[str] = field(default_factory=list)
    removed_autotext: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def has_changes(self) -> bool:
        return bool(
            self.baseline_sha256 != self.current_sha256
            or self.style_changes
            or self.added_building_blocks
            or self.removed_building_blocks
            or self.changed_building_blocks
            or self.added_autotext
            or self.removed_autotext
        )

    def summary_lines(self, max_style_items: int = 40) -> list[str]:
        lines = [
            f"프로필: {self.profile_id}",
            f"기준 파일: {self.baseline_path}",
            f"현재 파일: {self.current_path}",
            f"파일 변경: {self.baseline_sha256 != self.current_sha256}",
            f"스타일 변경 스타일 수: {len(self.style_changes)}",
            f"Building Block 추가/삭제/변경: "
            f"{len(self.added_building_blocks)}/"
            f"{len(self.removed_building_blocks)}/"
            f"{len(self.changed_building_blocks)}",
            f"AutoText 추가/삭제: "
            f"{len(self.added_autotext)}/{len(self.removed_autotext)}",
        ]
        for style_name, changes in list(self.style_changes.items())[
            :max_style_items
        ]:
            lines.append(f"- {style_name}: {', '.join(sorted(changes))}")
        if len(self.style_changes) > max_style_items:
            lines.append(
                f"- ... 나머지 {len(self.style_changes) - max_style_items}개 스타일"
            )
        for label, values in (
            ("Building Block 추가", self.added_building_blocks),
            ("Building Block 삭제", self.removed_building_blocks),
            ("Building Block 변경", self.changed_building_blocks),
            ("AutoText 추가", self.added_autotext),
            ("AutoText 삭제", self.removed_autotext),
        ):
            for value in values[:20]:
                lines.append(f"- {label}: {value}")
        for warning in self.warnings:
            lines.append(f"- 경고: {warning}")
        return lines

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "baseline_path": self.baseline_path,
            "current_path": self.current_path,
            "created_at": self.created_at,
            "baseline_sha256": self.baseline_sha256,
            "current_sha256": self.current_sha256,
            "style_changes": {
                style_name: {
                    property_name: [old_value, new_value]
                    for property_name, (old_value, new_value) in changes.items()
                }
                for style_name, changes in self.style_changes.items()
            },
            "added_building_blocks": self.added_building_blocks,
            "removed_building_blocks": self.removed_building_blocks,
            "changed_building_blocks": self.changed_building_blocks,
            "added_autotext": self.added_autotext,
            "removed_autotext": self.removed_autotext,
            "warnings": self.warnings,
        }


@dataclass(slots=True)
class TemplateRegistry:
    active_profile_id: str = ""
    profiles: dict[str, TemplateProfile] = field(default_factory=dict)
    assets: dict[str, RegisteredTemplateAsset] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "active_profile_id": self.active_profile_id,
            "profiles": {
                key: value.to_dict()
                for key, value in sorted(self.profiles.items())
            },
            "assets": {
                key: value.to_dict()
                for key, value in sorted(self.assets.items())
            },
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "TemplateRegistry":
        return cls(
            active_profile_id=str(value.get("active_profile_id", "")),
            profiles={
                str(key): TemplateProfile.from_dict(item)
                for key, item in dict(value.get("profiles", {})).items()
            },
            assets={
                str(key): RegisteredTemplateAsset.from_dict(item)
                for key, item in dict(value.get("assets", {})).items()
            },
        )


def path_from_record(value: str) -> Path:
    return Path(value).expanduser().resolve()
