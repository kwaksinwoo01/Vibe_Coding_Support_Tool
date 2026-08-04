from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .models import StyleDefinition


@dataclass(frozen=True, slots=True)
class PropertyPolicy:
    editable: bool
    reason: str = ""


PARAGRAPH_STYLE_TYPES = frozenset({"Paragraph", "ParagraphOnly", "Linked"})
FONT_PROPERTIES = frozenset(
    {
        "font.name",
        "font.name_ascii",
        "font.name_far_east",
        "font.name_other",
        "font.size_pt",
        "font.bold",
        "font.italic",
        "font.underline",
        "font.scaling_percent",
    }
)
PARAGRAPH_PROPERTIES = frozenset(
    {
        "paragraph.alignment",
        "paragraph.left_indent_cm",
        "paragraph.right_indent_cm",
        "paragraph.first_line_indent_cm",
        "paragraph.space_before_pt",
        "paragraph.space_after_pt",
        "paragraph.line_spacing_rule",
        "paragraph.outline_level",
        "paragraph.keep_together",
        "paragraph.keep_with_next",
        "paragraph.page_break_before",
    }
)
DISPLAY_PROPERTIES = frozenset(
    {
        "style.priority",
        "style.quick_style",
        "style.hidden",
        "style.unhide_when_used",
    }
)
STRUCTURAL_PROPERTIES = frozenset(
    {
        "style.base_style",
        "style.next_style",
        "style.automatically_update",
        "style.no_space_same_style",
    }
)
SUPPORTED_EDITABLE_PROPERTIES = (
    FONT_PROPERTIES
    | PARAGRAPH_PROPERTIES
    | DISPLAY_PROPERTIES
    | STRUCTURAL_PROPERTIES
)


def property_policy(style: StyleDefinition, property_name: str) -> PropertyPolicy:
    """Return the compatibility policy for one style property.

    The policy is intentionally conservative. Word exposes many properties on
    COM objects even when a particular style type cannot safely persist them.
    Unsupported combinations stay visible for inspection but are read-only.
    """

    if property_name not in SUPPORTED_EDITABLE_PROPERTIES:
        return PropertyPolicy(False, "이 프로그램이 관리하지 않는 읽기 전용 속성")

    if property_name in FONT_PROPERTIES:
        return PropertyPolicy(True)

    if property_name in DISPLAY_PROPERTIES:
        return PropertyPolicy(True)

    if property_name in PARAGRAPH_PROPERTIES:
        if style.style_type not in PARAGRAPH_STYLE_TYPES:
            return PropertyPolicy(False, "문단 계열 스타일에만 적용 가능한 속성")
        return PropertyPolicy(True)

    if property_name == "style.base_style":
        if style.built_in:
            return PropertyPolicy(False, "내장 스타일의 상속 기준은 호환성 보호를 위해 잠금")
        return PropertyPolicy(True)

    if property_name == "style.next_style":
        if style.style_type not in PARAGRAPH_STYLE_TYPES:
            return PropertyPolicy(False, "다음 단락 스타일은 문단 계열에서만 사용 가능")
        if style.built_in:
            return PropertyPolicy(False, "내장 스타일의 다음 단락 연결은 호환성 보호를 위해 잠금")
        return PropertyPolicy(True)

    if property_name in {
        "style.automatically_update",
        "style.no_space_same_style",
    }:
        if style.style_type not in PARAGRAPH_STYLE_TYPES:
            return PropertyPolicy(False, "문단 계열 스타일에만 적용 가능한 속성")
        return PropertyPolicy(True)

    return PropertyPolicy(False, "호환성 정책에 등록되지 않은 속성")


def common_property_names(styles: Iterable[StyleDefinition]) -> list[str]:
    selected = list(styles)
    if not selected:
        return []
    common = set(selected[0].properties)
    for style in selected[1:]:
        common.intersection_update(style.properties)
    return sorted(common)


def common_property_policy(
    styles: Iterable[StyleDefinition],
    property_name: str,
) -> PropertyPolicy:
    selected = list(styles)
    if not selected:
        return PropertyPolicy(False, "선택한 스타일이 없음")
    policies = [property_policy(style, property_name) for style in selected]
    blocked = [policy.reason for policy in policies if not policy.editable]
    if blocked:
        unique_reasons = list(dict.fromkeys(blocked))
        return PropertyPolicy(False, " / ".join(unique_reasons))
    return PropertyPolicy(True)


def assert_property_editable(
    style: StyleDefinition,
    property_name: str,
) -> None:
    policy = property_policy(style, property_name)
    if not policy.editable:
        raise ValueError(
            f"{style.name}.{property_name} 속성은 편집할 수 없습니다: "
            f"{policy.reason}"
        )
