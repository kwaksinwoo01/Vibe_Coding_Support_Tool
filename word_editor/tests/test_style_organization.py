from word_editor.domain.models import StyleDefinition
from word_editor.ui.style_organization import organize_styles


def make_style(
    name: str,
    *,
    priority: int | None,
    hidden: bool,
) -> StyleDefinition:
    return StyleDefinition(
        name=name,
        style_type="Paragraph",
        built_in=False,
        in_use=False,
        properties={
            "style.priority": priority,
            "style.hidden": hidden,
        },
    )


def test_priority_sort_places_lower_priority_first_then_name() -> None:
    styles = [
        make_style("나", priority=3, hidden=False),
        make_style("가", priority=3, hidden=False),
        make_style("다", priority=1, hidden=False),
        make_style("라", priority=None, hidden=False),
    ]
    active, hidden = organize_styles(styles, "priority")
    assert [style.name for style in active] == ["다", "가", "나", "라"]
    assert hidden == []


def test_name_sort_and_hidden_grouping_are_independent() -> None:
    styles = [
        make_style("다", priority=1, hidden=True),
        make_style("가", priority=9, hidden=False),
        make_style("나", priority=2, hidden=True),
    ]
    active, hidden = organize_styles(styles, "name")
    assert [style.name for style in active] == ["가"]
    assert [style.name for style in hidden] == ["나", "다"]
