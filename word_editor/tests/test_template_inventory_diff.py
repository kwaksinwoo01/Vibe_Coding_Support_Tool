from word_editor.domain.template_lifecycle import TemplateAssetInventory
from word_editor.services.template_lifecycle_service import (
    compare_template_inventories,
)


def inventory(
    *,
    value_hash: str,
    value_length: int,
) -> TemplateAssetInventory:
    return TemplateAssetInventory(
        source_path="HeaderBlocks.dotm",
        captured_at="2026-08-06T00:00:00+00:00",
        file_sha256="file",
        file_size=100,
        styles_sha256="styles",
        building_blocks=[
            {
                "key": "회사 머리글|1|Company",
                "name": "회사 머리글",
                "type": 1,
                "category": "Company",
                "description": "표준 머리글",
                "insert_options": 0,
                "value_sha256": value_hash,
                "value_length": value_length,
            }
        ],
        autotext_entries=[],
        template_object_found=True,
    )


def test_same_building_block_name_with_changed_content_is_reported() -> None:
    baseline = inventory(value_hash="before", value_length=20)
    current = inventory(value_hash="after", value_length=24)

    added, removed, changed, added_autotext, removed_autotext = (
        compare_template_inventories(baseline, current)
    )

    assert added == []
    assert removed == []
    assert changed == ["회사 머리글|1|Company"]
    assert added_autotext == []
    assert removed_autotext == []


def test_unchanged_building_block_fingerprint_is_clean() -> None:
    baseline = inventory(value_hash="same", value_length=20)
    current = inventory(value_hash="same", value_length=20)

    _, _, changed, _, _ = compare_template_inventories(baseline, current)

    assert changed == []
