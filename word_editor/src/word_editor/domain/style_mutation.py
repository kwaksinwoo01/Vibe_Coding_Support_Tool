from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .models import StyleDefinition, TemplateSnapshot


class CreateStyleType(str, Enum):
    PARAGRAPH = "Paragraph"
    CHARACTER = "Character"
    TABLE = "Table"
    LIST = "List"

    @property
    def word_type(self) -> int:
        return {
            CreateStyleType.PARAGRAPH: 1,
            CreateStyleType.CHARACTER: 2,
            CreateStyleType.TABLE: 3,
            CreateStyleType.LIST: 4,
        }[self]


@dataclass(frozen=True, slots=True)
class CreateStyleRequest:
    name: str
    style_type: CreateStyleType
    clone_from: str | None = None


@dataclass(frozen=True, slots=True)
class DeleteStyleRequest:
    style_names: tuple[str, ...]
    replacement_style: str | None = None


@dataclass(frozen=True, slots=True)
class DeleteStyleBlocker:
    style_name: str
    reason: str
    referenced_by: tuple[str, ...] = ()


def validate_new_style_name(snapshot: TemplateSnapshot, name: str) -> str:
    normalized = name.strip()
    if not normalized:
        raise ValueError("새 스타일 이름은 비어 있을 수 없습니다.")
    folded = {style_name.casefold() for style_name in snapshot.styles}
    if normalized.casefold() in folded:
        raise ValueError(f"같은 이름의 스타일이 이미 존재합니다: {normalized}")
    return normalized


def delete_style_blockers(
    snapshot: TemplateSnapshot,
    style_names: tuple[str, ...],
) -> list[DeleteStyleBlocker]:
    selected = set(style_names)
    blockers: list[DeleteStyleBlocker] = []
    default_style = str(snapshot.metadata.get("default_paragraph_style") or "")

    for style_name in style_names:
        style = snapshot.styles.get(style_name)
        if style is None:
            blockers.append(DeleteStyleBlocker(style_name, "스타일을 찾지 못했습니다."))
            continue
        if style.built_in:
            blockers.append(DeleteStyleBlocker(style_name, "Word 내장 스타일은 삭제할 수 없습니다."))
            continue
        if default_style and style_name == default_style:
            blockers.append(DeleteStyleBlocker(style_name, "기본 문단 스타일은 삭제할 수 없습니다."))
            continue

        referenced_by: list[str] = []
        for candidate in snapshot.styles.values():
            if candidate.name in selected:
                continue
            if candidate.properties.get("style.base_style") == style_name:
                referenced_by.append(f"{candidate.name}.style.base_style")
            if candidate.properties.get("style.next_style") == style_name:
                referenced_by.append(f"{candidate.name}.style.next_style")
            if candidate.list_binding.get("linked_style") == style_name:
                referenced_by.append(f"{candidate.name}.list_binding.linked_style")
        if referenced_by:
            blockers.append(
                DeleteStyleBlocker(
                    style_name,
                    "다른 스타일이 참조하고 있어 먼저 참조를 변경해야 합니다.",
                    tuple(sorted(referenced_by, key=str.casefold)),
                )
            )
    return blockers


def cloneable_properties(style: StyleDefinition) -> dict[str, object]:
    """Return only property values already captured by the editor.

    Structural identity, built-in identity, and list bindings are deliberately
    excluded. The created style gets a new Word identity and then receives the
    safe editable property values through the normal patch pipeline.
    """

    return dict(style.properties)
