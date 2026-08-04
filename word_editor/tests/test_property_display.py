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


def test_boolean_values_keep_raw_json_representation() -> None:
    assert format_property_value("style.hidden", True) == "true"
    assert format_property_value("style.hidden", False) == "false"
    assert parse_property_value("style.hidden", "true", False) is True
    assert parse_property_value("style.hidden", "false", True) is False


def test_numeric_values_are_not_localized() -> None:
    assert format_property_value("style.hidden", 1) == "1"
    assert format_property_value("style.hidden", -1) == "-1"
    assert format_property_value("style.hidden", 0) == "0"
    assert format_property_value("paragraph.alignment", 1) == "1"
    assert format_property_value("paragraph.outline_level", 10) == "10"
    assert parse_property_value("paragraph.alignment", "2", 0) == 2


def test_style_type_value_is_not_translated() -> None:
    assert style_type_label("Paragraph") == "Paragraph"
    assert format_property_value("meta.style_type", "Character") == "Character"


def test_strings_and_null_keep_raw_representation() -> None:
    assert format_property_value("font.name", "Arial") == "Arial"
    assert format_property_value("style.base_style", None) == "null"
    assert parse_property_value("style.base_style", "SOP_본문", "") == "SOP_본문"
    assert parse_property_value("font.size_pt", "", 10) is None


def test_unknown_property_keeps_internal_key_as_fallback() -> None:
    assert property_label("custom.value") == "custom.value"
