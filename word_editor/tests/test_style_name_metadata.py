from word_editor.domain.models import StyleDefinition, TemplateSnapshot


def test_old_snapshot_without_name_metadata_remains_readable() -> None:
    style = StyleDefinition.from_dict(
        {
            "name": "표준",
            "style_type": "Paragraph",
            "built_in": True,
            "in_use": True,
            "properties": {},
            "list_binding": {},
        }
    )
    assert style.local_name == "표준"
    assert style.original_name == "표준"
    assert style.built_in_id is None


def test_new_name_metadata_round_trips() -> None:
    original = StyleDefinition(
        name="제목 1",
        original_name="Heading 1",
        built_in_id=-2,
        style_type="Paragraph",
        built_in=True,
        in_use=True,
        properties={"font.size_pt": 14},
    )
    restored = StyleDefinition.from_dict(original.to_dict())
    assert restored.local_name == "제목 1"
    assert restored.original_name == "Heading 1"
    assert restored.built_in_id == -2


def test_snapshot_schema_is_upgraded_without_losing_styles() -> None:
    snapshot = TemplateSnapshot(
        source_path="Normal.dotm",
        sha256="abc",
        captured_at="now",
        word_version="16.0",
        styles={
            "표준": StyleDefinition(
                name="표준",
                original_name="Normal",
                built_in_id=-1,
                style_type="Paragraph",
                built_in=True,
                in_use=True,
            )
        },
    )
    payload = snapshot.to_dict()
    assert payload["schema_version"] == 2
    restored = TemplateSnapshot.from_dict(payload)
    assert restored.styles["표준"].original_name == "Normal"
