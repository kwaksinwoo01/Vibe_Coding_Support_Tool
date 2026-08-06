from __future__ import annotations

from word_editor.domain.template_lifecycle import utc_now_iso
from word_editor.services.template_lifecycle_service import (
    TemplateLifecycleError,
    TemplateLifecycleService,
)


def attach_asset_to_profile(
    lifecycle: TemplateLifecycleService,
    asset_id: str,
    profile_id: str,
) -> bool:
    try:
        asset = lifecycle.registry.assets[asset_id]
    except KeyError as exc:
        raise TemplateLifecycleError(
            f"등록 템플릿 자산을 찾지 못했습니다: {asset_id}"
        ) from exc
    try:
        profile = lifecycle.registry.profiles[profile_id]
    except KeyError as exc:
        raise TemplateLifecycleError(
            f"템플릿 프로필을 찾지 못했습니다: {profile_id}"
        ) from exc

    if asset.asset_id in profile.asset_ids:
        return False
    profile.asset_ids.append(asset.asset_id)
    profile.asset_ids.sort(key=str.casefold)
    profile.updated_at = utc_now_iso()
    lifecycle._save_registry()
    return True


def detach_asset_from_profile(
    lifecycle: TemplateLifecycleService,
    asset_id: str,
    profile_id: str,
) -> bool:
    try:
        profile = lifecycle.registry.profiles[profile_id]
    except KeyError as exc:
        raise TemplateLifecycleError(
            f"템플릿 프로필을 찾지 못했습니다: {profile_id}"
        ) from exc
    if asset_id not in profile.asset_ids:
        return False
    profile.asset_ids.remove(asset_id)
    profile.updated_at = utc_now_iso()
    lifecycle._save_registry()
    return True
