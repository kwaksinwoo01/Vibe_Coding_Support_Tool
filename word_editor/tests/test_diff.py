from __future__ import annotations

from word_editor.domain.diff import three_way_merge
from word_editor.domain.models import StyleDefinition, TemplateSnapshot


def snapshot(sha: str, value: int) -> TemplateSnapshot:
    return TemplateSnapshot(
        source_path="Normal.dotm",
        sha256=sha,
        captured_at="2026-07-31T00:00:00+00:00",
        word_version="16.0",
        styles={
            "SOP_본문": StyleDefinition(
                name="SOP_본문",
                style_type="Paragraph",
                built_in=False,
                in_use=True,
                properties={"paragraph.space_after_pt": value},
            )
        },
    )


def test_document_only_change_is_automatic() -> None:
    plan = three_way_merge(snapshot("b", 6), snapshot("n", 6), snapshot("d", 8))
    assert not plan.conflicts
    assert plan.automatic_values["SOP_본문"]["paragraph.space_after_pt"] == 8


def test_normal_only_change_is_automatic() -> None:
    plan = three_way_merge(snapshot("b", 6), snapshot("n", 4), snapshot("d", 6))
    assert not plan.conflicts
    assert plan.automatic_values["SOP_본문"]["paragraph.space_after_pt"] == 4


def test_different_changes_create_conflict() -> None:
    plan = three_way_merge(snapshot("b", 6), snapshot("n", 4), snapshot("d", 8))
    assert len(plan.conflicts) == 1
    conflict = plan.conflicts[0]
    assert conflict.style_name == "SOP_본문"
    assert conflict.baseline_value == 6
    assert conflict.normal_value == 4
    assert conflict.document_value == 8
