from word_editor.ui.property_display import (
    format_property_value,
    parse_property_value,
    property_label,
    style_type_label,
)


def test_property_keys_have_korean_labels() -> None:
    assert property_label("font.size_pt") == "글꼴 크기(pt)"
    assert property_label("paragraph.alignment") == "문단 정렬"
    assert property_label("style.hidden") == "스타일 숨김"


def test_boolean_values_are_localized_and_parse_back() -> None:
    assert format_property_value("style.hidden", True) == "예"
    assert format_property_value("style.hidden", False) == "아니오"
    assert parse_property_value("style.hidden", "예", False) is True
    assert parse_property_value("style.hidden", "아니오", True) is False


def test_word_boolean_integer_variants_are_normalized_for_display() -> None:
    assert format_property_value("style.hidden", 1) == "예"
    assert format_property_value("style.hidden", -1) == "예"
    assert format_property_value("style.hidden", 0) == "아니오"
    assert parse_property_value("style.hidden", "1", 0) is True
    assert parse_property_value("style.hidden", "-1", 0) is True
    assert parse_property_value("style.hidden", "0", 1) is False


def test_enum_values_are_localized_and_parse_back() -> None:
    assert format_property_value("paragraph.alignment", 1) == "가운데 맞춤"
    assert parse_property_value(
        "paragraph.alignment",
        "오른쪽 맞춤",
        0,
    ) == 2
    assert format_property_value(
        "paragraph.outline_level",
        10,
    ) == "본문 텍스트"


def test_style_type_is_localized() -> None:
    assert style_type_label("Paragraph") == "문단 스타일"
    assert format_property_value(
        "meta.style_type",
        "Character",
    ) == "문자 스타일"


def test_unknown_property_keeps_internal_key_as_fallback() -> None:
    assert property_label("custom.value") == "custom.value"
