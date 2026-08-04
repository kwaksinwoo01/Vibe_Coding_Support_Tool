from pathlib import Path

from word_editor.domain.models import StyleDefinition
from word_editor.infrastructure.editable_word_com import EditableWordComGateway
from word_editor.infrastructure.word_com import WordComGateway


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
