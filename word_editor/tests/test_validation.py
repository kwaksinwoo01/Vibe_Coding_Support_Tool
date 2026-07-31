from __future__ import annotations

from word_editor.domain.models import StyleDefinition, TemplateSnapshot
from word_editor.domain.validation import validate_snapshot


def test_invalid_size_and_missing_reference_are_reported() -> None:
    snapshot = TemplateSnapshot(
        source_path="Normal.dotm",
        sha256="abc",
        captured_at="2026-07-31T00:00:00+00:00",
        word_version="16.0",
        styles={
            "SOP_본문": StyleDefinition(
                name="SOP_본문",
                style_type="Paragraph",
                built_in=False,
                in_use=True,
                properties={
                    "style.base_style": "없는 스타일",
                    "font.size_pt": 0,
                },
            )
        },
    )
    issues = validate_snapshot(snapshot)
    messages = {issue.message for issue in issues}
    assert any("Referenced style" in message for message in messages)
    assert any("outside" in message for message in messages)


def test_valid_minimal_snapshot_has_no_errors() -> None:
    snapshot = TemplateSnapshot(
        source_path="Normal.dotm",
        sha256="abc",
        captured_at="2026-07-31T00:00:00+00:00",
        word_version="16.0",
        styles={
            "SOP_본문": StyleDefinition(
                name="SOP_본문",
                style_type="Paragraph",
                built_in=False,
                in_use=True,
                properties={"font.size_pt": 10},
            )
        },
    )
    errors = [issue for issue in validate_snapshot(snapshot) if issue.severity.value == "error"]
    assert errors == []
