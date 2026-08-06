from pathlib import Path
from types import SimpleNamespace

import pytest

from word_editor.services.audited_distribution_service import (
    _installer_script,
    _validate_unique_asset_file_names,
)
from word_editor.services.template_lifecycle_service import TemplateLifecycleError


def fake_lifecycle(asset_names: list[str]) -> SimpleNamespace:
    profile = SimpleNamespace(
        asset_ids=[f"asset-{index}" for index in range(len(asset_names))]
    )
    assets = {
        f"asset-{index}": SimpleNamespace(
            asset_id=f"asset-{index}",
            managed_path=str(Path("C:/managed") / file_name),
        )
        for index, file_name in enumerate(asset_names)
    }
    return SimpleNamespace(
        registry=SimpleNamespace(
            profiles={"fdm": profile},
            assets=assets,
        )
    )


def test_global_template_installer_uses_startup_root_directly() -> None:
    script = _installer_script("a" * 64)

    assert '"Microsoft\\Word\\STARTUP"' in script
    assert "STARTUP\\CompanyTemplates" not in script
    assert "before-company-$stamp.bak" in script


def test_duplicate_asset_file_names_are_rejected_case_insensitively() -> None:
    lifecycle = fake_lifecycle(["Header.dotm", "header.DOTM"])

    with pytest.raises(TemplateLifecycleError):
        _validate_unique_asset_file_names(lifecycle, "fdm")


def test_distinct_asset_file_names_are_allowed() -> None:
    lifecycle = fake_lifecycle(["Header.dotm", "Footer.dotm"])

    _validate_unique_asset_file_names(lifecycle, "fdm")
