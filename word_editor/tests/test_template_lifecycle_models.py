from word_editor.domain.template_lifecycle import (
    RegisteredTemplateAsset,
    TemplateAssetInventory,
    TemplateChangeReport,
    TemplateProfile,
    TemplateRegistry,
)


def test_registry_round_trip_preserves_profiles_assets_and_active_id() -> None:
    profile = TemplateProfile(
        profile_id="fdm-paper",
        display_name="FDM 종이문서",
        classification_code="FDM",
        canonical_path="C:/managed/fdm/Normal.dotm",
        created_at="2026-08-06T00:00:00+00:00",
        updated_at="2026-08-06T00:00:00+00:00",
        asset_ids=["header-template"],
    )
    asset = RegisteredTemplateAsset(
        asset_id="header-template",
        display_name="회사 머리글 블록",
        role="header-building-block-template",
        managed_path="C:/managed/assets/header.dotm",
        source_path="C:/source/header.dotm",
        created_at="2026-08-06T00:00:00+00:00",
        updated_at="2026-08-06T00:00:00+00:00",
    )
    registry = TemplateRegistry(
        active_profile_id=profile.profile_id,
        profiles={profile.profile_id: profile},
        assets={asset.asset_id: asset},
    )

    restored = TemplateRegistry.from_dict(registry.to_dict())

    assert restored.active_profile_id == "fdm-paper"
    assert restored.profiles["fdm-paper"].classification_code == "FDM"
    assert restored.profiles["fdm-paper"].asset_ids == ["header-template"]
    assert restored.assets["header-template"].role == (
        "header-building-block-template"
    )


def test_inventory_round_trip_preserves_building_blocks_and_autotext() -> None:
    inventory = TemplateAssetInventory(
        source_path="Normal.dotm",
        captured_at="2026-08-06T00:00:00+00:00",
        file_sha256="abc",
        file_size=123,
        styles_sha256="styles",
        building_blocks=[
            {
                "key": "Header|1|Company",
                "name": "Header",
                "type": 1,
                "category": "Company",
            }
        ],
        autotext_entries=["회사명", "문서번호"],
        template_object_found=True,
    )

    restored = TemplateAssetInventory.from_dict(inventory.to_dict())

    assert restored.file_sha256 == "abc"
    assert restored.building_blocks[0]["key"] == "Header|1|Company"
    assert restored.autotext_entries == ["회사명", "문서번호"]
    assert restored.template_object_found is True


def test_change_report_treats_file_hash_only_difference_as_change() -> None:
    report = TemplateChangeReport(
        profile_id="dcm-electronic",
        baseline_path="managed/Normal.dotm",
        current_path="live/Normal.dotm",
        created_at="2026-08-06T00:00:00+00:00",
        baseline_sha256="before",
        current_sha256="after",
    )

    assert report.has_changes
    assert any("파일 변경: True" in line for line in report.summary_lines())


def test_change_report_without_any_difference_is_clean() -> None:
    report = TemplateChangeReport(
        profile_id="dcm-electronic",
        baseline_path="managed/Normal.dotm",
        current_path="live/Normal.dotm",
        created_at="2026-08-06T00:00:00+00:00",
        baseline_sha256="same",
        current_sha256="same",
    )

    assert not report.has_changes
