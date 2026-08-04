from word_editor.domain.models import StyleDefinition
from word_editor.domain.property_policy import (
    common_property_names,
    common_property_policy,
    property_policy,
)


def style(
    name: str,
    style_type: str,
    *,
    built_in: bool = False,
    properties: dict[str, object] | None = None,
) -> StyleDefinition:
    return StyleDefinition(
        name=name,
        style_type=style_type,
        built_in=built_in,
        in_use=False,
        properties=properties or {},
    )


def test_character_style_cannot_edit_paragraph_property() -> None:
    target = style(
        "강한 강조",
        "Character",
        built_in=True,
        properties={"paragraph.space_after_pt": None},
    )
    policy = property_policy(target, "paragraph.space_after_pt")
    assert not policy.editable
    assert "문단" in policy.reason


def test_builtin_style_structural_properties_are_locked() -> None:
    target = style(
        "표준",
        "Paragraph",
        built_in=True,
        properties={
            "style.base_style": "",
            "style.next_style": "표준",
        },
    )
    assert not property_policy(target, "style.base_style").editable
    assert not property_policy(target, "style.next_style").editable


def test_custom_paragraph_style_allows_safe_properties() -> None:
    target = style(
        "SOP_본문",
        "Paragraph",
        properties={
            "font.size_pt": 10,
            "paragraph.space_after_pt": 6,
            "style.base_style": "",
        },
    )
    assert property_policy(target, "font.size_pt").editable
    assert property_policy(target, "paragraph.space_after_pt").editable
    assert property_policy(target, "style.base_style").editable


def test_common_properties_are_intersection_only() -> None:
    first = style(
        "A",
        "Paragraph",
        properties={"font.size_pt": 10, "paragraph.alignment": 0},
    )
    second = style(
        "B",
        "Character",
        properties={"font.size_pt": 11, "font.bold": False},
    )
    assert common_property_names([first, second]) == ["font.size_pt"]


def test_common_policy_blocks_if_any_selected_style_is_incompatible() -> None:
    paragraph = style(
        "A",
        "Paragraph",
        properties={"paragraph.alignment": 0},
    )
    character = style(
        "B",
        "Character",
        properties={"paragraph.alignment": None},
    )
    policy = common_property_policy(
        [paragraph, character],
        "paragraph.alignment",
    )
    assert not policy.editable
