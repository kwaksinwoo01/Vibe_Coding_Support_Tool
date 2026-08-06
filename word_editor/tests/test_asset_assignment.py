from types import SimpleNamespace

from word_editor.services.asset_assignment_service import (
    attach_asset_to_profile,
    detach_asset_from_profile,
)


class FakeLifecycle:
    def __init__(self) -> None:
        self.saved = 0
        self.registry = SimpleNamespace(
            assets={
                "header": SimpleNamespace(asset_id="header"),
            },
            profiles={
                "dcm": SimpleNamespace(asset_ids=[], updated_at=""),
                "fdm": SimpleNamespace(asset_ids=[], updated_at=""),
            },
        )

    def _save_registry(self) -> None:
        self.saved += 1


def test_asset_can_be_shared_across_dcm_and_fdm_profiles() -> None:
    lifecycle = FakeLifecycle()

    assert attach_asset_to_profile(lifecycle, "header", "dcm")
    assert attach_asset_to_profile(lifecycle, "header", "fdm")

    assert lifecycle.registry.profiles["dcm"].asset_ids == ["header"]
    assert lifecycle.registry.profiles["fdm"].asset_ids == ["header"]
    assert lifecycle.saved == 2


def test_duplicate_profile_assignment_is_ignored() -> None:
    lifecycle = FakeLifecycle()

    assert attach_asset_to_profile(lifecycle, "header", "dcm")
    assert not attach_asset_to_profile(lifecycle, "header", "dcm")

    assert lifecycle.registry.profiles["dcm"].asset_ids == ["header"]
    assert lifecycle.saved == 1


def test_asset_can_be_detached_from_profile() -> None:
    lifecycle = FakeLifecycle()
    lifecycle.registry.profiles["dcm"].asset_ids = ["header"]

    assert detach_asset_from_profile(lifecycle, "header", "dcm")
    assert lifecycle.registry.profiles["dcm"].asset_ids == []
