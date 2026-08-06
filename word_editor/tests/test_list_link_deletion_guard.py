from word_editor.domain.models import StyleDefinition, TemplateSnapshot
from word_editor.domain.style_mutation import delete_style_blockers


def test_list_template_link_blocks_style_deletion() -> None:
    target = StyleDefinition(
        name="SOP_목록1",
        style_type="Paragraph",
        built_in=False,
        in_use=False,
    )
    snapshot = TemplateSnapshot(
        source_path="Normal.dotm",
        sha256="hash",
        captured_at="now",
        word_version="16",
        styles={target.name: target},
        list_templates={
            "1": {
                "name": "SOP 다단계",
                "levels": {
                    "1": {"linked_style": "SOP_목록1"},
                },
            }
        },
    )

    blockers = delete_style_blockers(snapshot, ("SOP_목록1",))

    assert blockers
    assert "목록 템플릿" in blockers[0].referenced_by[0]
