from word_editor.domain.template_lifecycle import TemplateAssetInventory
from word_editor.services.header_footer_review import (
    compare_header_footer_inventories,
)


def inventory(entries):
    return TemplateAssetInventory(
        source_path="HeaderFooter.dotm",
        captured_at="now",
        file_sha256="file",
        file_size=1,
        styles_sha256="styles",
        header_footer_entries=entries,
    )


def test_header_footer_diff_uses_section_kind_and_variant_key() -> None:
    before = inventory(
        [
            {
                "key": "section:1|header|primary",
                "content_sha256": "before",
            },
            {
                "key": "section:1|footer|primary",
                "content_sha256": "same",
            },
        ]
    )
    after = inventory(
        [
            {
                "key": "section:1|header|primary",
                "content_sha256": "after",
            },
            {
                "key": "section:1|footer|primary",
                "content_sha256": "same",
            },
            {
                "key": "section:1|header|first-page",
                "content_sha256": "new",
            },
        ]
    )

    added, removed, changed = compare_header_footer_inventories(before, after)

    assert added == ["section:1|header|first-page"]
    assert removed == []
    assert changed == ["section:1|header|primary"]


def test_old_inventory_without_header_footer_field_is_compatible() -> None:
    restored = TemplateAssetInventory.from_dict(
        {
            "source_path": "legacy.dotm",
            "captured_at": "now",
            "file_sha256": "hash",
            "file_size": 1,
            "styles_sha256": "styles",
        }
    )
    assert restored.header_footer_entries == []
