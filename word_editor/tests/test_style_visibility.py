from word_editor.domain.models import StyleDefinition
from word_editor.ui.style_visibility import belongs_to_hidden_tab


def make_style(
    *,
    hidden: object = False,
    priority: object = None,
) -> StyleDefinition:
    return StyleDefinition(
        name="Test",
        style_type="Paragraph",
        built_in=False,
        in_use=False,
        properties={
            "style.hidden": hidden,
            "style.priority": priority,
        },
    )


def test_priority_one_through_ten_remains_active() -> None:
    for priority in range(1, 11):
        assert not belongs_to_hidden_tab(
            make_style(hidden=False, priority=priority)
        )


def test_priority_eleven_and_above_moves_to_hidden_tab() -> None:
    for priority in (11, 12, 13, 14, 100):
        assert belongs_to_hidden_tab(
            make_style(hidden=False, priority=priority)
        )


def test_hidden_flag_always_moves_style_to_hidden_tab() -> None:
    assert belongs_to_hidden_tab(make_style(hidden=True, priority=1))
    assert belongs_to_hidden_tab(make_style(hidden=-1, priority=10))
    assert belongs_to_hidden_tab(make_style(hidden=1, priority=None))


def test_missing_or_non_numeric_priority_does_not_hide_by_itself() -> None:
    assert not belongs_to_hidden_tab(make_style(hidden=False, priority=None))
    assert not belongs_to_hidden_tab(make_style(hidden=False, priority=""))
    assert not belongs_to_hidden_tab(make_style(hidden=False, priority="unknown"))
