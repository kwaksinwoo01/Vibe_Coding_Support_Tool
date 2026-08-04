from __future__ import annotations

import json
from typing import Any

PROPERTY_LABELS: dict[str, str] = {
    "meta.local_name": "로컬 표시 이름",
    "meta.original_name": "Word 원래 이름",
    "meta.built_in_id": "내장 스타일 ID",
    "meta.style_type": "스타일 종류",
    "meta.built_in": "내장 스타일 여부",
    "meta.in_use": "현재 사용 여부",
    "style.base_style": "기준 스타일",
    "style.next_style": "다음 단락 스타일",
    "style.priority": "스타일 우선순위",
    "style.quick_style": "빠른 스타일 갤러리 표시",
    "style.hidden": "스타일 숨김",
    "style.unhide_when_used": "사용 시 다시 표시",
    "style.automatically_update": "자동 업데이트",
    "style.no_space_same_style": "같은 스타일 단락 간격 제거",
    "font.name": "기본 글꼴",
    "font.name_ascii": "영문 글꼴",
    "font.name_far_east": "한글·동아시아 글꼴",
    "font.name_other": "기타 문자 글꼴",
    "font.size_pt": "글꼴 크기(pt)",
    "font.bold": "굵게",
    "font.italic": "기울임꼴",
    "font.underline": "밑줄",
    "font.scaling_percent": "문자 배율(%)",
    "paragraph.alignment": "문단 정렬",
    "paragraph.left_indent_cm": "왼쪽 들여쓰기(cm)",
    "paragraph.right_indent_cm": "오른쪽 들여쓰기(cm)",
    "paragraph.first_line_indent_cm": "첫 줄 들여쓰기(cm)",
    "paragraph.space_before_pt": "문단 앞 간격(pt)",
    "paragraph.space_after_pt": "문단 뒤 간격(pt)",
    "paragraph.line_spacing_rule": "줄 간격 규칙",
    "paragraph.outline_level": "개요 수준",
    "paragraph.keep_together": "문단 나누지 않음",
    "paragraph.keep_with_next": "다음 문단과 함께",
    "paragraph.page_break_before": "앞에서 페이지 나누기",
}


def property_label(property_name: str) -> str:
    """Return only the Korean display label for an internal property key."""

    return PROPERTY_LABELS.get(property_name, property_name)


def style_type_label(value: str) -> str:
    """Keep the original style-type value unchanged."""

    return value


def format_property_value(property_name: str, value: Any) -> str:
    """Render the stored value without semantic translation.

    The property name is accepted for API compatibility but intentionally does
    not affect formatting. Strings remain strings; all other values use their
    JSON representation, such as true, false, null, 0, 1, and enum numbers.
    """

    del property_name
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False)


def parse_property_value(property_name: str, text: str, original: Any) -> Any:
    """Parse the edit field without localized aliases or enum conversion."""

    del property_name
    if isinstance(original, str):
        return text
    if text.strip() == "":
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text
