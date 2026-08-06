from word_editor.domain.models import StyleDefinition, TemplateSnapshot
from word_editor.domain.style_mutation import delete_style_blockers


def make_style(
    name: str,
    *,
    built_in: bool = False,
    base_style: str = "",
) -> StyleDefinition:
    return StyleDefinition(
        name=name,
        style_type="Paragraph",
        built_in=built_in,
        in_use=False,
        properties={
            "style.base_style": base_style,
            "style.next_style": "",
        },
    )


def test_builtin_style_is_guarded() -> None:
    normal = make_style("표준", built_in=True)
    snapshot = TemplateSnapshot(
        source_path="Normal.dotm",
        sha256="hash",
        captured_at="now",
        word_version="16",
        styles={normal.name: normal},
        metadata={"default_paragraph_style": "표준"},
    )
    assert delete_style_blockers(snapshot, ("표준",))


def test_referenced_style_is_guarded() -> None:
    base = make_style("SOP_기준")
    body = make_style("SOP_본문", base_style="SOP_기준")
    snapshot = TemplateSnapshot(
        source_path="Normal.dotm",
        sha256="hash",
        captured_at="now",
        word_version="16",
        styles={base.name: base, body.name: body},
    )
    blockers = delete_style_blockers(snapshot, ("SOP_기준",))
    assert blockers[0].referenced_by == ("SOP_본문.style.base_style",)
