import pytest

from word_editor.domain.models import StyleDefinition, TemplateSnapshot
from word_editor.domain.style_mutation import validate_new_style_name


def test_style_name_is_unique_case_insensitively() -> None:
    current = TemplateSnapshot(
        source_path="Normal.dotm",
        sha256="hash",
        captured_at="now",
        word_version="16",
        styles={
            "SOP_본문": StyleDefinition(
                name="SOP_본문",
                style_type="Paragraph",
                built_in=False,
                in_use=False,
            )
        },
    )
    with pytest.raises(ValueError):
        validate_new_style_name(current, "sop_본문")
    assert validate_new_style_name(current, "SOP_새본문") == "SOP_새본문"
