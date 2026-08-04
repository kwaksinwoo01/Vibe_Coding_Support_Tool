from pathlib import Path

import pytest

from word_editor.domain.models import StyleDefinition
from word_editor.infrastructure.editable_word_com import EditableWordComGateway
from word_editor.infrastructure.word_com import WordComGateway, WordGatewayError


class _FakeStyle:
    def __init__(self, name: str) -> None:
        self.NameLocal = name
        self.NextParagraphStyle = None
        self.BaseStyle = None


class _IndexOnlyStyles:
    """Mimic Word collections that reject a valid custom name in Item()."""

    def __init__(self, *styles: _FakeStyle) -> None:
        self._styles = styles
        self.Count = len(styles)

    def Item(self, index: int) -> _FakeStyle:
        if not isinstance(index, int):
            raise AssertionError("String lookup must not be used")
        return self._styles[index - 1]


def test_target_backup_is_a_byte_for_byte_file_copy(tmp_path: Path) -> None:
    target = tmp_path / "Normal.dotm"
    target.write_bytes(b"word-template-content")
    backup_directory = tmp_path / "backups"
    gateway = EditableWordComGateway(target, backup_directory)

    backup = gateway._make_target_backup(None, target)

    assert backup.parent == backup_directory
    assert backup.suffix == ".dotm"
    assert backup.read_bytes() == target.read_bytes()


def test_styles_hash_ignores_unrelated_list_template_state() -> None:
    styles = {
        "Normal": StyleDefinition(
            name="Normal",
            style_type="Paragraph",
            built_in=True,
            in_use=True,
            properties={"font.bold": False},
        )
    }

    styles_hash = WordComGateway._styles_hash(styles)
    first_snapshot_hash = WordComGateway._snapshot_hash(
        styles,
        {"001": {"name": "first"}},
    )
    second_snapshot_hash = WordComGateway._snapshot_hash(
        styles,
        {"001": {"name": "second"}},
    )

    assert first_snapshot_hash != second_snapshot_hash
    assert WordComGateway._styles_hash(styles) == styles_hash


def test_next_style_uses_resolved_com_object_instead_of_name(
    tmp_path: Path,
) -> None:
    source = _FakeStyle("SOP_머리글_지우기")
    collection = _IndexOnlyStyles(source)
    gateway = WordComGateway(
        tmp_path / "Normal.dotm",
        tmp_path / "backups",
    )
    style_index = gateway._build_style_object_index(collection)

    resolved_source = gateway._resolve_style_object(
        style_index,
        "SOP_머리글_지우기",
        context="Patch operation",
    )
    gateway._set_property(
        resolved_source,
        "style.next_style",
        "SOP_머리글_지우기",
        style_index,
    )

    assert source.NextParagraphStyle is source


def test_missing_style_reference_fails_before_word_assignment(
    tmp_path: Path,
) -> None:
    source = _FakeStyle("SOP_머리글_지우기")
    collection = _IndexOnlyStyles(source)
    gateway = WordComGateway(
        tmp_path / "Normal.dotm",
        tmp_path / "backups",
    )
    style_index = gateway._build_style_object_index(collection)

    with pytest.raises(WordGatewayError, match="not present"):
        gateway._set_property(
            source,
            "style.next_style",
            "존재하지_않는_스타일",
            style_index,
        )


def test_base_style_uses_resolved_com_object(tmp_path: Path) -> None:
    source = _FakeStyle("SOP_본문")
    base = _FakeStyle("표준")
    collection = _IndexOnlyStyles(source, base)
    gateway = WordComGateway(
        tmp_path / "Normal.dotm",
        tmp_path / "backups",
    )
    style_index = gateway._build_style_object_index(collection)

    gateway._set_property(
        source,
        "style.base_style",
        "표준",
        style_index,
    )

    assert source.BaseStyle is base
