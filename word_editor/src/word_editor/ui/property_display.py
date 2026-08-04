from __future__ import annotations

import json
from typing import Any

from word_editor.domain.models import (
    BOOLEAN_PROPERTY_NAMES,
    normalize_word_boolean,
)

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

BOOLEAN_DISPLAY_PROPERTIES = BOOLEAN_PROPERTY_NAMES | frozenset(
    {"meta.built_in", "meta.in_use"}
)

STYLE_TYPE_LABELS = {
    "Paragraph": "문단 스타일",
    "Character": "문자 스타일",
    "Table": "표 스타일",
    "List": "목록 스타일",
    "ParagraphOnly": "문단 전용 스타일",
    "Linked": "연결 스타일",
    "Unknown": "알 수 없음",
}

ENUM_VALUE_LABELS: dict[str, dict[int, str]] = {
    "paragraph.alignment": {
        0: "왼쪽 맞춤",
        1: "가운데 맞춤",
        2: "오른쪽 맞춤",
        3: "양쪽 맞춤",
        4: "균등 분할",
        5: "중간 양쪽 맞춤",
        6: "넓은 양쪽 맞춤",
        7: "좁은 양쪽 맞춤",
        8: "태국어 양쪽 맞춤",
    },
    "paragraph.line_spacing_rule": {
        0: "한 줄",
        1: "1.5줄",
        2: "두 줄",
        3: "최소",
        4: "고정",
        5: "배수",
    },
    "paragraph.outline_level": {
        1: "수준 1",
        2: "수준 2",
        3: "수준 3",
        4: "수준 4",
        5: "수준 5",
        6: "수준 6",
        7: "수준 7",
        8: "수준 8",
        9: "수준 9",
        10: "본문 텍스트",
    },
    "font.underline": {
        0: "없음",
        1: "한 줄",
        2: "단어만",
        3: "두 줄",
        4: "점선",
        6: "굵은 선",
        7: "파선",
        9: "일점쇄선",
        10: "이점쇄선",
        11: "물결선",
        27: "굵은 물결선",
        43: "두 줄 물결선",
    },
}


def property_label(property_name: str) -> str:
    return PROPERTY_LABELS.get(property_name, property_name)


def style_type_label(value: str) -> str:
    return STYLE_TYPE_LABELS.get(value, value)


def format_property_value(property_name: str, value: Any) -> str:
    if value is None:
        return "없음"
    if property_name in BOOLEAN_DISPLAY_PROPERTIES:
        normalized = normalize_word_boolean(value)
        if isinstance(normalized, bool):
            return "예" if normalized else "아니오"
    if isinstance(value, bool):
        return "예" if value else "아니오"
    if property_name == "meta.style_type" and isinstance(value, str):
        return style_type_label(value)
    enum_values = ENUM_VALUE_LABELS.get(property_name)
    if enum_values is not None:
        try:
            integer = int(value)
        except (TypeError, ValueError):
            pass
        else:
            if integer in enum_values:
                return enum_values[integer]
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False)


def parse_property_value(property_name: str, text: str, original: Any) -> Any:
    stripped = text.strip()
    if property_name in BOOLEAN_DISPLAY_PROPERTIES or isinstance(original, bool):
        lowered = stripped.casefold()
        if lowered in {"예", "참", "true", "yes", "1", "-1"}:
            return True
        if lowered in {"아니오", "거짓", "false", "no", "0"}:
            return False
    if original is None and stripped.casefold() in {"", "없음", "null", "none"}:
        return None
    enum_values = ENUM_VALUE_LABELS.get(property_name)
    if enum_values is not None:
        reverse = {label.casefold(): value for value, label in enum_values.items()}
        if stripped.casefold() in reverse:
            return reverse[stripped.casefold()]
    if isinstance(original, str):
        return text
    if stripped == "":
        return None
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        return text
